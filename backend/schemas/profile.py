from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class ProfileCreate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=2000)
    major: Optional[str] = Field(None, max_length=200)
    university: Optional[str] = Field(None, max_length=300)


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=2000)
    major: Optional[str] = Field(None, max_length=200)
    university: Optional[str] = Field(None, max_length=300)

class ProfileRead(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    major: Optional[str] = None
    university: Optional[str] = None

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
