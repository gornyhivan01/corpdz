"""Точка входа FastAPI-приложения."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.api.routes import auth, tasks, users
from src.core.config import get_settings
from src.core.exceptions import AppError

settings = get_settings()

# Уведомления и аудит пишутся в stdout через логгеры приложения.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description="""# Task Management System

REST API для управления задачами: JWT-аутентификация, RBAC (USER/ADMIN),
PostgreSQL, Alembic.

**Как попробовать:**

1. `POST /auth/register` — зарегистрируйтесь.
2. `POST /auth/login` — получите `access_token` и нажмите **Authorize**,
   вставив токен.
3. `POST /tasks` — создайте задачу, `GET /tasks` — посмотрите список.

Администратору доступны `GET /admin/users` и `PUT /admin/users/{id}/role`.
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


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Превращает доменные ошибки в HTTP-ответы."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health", tags=["service"], summary="Проверка живости сервиса")
async def health() -> dict[str, str]:
    """Возвращает `ok`, если сервис запущен."""
    return {"status": "ok"}
