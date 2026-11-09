"""Зависимости FastAPI: сессия БД и текущий пользователь.

Реализация текущего пользователя появится на этапе 2.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session

DbSession = Annotated[AsyncSession, Depends(get_session)]
