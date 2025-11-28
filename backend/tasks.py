# backend/tasks.py

import asyncio
from celery import shared_task

from backend.celery_app import celery_app
from backend.database import SessionLocal
from backend.models import UserProfile
from backend.service.parser_integration import ParserIntegrationService

from backend.parser.academic_api.main_parser import ParserConfig, parse_authors


@celery_app.task(bind=True, max_retries=3)
def parse_user_publications(
        self,
        user_id: int,
        use_arxiv: bool = True,
        use_semantic_scholar: bool = True,
        use_google_scholar: bool = False,
        use_scopus: bool = False,
        scopus_api_key: str = None,
):
    """Celery задача парсинга публикаций"""
    db = SessionLocal()

    try:
        profile = db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        if not profile:
            raise ValueError(f"Profile not found for user {user_id}")

        # Подготовка данных
        author_input = ParserIntegrationService.prepare_parser_input(profile)
        authors_dict = {user_id: author_input}

        config = ParserConfig(
            use_arxiv=use_arxiv,
            use_semantic_scholar=use_semantic_scholar,
            use_google_scholar=use_google_scholar,
            use_scopus=use_scopus,
            scopus_api_key=scopus_api_key,
        )

        # Запуск парсера
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            results = loop.run_until_complete(
                parse_authors(authors_dict, config, None)
            )
        finally:
            loop.close()

        # Сохранение
        if user_id in results:
            stats = ParserIntegrationService.save_parsing_results(
                db=db,
                user_id=user_id,
                parsed_data=results[user_id],
            )
            return {"status": "success", "user_id": user_id, "stats": stats}

        raise ValueError("No results from parser")

    except Exception as e:
        if "rate limit" in str(e).lower():
            raise self.retry(exc=e, countdown=60)
        raise

    finally:
        db.close()