"""Юнит-тесты безопасности: bcrypt и JWT (без базы данных)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import JWTError, jwt

from src.core.config import get_settings
from src.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_is_salted() -> None:
    """Один и тот же пароль даёт разные хеши благодаря соли."""
    first = hash_password("secret123")
    second = hash_password("secret123")

    assert first != second
    assert first.startswith("$2b$")
    assert verify_password("secret123", first)
    assert verify_password("secret123", second)


def test_verify_password_rejects_wrong_password() -> None:
    """Неверный пароль не проходит проверку."""
    hashed = hash_password("secret123")

    assert verify_password("secret124", hashed) is False


def test_verify_password_survives_broken_hash() -> None:
    """Битый хеш не роняет приложение, а просто не подтверждает пароль."""
    assert verify_password("secret123", "not-a-bcrypt-hash") is False


def test_access_token_roundtrip() -> None:
    """Токен кодируется и декодируется, ``sub`` сохраняется."""
    token = create_access_token("42")

    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert "exp" in payload


def test_decode_rejects_expired_token() -> None:
    """Просроченный токен считается невалидным."""
    settings = get_settings()
    token = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(JWTError):
        decode_access_token(token)


def test_decode_rejects_foreign_signature() -> None:
    """Токен с чужой подписью отклоняется."""
    settings = get_settings()
    token = jwt.encode({"sub": "42"}, "another-secret", algorithm=settings.jwt_algorithm)

    with pytest.raises(JWTError):
        decode_access_token(token)
