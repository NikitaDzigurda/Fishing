from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/authorityprompt"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    GEMINI_API_KEY: str ="<gemini_api_key>"

    SECRET_KEY: str = "329cd225b19f49a281b0fd4f046b084b5c80184dd71b98f66a88e8232e1be599"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ALLOWED_ORIGINS: list[str] = ["*"]

    REDIS_URL: str = "redis://redis:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
