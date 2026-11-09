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

Что произойдёт: поднимутся PostgreSQL, Redis и приложение, применятся миграции
Alembic (`alembic upgrade head`), сервис будет доступен на порту 8000.

- Swagger UI — <http://localhost:8000/docs>
- Схема OpenAPI — <http://localhost:8000/openapi.json>
- Проверка живости — <http://localhost:8000/health>

Остановить: `docker compose down` (с удалением данных — `docker compose down -v`).

## Запуск без Docker

```bash
cp .env.example .env          # DATABASE_URL должен указывать на ваш PostgreSQL
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

## Структура

```
src/
  api/
    dependencies.py       # зависимости FastAPI (сессия БД, текущий пользователь)
    routes/               # auth.py, tasks.py, users.py
    schemas/              # Pydantic-схемы
  core/                   # config.py, security.py, database.py
  models/                 # user.py, task.py
  repositories/           # доступ к данным
  services/               # бизнес-логика
  utils/unit_of_work.py   # единица работы
  main.py                 # создание приложения и /health
alembic/                  # миграции
tests/                    # тесты (появятся на этапе 3)
docker-compose.yml
Dockerfile
requirements.txt
```

## Эндпоинты

Сейчас реализованы:

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | Проверка живости |

В разработке (этап 2):

| Метод | Путь | Доступ |
|---|---|---|
| POST | `/auth/register` | публичный |
| POST | `/auth/login` | публичный |
| GET | `/auth/profile` | авторизованный |
| GET/POST | `/tasks` | авторизованный |
| GET/PUT/DELETE | `/tasks/{task_id}` | авторизованный |
| GET | `/admin/users` | ADMIN |
| PUT | `/admin/users/{user_id}/role` | ADMIN |

## Переменные окружения

| Переменная | Назначение |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | учётные данные PostgreSQL для compose |
| `DATABASE_URL` | строка подключения `postgresql+asyncpg://…` |
| `REDIS_URL` | адрес Redis |
| `SECRET_KEY` | секрет подписи JWT (обязательно заменить в проде) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | срок жизни токена |