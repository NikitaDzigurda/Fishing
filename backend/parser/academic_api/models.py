"""
Унифицированные модели данных для всех академических API
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class SourceType(Enum):
    """Источник данных"""
    ARXIV = "arxiv"
    GOOGLE_SCHOLAR = "google_scholar"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    SCOPUS = "scopus"  # <-- добавить
    DBLP = "dblp"
    PUBMED = "pubmed"
    CROSSREF = "crossref"
    OPENALEX = "openalex"
    ORCID = "orcid"
    UNKNOWN = "unknown"


@dataclass
class ExternalIds:
    """Внешние идентификаторы"""
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    pubmed_id: Optional[str] = None
    pmc_id: Optional[str] = None
    dblp_id: Optional[str] = None
    semantic_scholar_id: Optional[str] = None
    scopus_id: Optional[str] = None
    mag_id: Optional[str] = None  # Microsoft Academic Graph
    acl_id: Optional[str] = None
    isbn: Optional[str] = None
    issn: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "ExternalIds":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Author:
    """Автор публикации (краткая информация)"""
    name: str
    author_id: Optional[str] = None  # ID в источнике
    orcid: Optional[str] = None
    affiliation: Optional[str] = None
    email: Optional[str] = None
    source: SourceType = SourceType.UNKNOWN

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "author_id": self.author_id,
            "orcid": self.orcid,
            "affiliation": self.affiliation,
            "email": self.email,
            "source": self.source.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Author":
        data = data.copy()
        if "source" in data:
            data["source"] = SourceType(data["source"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Publication:
    """Унифицированная публикация"""
    # Основные поля
    title: str
    authors: list[Author]
    year: Optional[int] = None
    date: Optional[datetime] = None

    # Идентификаторы
    source: SourceType = SourceType.UNKNOWN
    source_id: Optional[str] = None  # ID в источнике
    external_ids: ExternalIds = field(default_factory=ExternalIds)

    # Контент
    abstract: Optional[str] = None
    keywords: list[str] = field(default_factory=list)

    # Публикация
    venue: Optional[str] = None  # Журнал/конференция
    venue_type: Optional[str] = None  # journal, conference, workshop, book, etc.
    publisher: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None

    # Категории
    categories: list[str] = field(default_factory=list)
    primary_category: Optional[str] = None
    fields_of_study: list[str] = field(default_factory=list)

    # Метрики
    citation_count: int = 0
    reference_count: int = 0
    influential_citation_count: int = 0

    # Ссылки
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    source_url: Optional[str] = None

    # Дополнительно
    language: Optional[str] = None
    license: Optional[str] = None
    is_open_access: bool = False
    raw_data: dict = field(default_factory=dict)  # Оригинальные данные

    def __repr__(self):
        return f"Publication({self.year}: {self.title[:50]}... [{self.citation_count} cit.])"

    @property
    def author_names(self) -> list[str]:
        return [a.name for a in self.authors]

    @property
    def first_author(self) -> Optional[Author]:
        return self.authors[0] if self.authors else None

    @property
    def doi(self) -> Optional[str]:
        return self.external_ids.doi

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": [a.to_dict() for a in self.authors],
            "year": self.year,
            "date": self.date.isoformat() if self.date else None,
            "source": self.source.value,
            "source_id": self.source_id,
            "external_ids": self.external_ids.to_dict(),
            "abstract": self.abstract,
            "keywords": self.keywords,
            "venue": self.venue,
            "venue_type": self.venue_type,
            "publisher": self.publisher,
            "volume": self.volume,
            "issue": self.issue,
            "pages": self.pages,
            "categories": self.categories,
            "primary_category": self.primary_category,
            "fields_of_study": self.fields_of_study,
            "citation_count": self.citation_count,
            "reference_count": self.reference_count,
            "influential_citation_count": self.influential_citation_count,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "source_url": self.source_url,
            "language": self.language,
            "license": self.license,
            "is_open_access": self.is_open_access
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Publication":
        data = data.copy()

        if "authors" in data:
            data["authors"] = [Author.from_dict(a) for a in data["authors"]]
        if "source" in data:
            data["source"] = SourceType(data["source"])
        if "external_ids" in data:
            data["external_ids"] = ExternalIds.from_dict(data["external_ids"])
        if "date" in data and data["date"]:
            data["date"] = datetime.fromisoformat(data["date"])

        # Убираем лишние поля
        data.pop("raw_data", None)
        valid_fields = {f for f in cls.__dataclass_fields__}
        data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**data)


@dataclass
class Metrics:
    """Метрики автора"""
    citation_count: int = 0
    citation_count_recent: int = 0  # За последние 5 лет
    h_index: int = 0
    h_index_recent: int = 0
    i10_index: int = 0
    i10_index_recent: int = 0
    publication_count: int = 0

    # Дополнительные метрики
    g_index: Optional[int] = None
    m_index: Optional[float] = None  # h-index / years_active
    avg_citations_per_paper: float = 0.0

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "Metrics":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CoAuthor:
    """Соавтор с количеством совместных работ"""
    author: Author
    collaboration_count: int = 0

    def to_dict(self) -> dict:
        return {
            "author": self.author.to_dict(),
            "collaboration_count": self.collaboration_count
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CoAuthor":
        return cls(
            author=Author.from_dict(data["author"]),
            collaboration_count=data.get("collaboration_count", 0)
        )


@dataclass
class AuthorProfile:
    """Полный профиль автора"""
    # Идентификация
    name: str
    source: SourceType
    source_id: str

    # Внешние ID
    orcid: Optional[str] = None
    external_ids: ExternalIds = field(default_factory=ExternalIds)

    # Информация
    aliases: list[str] = field(default_factory=list)  # Альтернативные имена
    affiliation: Optional[str] = None
    affiliations_history: list[str] = field(default_factory=list)
    email_domain: Optional[str] = None
    homepage: Optional[str] = None

    # Интересы
    interests: list[str] = field(default_factory=list)
    fields_of_study: list[str] = field(default_factory=list)

    # Метрики
    metrics: Metrics = field(default_factory=Metrics)
    citations_per_year: dict[int, int] = field(default_factory=dict)
    publications_per_year: dict[int, int] = field(default_factory=dict)

    # Данные
    publications: list[Publication] = field(default_factory=list)
    coauthors: list[CoAuthor] = field(default_factory=list)

    # Даты
    first_publication_year: Optional[int] = None
    last_publication_year: Optional[int] = None

    # Мета
    url: Optional[str] = None
    photo_url: Optional[str] = None
    fetched_at: datetime = field(default_factory=datetime.now)
    raw_data: dict = field(default_factory=dict)

    def __repr__(self):
        return f"AuthorProfile({self.name}, {self.source.value}, {len(self.publications)} pubs)"

    @property
    def years_active(self) -> int:
        if self.first_publication_year and self.last_publication_year:
            return self.last_publication_year - self.first_publication_year
        return 0

    @property
    def top_publications(self) -> list[Publication]:
        return sorted(self.publications, key=lambda x: -x.citation_count)[:10]

    @property
    def top_coauthors(self) -> list[CoAuthor]:
        return sorted(self.coauthors, key=lambda x: -x.collaboration_count)[:10]

    @property
    def categories_count(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for pub in self.publications:
            for cat in pub.categories:
                counts[cat] = counts.get(cat, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1]))

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "source": self.source.value,
            "source_id": self.source_id,
            "orcid": self.orcid,
            "external_ids": self.external_ids.to_dict(),
            "aliases": self.aliases,
            "affiliation": self.affiliation,
            "affiliations_history": self.affiliations_history,
            "email_domain": self.email_domain,
            "homepage": self.homepage,
            "interests": self.interests,
            "fields_of_study": self.fields_of_study,
            "metrics": self.metrics.to_dict(),
            "citations_per_year": self.citations_per_year,
            "publications_per_year": self.publications_per_year,
            "publications": [p.to_dict() for p in self.publications],
            "coauthors": [c.to_dict() for c in self.coauthors],
            "first_publication_year": self.first_publication_year,
            "last_publication_year": self.last_publication_year,
            "url": self.url,
            "photo_url": self.photo_url,
            "fetched_at": self.fetched_at.isoformat(),
            "years_active": self.years_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AuthorProfile":
        data = data.copy()

        if "source" in data:
            data["source"] = SourceType(data["source"])
        if "external_ids" in data:
            data["external_ids"] = ExternalIds.from_dict(data["external_ids"])
        if "metrics" in data:
            data["metrics"] = Metrics.from_dict(data["metrics"])
        if "publications" in data:
            data["publications"] = [Publication.from_dict(p) for p in data["publications"]]
        if "coauthors" in data:
            data["coauthors"] = [CoAuthor.from_dict(c) for c in data["coauthors"]]
        if "fetched_at" in data and data["fetched_at"]:
            data["fetched_at"] = datetime.fromisoformat(data["fetched_at"])

        data.pop("raw_data", None)
        data.pop("years_active", None)
        valid_fields = {f for f in cls.__dataclass_fields__}
        data = {k: v for k, v in data.items() if k in valid_fields}

        return cls(**data)


@dataclass
class SearchResult:
    """Результат поиска"""
    query: str
    source: SourceType
    total_results: int
    items: list[Publication | AuthorProfile]
    page: int = 1
    per_page: int = 10

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "source": self.source.value,
            "total_results": self.total_results,
            "items": [item.to_dict() for item in self.items],
            "page": self.page,
            "per_page": self.per_page
        }