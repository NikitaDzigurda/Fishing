from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.auth import UserCreate, UserRead, Token, UserLogin, RefreshTokenRequest
from backend.database import get_db
from backend.crud.users import get_user_by_email, create_user
from backend.service import auth as auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserRead)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    hashed = auth_service.get_password_hash(user_in.password)
    user = await create_user(db, email=user_in.email, hashed_password=hashed, role=user_in.role or "observer")
    return UserRead.from_orm(user)


@router.post("/login", response_model=Token)
async def login(form_data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, form_data.email)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not auth_service.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = auth_service.create_access_token(subject=str(user.id))
    refresh_token = auth_service.create_refresh_token(subject=str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    data = auth_service.decode_token(payload.refresh_token)
    if not data or "sub" not in data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # get user by id
    try:
        from sqlalchemy import select
        from backend.models import User
        sub = data.get("sub")
        user_id = int(sub)
        q = await db.execute(select(User).where(User.id == user_id))
        user = q.scalars().first()
    except Exception:
        user = None

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = auth_service.create_access_token(subject=str(user.id))
    refresh_token = auth_service.create_refresh_token(subject=str(user.id))
    return Token(access_token=access_token, refresh_token=refresh_token)

