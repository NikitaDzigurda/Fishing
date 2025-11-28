from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import UserProfile


async def get_profile_by_user_id(db: AsyncSession, user_id: int) -> Optional[UserProfile]:
    q = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    return q.scalars().first()


async def create_or_update_profile(db: AsyncSession, user_id: int, first_name: str | None, last_name: str | None) -> UserProfile:
    existing = await get_profile_by_user_id(db, user_id)
    if existing:
        if first_name is not None:
            existing.first_name = first_name
        if last_name is not None:
            existing.last_name = last_name
        db.add(existing)
        await db.commit()
        await db.refresh(existing)
        return existing

    profile = UserProfile(user_id=user_id, first_name=first_name, last_name=last_name)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
