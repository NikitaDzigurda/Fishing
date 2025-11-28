from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


# Базовый класс с общими полями, чтобы не дублировать код
class ProfileBase(BaseModel):
    # Личные данные
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=2000)
    major: Optional[str] = Field(None, max_length=200)
    university: Optional[str] = Field(None, max_length=300)

    # Идентификаторы (теперь они доступны для редактирования)
    google_scholar_id: Optional[str] = Field(None, max_length=100)
    scopus_id: Optional[str] = Field(None, max_length=100)
    orcid: Optional[str] = Field(None, max_length=50)
    arxiv_name: Optional[str] = Field(None, max_length=200)
    semantic_scholar_id: Optional[str] = Field(None, max_length=100)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileRead(ProfileBase):
    id: int
    user_id: int

    citations_total: int = 0
    citations_recent: int = 0
    h_index: int = 0
    i10_index: int = 0
    publication_count: int = 0
    metrics_updated_at: Optional[datetime] = None

    # Scientific Identifiers
    google_scholar_id: Optional[str] = None
    scopus_id: Optional[str] = None
    orcid: Optional[str] = None
    arxiv_name: Optional[str] = None
    semantic_scholar_id: Optional[str] = None

    # Metrics
    # We use Optional[int] = 0 to handle cases where these might be NULL in the DB
    # or not yet calculated, defaulting them to 0 for the frontend.
    citations_total: Optional[int] = None
    citations_recent: Optional[int] = None
    h_index: Optional[int] = None
    i10_index: Optional[int] = None
    publication_count: Optional[int] = None
    
    metrics_updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
