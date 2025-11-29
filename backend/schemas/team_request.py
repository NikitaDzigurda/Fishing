from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class RecommendedUser(BaseModel):
    id: int
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    major: Optional[str] = None

    class Config:
        from_attributes = True


class TeamRequestBase(BaseModel):
    title: str
    description: str
    required_roles: List[str]


class TeamRequestCreate(TeamRequestBase):
    pass


class TeamRequestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TeamRequestRead(TeamRequestBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime

    recommended_user_ids: List[int] = []
    recommendations_details: Optional[List[RecommendedUser]] = None

    class Config:
        from_attributes = True