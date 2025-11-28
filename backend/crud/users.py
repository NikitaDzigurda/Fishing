from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    q = await db.execute(select(User).where(User.email == email))
    return q.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    q = await db.execute(select(User).where(User.id == user_id))
    return q.scalars().first()


async def create_user(db: AsyncSession, *, email: str, hashed_password: str, role: str = "observer") -> User:
    user = User(email=email, hashed_password=hashed_password, role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
