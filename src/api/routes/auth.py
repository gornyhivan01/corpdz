"""Маршруты аутентификации.

Эндпоинты появятся на этапе 2: POST /auth/register, POST /auth/login,
GET /auth/profile.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
