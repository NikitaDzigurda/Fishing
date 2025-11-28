"""
Парсер Scopus API (Elsevier)

Документация: https://dev.elsevier.com/documentation/SCOPUSSearchAPI.wadl
Получить API ключ: https://dev.elsevier.com/apikey/manage
"""

import asyncio
import aiohttp
import re
from datetime import datetime
from typing import Optional, Any
from urllib.parse import urlparse, parse_qs

from ..base import BaseParser, ProgressCallback
from ..models import (
    AuthorProfile, Publication, Author, CoAuthor,
    Metrics, ExternalIds, SourceType
)


class ScopusAPIError(Exception):
    """Ошибка Scopus API"""
    pass


class ScopusRateLimitError(ScopusAPIError):
    """Превышен лимит запросов"""
    pass


class ScopusAuthError(ScopusAPIError):
    """Ошибка авторизации"""
    pass


class ScopusParser(BaseParser):
    """
    Парсер Scopus API

    Лимиты:
    - 20,000 запросов в неделю (бесплатный tier)
    - 2 запроса в секунду

    Пример:
        async with ScopusParser(api_key="your-key") as parser:
            profile = await parser.get_author_profile(author_id="7004367821")
    """

    source = SourceType.SCOPUS

    # API endpoints
    BASE_URL = "https://api.elsevier.com/content"
    SEARCH_URL = f"{BASE_URL}/search/scopus"
    AUTHOR_URL = f"{BASE_URL}/author/author_id"
    AUTHOR_SEARCH_URL = f"{BASE_URL}/search/author"
    ABSTRACT_URL = f"{BASE_URL}/abstract/scopus_id"

    # Лимиты
    RATE_LIMIT = 0.5  # 2 запроса в секунду
    BATCH_SIZE = 25  # Максимум результатов за запрос
    MAX_RETRIES = 3
    RETRY_DELAY = 5

    def __init__(self, api_key: str, inst_token: Optional[str] = None):
        """
        Args:
            api_key: API ключ от Elsevier (обязательно)
            inst_token: Institutional token (опционально, для расширенного доступа)
        """
        super().__init__()

        if not api_key:
            raise ValueError(
                "Scopus API key is required. "
                "Get one at https://dev.elsevier.com/apikey/manage"
            )

        self.api_key = api_key
        self.inst_token = inst_token
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def init(self):
        headers = {
            "X-ELS-APIKey": self.api_key,
            "Accept": "application/json",
            "User-Agent": "AcademicAPI/1.0"
        }

        if self.inst_token:
            headers["X-ELS-Insttoken"] = self.inst_token

        timeout = aiohttp.ClientTimeout(total=60)
        self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rate_limit_wait(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request
            if elapsed < self.RATE_LIMIT:
                await asyncio.sleep(self.RATE_LIMIT - elapsed)
            self._last_request = asyncio.get_event_loop().time()

    async def _get(
            self,
            url: str,
            params: dict = None,
            retries: int = 0
    ) -> dict:
        """GET запрос с retry логикой"""
        await self._rate_limit_wait()

        try:
            async with self._session.get(url, params=params) as response:
                # Обработка ошибок
                if response.status == 429:
                    if retries < self.MAX_RETRIES:
                        delay = self.RETRY_DELAY * (2 ** retries)
                        print(f"\n⚠️  Rate limit. Waiting {delay}s...")
                        await asyncio.sleep(delay)
                        return await self._get(url, params, retries + 1)
                    raise ScopusRateLimitError("Rate limit exceeded")

                if response.status == 401:
                    raise ScopusAuthError("Invalid API key")

                if response.status == 403:
                    raise ScopusAuthError(
                        "Access forbidden. Check your API key permissions or institutional access."
                    )

                if response.status == 404:
                    return {}

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientResponseError as e:
            if e.status == 429 and retries < self.MAX_RETRIES:
                delay = self.RETRY_DELAY * (2 ** retries)
                print(f"\n⚠️  Rate limit (429). Waiting {delay}s...")
                await asyncio.sleep(delay)
                return await self._get(url, params, retries + 1)
            raise ScopusAPIError(f"API error: {e}")

    @classmethod
    def parse_url(cls, url: str) -> dict:
        """
        Парсинг URL Scopus

        Форматы:
        - https://www.scopus.com/authid/detail.uri?authorId=7004367821
        - https://www.scopus.com/record/display.uri?eid=2-s2.0-84924355884
        """
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        # Author ID
        if "authorId" in params:
            return {"author_id": params["authorId"][0], "type": "author"}

        # Scopus ID (EID)
        if "eid" in params:
            return {"scopus_id": params["eid"][0], "type": "paper"}

        # Попробуем найти ID в пути
        author_match = re.search(r"authorId[=/](\d+)", url)
        if author_match:
            return {"author_id": author_match.group(1), "type": "author"}

        raise ValueError(f"Cannot parse Scopus URL: {url}")

    def _parse_author_from_entry(self, entry: dict) -> Author:
        """Парсинг автора из записи"""

        # Получаем имя
        preferred_name = entry.get("preferred-name", {})
        name = f"{preferred_name.get('given-name', '')} {preferred_name.get('surname', '')}".strip()

        if not name:
            name = entry.get("authname", "Unknown")

        # Аффилиация
        affiliation = None
        aff_current = entry.get("affiliation-current", {})
        if aff_current:
            affiliation = aff_current.get("affiliation-name")

        return Author(
            name=name,
            author_id=entry.get("dc:identifier", "").replace("AUTHOR_ID:", ""),
            orcid=entry.get("orcid"),
            affiliation=affiliation,
            source=SourceType.SCOPUS
        )

    def _parse_publication(self, entry: dict) -> Publication:
        """Преобразование записи Scopus в Publication"""

        # Авторы
        authors = []
        author_list = entry.get("author", [])
        if isinstance(author_list, dict):
            author_list = [author_list]

        for a in author_list:
            name = a.get("authname", "")
            if not name:
                given = a.get("given-name", "")
                surname = a.get("surname", "")
                name = f"{given} {surname}".strip()

            authors.append(Author(
                name=name,
                author_id=a.get("authid"),
                source=SourceType.SCOPUS
            ))

        # Если авторов нет, пробуем другое поле
        if not authors:
            creator = entry.get("dc:creator")
            if creator:
                authors.append(Author(name=creator, source=SourceType.SCOPUS))

        # Год
        year = None
        cover_date = entry.get("prism:coverDate", "")
        if cover_date:
            try:
                year = int(cover_date.split("-")[0])
            except (ValueError, IndexError):
                pass

        # Scopus ID (EID)
        eid = entry.get("eid", "")
        scopus_id = entry.get("dc:identifier", "").replace("SCOPUS_ID:", "")

        # External IDs
        external_ids = ExternalIds(
            doi=entry.get("prism:doi"),
            pubmed_id=entry.get("pubmed-id"),
            scopus_id=scopus_id or eid
        )

        # Тип публикации
        doc_type = entry.get("subtypeDescription", entry.get("prism:aggregationType", ""))
        venue_type = None
        if doc_type:
            type_map = {
                "Article": "journal",
                "Conference Paper": "conference",
                "Review": "journal",
                "Book Chapter": "book_chapter",
                "Book": "book",
                "Editorial": "journal",
                "Letter": "journal",
                "Note": "journal",
                "Short Survey": "journal"
            }
            venue_type = type_map.get(doc_type, "other")

        # Ссылки
        url = None
        for link in entry.get("link", []):
            if link.get("@ref") == "scopus":
                url = link.get("@href")
                break

        return Publication(
            title=entry.get("dc:title", ""),
            authors=authors,
            year=year,
            source=SourceType.SCOPUS,
            source_id=eid or scopus_id,
            external_ids=external_ids,
            abstract=entry.get("dc:description"),
            venue=entry.get("prism:publicationName"),
            venue_type=venue_type,
            publisher=entry.get("prism:publisher"),
            volume=entry.get("prism:volume"),
            issue=entry.get("prism:issueIdentifier"),
            pages=entry.get("prism:pageRange"),
            citation_count=int(entry.get("citedby-count", 0)),
            url=url,
            is_open_access=entry.get("openaccess", "0") == "1",
            keywords=entry.get("authkeywords", "").split(" | ") if entry.get("authkeywords") else [],
            raw_data=entry
        )

    async def search_authors(self, query: str, limit: int = 10) -> list[AuthorProfile]:
        """
        Поиск авторов

        Args:
            query: Имя автора
            limit: Максимум результатов
        """
        params = {
            "query": f"AUTHLASTNAME({query}) OR AUTHFIRST({query})",
            "count": min(limit, 25),
            "start": 0
        }

        data = await self._get(self.AUTHOR_SEARCH_URL, params)

        results = data.get("search-results", {})
        entries = results.get("entry", [])

        if isinstance(entries, dict):
            entries = [entries]

        profiles = []
        for entry in entries:
            # Пропускаем ошибки
            if entry.get("error"):
                continue

            preferred_name = entry.get("preferred-name", {})
            name = f"{preferred_name.get('given-name', '')} {preferred_name.get('surname', '')}".strip()

            if not name:
                name = entry.get("dc:identifier", "Unknown")

            author_id = entry.get("dc:identifier", "").replace("AUTHOR_ID:", "")

            # Аффилиация
            affiliation = None
            aff_current = entry.get("affiliation-current", {})
            if aff_current:
                affiliation = aff_current.get("affiliation-name")

            # Области исследований
            subject_areas = []
            for area in entry.get("subject-area", []):
                if isinstance(area, dict):
                    subject_areas.append(area.get("$", ""))

            profiles.append(AuthorProfile(
                name=name,
                source=SourceType.SCOPUS,
                source_id=author_id,
                orcid=entry.get("orcid"),
                affiliation=affiliation,
                interests=subject_areas[:10],
                metrics=Metrics(
                    citation_count=int(entry.get("citedby-count", 0)),
                    publication_count=int(entry.get("document-count", 0))
                ),
                url=f"https://www.scopus.com/authid/detail.uri?authorId={author_id}"
            ))

        return profiles

    async def search_publications(
            self,
            query: str,
            limit: int = 25,
            year_start: Optional[int] = None,
            year_end: Optional[int] = None
    ) -> list[Publication]:
        """
        Поиск публикаций

        Args:
            query: Поисковый запрос
            limit: Максимум результатов
            year_start: Начальный год
            year_end: Конечный год
        """
        # Формируем запрос
        search_query = query

        if year_start or year_end:
            year_filter = ""
            if year_start and year_end:
                year_filter = f"PUBYEAR > {year_start - 1} AND PUBYEAR < {year_end + 1}"
            elif year_start:
                year_filter = f"PUBYEAR > {year_start - 1}"
            elif year_end:
                year_filter = f"PUBYEAR < {year_end + 1}"

            search_query = f"({query}) AND {year_filter}"

        params = {
            "query": search_query,
            "count": min(limit, self.BATCH_SIZE),
            "start": 0,
            "sort": "-citedby-count"  # Сортировка по цитированиям
        }

        data = await self._get(self.SEARCH_URL, params)

        results = data.get("search-results", {})
        entries = results.get("entry", [])

        if isinstance(entries, dict):
            entries = [entries]

        publications = []
        for entry in entries:
            if entry.get("error"):
                continue
            publications.append(self._parse_publication(entry))

        return publications

    async def get_publication(self, publication_id: str) -> Publication:
        """
        Получить публикацию по Scopus ID или EID

        Args:
            publication_id: Scopus ID или EID (например, "2-s2.0-84924355884")
        """
        # Определяем тип ID
        if publication_id.startswith("2-s2.0-"):
            url = f"{self.ABSTRACT_URL}/{publication_id}"
        else:
            url = f"{self.BASE_URL}/abstract/scopus_id/{publication_id}"

        data = await self._get(url)

        abstract_response = data.get("abstracts-retrieval-response", {})
        coredata = abstract_response.get("coredata", {})

        if not coredata:
            raise ScopusAPIError(f"Publication not found: {publication_id}")

        # Получаем авторов
        authors = []
        author_group = abstract_response.get("authors", {}).get("author", [])
        if isinstance(author_group, dict):
            author_group = [author_group]

        for a in author_group:
            preferred = a.get("preferred-name", {})
            name = f"{preferred.get('ce:given-name', '')} {preferred.get('ce:surname', '')}".strip()
            authors.append(Author(
                name=name,
                author_id=a.get("@auid"),
                source=SourceType.SCOPUS
            ))

        # Год
        year = None
        cover_date = coredata.get("prism:coverDate", "")
        if cover_date:
            try:
                year = int(cover_date.split("-")[0])
            except:
                pass

        return Publication(
            title=coredata.get("dc:title", ""),
            authors=authors,
            year=year,
            source=SourceType.SCOPUS,
            source_id=coredata.get("eid"),
            external_ids=ExternalIds(
                doi=coredata.get("prism:doi"),
                scopus_id=coredata.get("dc:identifier", "").replace("SCOPUS_ID:", "")
            ),
            abstract=coredata.get("dc:description"),
            venue=coredata.get("prism:publicationName"),
            publisher=coredata.get("dc:publisher"),
            volume=coredata.get("prism:volume"),
            issue=coredata.get("prism:issueIdentifier"),
            pages=coredata.get("prism:pageRange"),
            citation_count=int(coredata.get("citedby-count", 0)),
            url=coredata.get("prism:url"),
            raw_data=data
        )

    async def _get_author_publications_paginated(
            self,
            author_id: str,
            progress_callback: Optional[ProgressCallback] = None
    ) -> list[Publication]:
        """Получить все публикации автора с пагинацией"""

        all_publications = []
        start = 0
        total_results = None

        while True:
            if progress_callback:
                status = f"Loading papers ({start}..."
                if total_results:
                    status = f"Loading papers ({len(all_publications)}/{total_results})..."
                await progress_callback(status, len(all_publications))

            params = {
                "query": f"AU-ID({author_id})",
                "count": self.BATCH_SIZE,
                "start": start,
                "sort": "-pubyear"  # Новые первыми
            }

            data = await self._get(self.SEARCH_URL, params)

            results = data.get("search-results", {})

            # Получаем общее количество
            if total_results is None:
                total_results = int(results.get("opensearch:totalResults", 0))

            entries = results.get("entry", [])

            if isinstance(entries, dict):
                entries = [entries]

            if not entries or entries[0].get("error"):
                break

            for entry in entries:
                if not entry.get("error"):
                    all_publications.append(self._parse_publication(entry))

            # Следующая страница
            start += self.BATCH_SIZE

            if start >= total_results:
                break

            # Защита
            if start > 10000:
                print("⚠️  Reached max limit")
                break

        return all_publications

    async def get_author_profile(
            self,
            author_id: Optional[str] = None,
            author_name: Optional[str] = None,
            author_url: Optional[str] = None,
            progress_callback: Optional[ProgressCallback] = None
    ) -> AuthorProfile:
        """
        Получить полный профиль автора

        Args:
            author_id: Scopus Author ID
            author_name: Имя для поиска
            author_url: URL профиля Scopus
            progress_callback: Callback прогресса
        """

        # Определяем ID
        if author_url:
            parsed = self.parse_url(author_url)
            author_id = parsed.get("author_id")

        if not author_id and author_name:
            if progress_callback:
                await progress_callback("Searching author...", 0)

            authors = await self.search_authors(author_name, limit=1)
            if authors:
                author_id = authors[0].source_id
                print(f"  Found author ID: {author_id}")
            else:
                raise ScopusAPIError(f"Author not found: {author_name}")

        if not author_id:
            raise ValueError("author_id is required")

        if progress_callback:
            await progress_callback("Loading author profile...", 0)

        # Получаем информацию об авторе
        author_url = f"{self.AUTHOR_URL}/{author_id}"
        params = {"view": "ENHANCED"}

        data = await self._get(author_url, params)

        author_response = data.get("author-retrieval-response", [])
        if isinstance(author_response, list) and author_response:
            author_data = author_response[0]
        else:
            author_data = author_response or {}

        if not author_data:
            raise ScopusAPIError(f"Author not found: {author_id}")

        # Основная информация
        coredata = author_data.get("coredata", {})

        # Имя
        preferred_name = author_data.get("author-profile", {}).get("preferred-name", {})
        name = f"{preferred_name.get('given-name', '')} {preferred_name.get('surname', '')}".strip()

        if not name:
            name = coredata.get("dc:identifier", "Unknown")

        # Аффилиации
        affiliations = []
        affiliation_current = author_data.get("author-profile", {}).get("affiliation-current", {})

        if isinstance(affiliation_current, dict):
            aff_list = affiliation_current.get("affiliation", [])
            if isinstance(aff_list, dict):
                aff_list = [aff_list]
            for aff in aff_list:
                aff_name = aff.get("ip-doc", {}).get("afdispname")
                if aff_name:
                    affiliations.append(aff_name)

        # История аффилиаций
        affiliation_history = []
        aff_hist = author_data.get("author-profile", {}).get("affiliation-history", {})
        if aff_hist:
            hist_list = aff_hist.get("affiliation", [])
            if isinstance(hist_list, dict):
                hist_list = [hist_list]
            for aff in hist_list:
                aff_name = aff.get("ip-doc", {}).get("afdispname")
                if aff_name and aff_name not in affiliation_history:
                    affiliation_history.append(aff_name)

        # Области исследований
        subject_areas = []
        areas = author_data.get("subject-areas", {}).get("subject-area", [])
        if isinstance(areas, dict):
            areas = [areas]
        for area in areas:
            if isinstance(area, dict):
                subject_areas.append(area.get("$", ""))

        # Метрики
        doc_count = int(coredata.get("document-count", 0))
        cited_by = int(coredata.get("cited-by-count", 0))
        citation_count = int(coredata.get("citation-count", 0))

        # h-index (если доступен)
        h_index = 0
        h_index_data = author_data.get("h-index")
        if h_index_data:
            try:
                h_index = int(h_index_data)
            except:
                pass

        # Публикации
        publications = await self._get_author_publications_paginated(
            author_id,
            progress_callback
        )

        # Сортировка
        publications.sort(key=lambda x: x.year or 0, reverse=True)

        # Статистика по годам
        pubs_per_year: dict[int, int] = {}
        for pub in publications:
            if pub.year:
                pubs_per_year[pub.year] = pubs_per_year.get(pub.year, 0) + 1

        years = [p.year for p in publications if p.year]

        # Соавторы
        coauthor_counts: dict[str, Author] = {}
        coauthor_collabs: dict[str, int] = {}
        name_lower = name.lower()

        for pub in publications:
            for author in pub.authors:
                if author.name.lower() != name_lower:
                    if author.name not in coauthor_counts:
                        coauthor_counts[author.name] = author
                        coauthor_collabs[author.name] = 0
                    coauthor_collabs[author.name] += 1

        coauthors = [
            CoAuthor(author=coauthor_counts[n], collaboration_count=c)
            for n, c in sorted(coauthor_collabs.items(), key=lambda x: -x[1])
        ]

        if progress_callback:
            await progress_callback("Done!", len(publications))

        return AuthorProfile(
            name=name,
            source=SourceType.SCOPUS,
            source_id=author_id,
            orcid=author_data.get("coredata", {}).get("orcid"),
            external_ids=ExternalIds(scopus_id=author_id),
            affiliation=affiliations[0] if affiliations else None,
            affiliations_history=affiliation_history,
            interests=subject_areas[:20],
            fields_of_study=subject_areas,
            metrics=Metrics(
                citation_count=citation_count or cited_by,
                h_index=h_index,
                publication_count=doc_count or len(publications)
            ),
            publications_per_year=pubs_per_year,
            publications=publications,
            coauthors=coauthors,
            first_publication_year=min(years) if years else None,
            last_publication_year=max(years) if years else None,
            url=f"https://www.scopus.com/authid/detail.uri?authorId={author_id}"
        )