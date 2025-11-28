from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.dependencies import get_current_user

from backend.crud.authors_profile import (
    get_profile_by_user_id,
    create_or_update_profile,
    create_profile
)
from backend.schemas.profile import ProfileCreate, ProfileUpdate, ProfileRead
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
            detail="Profile not found. Create one first."
        )
    return ProfileRead.model_validate(profile)


@router.post("/me", response_model=ProfileRead, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
        payload: ProfileCreate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    existing = await get_profile_by_user_id(db, current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile already exists. Use PUT to update."
        )

    profile = await create_profile(
        db,
        user_id=current_user.id,
        **payload.model_dump()
    )
    return ProfileRead.model_validate(profile)


@router.put("/me", response_model=ProfileRead)
async def update_my_profile(
        payload: ProfileUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    # create_or_update_profile тоже примет новые поля через **kwargs
    profile = await create_or_update_profile(
        db,
        user_id=current_user.id,
        **payload.model_dump()
    )
    return ProfileRead.model_validate(profile)


@router.patch("/me", response_model=ProfileRead)
async def patch_my_profile(
        payload: ProfileUpdate,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    profile = await get_profile_by_user_id(db, current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found. Create one first."
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        # Здесь мы динамически обновляем атрибуты модели.
        # Так как поля есть в модели SQLAlchemy, setattr сработает корректно.
        if hasattr(profile, field):
            setattr(profile, field, value)

    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return ProfileRead.model_validate(profile)