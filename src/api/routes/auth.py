"""Маршруты аутентификации: регистрация, вход и профиль."""

from __future__ import annotations

from fastapi import APIRouter, status

from src.api.dependencies import CurrentUser, DbSession
from src.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from src.api.schemas.user import UserRead
from src.core.config import get_settings
from src.core.security import create_access_token
from src.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация пользователя",
)
async def register(payload: RegisterRequest, session: DbSession) -> UserRead:
    """Создаёт пользователя с ролью USER."""
    service = UserService(session)
    user = await service.register(email=payload.email, password=payload.password, name=payload.name)
    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse, summary="Вход и получение JWT")
async def login(payload: LoginRequest, session: DbSession) -> TokenResponse:
    """Проверяет пароль и выпускает access-токен."""
    service = UserService(session)
    user = await service.authenticate(email=payload.email, password=payload.password)
    settings = get_settings()
    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/profile", response_model=UserRead, summary="Профиль текущего пользователя")
async def profile(current_user: CurrentUser) -> UserRead:
    """Возвращает профиль владельца токена."""
    return UserRead.model_validate(current_user)
