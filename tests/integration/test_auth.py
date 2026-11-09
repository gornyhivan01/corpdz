"""Интеграционные тесты регистрации, входа и профиля."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient

from tests.helpers import DEFAULT_PASSWORD, auth_headers, login, register_user


async def test_register_creates_user_with_role_user(async_client: AsyncClient) -> None:
    """Регистрация возвращает 201 и пользователя с ролью USER."""
    response = await async_client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": DEFAULT_PASSWORD, "name": "Новый"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "new@example.com"
    assert body["name"] == "Новый"
    assert body["role"] == "USER"
    assert body["id"] > 0
    assert "created_at" in body
    # Пароль и его хеш наружу не отдаются.
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_lowercases_email(async_client: AsyncClient) -> None:
    """Email приводится к нижнему регистру, вход работает по любому варианту."""
    response = await async_client.post(
        "/auth/register",
        json={
            "email": "Mixed.Case@Example.COM",
            "password": DEFAULT_PASSWORD,
            "name": "Регистр",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["email"] == "mixed.case@example.com"

    token = await login(async_client, "mixed.case@example.com")
    assert token


async def test_register_duplicate_email_returns_409(async_client: AsyncClient) -> None:
    """Повторная регистрация того же email даёт 409."""
    await register_user(async_client, "dup@example.com")

    response = await async_client.post(
        "/auth/register",
        json={"email": "dup@example.com", "password": DEFAULT_PASSWORD, "name": "Дубль"},
    )

    assert response.status_code == 409
    assert "уже существует" in response.json()["detail"]


async def test_register_short_password_returns_422(async_client: AsyncClient) -> None:
    """Пароль короче 8 символов не проходит валидацию схемы."""
    response = await async_client.post(
        "/auth/register",
        json={"email": "short@example.com", "password": "1234567", "name": "Короткий"},
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"][-1] == "password" for error in errors)


async def test_register_invalid_email_returns_422(async_client: AsyncClient) -> None:
    """Строка, не похожая на email, отклоняется."""
    response = await async_client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": DEFAULT_PASSWORD, "name": "Без почты"},
    )

    assert response.status_code == 422
    assert any(error["loc"][-1] == "email" for error in response.json()["detail"])


async def test_login_returns_access_token(async_client: AsyncClient) -> None:
    """Успешный вход отдаёт JWT и срок его жизни."""
    await register_user(async_client, "login@example.com")

    response = await async_client.post(
        "/auth/login", json={"email": "login@example.com", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0


async def test_login_with_wrong_password_returns_401(async_client: AsyncClient) -> None:
    """Неверный пароль даёт 401 без подсказок о существовании пользователя."""
    await register_user(async_client, "wrong-pass@example.com")

    response = await async_client.post(
        "/auth/login", json={"email": "wrong-pass@example.com", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль"


async def test_login_with_unknown_email_returns_401(async_client: AsyncClient) -> None:
    """Несуществующий email даёт тот же 401, что и неверный пароль."""
    response = await async_client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль"


async def test_profile_returns_current_user(async_client: AsyncClient) -> None:
    """Профиль отдаёт данные владельца токена."""
    user = await register_user(async_client, "profile@example.com", name="Профиль")
    token = await login(async_client, "profile@example.com")

    response = await async_client.get("/auth/profile", headers=auth_headers(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == user["id"]
    assert body["email"] == user["email"]
    assert body["name"] == "Профиль"


async def test_profile_without_token_returns_401(async_client: AsyncClient) -> None:
    """Без заголовка Authorization профиль недоступен."""
    response = await async_client.get("/auth/profile")

    assert response.status_code == 401
    assert response.json()["detail"] == "Не удалось проверить токен"


async def test_profile_with_broken_token_returns_401(async_client: AsyncClient) -> None:
    """Строка вместо JWT не проходит проверку подписи."""
    response = await async_client.get("/auth/profile", headers=auth_headers("not-a-jwt"))

    assert response.status_code == 401


async def test_profile_with_expired_token_returns_401(async_client: AsyncClient) -> None:
    """Просроченный токен отклоняется."""
    from jose import jwt

    from src.core.config import get_settings

    settings = get_settings()
    expired = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await async_client.get("/auth/profile", headers=auth_headers(expired))

    assert response.status_code == 401


async def test_profile_with_token_of_unknown_user_returns_401(async_client: AsyncClient) -> None:
    """Корректно подписанный токен удалённого пользователя не проходит."""
    from src.core.security import create_access_token

    response = await async_client.get(
        "/auth/profile", headers=auth_headers(create_access_token("999999"))
    )

    assert response.status_code == 401
