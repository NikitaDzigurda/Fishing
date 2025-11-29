"""
Простой массовый парсинг авторов
"""

import asyncio
import re
from typing import Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

from backend.parser.academic_api import (
    ArxivParser,
    SemanticScholarParser,
    ScopusParser,
    GoogleScholarParser,
)
from backend.parser.academic_api.models import AuthorProfile


@dataclass
class ParserConfig:
    """Конфигурация парсеров"""
    scopus_api_key: Optional[str] = None
    semantic_scholar_api_key: Optional[str] = None

    # Какие источники использовать
    use_arxiv: bool = True
    use_semantic_scholar: bool = True
    use_scopus: bool = False
    use_google_scholar: bool = False


async def parse_authors(
        authors_dict: dict[int, dict],
        config: Optional[ParserConfig] = None,
        progress_callback: Optional[callable] = None
) -> dict[int, dict]:
    """
    Массовый парсинг авторов
    """
    config = config or ParserConfig()
    results = {}
    total = len(authors_dict)

    # Инициализация парсеров
    parsers = {}

    if config.use_arxiv:
        parsers["arxiv"] = ArxivParser()
        await parsers["arxiv"].init()

    if config.use_semantic_scholar:
        parsers["semantic_scholar"] = SemanticScholarParser(
            api_key=config.semantic_scholar_api_key
        )
        await parsers["semantic_scholar"].init()

    if config.use_scopus and config.scopus_api_key:
        parsers["scopus"] = ScopusParser(api_key=config.scopus_api_key)
        await parsers["scopus"].init()

    if config.use_google_scholar:
        parsers["google_scholar"] = GoogleScholarParser()  # Без прокси
        await parsers["google_scholar"].init()

    try:
        for idx, (key, author_data) in enumerate(authors_dict.items()):
            author_name = author_data.get("name", f"Author {key}")

            if progress_callback:
                progress_callback(idx + 1, total, author_name, "starting")

            result = {
                "input": author_data,
                "errors": {},
                "parsed_at": datetime.now().isoformat()
            }

            profiles = {}

            # arXiv
            if "arxiv" in parsers:
                arxiv_name = author_data.get("arxiv_name") or author_data.get("name")
                if arxiv_name:
                    try:
                        if progress_callback:
                            progress_callback(idx + 1, total, author_name, "arxiv")

                        profile = await parsers["arxiv"].get_author_profile(
                            author_name=arxiv_name
                        )
                        profiles["arxiv"] = profile
                        result["arxiv"] = _profile_to_dict(profile)
                    except Exception as e:
                        result["errors"]["arxiv"] = str(e)

            # Semantic Scholar
            if "semantic_scholar" in parsers:
                s2_id = author_data.get("semantic_scholar_id")
                s2_name = author_data.get("name")

                if s2_id or s2_name:
                    try:
                        if progress_callback:
                            progress_callback(idx + 1, total, author_name, "semantic_scholar")

                        profile = await parsers["semantic_scholar"].get_author_profile(
                            author_id=s2_id,
                            author_name=s2_name if not s2_id else None
                        )
                        profiles["semantic_scholar"] = profile
                        result["semantic_scholar"] = _profile_to_dict(profile)
                    except Exception as e:
                        result["errors"]["semantic_scholar"] = str(e)

            # Scopus
            if "scopus" in parsers:
                scopus_id = author_data.get("scopus_id")
                if scopus_id:
                    try:
                        if progress_callback:
                            progress_callback(idx + 1, total, author_name, "scopus")

                        profile = await parsers["scopus"].get_author_profile(
                            author_id=scopus_id
                        )
                        profiles["scopus"] = profile
                        result["scopus"] = _profile_to_dict(profile)
                    except Exception as e:
                        result["errors"]["scopus"] = str(e)

            # Google Scholar
            if "google_scholar" in parsers:
                scholar_id = author_data.get("scholar_id") or author_data.get("google_scholar_id")
                if scholar_id:
                    try:
                        if progress_callback:
                            progress_callback(idx + 1, total, author_name, "google_scholar")

                        profile = await parsers["google_scholar"].get_author_profile(
                            author_id=scholar_id,
                            fill_publications=True
                        )
                        profiles["google_scholar"] = profile
                        result["google_scholar"] = _profile_to_dict(profile)
                    except Exception as e:
                        result["errors"]["google_scholar"] = str(e)

            # Объединяем данные
            result["combined"] = _combine_profiles(profiles, author_data)

            results[key] = result

            if progress_callback:
                progress_callback(idx + 1, total, author_name, "done")

    finally:
        for parser in parsers.values():
            await parser.close()

    return results


def _profile_to_dict(profile: AuthorProfile) -> dict:
    """Конвертация профиля в словарь"""
    return {
        "name": profile.name,
        "source": profile.source.value,
        "source_id": profile.source_id,
        "affiliation": profile.affiliation,
        "orcid": profile.orcid,
        "homepage": profile.homepage,
        "interests": profile.interests,

        "metrics": {
            "citations": profile.metrics.citation_count,
            "citations_recent": profile.metrics.citation_count_recent,
            "h_index": profile.metrics.h_index,
            "h_index_recent": profile.metrics.h_index_recent,
            "i10_index": profile.metrics.i10_index,
            "publication_count": profile.metrics.publication_count,
        },

        "citations_per_year": profile.citations_per_year,
        "publications_per_year": profile.publications_per_year,
        "first_publication_year": profile.first_publication_year,
        "last_publication_year": profile.last_publication_year,
        "years_active": profile.years_active,

        "publications": [
            {
                "title": p.title,
                "year": p.year,
                "citations": p.citation_count,
                "abstract": p.abstract,
                "venue": p.venue,
                "doi": p.external_ids.doi,
                "url": p.url,
                "authors": [a.name for a in p.authors]
            }
            for p in profile.publications
        ],
        "top_coauthors": [
            {
                "name": c.author.name,
                "collaborations": c.collaboration_count
            }
            for c in profile.top_coauthors
        ]
    }


def _normalize_title(title: str) -> str:
    """Нормализация названия для поиска дубликатов"""
    if not title:
        return ""
    # Приводим к нижнему регистру и оставляем только буквы и цифры
    return "".join(c.lower() for c in title if c.isalnum())


def _combine_profiles(profiles: dict[str, AuthorProfile], input_data: dict) -> dict:
    """Объединение данных из разных источников, включая слияние публикаций"""

    combined = {
        "name": input_data.get("name"),
        "affiliation": None,
        "orcid": None,
        "homepage": None,
        "interests": [],

        "metrics": {
            "citations": 0,
            "h_index": 0,
            "i10_index": 0,
            "publication_count": 0
        },

        "sources_found": list(profiles.keys()),
        "total_publications_all_sources": 0,
        "publications": []  # Сюда сложим уникальные
    }

    # Приоритет для метаданных и метрик
    # Google Scholar обычно имеет самые высокие цифры цитирования, но плохие метаданные
    # Semantic Scholar / Scopus имеют хорошие метаданные
    priority = ["google_scholar", "scopus", "semantic_scholar", "arxiv"]

    # === 1. Объединение метаданных ===
    for source in priority:
        if source in profiles:
            p = profiles[source]

            if not combined["affiliation"] and p.affiliation:
                combined["affiliation"] = p.affiliation

            if not combined["orcid"] and p.orcid:
                combined["orcid"] = p.orcid

            if not combined["homepage"] and p.homepage:
                combined["homepage"] = p.homepage

            combined["interests"] = list(set(combined["interests"] + p.interests))

            # Берем максимальные метрики
            if p.metrics.citation_count > combined["metrics"]["citations"]:
                combined["metrics"]["citations"] = p.metrics.citation_count
            if p.metrics.h_index > combined["metrics"]["h_index"]:
                combined["metrics"]["h_index"] = p.metrics.h_index
            if p.metrics.i10_index > combined["metrics"]["i10_index"]:
                combined["metrics"]["i10_index"] = p.metrics.i10_index
            if p.metrics.publication_count > combined["metrics"]["publication_count"]:
                combined["metrics"]["publication_count"] = p.metrics.publication_count

            combined["total_publications_all_sources"] += len(p.publications)

    # === 2. Объединение публикаций (Дедупликация) ===
    merged_publications = []

    # Словари для быстрого поиска дублей
    seen_dois = {}    # doi -> index in merged_publications
    seen_titles = {}  # normalized_title -> index in merged_publications

    # Проходим по источникам.
    # Для метаданных статей лучше Scopus/Semantic Scholar, поэтому порядок такой:
    merge_priority = ["scopus", "semantic_scholar", "google_scholar", "arxiv"]

    for source in merge_priority:
        if source not in profiles:
            continue

        profile = profiles[source]
        for pub in profile.publications:
            # Получаем ключи для матчинга
            doi = pub.external_ids.doi
            if doi:
                doi = doi.lower().strip()

            norm_title = _normalize_title(pub.title)
            if not norm_title:
                continue

            # Проверяем, есть ли уже такая статья
            match_index = -1

            if doi and doi in seen_dois:
                match_index = seen_dois[doi]
            elif norm_title in seen_titles:
                match_index = seen_titles[norm_title]

            # Данные текущей статьи для сохранения
            pub_dict = {
                "title": pub.title,
                "year": pub.year,
                "citations": pub.citation_count,
                "abstract": pub.abstract,
                "venue": pub.venue,
                "doi": pub.external_ids.doi,
                "url": pub.url,
                "authors": [a.name for a in pub.authors],
                "sources": [source] # Отслеживаем, где нашли
            }

            if match_index > -1:
                # === MERGE (Обновление существующей) ===
                existing = merged_publications[match_index]

                # Берем максимальное цитирование
                existing["citations"] = max(existing["citations"], pub_dict["citations"])

                # Если в текущей есть abstract, а в сохраненной нет - берем текущий
                if not existing["abstract"] and pub_dict["abstract"]:
                    existing["abstract"] = pub_dict["abstract"]

                # Если в текущей есть DOI, а в сохраненной нет
                if not existing["doi"] and pub_dict["doi"]:
                    existing["doi"] = pub_dict["doi"]
                    if pub_dict["doi"]:
                        seen_dois[pub_dict["doi"].lower().strip()] = match_index

                # Если в текущей есть URL, а в сохраненной нет
                if not existing["url"] and pub_dict["url"]:
                    existing["url"] = pub_dict["url"]

                # Если в текущей есть venue, а в сохраненной нет
                if not existing["venue"] and pub_dict["venue"]:
                    existing["venue"] = pub_dict["venue"]

                # Если название длиннее (вероятно полнее), берем его
                if len(pub_dict["title"]) > len(existing["title"]):
                     existing["title"] = pub_dict["title"]

                if source not in existing["sources"]:
                    existing["sources"].append(source)

            else:
                # === INSERT (Новая статья) ===
                merged_publications.append(pub_dict)
                new_index = len(merged_publications) - 1

                seen_titles[norm_title] = new_index
                if doi:
                    seen_dois[doi] = new_index

    # Сортируем итоговый список по цитированиям
    merged_publications.sort(key=lambda x: -(x["citations"] or 0))

    combined["publications"] = merged_publications

    # Пересчитываем метрики на основе объединенных данных (опционально)
    # Например, если мы доверяем сумме уникальных статей больше, чем цифре из профиля
    # combined["metrics"]["publication_count"] = len(merged_publications)

    return combined


def parse_authors_sync(
        authors_dict: dict[int, dict],
        config: Optional[ParserConfig] = None,
        progress_callback: Optional[callable] = None
) -> dict[int, dict]:
    """Синхронная версия parse_authors"""
    return asyncio.run(parse_authors(authors_dict, config, progress_callback))