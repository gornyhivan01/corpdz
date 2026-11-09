"""Сервис задач: CRUD с проверкой прав."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models.task import Task
from src.models.user import User, UserRole
from src.repositories.task_repo import TaskRepository
from src.utils.unit_of_work import UnitOfWork


class TaskService:
    """Бизнес-логика задач: пользователь работает только со своими."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TaskRepository(session)
        self._uow = UnitOfWork(session)

    def _visible_owner_id(self, user: User) -> int | None:
        """ADMIN видит все задачи, остальные — только свои."""
        return None if user.role == UserRole.ADMIN.value else user.id

    async def _get_accessible(self, *, user: User, task_id: int) -> Task:
        task = await self._repo.get_by_id(task_id)
        if task is None:
            raise NotFoundError("Задача не найдена")
        if user.role != UserRole.ADMIN.value and task.user_id != user.id:
            raise ForbiddenError("Недостаточно прав")
        return task

    async def list(
        self,
        *,
        user: User,
        status: str | None = None,
        priority: str | None = None,
        deadline_from: datetime | None = None,
        deadline_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        owner_id = self._visible_owner_id(user)
        items = await self._repo.list(
            owner_id=owner_id,
            status=status,
            priority=priority,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
            limit=limit,
            offset=offset,
        )
        total = await self._repo.count(
            owner_id=owner_id,
            status=status,
            priority=priority,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
        )
        return items, total

    async def create(self, *, user: User, **fields: object) -> Task:
        task = await self._repo.create(owner_id=user.id, **fields)
        await self._uow.commit()
        await self._session.refresh(task)
        return task

    async def get(self, *, user: User, task_id: int) -> Task:
        return await self._get_accessible(user=user, task_id=task_id)

    async def update(self, *, user: User, task_id: int, changes: dict[str, object]) -> Task:
        task = await self._get_accessible(user=user, task_id=task_id)
        for field, value in changes.items():
            setattr(task, field, value)
        await self._uow.commit()
        await self._session.refresh(task)
        return task

    async def delete(self, *, user: User, task_id: int) -> None:
        task = await self._get_accessible(user=user, task_id=task_id)
        await self._repo.delete(task)
        await self._uow.commit()
