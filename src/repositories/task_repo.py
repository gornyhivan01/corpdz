"""Репозиторий задач."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.task import Task


class TaskRepository:
    """Операции с таблицей tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _filtered(
        *,
        owner_id: int | None,
        status: str | None,
        priority: str | None,
        deadline_from: datetime | None,
        deadline_to: datetime | None,
    ) -> Select[tuple[Task]]:
        query = select(Task)
        if owner_id is not None:
            query = query.where(Task.user_id == owner_id)
        if status is not None:
            query = query.where(Task.status == status)
        if priority is not None:
            query = query.where(Task.priority == priority)
        if deadline_from is not None:
            query = query.where(Task.deadline >= deadline_from)
        if deadline_to is not None:
            query = query.where(Task.deadline <= deadline_to)
        return query

    async def list(
        self,
        *,
        owner_id: int | None,
        status: str | None,
        priority: str | None,
        deadline_from: datetime | None,
        deadline_to: datetime | None,
        limit: int,
        offset: int,
    ) -> list[Task]:
        query = self._filtered(
            owner_id=owner_id,
            status=status,
            priority=priority,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
        ).order_by(Task.created_at.desc(), Task.id.desc())
        result = await self._session.scalars(query.limit(limit).offset(offset))
        return list(result)

    async def count(
        self,
        *,
        owner_id: int | None,
        status: str | None,
        priority: str | None,
        deadline_from: datetime | None,
        deadline_to: datetime | None,
    ) -> int:
        query = self._filtered(
            owner_id=owner_id,
            status=status,
            priority=priority,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
        )
        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        return total or 0

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self._session.get(Task, task_id)

    async def create(self, *, owner_id: int, **fields: object) -> Task:
        task = Task(user_id=owner_id, **fields)
        self._session.add(task)
        await self._session.flush()
        return task

    async def delete(self, task: Task) -> None:
        await self._session.delete(task)
        await self._session.flush()
