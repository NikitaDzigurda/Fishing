"""
Парсер Google Scholar через scholarly
С полным парсингом авторов статей и описаний
"""

import re
import asyncio
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional
from enum import Enum
from tqdm import tqdm

from scholarly import scholarly, ProxyGenerator

from ..base import BaseParser, ProgressCallback
from ..models import (
    AuthorProfile, Publication, Author, CoAuthor,
    Metrics, ExternalIds, SourceType
)


class ProxyType(Enum):
    NONE = "none"
    FREE = "free"
    TOR = "tor"
    SCRAPER_API = "scraperapi"


class GoogleScholarParser(BaseParser):
    """
    Парсер Google Scholar через scholarly

    ВАЖНО: fill_publications=True обязателен для получения авторов публикаций!

    Пример:
        async with GoogleScholarParser() as parser:
            profile = await parser.get_author_profile(
                author_id="JicYPdAAAAAJ",
                fill_publications=True  # Нужно для авторов!
            )
    """

    source = SourceType.GOOGLE_SCHOLAR

    def __init__(
            self,
            proxy_type: ProxyType = ProxyType.NONE,
            scraper_api_key: Optional[str] = None,
            delay_range: tuple[float, float] = (1.0, 3.0)
    ):
        super().__init__()
        self.proxy_type = proxy_type
        self.scraper_api_key = scraper_api_key
        self.delay_range = delay_range
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._proxy_setup_done = False

    async def init(self):
        if self.proxy_type != ProxyType.NONE:
            await self._setup_proxy()

    async def close(self):
        self._executor.shutdown(wait=False)

    async def _setup_proxy(self):
        if self._proxy_setup_done:
            return

        def setup():
            if self.proxy_type == ProxyType.FREE:
                pg = ProxyGenerator()
                pg.FreeProxies()
                scholarly.use_proxy(pg)
            elif self.proxy_type == ProxyType.TOR:
                pg = ProxyGenerator()
                pg.Tor_Internal(tor_cmd="tor")
                scholarly.use_proxy(pg)
            elif self.proxy_type == ProxyType.SCRAPER_API:
                if not self.scraper_api_key:
                    raise ValueError("scraper_api_key required")
                pg = ProxyGenerator()
                pg.ScraperAPI(self.scraper_api_key)
                scholarly.use_proxy(pg)

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(self._executor, setup)
        self._proxy_setup_done = True

    async def _delay(self):
        await asyncio.sleep(random.uniform(*self.delay_range))

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: func(*args, **kwargs)
        )

    def _parse_authors_from_string(self, authors_str: str) -> list[Author]:
        """
        Парсинг строки авторов в список объектов Author

        Форматы:
        - "Alex Krizhevsky and Ilya Sutskever and Geoffrey E Hinton"
        - "Yann LeCun and Yoshua Bengio and Geoffrey Hinton"
        """
        if not authors_str:
            return []

        authors = []

        # Разделяем по " and "
        parts = authors_str.split(" and ")

        for part in parts:
            name = part.strip()
            if not name:
                continue

            # Убираем лишние пробелы
            name = re.sub(r'\s+', ' ', name)

            authors.append(Author(
                name=name,
                source=SourceType.GOOGLE_SCHOLAR
            ))

        return authors

    def _parse_publication(self, pub_dict: dict) -> Publication:
        """
        Преобразование публикации scholarly в Publication

        ВАЖНО: pub_dict должен быть после scholarly.fill() для получения авторов!
        """
        bib = pub_dict.get("bib", {})

        # === АВТОРЫ (появляются только после fill) ===
        authors = []
        authors_str = bib.get("author", "")

        if authors_str:
            authors = self._parse_authors_from_string(authors_str)

        # === ГОД ===
        year = None
        pub_year = bib.get("pub_year")
        if pub_year:
            try:
                year = int(pub_year)
            except (ValueError, TypeError):
                pass

        # === ABSTRACT (появляется только после fill) ===
        abstract = bib.get("abstract")

        # === VENUE ===
        venue = (
            bib.get("journal") or
            bib.get("venue") or
            bib.get("booktitle") or
            bib.get("conference")
        )

        # === ДОПОЛНИТЕЛЬНЫЕ ПОЛЯ ===
        publisher = bib.get("publisher")
        volume = bib.get("volume")
        issue = bib.get("number")
        pages = bib.get("pages")

        # === EXTERNAL IDS ===
        external_ids = ExternalIds()

        # Пробуем найти DOI
        pub_url = pub_dict.get("pub_url", "")
        if "doi.org" in pub_url:
            doi_match = re.search(r'doi\.org/(.+?)(?:\?|$)', pub_url)
            if doi_match:
                external_ids.doi = doi_match.group(1)

        # arXiv
        eprint_url = pub_dict.get("eprint_url", "") or ""
        if "arxiv.org" in eprint_url:
            arxiv_match = re.search(r'arxiv\.org/(?:abs|pdf)/([^\s/?]+)', eprint_url)
            if arxiv_match:
                external_ids.arxiv_id = arxiv_match.group(1).replace(".pdf", "")

        return Publication(
            title=bib.get("title", "Unknown"),
            authors=authors,
            year=year,
            source=SourceType.GOOGLE_SCHOLAR,
            source_id=pub_dict.get("author_pub_id"),
            external_ids=external_ids,
            abstract=abstract,
            venue=venue,
            publisher=publisher,
            volume=volume,
            issue=issue,
            pages=pages,
            citation_count=pub_dict.get("num_citations", 0),
            url=pub_dict.get("pub_url"),
            pdf_url=pub_dict.get("eprint_url"),
            raw_data=pub_dict
        )

    def _parse_author_profile(self, author_dict: dict, publications: list[Publication]) -> AuthorProfile:
        """Преобразование профиля scholarly в AuthorProfile"""

        # Цитирования по годам
        citations_per_year = {}
        for year, count in author_dict.get("cites_per_year", {}).items():
            try:
                citations_per_year[int(year)] = count
            except (ValueError, TypeError):
                pass

        # === СОАВТОРЫ ИЗ ПРОФИЛЯ ===
        coauthors_from_profile = {}
        for c in author_dict.get("coauthors", []):
            name = c.get("name", "")
            if name:
                coauthors_from_profile[name.lower()] = CoAuthor(
                    author=Author(
                        name=name,
                        author_id=c.get("scholar_id"),
                        affiliation=c.get("affiliation"),
                        source=SourceType.GOOGLE_SCHOLAR
                    ),
                    collaboration_count=0
                )

        # === СЧИТАЕМ КОЛЛАБОРАЦИИ ИЗ ПУБЛИКАЦИЙ ===
        author_name_lower = author_dict.get("name", "").lower()
        coauthor_counts: dict[str, int] = {}
        coauthor_objects: dict[str, Author] = {}

        for pub in publications:
            for author in pub.authors:
                name_lower = author.name.lower()
                if name_lower != author_name_lower and name_lower:
                    if name_lower not in coauthor_counts:
                        coauthor_counts[name_lower] = 0
                        coauthor_objects[name_lower] = author
                    coauthor_counts[name_lower] += 1

        # === ОБЪЕДИНЯЕМ СОАВТОРОВ ===
        coauthors = []

        # Сначала добавляем из профиля с подсчитанными коллаборациями
        for name_lower, coauthor in coauthors_from_profile.items():
            coauthor.collaboration_count = coauthor_counts.get(name_lower, 0)
            coauthors.append(coauthor)
            # Убираем из подсчитанных
            coauthor_counts.pop(name_lower, None)

        # Добавляем оставшихся (не было в профиле)
        for name_lower, count in coauthor_counts.items():
            coauthors.append(CoAuthor(
                author=coauthor_objects[name_lower],
                collaboration_count=count
            ))

        # Сортируем по коллаборациям
        coauthors.sort(key=lambda x: -x.collaboration_count)

        # === ПУБЛИКАЦИИ ПО ГОДАМ ===
        pubs_per_year: dict[int, int] = {}
        for pub in publications:
            if pub.year:
                pubs_per_year[pub.year] = pubs_per_year.get(pub.year, 0) + 1

        years = [p.year for p in publications if p.year]

        return AuthorProfile(
            name=author_dict.get("name", "Unknown"),
            source=SourceType.GOOGLE_SCHOLAR,
            source_id=author_dict.get("scholar_id", ""),
            affiliation=author_dict.get("affiliation"),
            email_domain=author_dict.get("email_domain"),
            homepage=author_dict.get("homepage"),
            interests=author_dict.get("interests", []),
            metrics=Metrics(
                citation_count=author_dict.get("citedby", 0),
                citation_count_recent=author_dict.get("citedby5y", 0),
                h_index=author_dict.get("hindex", 0),
                h_index_recent=author_dict.get("hindex5y", 0),
                i10_index=author_dict.get("i10index", 0),
                i10_index_recent=author_dict.get("i10index5y", 0),
                publication_count=len(publications)
            ),
            citations_per_year=citations_per_year,
            publications_per_year=pubs_per_year,
            publications=publications,
            coauthors=coauthors,
            first_publication_year=min(years) if years else None,
            last_publication_year=max(years) if years else None,
            photo_url=author_dict.get("url_picture"),
            url=f"https://scholar.google.com/citations?user={author_dict.get('scholar_id', '')}",
            raw_data=author_dict
        )

    @classmethod
    def parse_url(cls, url: str) -> dict:
        """Парсинг URL Google Scholar"""
        match = re.search(r"user=([a-zA-Z0-9_-]+)", url)
        if match:
            return {"author_id": match.group(1), "type": "profile"}
        raise ValueError(f"Cannot parse Google Scholar URL: {url}")

    async def search_authors(self, query: str, limit: int = 10) -> list[AuthorProfile]:
        """Поиск авторов"""
        await self._delay()

        def search():
            results = []
            search_query = scholarly.search_author(query)
            for i, author in enumerate(search_query):
                if i >= limit:
                    break
                results.append(author)
            return results

        authors = await self._run_sync(search)

        profiles = []
        for a in authors:
            profiles.append(AuthorProfile(
                name=a.get("name", ""),
                source=SourceType.GOOGLE_SCHOLAR,
                source_id=a.get("scholar_id", ""),
                affiliation=a.get("affiliation"),
                interests=a.get("interests", []),
                metrics=Metrics(citation_count=a.get("citedby", 0))
            ))

        return profiles

    async def search_publications(
            self,
            query: str,
            limit: int = 20,
            year_start: Optional[int] = None,
            year_end: Optional[int] = None,
            fill_details: bool = True
    ) -> list[Publication]:
        """
        Поиск публикаций

        Args:
            fill_details: True для получения авторов и abstract (медленнее)
        """
        await self._delay()

        def search():
            results = []
            search_query = scholarly.search_pubs(
                query,
                year_low=year_start,
                year_high=year_end
            )
            for i, pub in enumerate(search_query):
                if i >= limit:
                    break
                results.append(pub)
            return results

        pubs = await self._run_sync(search)

        publications = []
        for pub in pubs:
            if fill_details:
                await self._delay()
                try:
                    pub = await self._run_sync(scholarly.fill, pub)
                except Exception:
                    pass
            publications.append(self._parse_publication(pub))

        return publications

    async def get_publication(self, publication_id: str) -> Publication:
        """Получить публикацию (не поддерживается напрямую)"""
        raise NotImplementedError("Direct publication lookup not supported")

    async def get_author_profile(
            self,
            author_id: Optional[str] = None,
            author_name: Optional[str] = None,
            author_url: Optional[str] = None,
            fill_publications: bool = True,
            progress_callback: Optional[ProgressCallback] = None
    ) -> AuthorProfile:
        """
        Получить полный профиль автора

        Args:
            author_id: Google Scholar ID (например "JicYPdAAAAAJ")
            author_name: Имя для поиска
            author_url: URL профиля
            fill_publications: True для получения авторов и abstract каждой публикации
                               ОБЯЗАТЕЛЬНО True если нужны авторы публикаций!
            progress_callback: Callback прогресса

        Returns:
            AuthorProfile с публикациями
        """

        # === ОПРЕДЕЛЯЕМ ID ===
        if author_url:
            parsed = self.parse_url(author_url)
            author_id = parsed.get("author_id")

        if not author_id and author_name:
            authors = await self.search_authors(author_name, limit=1)
            if authors:
                author_id = authors[0].source_id

        if not author_id:
            raise ValueError("author_id is required")

        await self._delay()

        # === ЗАГРУЖАЕМ АВТОРА ===
        def fetch_author():
            author = scholarly.search_author_id(author_id)
            author = scholarly.fill(author, sections=[
                'basics', 'indices', 'counts', 'coauthors', 'publications'
            ])
            return author

        if progress_callback:
            await progress_callback("Loading profile...", 0)

        author_dict = await self._run_sync(fetch_author)

        # === ЗАГРУЖАЕМ ПУБЛИКАЦИИ ===
        publications = []
        raw_pubs = author_dict.get("publications", [])
        total = len(raw_pubs)

        if progress_callback:
            await progress_callback(f"Found {total} publications", 0)

        for i, pub in tqdm(enumerate(raw_pubs), total=len(raw_pubs)):

            if fill_publications:
                # ОБЯЗАТЕЛЬНО для получения авторов и abstract!
                await self._delay()

                try:
                    filled_pub = await self._run_sync(scholarly.fill, pub)
                except Exception as e:
                    # Если не удалось - используем как есть (без авторов)
                    filled_pub = pub

                publications.append(self._parse_publication(filled_pub))
            else:
                # Без fill - авторов и abstract НЕ БУДЕТ!
                publications.append(self._parse_publication(pub))

            if progress_callback:
                await progress_callback(f"Publications: {i + 1}/{total}", i + 1)

        # Сортируем по цитированиям (самые цитируемые первыми)
        publications.sort(key=lambda x: -(x.citation_count or 0))

        if progress_callback:
            await progress_callback("Done!", total)

        return self._parse_author_profile(author_dict, publications)