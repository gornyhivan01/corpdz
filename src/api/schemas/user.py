"""Схемы пользователя."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRole(str, Enum):
    """Роль пользователя."""

    USER = "USER"
    ADMIN = "ADMIN"


class UserRead(BaseModel):
    """Пользователь, возвращаемый API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str
    role: UserRole
    created_at: datetime


class RoleUpdate(BaseModel):
    """Новая роль пользователя."""

    role: UserRole = Field(description="Роль: USER или ADMIN")
