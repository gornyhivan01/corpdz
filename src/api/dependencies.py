"""Зависимости FastAPI: сессия БД и текущий пользователь."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.exceptions import ForbiddenError, UnauthorizedError
from src.core.security import decode_access_token
from src.models.user import User, UserRole

DbSession = Annotated[AsyncSession, Depends(get_session)]

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: DbSession,
) -> User:
    """Достаёт пользователя из JWT в заголовке Authorization."""
    if credentials is None:
        raise UnauthorizedError("Не удалось проверить токен")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise UnauthorizedError("Не удалось проверить токен") from exc

    user = await session.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Не удалось проверить токен")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(current_user: CurrentUser) -> User:
    """Пропускает только администратора."""
    if current_user.role != UserRole.ADMIN.value:
        raise ForbiddenError("Недостаточно прав")
    return current_user


AdminUser = Annotated[User, Depends(require_admin)]
