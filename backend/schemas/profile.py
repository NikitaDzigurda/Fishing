from __future__ import annotations

from pydantic import BaseModel, Field
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
    contact_info: Optional[str] = Field(None, max_length=300)

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

    model_config = {"from_attributes": True}