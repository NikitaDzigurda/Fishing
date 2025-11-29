from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from backend.models import User, Article
from backend.service.recommendations.recsys import RecSys
from backend.settings import settings

class RecSysService:
    """
    Singleton Manager for the RecSys class.
    Fetches SQL data -> Converts to Dict -> Initializes RecSys.
    """
    _instance: Optional[RecSys] = None

    @classmethod
    def get_instance(cls) -> Optional[RecSys]:
        return cls._instance

    @classmethod
    async def load_and_init(cls, db: AsyncSession):
        """
        Loads data from DB, formats it, and initializes the ML engine.
        """
        print(" [ML] Starting Data Sync from Postgres...")

        # 1. Fetch Users + Profiles
        # We need users who have a profile to be recommendable
        result_users = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.is_active == True)
        )
        users = result_users.scalars().all()

        # 2. Fetch All Articles
        # We need articles to build the interaction graph
        result_articles = await db.execute(select(Article))
        articles = result_articles.scalars().all()

        # 3. Transform to RecSys Dictionary Format
        # Format: { user_id: { "combined": { "name":..., "interests":..., "publications": [...] } } }
        authors_data = {}

        # Initialize entries for all users
        for u in users:
            if not u.profile:
                continue

            # Construct display name
            full_name = f"{u.profile.first_name or ''} {u.profile.last_name or ''}".strip()
            if not full_name:
                full_name = f"User {u.id}"

            # Construct interests (Major + Bio keywords could go here)
            interests = []
            if u.profile.major:
                interests.append(u.profile.major)
            
            authors_data[u.id] = {
                "combined": {
                    "name": full_name,
                    "interests": interests,
                    "bio": u.profile.bio, # RecSys uses this for embedding
                    "publications": []    # To be populated next
                }
            }

        # 4. Map Articles to Users
        count_pubs = 0
        for art in articles:
            # Your Article model has 'author_user_ids' as JSON list: [101, 102]
            user_ids = art.author_user_ids or []

            # Create the publication dict expected by RecSys
            pub_dict = {
                "title": art.title,
                "abstract": art.abstract or "",
                "year": art.year,
                "authors": user_ids # Crucial for co-authorship logic in RecSys
            }

            # Distribute this publication to all its authors in our dict
            for uid in user_ids:
                # Ensure JSON integers match the dictionary keys (int)
                if uid in authors_data:
                    authors_data[uid]["combined"]["publications"].append(pub_dict)
                    count_pubs += 1

        print(f" [ML] Data loaded: {len(authors_data)} authors, {count_pubs} links.")

        # 5. Instantiate RecSys
        # This triggers internal indexing (Vector DB build + Graph build)
        try:
            cls._instance = RecSys(
                authors_data=authors_data,
                gemini_api_key=settings.GEMINI_API_KEY
            )
            print(" [ML] RecSys initialized successfully.")
        except Exception as e:
            print(f" [ML] Failed to initialize RecSys: {e}")
            raise e