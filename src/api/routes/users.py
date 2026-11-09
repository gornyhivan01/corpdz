"""Админские маршруты: список пользователей и смена роли."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from src.api.dependencies import AdminUser, DbSession
from src.api.schemas.user import RoleUpdate, UserPage, UserRead
from src.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=UserPage, summary="Список пользователей")
async def list_users(
    admin: AdminUser,
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> UserPage:
    """Доступно только администратору."""
    users, total = await UserService(session).list_users(limit=limit, offset=offset)
    return UserPage(
        total=total,
        limit=limit,
        offset=offset,
        items=[UserRead.model_validate(user) for user in users],
    )


@router.put("/users/{user_id}/role", response_model=UserRead, summary="Изменить роль")
async def change_role(
    user_id: int, payload: RoleUpdate, admin: AdminUser, session: DbSession
) -> UserRead:
    """Меняет роль пользователя; доступно только администратору."""
    user = await UserService(session).change_role(user_id=user_id, role=payload.role)
    return UserRead.model_validate(user)
