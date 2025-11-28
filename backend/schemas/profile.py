from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


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

    model_config = {"from_attributes": True}