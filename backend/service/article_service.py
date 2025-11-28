# services/article_service.py

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from backend.models import Article, UserProfile
from backend.schemas.articles import ArticleCreate, ArticleUpdate


class ArticleService:

    @staticmethod
    def get_by_id(db: Session, article_id: int) -> Optional[Article]:
        return db.query(Article).filter(Article.id == article_id).first()

    @staticmethod
    def get_by_doi(db: Session, doi: str) -> Optional[Article]:
        return db.query(Article).filter(Article.doi == doi).first()

    @staticmethod
    def get_by_arxiv_id(db: Session, arxiv_id: str) -> Optional[Article]:
        return db.query(Article).filter(Article.arxiv_id == arxiv_id).first()

    @staticmethod
    def get_user_articles(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> list[Article]:
        """Получить все статьи пользователя"""
        # Ищем статьи где user_id есть в массиве author_user_ids
        # Для PostgreSQL с JSONB:
        return db.query(Article).filter(
            Article.author_user_ids.contains([user_id])
        ).offset(skip).limit(limit).all()

    @staticmethod
    def check_articles_exist(db: Session, user_id: int) -> bool:
        """Проверить есть ли статьи у пользователя в БД"""
        return db.query(Article).filter(
            Article.author_user_ids.contains([user_id])
        ).first() is not None

    @staticmethod
    def create(db: Session, article_data: ArticleCreate) -> Article:
        """Создать статью"""
        article = Article(**article_data.model_dump())
        db.add(article)
        db.commit()
        db.refresh(article)
        return article

    @staticmethod
    def bulk_create(db: Session, articles_data: list[ArticleCreate]) -> list[Article]:
        """Массовое создание статей"""
        articles = [Article(**data.model_dump()) for data in articles_data]
        db.add_all(articles)
        db.commit()
        return articles

    @staticmethod
    def update(db: Session, article_id: int, article_data: ArticleUpdate) -> Optional[Article]:
        """Обновить статью"""
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None

        update_data = article_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(article, field, value)

        db.commit()
        db.refresh(article)
        return article

    @staticmethod
    def link_user_to_article(db: Session, article_id: int, user_id: int) -> Optional[Article]:
        """Привязать пользователя к статье как автора"""
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None

        if user_id not in article.author_user_ids:
            article.author_user_ids = article.author_user_ids + [user_id]
            db.commit()
            db.refresh(article)

        return article

    @staticmethod
    def unlink_user_from_article(db: Session, article_id: int, user_id: int) -> Optional[Article]:
        """Отвязать пользователя от статьи"""
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None

        if user_id in article.author_user_ids:
            article.author_user_ids = [uid for uid in article.author_user_ids if uid != user_id]
            db.commit()
            db.refresh(article)

        return article

    @staticmethod
    def search(
            db: Session,
            query: Optional[str] = None,
            year_from: Optional[int] = None,
            year_to: Optional[int] = None,
            skip: int = 0,
            limit: int = 50
    ) -> list[Article]:
        """Поиск статей"""
        q = db.query(Article)

        if query:
            q = q.filter(
                or_(
                    Article.title.ilike(f"%{query}%"),
                    Article.abstract.ilike(f"%{query}%")
                )
            )

        if year_from:
            q = q.filter(Article.year >= year_from)
        if year_to:
            q = q.filter(Article.year <= year_to)

        return q.order_by(Article.year.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_with_registered_authors(db: Session, article_id: int) -> Optional[dict]:
        """Получить статью с информацией о зарегистрированных авторах"""
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            return None

        # Получаем профили зарегистрированных авторов
        registered_authors = []
        if article.author_user_ids:
            profiles = db.query(UserProfile).filter(
                UserProfile.user_id.in_(article.author_user_ids)
            ).all()

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