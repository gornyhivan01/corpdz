"""Настройки приложения через pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки сервиса (читаются из переменных окружения и .env)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Task Management System"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/app"

    secret_key: str = "change-me-in-production-please"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, gt=0)

    redis_url: str = "redis://localhost:6379/0"


@lru_cache
def get_settings() -> Settings:
    """Возвращает синглтон настроек (читает окружение один раз)."""
    return Settings()
