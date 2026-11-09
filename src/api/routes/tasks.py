"""Маршруты задач.

CRUD появится на этапе 2: GET/POST /tasks, GET/PUT/DELETE /tasks/{task_id}.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/tasks", tags=["tasks"])
