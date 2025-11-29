from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select, func
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from backend.database import get_db
from backend.models import User, UserProfile, Article
from backend.dependencies import get_current_user
from backend.tasks import parse_user_publications

router = APIRouter(prefix="/api/v1/articles", tags=["articles"])


class ArticleResponse(BaseModel):
    id: int
    title: str
    year: Optional[int]
    venue: Optional[str]
    citations: int
    authors_list: list[str]
    author_user_ids: list[int]
    doi: Optional[str]
    url: Optional[str]
    source: Optional[str]

    class Config:
        from_attributes = True


class UserArticlesResponse(BaseModel):
    articles: list[ArticleResponse]
    total: int
    metrics: dict


class StartParsingRequest(BaseModel):
    use_arxiv: bool = True
    use_semantic_scholar: bool = True
    use_google_scholar: bool = False
    use_scopus: bool = False
    scopus_api_key: Optional[str] = None


# === Эндпоинты ===

@router.get("/user/{user_id}", response_model=UserArticlesResponse)
async def get_user_articles(
        user_id: int,
        db: AsyncSession = Depends(get_db),
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
):
    # --- 1. Получаем профиль ---
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    # --- 2. Запрашиваем статьи ---

    # 👇 ИСПРАВЛЕНО: Оставили только один запрос, без cast(JSONB)
    total_result = await db.execute(
        select(func.count(Article.id)).where(
            Article.author_user_ids.contains([user_id])
        )
    )
    total = total_result.scalar() or 0

    # сами статьи
    articles_result = await db.execute(
        select(Article)
        .where(Article.author_user_ids.contains([user_id]))
        .order_by(desc(Article.citations))
        .offset(skip)
        .limit(limit)
    )
    articles = articles_result.scalars().all()

    return {
        "articles": articles,
        "total": total,
        "metrics": {
            "citations_total": profile.citations_total,
            "h_index": profile.h_index,
            "i10_index": profile.i10_index,
            "publication_count": profile.publication_count,
            "updated_at": (
                profile.metrics_updated_at.isoformat()
                if profile.metrics_updated_at else None
            ),
        }
    }


@router.post("/user/{user_id}/parse")
async def start_parsing(
        user_id: int,
        request: StartParsingRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
):
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    has_ids = any([
        profile.google_scholar_id,
        profile.semantic_scholar_id,
        profile.arxiv_name,
        profile.first_name and profile.last_name,
    ])

    if not has_ids:
        raise HTTPException(
            status_code=400,
            detail="Profile needs at least one identifier"
        )

    task = parse_user_publications.delay(
        user_id=user_id,
        use_arxiv=request.use_arxiv,
        use_semantic_scholar=request.use_semantic_scholar,
        use_google_scholar=request.use_google_scholar,
        use_scopus=request.use_scopus,
        scopus_api_key=request.scopus_api_key,
    )

    return {
        "task_id": task.id,
        "status": "started",
        "message": "Parsing started"
    }


@router.get("/parse-status/{task_id}")
async def get_parse_status(task_id: str):
    """Проверить статус задачи парсинга"""
    from backend.celery_app import celery_app

    result = celery_app.AsyncResult(task_id)

    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(article_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Article).where(Article.id == article_id)
    )
    article = result.scalar_one_or_none()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return article


@router.get("/", response_model=list[ArticleResponse])
async def search_articles(
        q: Optional[str] = None,
        year: Optional[int] = None,
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=200),
        db: AsyncSession = Depends(get_db),
):
    query = select(Article)

    if q:
        query = query.where(Article.title.ilike(f"%{q}%"))
    if year:
        query = query.where(Article.year == year)

    query = query.order_by(desc(Article.citations)).offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()