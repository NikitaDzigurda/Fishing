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
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        bio: Optional[str] = None,
        major: Optional[str] = None,
        university: Optional[str] = None
) -> UserProfile:
    profile = UserProfile(
        user_id=user_id,
        first_name=first_name,
        last_name=last_name,
        bio=bio,
        major=major,
        university=university
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


async def update_profile(
        db: AsyncSession,
        profile: UserProfile,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        bio: Optional[str] = None,
        major: Optional[str] = None,
        university: Optional[str] = None
) -> UserProfile:

    if first_name is not None:
        profile.first_name = first_name
    if last_name is not None:
        profile.last_name = last_name
    if bio is not None:
        profile.bio = bio
    if major is not None:
        profile.major = major
    if university is not None:
        profile.university = university

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
        university: Optional[str] = None
) -> UserProfile:
    """Создать или обновить профиль"""
    existing = await get_profile_by_user_id(db, user_id)

    if existing:
        return await update_profile(
            db, existing,
            first_name=first_name,
            last_name=last_name,
            bio=bio,
            major=major,
            university=university
        )

    return await create_profile(
        db, user_id,
        first_name=first_name,
        last_name=last_name,
        bio=bio,
        major=major,
        university=university
    )