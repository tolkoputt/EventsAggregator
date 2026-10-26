# Events Aggregator

Сервис агрегирует события из внешнего API, предоставляет HTTP API для событий
и регистрации на них, а также отправляет уведомления о регистрации через
Capashino.

## Требования

- Python 3.13+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/)
- URL и API-ключи внешнего провайдера событий и Capashino

## Конфигурация

Приложение читает настройки из переменных окружения. Для локальной разработки
их можно поместить в `.env` в корне проекта. Файл `.env` не следует коммитить.

| Переменная | Обязательная | Назначение |
| --- | --- | --- |
| `POSTGRES_USERNAME` | Да | Пользователь PostgreSQL |
| `POSTGRES_PASSWORD` | Да | Пароль PostgreSQL |
| `POSTGRES_HOST` | Да | Хост PostgreSQL |
| `POSTGRES_PORT` | Нет | Порт PostgreSQL, по умолчанию `5432` |
| `POSTGRES_DATABASE_NAME` | Да | Имя базы данных |
| `EXTERNAL_API_KEY` | Да | API-ключ внешнего API событий |
| `EXTERNAL_API_URL` | Да | Базовый URL внешнего API событий |
| `CAPASHINO_API_URL` | Да | Базовый URL Capashino |
| `SENTRY_DSN` | Нет | DSN GlitchTip; без него отправка ошибок отключена |

Минимальный шаблон `.env`:

```dotenv
POSTGRES_USERNAME=events_user
POSTGRES_PASSWORD=replace-me
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE_NAME=events

EXTERNAL_API_KEY=replace-me
EXTERNAL_API_URL=https://events-provider.example
CAPASHINO_API_URL=https://capashino.example

# Необязательно для локальной разработки. В production задаётся.
SENTRY_DSN=
```

Не используйте примерные значения в рабочем окружении. Если приложение должно
читать настройки из другого файла, укажите путь переменной `ENV_FILE`.

## Локальный запуск

Установите зависимости и создайте виртуальное окружение:

```bash
uv sync
```

Примените миграции к настроенной базе:

```bash
uv run alembic upgrade head
```

Запустите API:

```bash
uv run uvicorn eventsaggregator.main:app --reload
```

По умолчанию API будет доступен на `http://127.0.0.1:8000`.

## Docker

Docker-образ запускает миграции (`alembic upgrade head`), затем стартует
Uvicorn на порту `8000`. Перед запуском контейнера передайте ему те же
обязательные переменные окружения, что перечислены выше. `SENTRY_DSN` можно
передавать через механизм secrets/environment платформы деплоя; не встраивайте
DSN и API-ключи в образ.

## HTTP API

Интерактивная документация OpenAPI доступна по адресу `/docs`, схема — `/openapi.json`.

| Метод | Путь | Назначение |
| --- | --- | --- |
| `GET` | `/api/health` | Проверка доступности сервиса |
| `GET` | `/api/events` | Список событий с пагинацией |
| `GET` | `/api/events/{event_id}` | Информация о событии |
| `GET` | `/api/events/{event_id}/seats` | Доступные места опубликованного события |
| `POST` | `/api/tickets` | Регистрация на событие |
| `DELETE` | `/api/tickets/{ticket_id}` | Отмена регистрации |
| `POST` | `/api/sync/trigger` | Запустить синхронизацию вручную |

Список событий поддерживает параметры `page` (начиная с 1), `page_size`
(от 1 до 100, по умолчанию 10) и необязательный `date_from`:

```text
GET /api/events?page=1&page_size=20&date_from=2026-10-01T00:00:00Z
```

Пример регистрации:

```bash
curl -X POST http://127.0.0.1:8000/api/tickets \
  -H 'Content-Type: application/json' \
  -d '{
    "idempotency_key": "client-request-123",
    "event_id": "1045417a-8597-4d37-9e7d-57c44576b871",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "email": "ada@example.com",
    "seat": "B1"
  }'
```

`idempotency_key` необязателен. При повторе того же ключа с теми же данными
сервис возвращает уже созданный билет; повторное использование ключа с другим
payload приводит к `409 Conflict`.

## Фоновые задачи и уведомления

- Синхронизация событий запускается ежедневно в `03:00` по часовому поясу
  `Asia/Yekaterinburg`; также её можно запустить через `/api/sync/trigger`.
- Outbox проверяется каждые 20 секунд. Для каждой записи используется блокировка
  PostgreSQL `FOR UPDATE SKIP LOCKED`, чтобы несколько экземпляров сервиса не
  обрабатывали одну запись одновременно.
- Для временных ошибок Capashino выполняется до пяти HTTP-попыток. Постоянные
  ошибки и записи, достигшие лимита, автоматически больше не выбираются.
- Статус доставки `409 Conflict` от Capashino считается успешным повтором по
  idempotency key.

## GlitchTip

Проект использует `sentry-sdk` с FastAPI-интеграцией. Укажите `SENTRY_DSN` в
окружении приложения, используя DSN, выданный GlitchTip. Если DSN отсутствует,
приложение запускается без отправки событий. PII по умолчанию не отправляются.

После деплоя проверьте интеграцию, вызвав тестовый необработанный сбой только в
безопасной тестовой среде, и убедитесь, что событие появилось в нужном проекте
GlitchTip. Не публикуйте DSN в исходном коде или логах.

## Миграции базы данных

Применить все миграции:

```bash
uv run alembic upgrade head
```

Создать миграцию после изменения SQLAlchemy-моделей и применить её:

```bash
uv run alembic revision --autogenerate -m "describe schema change"
uv run alembic upgrade head
```

## Тесты и линтер

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```
