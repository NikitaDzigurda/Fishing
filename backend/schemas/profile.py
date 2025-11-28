from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class ProfileCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class ProfileRead(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    model_config = {"from_attributes": True}