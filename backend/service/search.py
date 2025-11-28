from typing import List
from fastapi import Depends
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import UserProfile

class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_profiles(self, query: str, limit: int = 20, offset: int = 0) -> List[UserProfile]:
        """
        Searches UserProfile table only. 
        Does NOT join User table.
        """
        stmt = select(UserProfile)

        if query:
            search_term = f"%{query}%"
            stmt = stmt.where(
                or_(
                    UserProfile.first_name.ilike(search_term),
                    UserProfile.last_name.ilike(search_term),
                    UserProfile.university.ilike(search_term),
                    UserProfile.major.ilike(search_term),
                )
            )

        # Apply Pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await self.db.execute(stmt)
        return result.scalars().all()
