# Project REST API

Начальный проект на Django и django-modern-rest с msgspec.

## Запуск

Из каталога `lab_2/project`:

```bash
uv sync --locked
uv run python manage.py migrate
uv run python manage.py runserver
```

## Маршруты

- `GET /api/v1/health/` — состояние процесса: `{"status": "ok"}`
- `/api/docs/` — Swagger UI
- `/api/openapi.json` — OpenAPI-схема

Health endpoint не проверяет подключение к базе данных. Swagger UI использует CDN.

## Структура

- `config/` — настройки Django, корневые маршруты, WSGI и ASGI
- `api/controllers.py` — HTTP-контроллеры
- `api/schemas.py` — типизированные DTO на msgspec
- `api/urls.py` — маршруты API с префиксом `api/v1/`

Предметные Django-приложения добавляются по мере реализации бизнес-логики.

## Настройки окружения

- `DJANGO_DEBUG` — режим отладки, по умолчанию `true`
- `DJANGO_SECRET_KEY` — секретный ключ, обязателен при отключённой отладке
- `DJANGO_ALLOWED_HOSTS` — допустимые хосты через запятую

Переменные читаются из окружения процесса; `.env` автоматически не загружается.
SQLite используется по умолчанию. Валидация ответов API включена.
Для cookie-аутентификации потребуется включить CSRF-проверки контроллеров
и настроить обработчик CSRF-ошибок.

## Проверка конфигурации

```bash
uv run python manage.py check
```

## Pre-commit

После клонирования установите Git hook из каталога проекта:

```bash
uv sync --locked
uv run pre-commit install
```

При каждом коммите запускается `uv run --locked ty check` для всего проекта.
Для изменённых файлов также выполняются Ruff (линтинг, сортировка импортов,
форматирование), проверки YAML, TOML, конфликтов слияния и файлов больше 1 МиБ.
Пробелы в конце строк и переводы строк в конце файлов исправляются автоматически.
После автоматических исправлений добавьте изменённые файлы в индекс повторно.
Проверку можно запустить вручную:

```bash
uv run pre-commit run --all-files
```
