"""Админские маршруты.

Эндпоинты появятся на этапе 2: GET /admin/users,
PUT /admin/users/{user_id}/role.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])
