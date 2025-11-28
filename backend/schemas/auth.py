from __future__ import annotations

from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class UserCreate(BaseModel):
	email: EmailStr
	password: str
	role: Optional[str] = "observer"


class UserRead(BaseModel):
	id: int
	email: str
	role: str
	is_active: bool
	model_config = {"from_attributes": True}


class Token(BaseModel):
	access_token: str
	refresh_token: str
	token_type: str = "bearer"


class TokenPayload(BaseModel):
	sub: Optional[str] = None
	exp: Optional[int] = None


class UserLogin(BaseModel):
	email: EmailStr
	password: str


class RefreshTokenRequest(BaseModel):
	refresh_token: str
