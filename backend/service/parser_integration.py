# backend/services/parser_integration.py

import re
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from backend.models import Article, UserProfile


def normalize_title(title: str) -> str:
    """Нормализация названия для поиска дубликатов"""
    if not title:
        return ""
    return "".join(c.lower() for c in title if c.isalnum())


class ParserIntegrationService:
    """Сервис интеграции результатов парсера с БД"""

    @staticmethod
    def prepare_parser_input(profile: UserProfile) -> dict:
        """Подготовка входных данных для парсера"""
        name = f"{profile.first_name or ''} {profile.last_name or ''}".strip()

        return {
            "id": profile.user_id,
            "name": name or f"user_{profile.user_id}",
            "scholar_id": profile.google_scholar_id,
            "semantic_scholar_id": profile.semantic_scholar_id,
            "scopus_id": profile.scopus_id,
            "arxiv_name": profile.arxiv_name or name,
            "orcid": profile.orcid,
        }

    @staticmethod
    def save_parsing_results(
            db: Session,
            user_id: int,
            parsed_data: dict,
    ) -> dict:
        """
        Сохранение результатов парсинга в БД

        Returns:
            {"new": X, "updated": Y, "total": Z, "errors": [...]}
        """
        stats = {"new": 0, "updated": 0, "total": 0, "errors": []}

        profile = db.query(UserProfile).filter(
            UserProfile.user_id == user_id
        ).first()

        if not profile:
            stats["errors"].append(f"Profile not found for user {user_id}")
            return stats

        combined = parsed_data.get("combined", {})

        # === 1. Обновляем метрики профиля ===
        metrics = combined.get("metrics", {})
        profile.citations_total = metrics.get("citations", 0)
        profile.h_index = metrics.get("h_index", 0)
        profile.i10_index = metrics.get("i10_index", 0)
        profile.publication_count = metrics.get("publication_count", 0)
        profile.metrics_updated_at = datetime.utcnow()

        # === 2. Сохраняем публикации ===
        publications = combined.get("publications", [])
        stats["total"] = len(publications)

        for pub_data in publications:
            try:
                result = ParserIntegrationService._save_article(db, user_id, pub_data)
                if result == "new":
                    stats["new"] += 1
                elif result == "updated":
                    stats["updated"] += 1
            except Exception as e:
                stats["errors"].append(str(e))

        db.commit()
        return stats

    @staticmethod
    def _save_article(db: Session, user_id: int, pub_data: dict) -> str:
        """
        Сохранение одной статьи

        Returns: "new" | "updated" | "skipped"
        """
        title = pub_data.get("title", "").strip()
        if not title:
            return "skipped"

        title_norm = normalize_title(title)
        doi = pub_data.get("doi")
        if doi:
            doi = doi.lower().strip()

        year = pub_data.get("year")

        # === Поиск существующей статьи ===
        existing = None

        # По DOI
        if doi:
            existing = db.query(Article).filter(Article.doi == doi).first()

        # По названию + году
        if not existing and title_norm:
            # Ищем похожие
            candidates = db.query(Article).filter(Article.year == year).all()
            for candidate in candidates:
                if normalize_title(candidate.title) == title_norm:
                    existing = candidate
                    break

        # === Данные ===
        authors_list = pub_data.get("authors", [])
        sources = pub_data.get("sources", [])
        source = sources[0] if sources else None

        if existing:
            # === UPDATE ===
            if pub_data.get("citations", 0) > existing.citations:
                existing.citations = pub_data["citations"]

            if not existing.abstract and pub_data.get("abstract"):
                existing.abstract = pub_data["abstract"]

            if not existing.doi and doi:
                existing.doi = doi

            if not existing.url and pub_data.get("url"):
                existing.url = pub_data["url"]

            if not existing.venue and pub_data.get("venue"):
                existing.venue = pub_data["venue"]

            # Добавляем user_id
            current_ids = existing.author_user_ids or []
            if user_id not in current_ids:
                existing.author_user_ids = current_ids + [user_id]

            return "updated"

        else:
            # === INSERT ===
            article = Article(
                title=title,
                year=year,
                abstract=pub_data.get("abstract"),
                doi=doi,
                url=pub_data.get("url"),
                venue=pub_data.get("venue"),
                citations=pub_data.get("citations", 0),
                authors_list=authors_list,
                author_user_ids=[user_id],
                source=source,
            )

            # Извлекаем arxiv_id из URL
            url = pub_data.get("url", "") or ""
            if "arxiv.org" in url:
                match = re.search(r'arxiv\.org/(?:abs|pdf)/([^\s/?]+)', url)
                if match:
                    article.arxiv_id = match.group(1).replace(".pdf", "")

            db.add(article)
            return "new"