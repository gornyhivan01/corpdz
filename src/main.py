"""Точка входа FastAPI-приложения."""

from __future__ import annotations

from fastapi import FastAPI

from src.api.routes import auth, tasks, users
from src.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="""# Task Management System

REST API для управления задачами: JWT-аутентификация, RBAC (USER/ADMIN),
PostgreSQL, Alembic.

**Служебные ручки:** `GET /health`.

Остальные разделы появятся по мере разработки.
""",
    openapi_tags=[
        {"name": "service", "description": "Служебные ручки."},
        {"name": "auth", "description": "Регистрация, вход и профиль."},
        {"name": "tasks", "description": "CRUD задач."},
        {"name": "admin", "description": "Управление пользователями (ADMIN)."},
    ],
)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(users.router)


@app.get("/health", tags=["service"], summary="Проверка живости сервиса")
async def health() -> dict[str, str]:
    """Возвращает `ok`, если сервис запущен."""
    return {"status": "ok"}
