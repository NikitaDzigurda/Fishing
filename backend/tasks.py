import asyncio
from typing import Optional
from datetime import datetime

from sqlalchemy import select

from backend.celery_app import celery_app
from backend.database import SessionLocal
from backend.models import User, UserProfile, Article
from backend.parser.academic_api.main_parser import ParserConfig, parse_authors


@celery_app.task(bind=True, max_retries=3)
def parse_user_publications(
        self,
        user_id: int,
        use_arxiv: bool = True,
        use_semantic_scholar: bool = True,
        use_google_scholar: bool = False,
        use_scopus: bool = False,
        scopus_api_key: Optional[str] = None,
):
    """
    Celery task для парсинга публикаций пользователя.
    """
    db = SessionLocal()

    try:
        # 1. Получаем профиль
        profile = db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        ).scalar_one_or_none()

        if not profile:
            return {"status": "error", "message": "Profile not found"}

        # 2. Формируем имя автора
        author_name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()
        if not author_name:
            user = db.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            author_name = user.email.split("@")[0] if user else f"User {user_id}"

        # 3. Данные автора для парсера
        authors = {
            user_id: {
                "id": user_id,
                "name": author_name,
                "scholar_id": profile.google_scholar_id,
                "semantic_scholar_id": profile.semantic_scholar_id,
                "arxiv_name": profile.arxiv_name or author_name,
                "scopus_id": profile.scopus_id,
                "orcid": profile.orcid,
            }
        }

        # 4. Конфиг парсера
        config = ParserConfig(
            use_arxiv=use_arxiv,
            use_semantic_scholar=use_semantic_scholar,
            use_google_scholar=use_google_scholar,
            use_scopus=use_scopus,
            scopus_api_key=scopus_api_key,
        )

        # 5. Progress callback для Celery
        def progress_callback(current, total, name, status):
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': current,
                    'total': total,
                    'author': name,
                    'status': status
                }
            )

        # 6. Запускаем async парсинг в sync контексте
        results = asyncio.run(
            parse_authors(authors, config, progress_callback)
        )

        if user_id not in results:
            return {"status": "error", "message": "No results returned"}

        author_data = results[user_id]
        combined = author_data.get("combined", {})
        metrics = combined.get("metrics", {})
        publications = combined.get("publications", [])

        # 7. Обновляем метрики в профиле
        profile.citations_total = metrics.get("citations", 0)
        profile.citations_recent = metrics.get("citations_recent", 0)
        profile.h_index = metrics.get("h_index", 0)
        profile.i10_index = metrics.get("i10_index", 0)
        profile.publication_count = len(publications)
        profile.metrics_updated_at = datetime.utcnow()

        # 8. Сохраняем статьи
        articles_added = 0
        articles_updated = 0

        for pub in publications:
            existing = _find_existing_article(db, pub)

            if existing:
                _update_article(existing, pub, user_id)
                articles_updated += 1
            else:
                article = _create_article(pub, user_id)
                db.add(article)
                articles_added += 1

        db.commit()

        return {
            "status": "success",
            "user_id": user_id,
            "metrics": {
                "citations_total": profile.citations_total,
                "h_index": profile.h_index,
                "i10_index": profile.i10_index,
                "publication_count": profile.publication_count,
            },
            "articles_added": articles_added,
            "articles_updated": articles_updated,
            "sources_found": combined.get("sources_found", []),
            "errors": author_data.get("errors", []),
        }

    except Exception as e:
        db.rollback()
        # Логируем ошибку
        print(f"Error parsing publications for user {user_id}: {e}")
        raise self.retry(exc=e, countdown=60)

    finally:
        db.close()


def _find_existing_article(db, pub: dict) -> Optional[Article]:
    """Ищем существующую статью"""

    if pub.get("doi"):
        article = db.execute(
            select(Article).where(Article.doi == pub["doi"])
        ).scalar_one_or_none()
        if article:
            return article

    if pub.get("arxiv_id"):
        article = db.execute(
            select(Article).where(Article.arxiv_id == pub["arxiv_id"])
        ).scalar_one_or_none()
        if article:
            return article

    if pub.get("title") and pub.get("year"):
        article = db.execute(
            select(Article).where(
                Article.title == pub["title"],
                Article.year == pub["year"]
            )
        ).scalar_one_or_none()
        if article:
            return article

    return None


def _update_article(article: Article, pub: dict, user_id: int) -> None:
    """Обновляем существующую статью"""
    article.citations = max(article.citations or 0, pub.get("citations", 0))

    current_ids = article.author_user_ids or []
    if user_id not in current_ids:
        article.author_user_ids = current_ids + [user_id]

    if not article.abstract and pub.get("abstract"):
        article.abstract = pub["abstract"]
    if not article.doi and pub.get("doi"):
        article.doi = pub["doi"]
    if not article.url and pub.get("url"):
        article.url = pub["url"]


def _create_article(pub: dict, user_id: int) -> Article:
    """Создаём новую статью"""
    return Article(
        title=pub.get("title", "Untitled"),
        year=pub.get("year"),
        abstract=pub.get("abstract"),
        doi=pub.get("doi"),
        arxiv_id=pub.get("arxiv_id"),
        url=pub.get("url"),
        venue=pub.get("venue"),
        citations=pub.get("citations", 0),
        author_user_ids=[user_id],
        authors_list=pub.get("authors", []),
        source=pub.get("source"),
        external_id=pub.get("external_id"),
    )