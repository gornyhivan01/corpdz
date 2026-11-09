# Task Management System

Итоговое домашнее задание: REST API для управления задачами.

**Стек:** FastAPI, Pydantic v2, PostgreSQL, SQLAlchemy 2.0 (async, asyncpg),
Alembic, JWT, bcrypt, Docker Compose, GitHub Actions.

## Требования

- Docker и Docker Compose
- Python 3.11+ (для запуска без Docker)

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up -d
```

Поднимутся PostgreSQL, Redis и приложение, применятся миграции Alembic.
Сервис: <http://localhost:8000>, Swagger UI: <http://localhost:8000/docs>.

Остановить: `docker compose down` (с данными — `docker compose down -v`).

## Запуск без Docker

```bash
cp .env.example .env          # DATABASE_URL должен указывать на ваш PostgreSQL
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

## Эндпоинты

| Метод | Путь | Доступ | Назначение |
|---|---|---|---|
| GET | `/health` | публичный | Проверка живости |
| POST | `/auth/register` | публичный | Регистрация (роль USER) |
| POST | `/auth/login` | публичный | Вход, выдача JWT |
| GET | `/auth/profile` | авторизованный | Профиль текущего пользователя |
| GET | `/tasks` | авторизованный | Список задач (пагинация, фильтры) |
| POST | `/tasks` | авторизованный | Создать задачу + email-уведомление |
| GET | `/tasks/{task_id}` | авторизованный | Задача по id |
| PUT | `/tasks/{task_id}` | авторизованный | Обновить задачу |
| DELETE | `/tasks/{task_id}` | авторизованный | Удалить задачу |
| GET | `/admin/users` | ADMIN | Список пользователей |
| PUT | `/admin/users/{user_id}/role` | ADMIN | Сменить роль |

**Права:** пользователь видит и меняет только свои задачи; администратор —
все задачи и управление ролями.

## Примеры запросов

```bash
# Регистрация
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "password": "secure123", "name": "Иван Иванов"}'

# Вход (сохраняем токен)
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "user@example.com", "password": "secure123"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Создание задачи
curl -X POST http://localhost:8000/tasks \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title": "Разработать API", "description": "Создать REST API", "priority": "high", "deadline": "2026-12-01T00:00:00"}'

# Список с фильтром и пагинацией
curl "http://localhost:8000/tasks?status=pending&priority=high&limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

## Структура

```
src/
  api/            # маршруты, схемы, зависимости
  core/           # config, security, database, exceptions
  models/         # User, Task
  repositories/   # доступ к данным
  services/       # бизнес-логика, уведомления
  utils/          # unit_of_work
  main.py
alembic/          # миграции
tests/            # тесты (этап 3)
```

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | PostgreSQL для compose |
| `DATABASE_URL` | `postgresql+asyncpg://…` |
| `REDIS_URL` | адрес Redis (задел под Celery) |
| `SECRET_KEY` | секрет подписи JWT — заменить в проде |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | срок жизни токена |
## Первый администратор

Регистрация всегда создаёт пользователя с ролью `USER`. Первого администратора
нужно назначить вручную — через SQL:

```bash
docker compose exec db psql -U app -d app \
  -c "UPDATE users SET role='ADMIN' WHERE email='admin@example.com';"
```

После этого вход тем же email даёт админские права (`GET /admin/users`,
`PUT /admin/users/{id}/role`).
