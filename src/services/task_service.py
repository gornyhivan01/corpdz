"""Сервис задач.

Реализация появится на этапе 2.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.repositories.task_repo import TaskRepository


class TaskService:
    """Бизнес-логика задач."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = TaskRepository(session)
