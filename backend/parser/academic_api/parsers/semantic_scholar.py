"""
Парсер Semantic Scholar API (официальный)
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Optional

from ..base import BaseParser, ProgressCallback
from ..models import (
    AuthorProfile, Publication, Author, CoAuthor,
    Metrics, ExternalIds, SourceType
)


class RateLimitError(Exception):
    """Превышен лимит запросов"""
    pass


class SemanticScholarParser(BaseParser):
    """
    Парсер Semantic Scholar API

    Лимиты API:
    - Без ключа: 100 запросов в 5 минут
    - С ключом: 1 запрос в секунду

    Получить ключ: https://www.semanticscholar.org/product/api#api-key

    Пример:
        async with SemanticScholarParser() as parser:
            profile = await parser.get_author_profile(author_name="Yann LeCun")
    """

    source = SourceType.SEMANTIC_SCHOLAR
    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    # Лимиты
    RATE_LIMIT_NO_KEY = 3.5
    RATE_LIMIT_WITH_KEY = 1.0
    BATCH_SIZE = 100
    MAX_RETRIES = 3
    RETRY_DELAY = 10

    # Поля для запросов публикаций (включая abstract)
    PAPER_FIELDS = ",".join([
        "title",
        "authors",
        "year",
        "venue",
        "publicationVenue",
        "citationCount",
        "referenceCount",
        "influentialCitationCount",
        "abstract",  # <-- ABSTRACT
        "externalIds",
        "url",
        "openAccessPdf",
        "isOpenAccess",
        "s2FieldsOfStudy",
        "publicationTypes",
        "publicationDate"
    ])

    # Поля для поиска публикаций
    SEARCH_PAPER_FIELDS = ",".join([
        "title",
        "authors",
        "year",
        "venue",
        "citationCount",
        "abstract",  # <-- ABSTRACT
        "externalIds",
        "url",
        "openAccessPdf",
        "isOpenAccess"
    ])

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key
        self.rate_limit = self.RATE_LIMIT_WITH_KEY if api_key else self.RATE_LIMIT_NO_KEY
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def init(self):
        headers = {"User-Agent": "AcademicAPI/1.0"}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        timeout = aiohttp.ClientTimeout(total=60)
        self._session = aiohttp.ClientSession(headers=headers, timeout=timeout)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rate_limit_wait(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request
            if elapsed < self.rate_limit:
                wait_time = self.rate_limit - elapsed
                await asyncio.sleep(wait_time)
            self._last_request = asyncio.get_event_loop().time()

    async def _get(self, endpoint: str, params: dict = None, retries: int = 0) -> dict:
        """GET запрос с retry логикой"""
        await self._rate_limit_wait()
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            async with self._session.get(url, params=params) as response:
                if response.status == 429:
                    if retries < self.MAX_RETRIES:
                        delay = self.RETRY_DELAY * (2 ** retries)
                        print(f"\n⚠️  Rate limit hit. Waiting {delay}s...")
                        await asyncio.sleep(delay)
                        return await self._get(endpoint, params, retries + 1)
                    raise RateLimitError("Rate limit exceeded after max retries")

                response.raise_for_status()
                return await response.json()

        except aiohttp.ClientResponseError as e:
            if e.status == 429 and retries < self.MAX_RETRIES:
                delay = self.RETRY_DELAY * (2 ** retries)
                print(f"\n⚠️  Rate limit (429). Waiting {delay}s...")
                await asyncio.sleep(delay)
                return await self._get(endpoint, params, retries + 1)
            raise

    def _parse_publication(self, data: dict) -> Publication:
        """Преобразование данных S2 в Publication"""

        # === АВТОРЫ ===
        authors = [
            Author(
                name=a.get("name", ""),
                author_id=a.get("authorId"),
                source=SourceType.SEMANTIC_SCHOLAR
            )
            for a in data.get("authors", [])
        ]

        # === EXTERNAL IDS ===
        ext_ids = data.get("externalIds") or {}
        external_ids = ExternalIds(
            doi=ext_ids.get("DOI"),
            arxiv_id=ext_ids.get("ArXiv"),
            pubmed_id=ext_ids.get("PubMed"),
            semantic_scholar_id=data.get("paperId")
        )

        # === ПОЛЯ ИССЛЕДОВАНИЯ ===
        fields = []
        for f in data.get("s2FieldsOfStudy", []):
            if f.get("category"):
                fields.append(f["category"])

        # === VENUE ===
        venue = data.get("venue") or ""
        publication_venue = data.get("publicationVenue") or {}
        if not venue and publication_venue:
            venue = publication_venue.get("name", "")

        # Тип venue
        venue_type = None
        pub_types = data.get("publicationTypes") or []
        if pub_types:
            venue_type = pub_types[0]  # Journal, Conference, etc.

        # === ДАТА ===
        year = data.get("year")
        publication_date = data.get("publicationDate")  # "2023-05-15"

        # === ABSTRACT ===
        abstract = data.get("abstract")  # <-- ПАРСИМ ABSTRACT

        # === PDF ===
        pdf_url = None
        open_access_pdf = data.get("openAccessPdf")
        if open_access_pdf:
            pdf_url = open_access_pdf.get("url")

        return Publication(
            title=data.get("title", ""),
            authors=authors,
            year=year,
            source=SourceType.SEMANTIC_SCHOLAR,
            source_id=data.get("paperId"),
            external_ids=external_ids,
            abstract=abstract,  # <-- ABSTRACT
            venue=venue,
            venue_type=venue_type,
            citation_count=data.get("citationCount", 0),
            reference_count=data.get("referenceCount", 0),
            influential_citation_count=data.get("influentialCitationCount", 0),
            url=data.get("url"),
            pdf_url=pdf_url,
            is_open_access=data.get("isOpenAccess", False),
            fields_of_study=fields,
            raw_data=data
        )

    async def search_authors(self, query: str, limit: int = 10) -> list[AuthorProfile]:
        """Поиск авторов"""
        data = await self._get("author/search", {
            "query": query,
            "limit": min(limit, 100),
            "fields": "name,affiliations,citationCount,hIndex,paperCount"
        })

        profiles = []
        for a in data.get("data", []):
            affiliations = a.get("affiliations") or []
            profiles.append(AuthorProfile(
                name=a.get("name", ""),
                source=SourceType.SEMANTIC_SCHOLAR,
                source_id=a.get("authorId", ""),
                affiliation=affiliations[0] if affiliations else None,
                metrics=Metrics(
                    citation_count=a.get("citationCount", 0),
                    h_index=a.get("hIndex", 0),
                    publication_count=a.get("paperCount", 0)
                )
            ))

        return profiles

    async def search_publications(
        self,
        query: str,
        limit: int = 20,
        year_start: Optional[int] = None,
        year_end: Optional[int] = None
    ) -> list[Publication]:
        """Поиск публикаций (с abstract)"""
        params = {
            "query": query,
            "limit": min(limit, 100),
            "fields": self.SEARCH_PAPER_FIELDS  # Включает abstract
        }

        if year_start or year_end:
            year_filter = ""
            if year_start:
                year_filter += str(year_start)
            year_filter += "-"
            if year_end:
                year_filter += str(year_end)
            params["year"] = year_filter

        data = await self._get("paper/search", params)
        print(data)
        return [self._parse_publication(p) for p in data.get("data", [])]

    async def get_publication(self, publication_id: str) -> Publication:
        """Получить публикацию по ID (с полным abstract)"""
        data = await self._get(f"paper/{publication_id}", {"fields": self.PAPER_FIELDS})
        return self._parse_publication(data)

    async def _get_author_papers_paginated(
        self,
        author_id: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> list[Publication]:
        """Получить все публикации автора с пагинацией (включая abstract)"""

        all_publications = []
        offset = 0

        # Поля для публикаций автора (включая abstract)
        fields = ",".join([
            "title",
            "authors",
            "year",
            "venue",
            "citationCount",
            "referenceCount",
            "abstract",  # <-- ABSTRACT
            "externalIds",
            "url",
            "openAccessPdf",
            "isOpenAccess",
            "s2FieldsOfStudy",
            "publicationTypes"
        ])

        while True:
            if progress_callback:
                await progress_callback(f"Loading papers (offset {offset})...", len(all_publications))

            data = await self._get(
                f"author/{author_id}/papers",
                {
                    "fields": fields,
                    "limit": self.BATCH_SIZE,
                    "offset": offset
                }
            )

            papers = data.get("data", [])

            if not papers:
                break

            for p in papers:
                all_publications.append(self._parse_publication(p))

            if len(papers) < self.BATCH_SIZE:
                break

            offset += self.BATCH_SIZE

            if offset > 10000:
                print("⚠️  Reached max offset limit")
                break

        return all_publications

    async def get_author_profile(
        self,
        author_id: Optional[str] = None,
        author_name: Optional[str] = None,
        author_url: Optional[str] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> AuthorProfile:
        """Получить профиль автора (публикации включают abstract)"""

        # Определяем ID
        if not author_id and author_name:
            if progress_callback:
                await progress_callback("Searching author...", 0)

            authors = await self.search_authors(author_name, limit=1)
            if authors:
                author_id = authors[0].source_id

        if not author_id:
            raise ValueError("author_id is required or author not found")

        if progress_callback:
            await progress_callback("Loading profile...", 0)

        # Базовая информация
        author_data = await self._get(
            f"author/{author_id}",
            {"fields": "name,affiliations,citationCount,hIndex,paperCount"}
        )

        # Публикации с пагинацией (включая abstract)
        publications = await self._get_author_papers_paginated(author_id, progress_callback)

        # Сортировка по году (новые первыми)
        publications.sort(key=lambda x: x.year or 0, reverse=True)

        # Статистика по годам
        pubs_per_year: dict[int, int] = {}
        for pub in publications:
            if pub.year:
                pubs_per_year[pub.year] = pubs_per_year.get(pub.year, 0) + 1

        years = [p.year for p in publications if p.year]

        # Анализ соавторов
        coauthor_counts: dict[str, Author] = {}
        coauthor_collabs: dict[str, int] = {}
        author_name_lower = author_data.get("name", "").lower()

        for pub in publications:
            for author in pub.authors:
                if author.name.lower() != author_name_lower:
                    if author.name not in coauthor_counts:
                        coauthor_counts[author.name] = author
                        coauthor_collabs[author.name] = 0
                    coauthor_collabs[author.name] += 1

        coauthors = [
            CoAuthor(author=coauthor_counts[name], collaboration_count=count)
            for name, count in sorted(coauthor_collabs.items(), key=lambda x: -x[1])
        ]

        affiliations = author_data.get("affiliations") or []

        if progress_callback:
            await progress_callback("Done!", len(publications))

        return AuthorProfile(
            name=author_data.get("name", ""),
            source=SourceType.SEMANTIC_SCHOLAR,
            source_id=author_id,
            affiliation=affiliations[0] if affiliations else None,
            affiliations_history=affiliations,
            metrics=Metrics(
                citation_count=author_data.get("citationCount", 0),
                h_index=author_data.get("hIndex", 0),
                publication_count=author_data.get("paperCount", 0)
            ),
            publications_per_year=pubs_per_year,
            publications=publications,
            coauthors=coauthors,
            first_publication_year=min(years) if years else None,
            last_publication_year=max(years) if years else None,
            url=f"https://www.semanticscholar.org/author/{author_id}"
        )