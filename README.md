# Task Management System

Итоговое домашнее задание: REST API для управления задачами.

**Стек:** FastAPI, Pydantic v2, PostgreSQL, SQLAlchemy 2.0 (async, asyncpg),
Alembic, JWT, bcrypt, React 18 + Vite + TypeScript, Docker Compose, GitHub Actions.

## Архитектура

Компоненты и связи:

```mermaid
flowchart LR
    subgraph client["Клиент"]
        SPA["React SPA<br/>HashRouter + fetch"]
        DOCS["Swagger UI<br/>/docs"]
        CLI["curl / Postman"]
    end

    subgraph app["FastAPI (src/)"]
        ROUTES["Роуты<br/>auth · tasks · admin · health"]
        DEPS["Зависимости<br/>JWT · RBAC · сессия БД"]
        SERVICES["Сервисы<br/>UserService · TaskService"]
        REPOS["Репозитории<br/>User · Task"]
        UOW["Unit of Work<br/>commit / rollback"]
        BG["BackgroundTasks<br/>«email» → лог"]
        STATIC["StaticFiles<br/>frontend/dist"]
    end

    PG[("PostgreSQL 16")]
    REDIS[("Redis 7<br/>резерв под Celery")]
    ALEMBIC["Alembic<br/>миграции"]

    SPA -->|"REST + Bearer JWT"| ROUTES
    DOCS --> ROUTES
    CLI --> ROUTES
    STATIC -->|"index.html + assets"| SPA
    ROUTES --> DEPS
    ROUTES --> SERVICES
    ROUTES -.->|"после ответа"| BG
    SERVICES --> REPOS
    SERVICES --> UOW
    REPOS -->|"SQLAlchemy async"| PG
    UOW --> PG
    ALEMBIC -->|"upgrade head"| PG
    REDIS -.->|"пока не используется"| SERVICES
```

Путь запроса:

1. Браузер (React SPA), Swagger UI или curl отправляет REST-запрос с
   `Authorization: Bearer <JWT>`.
2. Зависимости (`src/api/dependencies.py`) проверяют подпись токена и роль,
   затем открывают `AsyncSession` через `get_session`.
3. Роут вызывает сервис, сервис — репозиторий; транзакцию закрывает `UnitOfWork`
   (`commit` при успехе, `rollback` при ошибке).
4. После ответа `BackgroundTasks` пишет «письмо» о созданной задаче в лог
   (`app.notifications`).
5. Схему БД накатывает Alembic при старте контейнера; Redis оставлен под будущий
   Celery и сейчас не используется.

## Требования

- Docker и Docker Compose
- Python 3.11+ (для запуска без Docker)
- Node.js 22+ (только для разработки интерфейса)

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up -d
```

Поднимутся PostgreSQL, Redis и приложение, применятся миграции Alembic.
Интерфейс: <http://localhost:8000/>, Swagger UI: <http://localhost:8000/docs>.

Остановить: `docker compose down` (с данными — `docker compose down -v`).

## Веб-интерфейс

React-приложение (React 18 + Vite + TypeScript) собирается в `frontend/dist` и
раздаётся тем же FastAPI по `/` — отдельный сервер и CORS не нужны. Во время
разработки Vite проксирует `/auth`, `/tasks`, `/admin` на `http://127.0.0.1:8000`.

Экраны:

- вход и регистрация (JWT хранится в `localStorage`);
- список задач с фильтрами по статусу, приоритету и дедлайну, пагинацией,
  созданием, редактированием и удалением в модальном окне;
- админка (видна только роли ADMIN): список пользователей и смена роли.

Разработка:

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173, запросы к API проксируются на 8000
```

Сборка статики (её же делает `Dockerfile` в первом stage):

```bash
cd frontend
npm run build      # dist/ -> в образе /app/static
```

## Запуск без Docker

```bash
cp .env.example .env          # DATABASE_URL должен указывать на ваш PostgreSQL
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

## Тесты

```bash
uv sync
uv run pytest -q
```

Нужен запущенный Docker: интеграционные тесты сами поднимают `postgres:16-alpine`
через Testcontainers, накатывают миграции Alembic и очищают таблицы перед каждым
тестом. Сеть не используется — запросы идут в приложение через `ASGITransport`.

Если Docker недоступен (например, в CI), укажите готовую базу:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://app:app@localhost:5432/app uv run pytest -q
```

Что покрыто:

- `tests/integration/` — регистрация/вход/профиль, CRUD задач, RBAC (403 на
  чужую задачу и на админ-ручки), админские ручки и смена роли, ошибки
  401/404/422, фильтры и пагинация;
- `tests/unit/` — bcrypt, JWT и валидация Pydantic-схем.

## CI

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) запускается на push и pull
request и состоит из трёх job:

| Job | Что делает |
|---|---|
| `test` | линтер `ruff`, затем `uv run pytest -q` против сервиса `postgres` |
| `frontend` | собирает React-интерфейс (`npm ci && npm run build`) |
| `docker` | собирает образ, проверяет импорт приложения и что по `/` отдаётся интерфейс |

Пуш образа в реестр не выполняется — достаточно успешной сборки.

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

## Примеры использования

Базовый URL — `http://localhost:8000`. Сквозной сценарий: Иван
(`ivan@example.com`, роль USER) и администратор (`admin@example.com`).
Считаем, что Иван уже зарегистрирован (раздел 1), а администратор назначен
(см. «Первый администратор»). Все ответы ниже — реальные ответы запущенного стека.

Подготовка токенов:

```bash
BASE=http://localhost:8000

TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "ivan@example.com", "password": "secure123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

ADMIN_TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "admin@example.com", "password": "secure123"}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")
```

### 1. Регистрация

```bash
curl -s -X POST $BASE/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email": "ivan@example.com", "password": "secure123", "name": "Иван Иванов"}'
```

`201 Created`:

```json
{
  "id": 1,
  "email": "ivan@example.com",
  "name": "Иван Иванов",
  "role": "USER",
  "created_at": "2026-11-09T12:37:11.955934Z"
}
```

Повторная регистрация того же email — `409 Conflict`:

```json
{"detail": "Пользователь с таким email уже существует"}
```

### 2. Вход

```bash
curl -s -X POST $BASE/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "ivan@example.com", "password": "secure123"}'
```

`200 OK`:

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiaWF0IjoxNzk0MjI3NTQwLCJleHAiOjE3OTQyMjkzNDB9.O_jGPmJfm0_XOI-mLHk3C4kjz2X_hgQAxEvjSIY45_0",
  "token_type": "bearer",
  "expires_in": 1800
}
```

Неверный пароль — `401 Unauthorized`:

```json
{"detail": "Неверный email или пароль"}
```

### 3. Профиль

```bash
curl -s $BASE/auth/profile -H "Authorization: Bearer $TOKEN"
```

```json
{
  "id": 1,
  "email": "ivan@example.com",
  "name": "Иван Иванов",
  "role": "USER",
  "created_at": "2026-11-09T12:37:11.955934Z"
}
```

Без заголовка `Authorization` — `401 Unauthorized`:

```json
{"detail": "Не удалось проверить токен"}
```

### 4. Создание задачи

```bash
curl -s -X POST $BASE/tasks \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title": "Разработать API", "description": "Этапы 1–2", "priority": "high", "deadline": "2026-12-01T10:00:00+03:00"}'
```

`201 Created` — дедлайн приводится к UTC, `status` по умолчанию `pending`:

```json
{
  "id": 1,
  "title": "Разработать API",
  "description": "Этапы 1–2",
  "status": "pending",
  "priority": "high",
  "deadline": "2026-12-01T07:00:00Z",
  "user_id": 1,
  "created_at": "2026-11-09T12:37:12.720175Z",
  "updated_at": "2026-11-09T12:37:12.720175Z"
}
```

### 5. Список задач с фильтрами и пагинацией

```bash
curl -s "$BASE/tasks?status=pending&priority=high&limit=10&offset=0" \
  -H "Authorization: Bearer $TOKEN"
```

`200 OK` — только свои задачи (ADMIN видит все), сортировка от новых к старым:

```json
{
  "total": 2,
  "limit": 10,
  "offset": 0,
  "items": [
    {
      "id": 2,
      "title": "Написать тесты",
      "description": null,
      "status": "pending",
      "priority": "high",
      "deadline": null,
      "user_id": 1,
      "created_at": "2026-11-09T12:40:01.100000Z",
      "updated_at": "2026-11-09T12:40:01.100000Z"
    },
    {
      "id": 1,
      "title": "Разработать API",
      "description": "Этапы 1–2",
      "status": "pending",
      "priority": "high",
      "deadline": "2026-12-01T07:00:00Z",
      "user_id": 1,
      "created_at": "2026-11-09T12:37:12.720175Z",
      "updated_at": "2026-11-09T12:37:12.720175Z"
    }
  ]
}
```

### 6. Изменение задачи

```bash
curl -s -X PUT $BASE/tasks/2 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"status": "done"}'
```

`200 OK` — меняются только переданные поля, `updated_at` обновляется:

```json
{
  "id": 2,
  "title": "Написать тесты",
  "description": null,
  "status": "done",
  "priority": "high",
  "deadline": null,
  "user_id": 1,
  "created_at": "2026-11-09T12:40:01.100000Z",
  "updated_at": "2026-11-09T12:41:33.500000Z"
}
```

### 7. Удаление задачи

```bash
curl -i -X DELETE $BASE/tasks/2 -H "Authorization: Bearer $TOKEN"
```

`204 No Content` — тело пустое; повторный `GET /tasks/2` вернёт `404 Not Found`:

```json
{"detail": "Задача не найдена"}
```

### 8. Админские ручки (роль ADMIN)

Список пользователей:

```bash
curl -s "$BASE/admin/users?limit=20&offset=0" -H "Authorization: Bearer $ADMIN_TOKEN"
```

```json
{
  "total": 2,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "email": "ivan@example.com",
      "name": "Иван Иванов",
      "role": "USER",
      "created_at": "2026-11-09T12:37:11.955934Z"
    },
    {
      "id": 2,
      "email": "admin@example.com",
      "name": "Администратор",
      "role": "ADMIN",
      "created_at": "2026-11-09T12:38:02.311000Z"
    }
  ]
}
```

Смена роли:

```bash
curl -s -X PUT $BASE/admin/users/1/role \
  -H "Authorization: Bearer $ADMIN_TOKEN" -H 'Content-Type: application/json' \
  -d '{"role": "ADMIN"}'
```

```json
{
  "id": 1,
  "email": "ivan@example.com",
  "name": "Иван Иванов",
  "role": "ADMIN",
  "created_at": "2026-11-09T12:37:11.955934Z"
}
```

Под токеном USER те же ручки отвечают `403 Forbidden`:

```json
{"detail": "Недостаточно прав"}
```

### Ошибки

| Код | Ситуация | Тело ответа |
|---|---|---|
| 401 | нет, битый или просроченный токен | `{"detail": "Не удалось проверить токен"}` |
| 401 | неверный email или пароль | `{"detail": "Неверный email или пароль"}` |
| 403 | чужая задача или нет роли ADMIN | `{"detail": "Недостаточно прав"}` |
| 404 | задачи или пользователя нет | `{"detail": "Задача не найдена"}` |
| 409 | email уже занят | `{"detail": "Пользователь с таким email уже существует"}` |
| 422 | невалидные данные | `{"detail": [{"type": "string_too_short", "loc": ["body", "password"], "msg": "String should have at least 8 characters", "input": "12345", "ctx": {"min_length": 8}}]}` |

Проверить примеры можно и из интерфейса: <http://localhost:8000/> — те же
операции, только через формы.

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
frontend/         # React + Vite + TypeScript (src/api, src/auth, src/pages)
static/           # собранный интерфейс (создаётся сборкой, в git не хранится)
alembic/          # миграции
tests/            # unit- и интеграционные тесты
.github/          # CI: сборка образа и тесты
Dockerfile        # образ приложения (python:3.12-slim, appuser, сборка фронта)
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
