"""Сервис пользователей.

Реализация появится на этапе 2.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.user_repo import UserRepository


class UserService:
    """Бизнес-логика пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = UserRepository(session)
