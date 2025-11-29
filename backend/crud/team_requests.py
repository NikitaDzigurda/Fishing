# backend/crud/team_requests.py

from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import TeamRequest

async def create_team_request(
    db: AsyncSession,
    user_id: int,
    title: str,
    description: str,
    required_roles: list[str]
) -> TeamRequest:
    request = TeamRequest(
        user_id=user_id,
        title=title,
        description=description,
        required_roles=required_roles,
        recommended_user_ids=[] # При создании рекомендаций пока нет
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request

async def get_user_requests(db: AsyncSession, user_id: int) -> List[TeamRequest]:
    """Получить все заявки конкретного пользователя"""
    q = await db.execute(
        select(TeamRequest)
        .where(TeamRequest.user_id == user_id)
        .order_by(desc(TeamRequest.created_at))
    )
    return q.scalars().all()

async def get_request_by_id(db: AsyncSession, request_id: int) -> Optional[TeamRequest]:
    q = await db.execute(select(TeamRequest).where(TeamRequest.id == request_id))
    return q.scalars().first()

async def update_request_recommendations(
    db: AsyncSession,
    request_id: int,
    user_ids: list[int]
) -> Optional[TeamRequest]:
    """Функция для будущего ML алгоритма: записать топ-5 ID"""
    request = await get_request_by_id(db, request_id)
    if request:
        request.recommended_user_ids = user_ids
        db.add(request)
        await db.commit()
        await db.refresh(request)
    return request

async def update_team_request(
    db: AsyncSession,
    request: TeamRequest,
    title: Optional[str] = None,
    description: Optional[str] = None,
    required_roles: Optional[list[str]] = None,
    is_active: Optional[bool] = None
) -> TeamRequest:
    """Обновление полей заявки"""
    if title is not None:
        request.title = title
    if description is not None:
        request.description = description
    if required_roles is not None:
        request.required_roles = required_roles
    if is_active is not None:
        request.is_active = is_active

    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request

async def soft_delete_team_request(db: AsyncSession, request: TeamRequest) -> TeamRequest:
    """Мягкое удаление (деактивация)"""
    request.is_active = False
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request