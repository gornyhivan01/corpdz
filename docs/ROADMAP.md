# Состояние проекта и план

Документ для продолжения работы: что готово, какие решения приняты и что делать
дальше. Обновляется по мере прохождения этапов ТЗ.

## Готово

**Этап 1.** Каркас Clean Architecture: `src/{api,core,models,repositories,services,utils}`,
Alembic с миграцией `0001` (users, tasks), `Dockerfile`, `docker-compose.yml`
(app + PostgreSQL + Redis), `.env.example`, `requirements.txt` из `uv.lock`.

**Этап 2.** API:

| Метод | Путь | Доступ |
|---|---|---|
| POST | `/auth/register` | публичный |
| POST | `/auth/login` | публичный |
| GET | `/auth/profile` | авторизованный |
| GET/POST | `/tasks` | авторизованный |
| GET/PUT/DELETE | `/tasks/{task_id}` | авторизованный |
| GET | `/admin/users` | ADMIN |
| POST | `/admin/users` | ADMIN |
| DELETE | `/admin/users/{user_id}` | ADMIN |
| PUT | `/admin/users/{user_id}/role` | ADMIN |
| GET | `/health` | публичный |

Проверено на живом стеке: регистрация, вход, создание/список/фильтры задач,
403 на чужую задачу, 401 без токена, админ-ручки, смена роли, удаление (204),
фоновая «отправка письма» в лог.

**Этап 3.** Тесты:

- `pytest` + `pytest-asyncio` (`asyncio_mode = "auto"`), `httpx.AsyncClient`
  поверх `ASGITransport` — приложение тестируется как есть, без сети.
- `tests/conftest.py`: `postgres_container` (Testcontainers, `postgres:16-alpine`),
  применение `alembic upgrade head` к тестовой базе, `async_client`,
  токены `user_token` / `other_user_token` / `admin_token`, очистка таблиц
  перед каждым тестом.
- `tests/integration/`: регистрация и вход (успех, 409 на дубль, 401 на неверный
  пароль, 422 на короткий пароль), профиль, CRUD задач, RBAC (чужая задача → 403,
  `/admin/users` под USER → 403), админские ручки и смена роли, ошибки 401/404/422,
  фильтры `status`/`priority`/`deadline_from`/`deadline_to` и пагинация.
- `tests/unit/`: bcrypt, JWT (в том числе просроченный и чужой токен),
  валидация Pydantic-схем.
- CI: job `test` с сервисом `postgres`, тесты берут его через `TEST_DATABASE_URL`.

Запуск: `uv run pytest -q` (нужен Docker) или, без Docker,
`TEST_DATABASE_URL=… uv run pytest -q`.

**Этап 4.** Docker и CI/CD:

- `Dockerfile` — `python:3.12-slim`, непривилегированный `appuser`, зависимости из
  `requirements.txt`; `.dockerignore` не пускает в контекст `.git`, `.env`,
  `.venv`, `tests`, `docs`.
- `docker compose` (app + PostgreSQL + Redis) проверен **с нуля на чистом томе**:
  `docker compose down -v && docker compose up -d --build` — миграции применяются
  при старте, `/health` отвечает, API работает на PostgreSQL.
- CI: два job — `test` (тесты с сервисом `postgres`) и `docker` (сборка образа +
  проверка, что приложение импортируется внутри образа). Пуш в реестр не нужен.

**Дополнительно: веб-интерфейс.** React 18 + Vite + TypeScript в `frontend/`:

- экраны входа и регистрации, список задач (фильтры по статусу/приоритету/
  дедлайну, пагинация, создание/редактирование/удаление в модальном окне),
  админка для роли ADMIN — пользователи, создание, удаление и смена роли,
  переключатель «Архив» у администратора;
- `npm run build` → `dist/`, в образе копируется в `/app/static` и раздаётся тем
  же FastAPI по `/`; локально `npm run dev` проксирует API на порт 8000;
- JWT хранится в `localStorage`, на 401 интерфейс разлогинивается;
- CI: job `frontend` собирает интерфейс, job `docker` проверяет, что `/` отдаёт SPA.

**Дополнительно: управление пользователями и архив задач.**

- ADMIN может создавать пользователей с любой ролью (`POST /admin/users`) и
  удалять их (`DELETE /admin/users/{user_id}`, 204).
- При удалении пользователя его задачи **не удаляются**, а уходят в архив:
  миграция `0002` делает `tasks.user_id` nullable (FK `ON DELETE SET NULL`) и
  добавляет `archived_at` + `archived_owner_email`.
- Архив виден только ADMIN и отдельным запросом `GET /tasks?archived=true`;
  обычный список архив не показывает. Фильтры и пагинация работают и там.
- Защиты: нельзя удалить собственную учётную запись (400) и последнего
  администратора (400); дубль email при создании — 409.

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
- Тесты по умолчанию поднимают PostgreSQL в Testcontainers; `TEST_DATABASE_URL`
  переключает их на внешнюю базу (так устроен CI, где Docker-в-Docker не нужен).
- Тестовая схема создаётся только миграциями Alembic, а не `create_all`, —
  проверяется и сама миграция `0001`.
- Изоляция тестов: таблицы очищаются `TRUNCATE ... RESTART IDENTITY` перед
  каждым тестом, пул соединений закрывается после теста.
- Администратора в тестах назначаем SQL-запросом (публичной ручки выдачи роли
  нет), как описано в README.
- Весь прогон идёт в одном event loop (`loop_scope = session`), чтобы пул
  asyncpg не переезжал между циклами.
- CI образ только собирает (`docker build`), без пуша в реестр: для сдачи
  достаточно успешной сборки и проверки импорта внутри образа.
- Фронтенд — React 18 + Vite + TypeScript, без Next.js: SPA раздаётся тем же
  FastAPI из `static/`, отдельный контейнер и CORS не нужны.
- Маршруты SPA — `HashRouter`: серверу не нужен fallback на `index.html`, а API
  сохраняет 404 для неизвестных путей.
- Удаление пользователя — физическое (строка `users` исчезает), но задачи
  сохраняются в архиве с email владельца: история не теряется, а
  `user_id` обнуляется через `ON DELETE SET NULL`.
- Архив — отдельный флаг `?archived=true`, а не смешивание с активными задачами:
  обычный список остаётся предсказуемым, а ADMIN переключает режим явно.

## Как запустить

```bash
docker compose up -d          # app + postgres + redis, миграции при старте
docker compose down -v        # остановить и удалить данные (чистый старт)
# Интерфейс: http://localhost:8000/   Swagger: http://localhost:8000/docs
```

Локально без Docker: `uv sync && uv run alembic upgrade head && uv run uvicorn src.main:app --reload`.

Тесты: `uv run pytest -q`.

## Дальше: этап 5 — сдача

- README: mermaid-схема компонентов и сквозные примеры с данными (есть).
- Публичный репозиторий: <https://github.com/gornyhivan01/corpdz>.
