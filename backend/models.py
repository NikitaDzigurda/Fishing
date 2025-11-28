# models.py

from __future__ import annotations

from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
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

    profile = relationship("UserProfile", back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Личные данные
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    bio = Column(Text, nullable=True)
    major = Column(String(200), nullable=True)
    university = Column(String(300), nullable=True)

    # Идентификаторы для парсинга научных баз
    google_scholar_id = Column(String(100), nullable=True)
    scopus_id = Column(String(100), nullable=True)
    orcid = Column(String(50), nullable=True)
    arxiv_name = Column(String(200), nullable=True)
    semantic_scholar_id = Column(String(100), nullable=True)

    # Метрики автора (агрегированные)
    citations_total = Column(Integer, default=0)
    citations_recent = Column(Integer, default=0)
    h_index = Column(Integer, default=0)
    i10_index = Column(Integer, default=0)
    publication_count = Column(Integer, default=0)
    metrics_updated_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="profile")


class Article(Base):
    """Статья/публикация"""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)

    # === Основная информация ===
    title = Column(String(1000), nullable=False, index=True)
    year = Column(Integer, nullable=True, index=True)
    abstract = Column(Text, nullable=True)

    # === Идентификаторы ===
    doi = Column(String(255), unique=True, nullable=True, index=True)
    arxiv_id = Column(String(100), unique=True, nullable=True, index=True)
    url = Column(String(500), nullable=True)

    # === Место публикации ===
    venue = Column(String(500), nullable=True)  # журнал/конференция

    # === Метрики ===
    citations = Column(Integer, default=0)

    # === Авторы ===
    # ID пользователей системы, которые являются авторами (JSON массив)
    # Пример: [1, 5, 23] или [] если никто не зарегистрирован
    author_user_ids = Column(JSON, default=list, nullable=False)

    # Все авторы как список строк (для отображения)
    # Пример: ["Yann LeCun", "Randall Balestriero", "Mike Rabbat"]
    authors_list = Column(JSON, default=list, nullable=False)

    # === Служебные поля ===
    source = Column(String(100), nullable=True)  # 'arxiv', 'google_scholar', 'scopus'
    external_id = Column(String(255), nullable=True)  # ID в источнике
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())