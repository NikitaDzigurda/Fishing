from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user  # 👈 Импорт из единого файла
from backend.crud.authors_profile import get_profile_by_user_id, create_or_update_profile
from backend.schemas.profile import ProfileCreate, ProfileRead
from backend.models import User

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("/me", response_model=ProfileRead)
async def read_my_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    profile = await get_profile_by_user_id(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return ProfileRead.model_validate(profile)


@router.post("/me", response_model=ProfileRead)
async def create_update_my_profile(
    payload: ProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    profile = await create_or_update_profile(
        db,
        user_id=current_user.id,
        first_name=payload.first_name,
        last_name=payload.last_name
    )
    return ProfileRead.model_validate(profile)