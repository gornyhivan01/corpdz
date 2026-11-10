"""Сервис пользователей: регистрация, вход, профиль, администрирование."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from src.core.security import hash_password, verify_password
from src.models.user import User, UserRole
from src.repositories.task_repo import TaskRepository
from src.repositories.user_repo import UserRepository
from src.utils.unit_of_work import UnitOfWork


class UserService:
    """Бизнес-логика пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)
        self._tasks = TaskRepository(session)
        self._uow = UnitOfWork(session)

    async def register(self, *, email: str, password: str, name: str) -> User:
        """Регистрирует пользователя с ролью USER."""
        return await self._create(email=email, password=password, name=name, role=UserRole.USER)

    async def create_user(self, *, email: str, password: str, name: str, role: UserRole) -> User:
        """Создаёт пользователя с указанной ролью (только для администратора)."""
        return await self._create(email=email, password=password, name=name, role=role)

    async def _create(self, *, email: str, password: str, name: str, role: UserRole) -> User:
        normalized = email.strip().lower()
        if await self._repo.get_by_email(normalized) is not None:
            raise ConflictError("Пользователь с таким email уже существует")

        user = await self._repo.create(
            email=normalized,
            hashed_password=hash_password(password),
            name=name.strip(),
            role=role.value,
        )
        await self._uow.commit()
        await self._session.refresh(user)
        return user

    async def authenticate(self, *, email: str, password: str) -> User:
        """Проверяет email и пароль, возвращает пользователя."""
        user = await self._repo.get_by_email(email.strip().lower())
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Неверный email или пароль")
        return user

    async def get_profile(self, user_id: int) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден")
        return user

    async def list_users(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        users = await self._repo.list_all(limit=limit, offset=offset)
        total = await self._repo.count()
        return users, total

    async def change_role(self, *, user_id: int, role: UserRole) -> User:
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден")
        await self._repo.set_role(user, role)
        await self._uow.commit()
        await self._session.refresh(user)
        return user

    async def delete_user(self, *, admin: User, user_id: int) -> int:
        """Удаляет пользователя, перенося его задачи в архив.

        Возвращает число заархивированных задач.
        """
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден")
        if user.id == admin.id:
            raise BadRequestError("Нельзя удалить собственную учётную запись")
        if user.role == UserRole.ADMIN.value and await self._repo.count_admins() <= 1:
            raise BadRequestError("Нельзя удалить последнего администратора")

        archived = await self._tasks.archive_by_owner(
            owner_id=user.id, email=user.email, archived_at=datetime.now(UTC)
        )
        await self._repo.delete(user)
        await self._uow.commit()
        return archived
