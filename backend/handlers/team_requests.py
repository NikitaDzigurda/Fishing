from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User, UserProfile
from backend.schemas.team_request import TeamRequestCreate, TeamRequestRead, RecommendedUser, TeamRequestUpdate
from backend.crud import team_requests as crud_requests

router = APIRouter(prefix="/api/v1/requests", tags=["team_requests"])


async def _fetch_recommendation_details(db: AsyncSession, user_ids: List[int]) -> List[RecommendedUser]:
    """Вспомогательная функция: по списку ID получает данные пользователей для фронта"""
    if not user_ids:
        return []

    # Делаем JOIN чтобы получить email из User и имя из UserProfile
    query = (
        select(User.id, User.email, UserProfile.first_name, UserProfile.last_name, UserProfile.major)
        .join(UserProfile, User.profile)
        .where(User.id.in_(user_ids))
    )
    result = await db.execute(query)
    rows = result.all()

    # Преобразуем в схему
    details = []
    for row in rows:
        details.append(RecommendedUser(
            id=row.id,
            email=row.email,
            first_name=row.first_name,
            last_name=row.last_name,
            major=row.major
        ))
    return details


@router.post("/", response_model=TeamRequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(
        payload: TeamRequestCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Создать новую заявку на поиск людей"""
    new_request = await crud_requests.create_team_request(
        db=db,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        required_roles=payload.required_roles
    )

    # Здесь в будущем можно вызвать Celery задачу для запуска ML рекомендаций
    # parsing_service.calculate_recommendations.delay(new_request.id)

    return new_request


@router.get("/my", response_model=List[TeamRequestRead])
async def get_my_requests(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Получить все мои заявки с подгруженными рекомендациями"""
    requests = await crud_requests.get_user_requests(db, current_user.id)

    # Обогащаем данные (подгружаем детали рекомендаций)
    result = []
    for req in requests:
        # Преобразуем SQLAlchemy модель в Pydantic модель
        req_pydantic = TeamRequestRead.model_validate(req)

        # Если есть рекомендации, подтягиваем инфо о людях
        if req.recommended_user_ids:
            details = await _fetch_recommendation_details(db, req.recommended_user_ids)
            req_pydantic.recommendations_details = details

        result.append(req_pydantic)

    return result


@router.patch("/{request_id}", response_model=TeamRequestRead)
async def update_request(
        request_id: int,
        payload: TeamRequestUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Обновить заявку.
    Можно изменить title, description, roles или закрыть заявку (is_active=False).
    """
    req = await crud_requests.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    # Проверка прав: только автор или админ может менять заявку
    if req.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this request")

    updated_req = await crud_requests.update_team_request(
        db=db,
        request=req,
        title=payload.title,
        description=payload.description,
        required_roles=payload.required_roles,
        is_active=payload.is_active
    )

    # Преобразуем для ответа (с деталями рекомендаций, если есть)
    req_pydantic = TeamRequestRead.model_validate(updated_req)
    if updated_req.recommended_user_ids:
        details = await _fetch_recommendation_details(db, updated_req.recommended_user_ids)
        req_pydantic.recommendations_details = details

    return req_pydantic


@router.get("/{request_id}", response_model=TeamRequestRead)
async def get_request(
        request_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """Получить детали конкретной заявки"""
    req = await crud_requests.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    req_pydantic = TeamRequestRead.model_validate(req)

    if req.recommended_user_ids:
        details = await _fetch_recommendation_details(db, req.recommended_user_ids)
        req_pydantic.recommendations_details = details

    return req_pydantic


@router.delete("/{request_id}", response_model=TeamRequestRead)
async def delete_request(
        request_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    """
    Деактивировать заявку (Soft delete).
    Запись остается в БД, но поле is_active становится False.
    """
    req = await crud_requests.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this request")

    # Используем функцию soft_delete или просто update
    deactivated_req = await crud_requests.soft_delete_team_request(db, req)

    # Возвращаем обновленный объект
    req_pydantic = TeamRequestRead.model_validate(deactivated_req)
    # Подгружаем детали если нужно, или возвращаем пустыми, так как заявка закрыта
    return req_pydantic