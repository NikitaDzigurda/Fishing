# services/article_service.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, update
from typing import Optional, List

from backend.models import Article, UserProfile


# from backend.schemas.articles import ArticleCreate, ArticleUpdate
# (убедись, что схемы существуют или используй dict)

class ArticleService:

    @staticmethod
    async def get_by_id(db: AsyncSession, article_id: int) -> Optional[Article]:
        result = await db.execute(select(Article).where(Article.id == article_id))
        return result.scalars().first()

    @staticmethod
    async def get_by_doi(db: AsyncSession, doi: str) -> Optional[Article]:
        result = await db.execute(select(Article).where(Article.doi == doi))
        return result.scalars().first()

    @staticmethod
    async def get_by_arxiv_id(db: AsyncSession, arxiv_id: str) -> Optional[Article]:
        result = await db.execute(select(Article).where(Article.arxiv_id == arxiv_id))
        return result.scalars().first()

    @staticmethod
    async def get_user_articles(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100) -> List[Article]:
        """Получить все статьи пользователя"""
        # Используем contains для ARRAY
        query = select(Article).where(
            Article.author_user_ids.contains([user_id])
        ).offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def check_articles_exist(db: AsyncSession, user_id: int) -> bool:
        """Проверить есть ли статьи у пользователя в БД"""
        query = select(Article).where(Article.author_user_ids.contains([user_id])).limit(1)
        result = await db.execute(query)
        return result.scalars().first() is not None

    @staticmethod
    async def create(db: AsyncSession, article_data: dict) -> Article:  # или ArticleCreate
        """Создать статью"""
        article = Article(**article_data)  # .model_dump() если Pydantic
        db.add(article)
        await db.commit()
        await db.refresh(article)
        return article

    # Bulk create в async лучше делать через insert(), но для простоты можно циклом (медленнее)
    # или db.add_all() если объектов немного

    @staticmethod
    async def update(db: AsyncSession, article_id: int, article_data: dict) -> Optional[Article]:
        """Обновить статью"""
        article = await ArticleService.get_by_id(db, article_id)
        if not article:
            return None

        # update_data = article_data.model_dump(exclude_unset=True) # если Pydantic
        for field, value in article_data.items():
            setattr(article, field, value)

        db.add(article)
        await db.commit()
        await db.refresh(article)
        return article

    @staticmethod
    async def link_user_to_article(db: AsyncSession, article_id: int, user_id: int) -> Optional[Article]:
        """Привязать пользователя к статье как автора"""
        article = await ArticleService.get_by_id(db, article_id)
        if not article:
            return None

        # Для ARRAY нужно создать новый список, чтобы SQLAlchemy увидел изменения
        current_ids = list(article.author_user_ids)
        if user_id not in current_ids:
            article.author_user_ids = current_ids + [user_id]
            db.add(article)  # Важно пометить объект как измененный
            await db.commit()
            await db.refresh(article)

        return article

    @staticmethod
    async def unlink_user_from_article(db: AsyncSession, article_id: int, user_id: int) -> Optional[Article]:
        """Отвязать пользователя от статьи"""
        article = await ArticleService.get_by_id(db, article_id)
        if not article:
            return None

        current_ids = list(article.author_user_ids)
        if user_id in current_ids:
            article.author_user_ids = [uid for uid in current_ids if uid != user_id]
            db.add(article)
            await db.commit()
            await db.refresh(article)

        return article

    @staticmethod
    async def search(
            db: AsyncSession,
            query: Optional[str] = None,
            year_from: Optional[int] = None,
            year_to: Optional[int] = None,
            skip: int = 0,
            limit: int = 50
    ) -> List[Article]:
        """Поиск статей"""
        q = select(Article)

        if query:
            q = q.where(
                or_(
                    Article.title.ilike(f"%{query}%"),
                    Article.abstract.ilike(f"%{query}%")
                )
            )

        if year_from:
            q = q.where(Article.year >= year_from)
        if year_to:
            q = q.where(Article.year <= year_to)

        q = q.order_by(Article.year.desc()).offset(skip).limit(limit)

        result = await db.execute(q)
        return result.scalars().all()

    @staticmethod
    async def get_with_registered_authors(db: AsyncSession, article_id: int) -> Optional[dict]:
        """Получить статью с информацией о зарегистрированных авторах"""
        article = await ArticleService.get_by_id(db, article_id)
        if not article:
            return None

        # Получаем профили зарегистрированных авторов
        registered_authors = []
        if article.author_user_ids:
            # Важно: .in_ ожидает список/tuple
            ids_list = list(article.author_user_ids)
            if ids_list:
                q = select(UserProfile).where(UserProfile.user_id.in_(ids_list))
                result = await db.execute(q)
                profiles = result.scalars().all()

                registered_authors = [
                    {
                        "user_id": p.user_id,
                        "first_name": p.first_name,
                        "last_name": p.last_name,
                        "university": p.university
                    }
                    for p in profiles
                ]

        return {
            "article": article,
            "registered_authors": registered_authors
        }