# crud/authors_profile.py
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import UserProfile


async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
    q = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return q.scalars().first()


async def create_profile(
        db: AsyncSession,
        user_id: int,
        # Основные поля
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        bio: Optional[str] = None,
        major: Optional[str] = None,
        university: Optional[str] = None,
        # Новые поля
        google_scholar_id: Optional[str] = None,
        scopus_id: Optional[str] = None,
        orcid: Optional[str] = None,
        arxiv_name: Optional[str] = None,
        semantic_scholar_id: Optional[str] = None,
) -> UserProfile:
    profile = UserProfile(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        bio=bio,
        major=major,
        university=university,
        google_scholar_id=google_scholar_id,
        scopus_id=scopus_id,
        orcid=orcid,
        arxiv_name=arxiv_name,
        semantic_scholar_id=semantic_scholar_id,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def create_or_update_profile(
        db: AsyncSession,
        user_id: int,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        bio: Optional[str] = None,
        major: Optional[str] = None,
        university: Optional[str] = None,
        google_scholar_id: Optional[str] = None,
        scopus_id: Optional[str] = None,
        orcid: Optional[str] = None,
        arxiv_name: Optional[str] = None,
        semantic_scholar_id: Optional[str] = None,
) -> UserProfile:
    existing = await get_profile_by_user_id(db, user_id)

    if existing:
        if first_name is not None: existing.first_name = first_name
        if last_name is not None: existing.last_name = last_name
        if bio is not None: existing.bio = bio
        if major is not None: existing.major = major
        if university is not None: existing.university = university

        if google_scholar_id is not None: existing.google_scholar_id = google_scholar_id
        if scopus_id is not None: existing.scopus_id = scopus_id
        if orcid is not None: existing.orcid = orcid
        if arxiv_name is not None: existing.arxiv_name = arxiv_name
        if semantic_scholar_id is not None: existing.semantic_scholar_id = semantic_scholar_id

        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing

    # Если профиля нет - создаем
    return await create_profile(
        db, user_id, first_name, last_name, bio, major, university,
        google_scholar_id, scopus_id, orcid, arxiv_name, semantic_scholar_id
    )