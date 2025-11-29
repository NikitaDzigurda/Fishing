from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from sqlalchemy.orm import selectinload

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.models import User, UserProfile, TeamRequest
from backend.schemas.team_request import (
    TeamRequestCreate,
    TeamRequestRead,
    RecommendedUser,
    TeamRequestUpdate,
    RequestAuthor
)
from backend.crud import team_requests as crud_requests

router = APIRouter(prefix="/api/v1/requests", tags=["team_requests"])


async def _fetch_recommendation_details(db: AsyncSession, user_ids: List[int]) -> List[RecommendedUser]:
    if not user_ids:
        return []

    query = select(UserProfile).where(UserProfile.user_id.in_(user_ids))
    result = await db.execute(query)
    profiles = result.scalars().all()

    query_users = (
        select(User.id, User.email, UserProfile)
        .join(UserProfile, User.profile)
        .where(User.id.in_(user_ids))
    )
    res_users = await db.execute(query_users)
    rows = res_users.all()

    details = []
    for uid, email, profile in rows:
        details.append(RecommendedUser(
            id=uid,
            email=email,
            first_name=profile.first_name,
            last_name=profile.last_name,
            major=profile.major,
            contact_info=profile.contact_info  # 👈 Контакт
        ))
    return details


@router.post("/", response_model=TeamRequestRead, status_code=status.HTTP_201_CREATED)
async def create_request(
        payload: TeamRequestCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    new_request = await crud_requests.create_team_request(
        db=db,
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        required_roles=payload.required_roles
    )
    return new_request

@router.get("/all", response_model=List[TeamRequestRead])
async def get_all_requests(
        skip: int = Query(0, ge=0),
        limit: int = Query(20, ge=1, le=100),
        q: Optional[str] = Query(None, description="Search by title or description"),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    requests = await crud_requests.get_all_active_requests(db, skip, limit, q)

    result = []


    for req in requests:
        req_pydantic = TeamRequestRead.model_validate(req)
        if req.author:
            author_data = {
                "id": req.author.id,
                "first_name": None,
                "last_name": None,
                "major": None,
                "contact_info": None
            }
            if req.author.profile:
                author_data.update({
                    "first_name": req.author.profile.first_name,
                    "last_name": req.author.profile.last_name,
                    "major": req.author.profile.major,
                    "contact_info": req.author.profile.contact_info
                })
            req_pydantic.author_details = RequestAuthor(**author_data)

        req_pydantic.recommended_user_ids = []
        req_pydantic.recommendations_details = None

        result.append(req_pydantic)

    return result


@router.get("/my", response_model=List[TeamRequestRead])
async def get_my_requests(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    requests = await crud_requests.get_user_requests(db, current_user.id)

    result = []
    for req in requests:
        req_pydantic = TeamRequestRead.model_validate(req)

        if req.recommended_user_ids:
            details = await _fetch_recommendation_details(db, req.recommended_user_ids)
            req_pydantic.recommendations_details = details

        result.append(req_pydantic)

    return result


@router.get("/{request_id}", response_model=TeamRequestRead)
async def get_request(
        request_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    query = (
        select(TeamRequest)
        .options(selectinload(TeamRequest.author).selectinload(User.profile))
        .where(TeamRequest.id == request_id)
    )
    result = await db.execute(query)
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    req_pydantic = TeamRequestRead.model_validate(req)

    if req.author and req.author.profile:
        req_pydantic.author_details = RequestAuthor(
            id=req.author.id,
            first_name=req.author.profile.first_name,
            last_name=req.author.profile.last_name,
            major=req.author.profile.major,
            contact_info=req.author.profile.contact_info
        )
    elif req.author:
        req_pydantic.author_details = RequestAuthor(id=req.author.id)

    if req.user_id == current_user.id or current_user.role == "admin":
        if req.recommended_user_ids:
            details = await _fetch_recommendation_details(db, req.recommended_user_ids)
            req_pydantic.recommendations_details = details
    else:
        req_pydantic.recommended_user_ids = []
        req_pydantic.recommendations_details = None

    return req_pydantic


@router.patch("/{request_id}", response_model=TeamRequestRead)
async def update_request(
        request_id: int,
        payload: TeamRequestUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    req = await crud_requests.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    updated_req = await crud_requests.update_team_request(
        db=db,
        request=req,
        title=payload.title,
        description=payload.description,
        required_roles=payload.required_roles,
        is_active=payload.is_active
    )

    req_pydantic = TeamRequestRead.model_validate(updated_req)
    return req_pydantic


@router.delete("/{request_id}", response_model=TeamRequestRead)
async def delete_request(
        request_id: int,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    req = await crud_requests.get_request_by_id(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    if req.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    deactivated_req = await crud_requests.soft_delete_team_request(db, req)
    return TeamRequestRead.model_validate(deactivated_req)