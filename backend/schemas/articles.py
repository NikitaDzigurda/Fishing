# schemas/article.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ArticleBase(BaseModel):
    title: str
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    url: Optional[str] = None
    venue: Optional[str] = None
    citations: int = 0
    authors_list: list[str] = []


class ArticleCreate(ArticleBase):
    author_user_ids: list[int] = []
    source: Optional[str] = None
    external_id: Optional[str] = None


class ArticleUpdate(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    venue: Optional[str] = None
    citations: Optional[int] = None
    author_user_ids: Optional[list[int]] = None
    authors_list: Optional[list[str]] = None


class ArticleResponse(ArticleBase):
    id: int
    author_user_ids: list[int]
    source: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class ArticleWithAuthorsResponse(ArticleResponse):
    """Статья с информацией о зарегистрированных авторах"""
    registered_authors: list[dict] = []  # [{id, first_name, last_name, university}]