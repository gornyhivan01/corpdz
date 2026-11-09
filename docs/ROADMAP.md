# Состояние проекта и план

Документ для продолжения работы: что готово, какие решения приняты и что делать
дальше. Обновляется по мере прохождения этапов ТЗ.

## Готово

**Этап 1 (15 баллов).** Каркас Clean Architecture: `src/{api,core,models,repositories,services,utils}`,
Alembic с миграцией `0001` (users, tasks), `Dockerfile`, `docker-compose.yml`
(app + PostgreSQL + Redis), `.env.example`, `requirements.txt` из `uv.lock`.

**Этап 2 (40 баллов).** API:

| Метод | Путь | Доступ |
|---|---|---|
| POST | `/auth/register` | публичный |
| POST | `/auth/login` | публичный |
| GET | `/auth/profile` | авторизованный |
| GET/POST | `/tasks` | авторизованный |
| GET/PUT/DELETE | `/tasks/{task_id}` | авторизованный |
| GET | `/admin/users` | ADMIN |
| PUT | `/admin/users/{user_id}/role` | ADMIN |
| GET | `/health` | публичный |

Проверено на живом стеке: регистрация, вход, создание/список/фильтры задач,
403 на чужую задачу, 401 без токена, админ-ручки, смена роли, удаление (204),
фоновая «отправка письма» в лог.

## Принятые решения

- Роли — `USER`/`ADMIN` (верхний регистр, как в ТЗ), в БД строка + CHECK.
- Пароли — `bcrypt` (не Argon2id).
- JWT — `python-jose`, HS256, `sub` = id пользователя.
- Фоновые уведомления — `BackgroundTasks` + логгер; Redis оставлен в compose
  под будущий Celery.
- `requirements.txt` генерируется из `uv.lock` (`uv export`), поэтому локально
  используется `uv`, а в Docker — pip.
- Первый администратор назначается SQL-запросом (см. README): регистрация
  всегда создаёт `USER`.

## Как запустить

```bash
docker compose up -d          # app + postgres + redis, миграции при старте
# Swagger: http://localhost:8000/docs
```

Локально без Docker: `uv sync && uv run alembic upgrade head && uv run uvicorn src.main:app --reload`.

## Дальше: этап 3 (20 баллов) — тесты

Требования ТЗ: минимум 5 интеграционных тестов, `pytest-asyncio`,
`httpx.AsyncClient`, Testcontainers (PostgreSQL), запуск в CI.

План:

1. `tests/conftest.py`:
   - `postgres_container` (session scope) через `testcontainers.postgres`,
   - применение `alembic upgrade head` к контейнеру,
   - `async_client` на `httpx.AsyncClient(transport=ASGITransport(app))`,
   - фикстуры токенов `user_token` / `admin_token`.
2. `tests/integration/`:
   - регистрация и вход (успех + 409 на дубль + 401 на неверный пароль),
   - создание и получение задачи,
   - RBAC: чужая задача → 403, `/admin/users` под USER → 403,
   - ошибки: 401 без токена, 404, 422 (короткий пароль),
   - фильтры и пагинация `/tasks`.
3. `pyproject.toml`: `asyncio_mode = "auto"`.
4. CI: job `test` с сервисом `postgres` и `pytest tests/`.

Запуск: `uv run pytest -q`.

## Дальше: этап 4 (15 баллов) — Docker и CI/CD

- CI: тесты + сборка образа (job `docker`).
- Проверить `docker compose up -d` с нуля на чистом томе.

## Дальше: этап 5 (10 баллов) — сдача

- README с примерами (есть, дополнить при изменениях).
- Публичный репозиторий: <https://github.com/gornyhivan01/corpdz>.