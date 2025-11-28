from __future__ import annotations

from sqlalchemy import Column, String, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class User(Base):
	__tablename__ = "users"

	id = Column(Integer, primary_key=True, index=True)
	email = Column(String(255), unique=True, nullable=False, index=True)
	hashed_password = Column(String(255), nullable=False)
	role = Column(String(50), nullable=False, default="observer")
	is_active = Column(Boolean, default=True, nullable=False)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserProfile(Base):
	__tablename__ = "user_profiles"

	id = Column(Integer, primary_key=True, index=True)
	user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
	first_name = Column(String(150), nullable=True)
	last_name = Column(String(150), nullable=True)
	created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

	user = relationship("User", back_populates="profile", uselist=False)


User.profile = relationship("UserProfile", back_populates="user", uselist=False)

