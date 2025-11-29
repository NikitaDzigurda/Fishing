"""
Парсер arXiv API
"""

import re
import asyncio
import aiohttp
import feedparser
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse, parse_qs

from ..base import BaseParser, ProgressCallback
from ..models import (
    AuthorProfile, Publication, Author, CoAuthor,
    Metrics, ExternalIds, SourceType
)


class ArxivParser(BaseParser):
    """
    Парсер для arXiv API

    Пример:
        async with ArxivParser() as parser:
            profile = await parser.get_author_profile(author_name="Yann LeCun")
    """

    source = SourceType.ARXIV
    BASE_URL = "http://export.arxiv.org/api/query"
    RATE_LIMIT = 3.0
    BATCH_SIZE = 200

    def __init__(self, rate_limit: float = 3.0):
        super().__init__()
        self.rate_limit = rate_limit
        self._last_request = 0.0
        self._lock = asyncio.Lock()

    async def init(self):
        timeout = aiohttp.ClientTimeout(total=120)
        self._session = aiohttp.ClientSession(
            headers={"User-Agent": "AcademicAPI/1.0"},
            timeout=timeout
        )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rate_limit_wait(self):
        async with self._lock:
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_request
            if elapsed < self.rate_limit:
                await asyncio.sleep(self.rate_limit - elapsed)
            self._last_request = asyncio.get_event_loop().time()

    async def _make_request(self, params: dict) -> feedparser.FeedParserDict:
        await self._rate_limit_wait()

        async with self._session.get(self.BASE_URL, params=params) as response:
            response.raise_for_status()
            content = await response.text()

        return feedparser.parse(content)

    def _parse_arxiv_id(self, entry: dict) -> str:
        id_url = entry.get("id", "")
        match = re.search(r"arxiv.org/abs/(.+?)(?:v\d+)?$", id_url)
        return match.group(1) if match else id_url.split("/")[-1]

    def _parse_datetime(self, time_struct) -> Optional[datetime]:
        if time_struct:
            return datetime(*time_struct[:6])
        return None

    def _parse_entry(self, entry: dict) -> Publication:
        """Преобразование записи arXiv в Publication"""

        # Авторы
        authors = []
        for a in entry.get("authors", []):
            authors.append(Author(
                name=a.get("name", ""),
                source=SourceType.ARXIV
            ))

        # Категории
        categories = [tag.get("term", "") for tag in entry.get("tags", []) if tag.get("term")]
        primary_category = entry.get("arxiv_primary_category", {}).get("term", "")
        if not primary_category and categories:
            primary_category = categories[0]

        # Ссылки
        pdf_url = ""
        abs_url = entry.get("id", "")
        for link in entry.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href", "")
            elif link.get("rel") == "alternate":
                abs_url = link.get("href", "")

        arxiv_id = self._parse_arxiv_id(entry)
        published = self._parse_datetime(entry.get("published_parsed"))

        return Publication(
            title=entry.get("title", "").replace("\n", " ").strip(),
            authors=authors,
            year=published.year if published else None,
            date=published,
            source=SourceType.ARXIV,
            source_id=arxiv_id,
            external_ids=ExternalIds(
                arxiv_id=arxiv_id,
                doi=entry.get("arxiv_doi")
            ),
            abstract=entry.get("summary", "").replace("\n", " ").strip(),
            categories=categories,
            primary_category=primary_category,
            url=abs_url,
            pdf_url=pdf_url,
            source_url=abs_url,
            is_open_access=True,
            raw_data=dict(entry)
        )

    @classmethod
    def parse_url(cls, url: str) -> dict:
        """Парсинг URL arXiv"""
        parsed = urlparse(url)

        # ORCID: /a/0000-0000-0000-0000
        if "/a/" in parsed.path:
            match = re.search(r"/a/(\d{4}-\d{4}-\d{4}-\d{4})", parsed.path)
            if match:
                return {"orcid": match.group(1), "type": "orcid"}

        # Поиск: /search/?searchtype=author&query=Name
        if "/search/" in parsed.path:
            params = parse_qs(parsed.query)
            if "query" in params:
                return {"author_name": params["query"][0], "type": "search"}

        # Статья: /abs/1234.5678
        if "/abs/" in parsed.path:
            match = re.search(r"/abs/([^/]+)", parsed.path)
            if match:
                return {"arxiv_id": match.group(1), "type": "paper"}

        raise ValueError(f"Unknown arXiv URL format: {url}")

    async def search_publications(
            self,
            query: str,
            limit: int = 100,
            year_start: Optional[int] = None,
            year_end: Optional[int] = None
    ) -> list[Publication]:
        """Поиск публикаций"""
        params = {
            "search_query": query,
            "start": 0,
            "max_results": min(limit, self.BATCH_SIZE),
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }

        feed = await self._make_request(params)
        return [self._parse_entry(e) for e in feed.entries]

    async def search_authors(self, query: str, limit: int = 10) -> list[AuthorProfile]:
        """Поиск авторов (через поиск публикаций)"""
        pubs = await self.search_publications(f'au:"{query}"', limit=50)

        # Собираем уникальных авторов
        author_pubs: dict[str, list[Publication]] = {}
        for pub in pubs:
            for author in pub.authors:
                if query.lower() in author.name.lower():
                    if author.name not in author_pubs:
                        author_pubs[author.name] = []
                    author_pubs[author.name].append(pub)

        profiles = []
        for name, pubs_list in list(author_pubs.items())[:limit]:
            profiles.append(AuthorProfile(
                name=name,
                source=SourceType.ARXIV,
                source_id=name,
                metrics=Metrics(publication_count=len(pubs_list)),
                publications=pubs_list
            ))

        return profiles

    async def get_publication(self, publication_id: str) -> Publication:
        """Получить публикацию по arXiv ID"""
        params = {"id_list": publication_id}
        feed = await self._make_request(params)

        if feed.entries:
            return self._parse_entry(feed.entries[0])

        raise ValueError(f"Publication not found: {publication_id}")

    async def _get_all_author_papers(
            self,
            author_name: str,
            progress_callback: Optional[ProgressCallback] = None
    ) -> list[Publication]:
        """Получить все публикации автора"""
        all_papers = []
        start = 0
        seen_ids = set()

        while True:
            params = {
                "search_query": f'au:"{author_name}"',
                "start": start,
                "max_results": self.BATCH_SIZE,
                "sortBy": "submittedDate",
                "sortOrder": "descending"
            }

            feed = await self._make_request(params)

            if not feed.entries:
                break

            for entry in feed.entries:
                paper = self._parse_entry(entry)
                if paper.source_id not in seen_ids:
                    seen_ids.add(paper.source_id)
                    all_papers.append(paper)

            if progress_callback:
                await progress_callback(f"Loaded {len(all_papers)} papers", len(all_papers))

            if len(feed.entries) < self.BATCH_SIZE:
                break

            start += self.BATCH_SIZE

        return all_papers

    async def get_author_profile(
            self,
            author_id: Optional[str] = None,
            author_name: Optional[str] = None,
            author_url: Optional[str] = None,
            progress_callback: Optional[ProgressCallback] = None
    ) -> AuthorProfile:
        """Получить профиль автора"""

        # Определяем имя автора
        if author_url:
            parsed = self.parse_url(author_url)
            author_name = parsed.get("author_name")
            if not author_name and parsed.get("type") == "orcid":
                # TODO: получить имя по ORCID
                raise NotImplementedError("ORCID lookup not implemented")

        if author_id and not author_name:
            author_name = author_id

        if not author_name:
            raise ValueError("author_name is required")

        # Загружаем все публикации
        publications = await self._get_all_author_papers(author_name, progress_callback)

        # Анализ соавторов
        coauthor_counts: dict[str, Author] = {}
        coauthor_collabs: dict[str, int] = {}
        categories_count: dict[str, int] = {}

        for pub in publications:
            for author in pub.authors:
                if author.name.lower() != author_name.lower():
                    if author.name not in coauthor_counts:
                        coauthor_counts[author.name] = author
                        coauthor_collabs[author.name] = 0
                    coauthor_collabs[author.name] += 1

            for cat in pub.categories:
                categories_count[cat] = categories_count.get(cat, 0) + 1

        coauthors = [
            CoAuthor(author=coauthor_counts[name], collaboration_count=count)
            for name, count in sorted(coauthor_collabs.items(), key=lambda x: -x[1])
        ]

        # Публикации по годам
        pubs_per_year: dict[int, int] = {}
        for pub in publications:
            if pub.year:
                pubs_per_year[pub.year] = pubs_per_year.get(pub.year, 0) + 1

        # Даты
        years = [p.year for p in publications if p.year]
        first_year = min(years) if years else None
        last_year = max(years) if years else None

        return AuthorProfile(
            name=author_name,
            source=SourceType.ARXIV,
            source_id=author_name,
            metrics=Metrics(publication_count=len(publications)),
            publications_per_year=pubs_per_year,
            publications=publications,
            coauthors=coauthors,
            fields_of_study=list(categories_count.keys())[:20],
            first_publication_year=first_year,
            last_publication_year=last_year
        )