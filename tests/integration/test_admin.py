"""Интеграционные тесты админских ручек и RBAC."""

from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import auth_headers, register_user


async def test_admin_users_requires_token(async_client: AsyncClient) -> None:
    """Без токена админская ручка недоступна."""
    response = await async_client.get("/admin/users")

    assert response.status_code == 401


async def test_admin_users_forbidden_for_user(async_client: AsyncClient, user_token: str) -> None:
    """Обычный пользователь получает 403."""
    response = await async_client.get("/admin/users", headers=auth_headers(user_token))

    assert response.status_code == 403
    assert response.json()["detail"] == "Недостаточно прав"


async def test_admin_users_returns_page(
    async_client: AsyncClient, admin_token: str, user_token: str
) -> None:
    """ADMIN видит список пользователей с пагинацией."""
    await register_user(async_client, "third@example.com", name="Третий")

    response = await async_client.get("/admin/users", headers=auth_headers(admin_token))

    assert response.status_code == 200, response.text
    page = response.json()
    assert page["total"] == 3
    assert page["limit"] == 20
    assert page["offset"] == 0
    assert {user["email"] for user in page["items"]} == {
        "admin@example.com",
        "user@example.com",
        "third@example.com",
    }
    assert all("hashed_password" not in user for user in page["items"])


async def test_admin_users_pagination(
    async_client: AsyncClient, admin_token: str, user_token: str
) -> None:
    """limit/offset работают и в списке пользователей."""
    response = await async_client.get(
        "/admin/users", params={"limit": 1, "offset": 1}, headers=auth_headers(admin_token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert body["offset"] == 1
    assert len(body["items"]) == 1


async def test_change_role_promotes_user(
    async_client: AsyncClient, admin_token: str, user_token: str
) -> None:
    """ADMIN повышает пользователя до ADMIN, и тому открываются админ-ручки."""
    profile = await async_client.get("/auth/profile", headers=auth_headers(user_token))
    user_id = profile.json()["id"]

    response = await async_client.put(
        f"/admin/users/{user_id}/role",
        json={"role": "ADMIN"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200, response.text
    assert response.json()["role"] == "ADMIN"

    promoted = await async_client.get("/admin/users", headers=auth_headers(user_token))
    assert promoted.status_code == 200

    updated_profile = await async_client.get("/auth/profile", headers=auth_headers(user_token))
    assert updated_profile.json()["role"] == "ADMIN"


async def test_change_role_back_to_user(
    async_client: AsyncClient, admin_token: str, user_token: str
) -> None:
    """Понижение роли сразу отзывает доступ к админским ручкам."""
    profile = await async_client.get("/auth/profile", headers=auth_headers(user_token))
    user_id = profile.json()["id"]

    await async_client.put(
        f"/admin/users/{user_id}/role",
        json={"role": "ADMIN"},
        headers=auth_headers(admin_token),
    )
    response = await async_client.put(
        f"/admin/users/{user_id}/role",
        json={"role": "USER"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    assert response.json()["role"] == "USER"

    forbidden = await async_client.get("/admin/users", headers=auth_headers(user_token))
    assert forbidden.status_code == 403


async def test_change_role_is_forbidden_for_user(
    async_client: AsyncClient, user_token: str
) -> None:
    """Обычный пользователь не может менять роли."""
    response = await async_client.put(
        "/admin/users/1/role", json={"role": "ADMIN"}, headers=auth_headers(user_token)
    )

    assert response.status_code == 403


async def test_change_role_unknown_user_returns_404(
    async_client: AsyncClient, admin_token: str
) -> None:
    """Несуществующий пользователь даёт 404."""
    response = await async_client.put(
        "/admin/users/999999/role",
        json={"role": "ADMIN"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Пользователь не найден"


async def test_change_role_invalid_role_returns_422(
    async_client: AsyncClient, admin_token: str
) -> None:
    """Роль вне перечисления отклоняется."""
    response = await async_client.put(
        "/admin/users/1/role",
        json={"role": "SUPERUSER"},
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 422
