"""Репозиторий пользователей.

Реализация появится на этапе 2.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class UserRepository:
    """Операции с таблицей users."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
