"""
Парсер Google Scholar через scholarly
"""

import re
import asyncio
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional
from enum import Enum

# pip install scholarly
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

    Пример:
        async with GoogleScholarParser(proxy_type=ProxyType.FREE) as parser:
            profile = await parser.get_author_profile(author_id="JicYPdAAAAAJ")
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

    def _parse_publication(self, pub_dict: dict) -> Publication:
        """Преобразование публикации scholarly в Publication"""
        bib = pub_dict.get("bib", {})

        # Авторы
        authors_raw = bib.get("author", "")
        if isinstance(authors_raw, str):
            author_names = [a.strip() for a in authors_raw.split(" and ")]
        else:
            author_names = authors_raw

        authors = [Author(name=name, source=SourceType.GOOGLE_SCHOLAR) for name in author_names]

        # Год
        year = None
        if bib.get("pub_year"):
            try:
                year = int(bib["pub_year"])
            except (ValueError, TypeError):
                pass

        return Publication(
            title=bib.get("title", "Unknown"),
            authors=authors,
            year=year,
            source=SourceType.GOOGLE_SCHOLAR,
            source_id=pub_dict.get("author_pub_id"),
            abstract=bib.get("abstract"),
            venue=bib.get("venue") or bib.get("journal") or bib.get("booktitle"),
            publisher=bib.get("publisher"),
            volume=bib.get("volume"),
            issue=bib.get("number"),
            pages=bib.get("pages"),
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

        # Соавторы
        coauthors = []
        for c in author_dict.get("coauthors", []):
            coauthors.append(CoAuthor(
                author=Author(
                    name=c.get("name", ""),
                    author_id=c.get("scholar_id"),
                    affiliation=c.get("affiliation"),
                    source=SourceType.GOOGLE_SCHOLAR
                ),
                collaboration_count=0
            ))

        # Публикации по годам
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
            year_end: Optional[int] = None
    ) -> list[Publication]:
        """Поиск публикаций"""
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
        return [self._parse_publication(p) for p in pubs]

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
        """Получить полный профиль автора"""

        # Определяем ID
        if author_url:
            parsed = self.parse_url(author_url)
            author_id = parsed.get("author_id")

        if not author_id and author_name:
            # Поиск по имени
            authors = await self.search_authors(author_name, limit=1)
            if authors:
                author_id = authors[0].source_id

        if not author_id:
            raise ValueError("author_id is required")

        await self._delay()

        # Загружаем автора
        def fetch_author():
            author = scholarly.search_author_id(author_id)
            author = scholarly.fill(author, sections=[
                'basics', 'indices', 'counts', 'coauthors', 'publications'
            ])
            return author

        if progress_callback:
            await progress_callback("Loading profile...", 0)

        author_dict = await self._run_sync(fetch_author)

        # Заполняем публикации
        publications = []
        raw_pubs = author_dict.get("publications", [])

        if fill_publications and raw_pubs:
            total = len(raw_pubs)

            for i, pub in enumerate(raw_pubs):
                await self._delay()

                def fill_pub(p):
                    try:
                        return scholarly.fill(p)
                    except:
                        return p

                filled = await self._run_sync(fill_pub, pub)
                publications.append(self._parse_publication(filled))

                if progress_callback:
                    await progress_callback(f"Publications: {i + 1}/{total}", i + 1)
        else:
            publications = [self._parse_publication(p) for p in raw_pubs]

        # Сортируем по году
        publications.sort(key=lambda x: x.year or 0, reverse=True)

        return self._parse_author_profile(author_dict, publications)