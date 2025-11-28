from __future__ import annotations

from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.sql import func

from backend.database import Base


class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, index=True)
	email = Column(String(255), unique=True, nullable=False, index=True)
	hashed_password = Column(String(255), nullable=False)
	role = Column(String(50), nullable=False, default="observer")
	is_active = Column(Boolean, default=True, nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

