from typing import Optional
from pydantic import BaseModel, ConfigDict


class ProfileSearchResult(BaseModel):
    id: int
    user_id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    university: Optional[str] = None
    major: Optional[str] = None
    bio: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
    