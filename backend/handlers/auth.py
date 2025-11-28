from fastapi import APIRouter, Depends, HTTPException, status, Cookie, Header
from fastapi.security import OAuth2PasswordRequestForm
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.auth import UserCreate, UserRead, Token, UserLogin, RefreshTokenRequest
from backend.database import get_db
from backend.crud.users import get_user_by_email, create_user, get_user_by_id
from backend.service import auth as auth_service
from backend.service.auth_service import AuthService, UserNotFoundedException, UserNotCorrectPasswordException
from backend.repositories.user_repository import get_user_repository, UserRepository
from backend.service.oauth_clients import get_google_client, get_yandex_client, GoogleClient, YandexClient
from backend.settings import settings

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


async def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    google_client: Annotated[GoogleClient, Depends(get_google_client)],
    yandex_client: Annotated[YandexClient, Depends(get_yandex_client)],
) -> AuthService:
    try:
        # use settings from backend.settings
        if not settings.SECRET_KEY:
            raise ValueError("SECRET_KEY is missing in settings")

        return AuthService(user_repository=user_repository, settings_obj=settings, google_client=google_client, yandex_client=yandex_client)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth service initialization failed: {str(e)}")


@router.get("/me-cookie-payload", response_model=dict)
async def me_cookie_payload(access_token: str | None = Cookie(None, alias="access_token")):
    """Read access_token from cookie named 'access_token' and return its decoded payload (claims).

    This returns the token claims (e.g. sub, exp, role) so the frontend can inspect them or the backend
    can use them to decide which DB objects to access.
    """
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No access token in cookies")

    data = auth_service.decode_token(access_token)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    return data


@router.get("/me-token-payload", response_model=dict)
async def me_token_payload(authorization: str | None = Header(None, alias="Authorization")):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No Authorization header")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Authorization header")

    token = parts[1]
    data = auth_service.decode_token(token)
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    return data


@router.post("/refresh", response_model=Token)
async def refresh_token(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    data = auth_service.decode_token(payload.refresh_token)
    if not data or "sub" not in data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # sub contains user id (int). Query by id.
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


@router.post("/token")
async def token(
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    # note: auth_service dependency will be provided via get_auth_service below in DI container
    try:
        user_dict = await auth_service.login(form_data.username, form_data.password)
        return {"access_token": user_dict.access_token, "token_type": "bearer"}

    except UserNotFoundedException as e:
        raise HTTPException(status_code=404, detail=e.detail)

    except UserNotCorrectPasswordException as e:
        raise HTTPException(status_code=401, detail=e.detail)


async def get_auth_service(
    user_repository: Annotated[UserRepository, Depends(get_user_repository)],
    google_client: Annotated[GoogleClient, Depends(get_google_client)],
    yandex_client: Annotated[YandexClient, Depends(get_yandex_client)],
) -> AuthService:
    try:
        # use settings from backend.settings
        if not settings.SECRET_KEY:
            raise ValueError("SECRET_KEY is missing in settings")

        return AuthService(user_repository=user_repository, settings_obj=settings, google_client=google_client, yandex_client=yandex_client)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Auth service initialization failed: {str(e)}")

