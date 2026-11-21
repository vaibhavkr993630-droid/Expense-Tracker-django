# Expense Tracker API (Django)

[![CI](https://github.com/vaibhavkr993630-droid/Expense-Tracker-django/actions/workflows/ci.yml/badge.svg)](https://github.com/vaibhavkr993630-droid/Expense-Tracker-django/actions/workflows/ci.yml)

A REST API for tracking personal expenses, setting monthly budgets with spending alerts, and viewing
spending analytics. Built with **Django 5.2 (LTS)**, **Django REST Framework** and **PostgreSQL**.

It reproduces the REST contract of an earlier FastAPI implementation, so the React app in
[`frontend/`](frontend/) works against it unchanged (see [`docs/api-contract.md`](docs/api-contract.md)).
The backend itself is written the Django way: custom user model, ORM aggregation, signals, the cache and
email frameworks, a management command, a customised admin, and a test suite that checks query counts.

- Interactive API docs (Swagger UI): `/api/docs` · Redoc: `/api/redoc` · OpenAPI schema: `/api/schema`

## Features

- **Accounts:** sign up, log in with email *or* username, JWT access tokens, profile, change password, delete account
- **Expenses:** create, list, update, delete; filter by date range, preset period (`week`, `month`, `3months`) and category;
  pagination; export to **CSV** (streamed) and **PDF**
- **Budgets:** one budget per category and month (creating again updates it); status per category:
  `ok` below 80 %, `warning` from 80 %, `exceeded` above 100 %
- **Alert emails:** sent when a budget gets worse (never repeated for the same level), plus a `send_budget_alerts`
  management command for scheduled runs
- **Analytics:** monthly summary, category breakdown, per-month trend, cached per user
- **Operations:** throttling on login, sign-up and exports; health check; Django admin; Docker setup; CI

## Tech stack

| Area | Choice |
|---|---|
| Framework | Django 5.2 LTS, Django REST Framework |
| Database | PostgreSQL 16 (SQLite for quick local development) |
| Auth | `djangorestframework-simplejwt` (access token, 30 min) |
| Filtering, docs | `django-filter`, `drf-spectacular` |
| PDF | `fpdf2` |
| Server | gunicorn + WhiteNoise (static files) |
| Tests, lint | pytest + pytest-django, ruff |
| Packaging, CI | Docker + docker-compose, GitHub Actions |

## Architecture

```mermaid
flowchart LR
    Client["React app / API client"] -->|"HTTP + Bearer JWT"| URLs["config/urls.py"]
    URLs --> Views["DRF views and viewsets"]
    Views --> Serializers["Serializers (validation)"]
    Views --> Services["Service functions (budgets, analytics)"]
    Services --> ORM["QuerySets (ORM aggregation)"]
    ORM --> DB[("PostgreSQL")]
    Views --> Cache["Django cache"]
    Signals["Signals (post_save / post_delete)"] -->|"invalidate"| Cache
    Views --> Mail["Django email framework"]
    Cmd["manage.py send_budget_alerts"] --> Services
```

Apps (each has its own models, serializers, views, urls and tests):

| App | Responsibility |
|---|---|
| `apps/accounts` | Custom `User` (email login), JWT login, profile endpoints, login backend |
| `apps/expenses` | `Expense` model and QuerySet, CRUD viewset, filters, pagination, CSV/PDF export |
| `apps/budgets` | `Budget` model, upsert endpoint, alert calculation, alert emails, management command |
| `apps/analytics` | Summaries with `Sum`/`Count`/`TruncMonth`, cache with per-user invalidation |
| `apps/core` | Shared pieces: owner permission, query-parameter serializer, schema helpers |
| `config/` | Split settings (`base`, `dev`, `prod`), root URLs, error handler |

Data model:

```mermaid
erDiagram
    USER ||--o{ EXPENSE : owns
    USER ||--o{ BUDGET : owns
    USER {
        string email UK
        string username UK
        string password
    }
    EXPENSE {
        decimal amount
        string category
        string description
        date date
    }
    BUDGET {
        string category
        decimal amount
        int month
        int year
        string last_alert_status
    }
```

## Django features used, and where

| Feature | Where |
|---|---|
| Custom user model (`AbstractUser`, email as `USERNAME_FIELD`, custom manager) | `apps/accounts/models.py` |
| Custom authentication backend (email or username) | `apps/accounts/backends.py` |
| Split settings driven by environment variables | `config/settings/` |
| `TextChoices`, `Meta.ordering`, composite indexes, `CheckConstraint`, `UniqueConstraint` | `apps/expenses/models.py`, `apps/budgets/models.py` |
| Custom QuerySet used as a manager (`for_user`, `in_month`, ...) | `apps/expenses/models.py` |
| Migrations (including adding a field with a default) | `apps/*/migrations/` |
| Serializers, `ModelViewSet`, mixin-based viewsets, `SimpleRouter`, `@action` | `apps/expenses/`, `apps/budgets/` |
| Object-level permission and queryset scoping (users only see their own data) | `apps/core/permissions.py`, `get_queryset()` |
| `django-filter` `FilterSet` and custom pagination | `apps/expenses/filters.py`, `pagination.py` |
| Throttling (`ScopedRateThrottle`) | `config/settings/base.py`, views |
| ORM aggregation: `aggregate`, `values().annotate()`, `TruncMonth`; no N+1 queries | `apps/analytics/services.py`, `apps/budgets/services.py` |
| Cache framework with versioned keys, signals for invalidation | `apps/analytics/cache.py`, `signals.py` |
| Email framework (multipart text + HTML, templates) | `apps/budgets/notifications.py` |
| Custom management command | `apps/budgets/management/commands/send_budget_alerts.py` |
| Streaming response (CSV) | `apps/expenses/exports.py` |
| Customised admin (filters, search, `date_hierarchy`, `list_select_related`, custom action) | `apps/*/admin.py` |
| OpenAPI docs | `drf-spectacular`, `config/urls.py` |

## API overview

All endpoints except `/signup`, `/login` and `/healthy` need `Authorization: Bearer <access_token>`.
Errors are returned as `{"detail": "<message>"}`. Full details, parameters and example bodies are in
`/api/docs`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/signup` | Register (rate limited) |
| POST | `/login` | Get a token (form fields `username` + `password`; username may be the email) |
| GET, DELETE | `/users/me` | Profile / delete account |
| PATCH | `/users/change-password` | Change password |
| GET, POST | `/expenses` | List with filters and pagination / add |
| GET, PUT, DELETE | `/expenses/{id}` | Read / update / delete one |
| GET | `/expenses/export/csv`, `/expenses/export/pdf` | Download with the same filters |
| GET | `/expenses/summary/monthly`, `/category`, `/trend` | Analytics |
| GET, POST | `/budgets` | List a month's budgets / set a budget |
| DELETE | `/budgets/{id}` | Delete a budget |
| GET | `/budgets/alerts` | Spending versus budget per category |
| GET | `/healthy` | Liveness check |

## Getting started

### 1. Run locally (SQLite, no Docker needed)

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env                 # optional in development
python manage.py migrate
python manage.py createsuperuser     # asks for email, username and password
python manage.py runserver           # http://localhost:8000
```

Open <http://localhost:8000/api/docs> to try the API, and <http://localhost:8000/admin/> for the admin.
In development, emails are printed to the terminal instead of being sent.

### 2. Run with Docker (PostgreSQL + gunicorn)

```bash
cp .env.example .env
# set DJANGO_SECRET_KEY to a random value of at least 32 characters, for example:
python -c "import secrets; print(secrets.token_urlsafe(50))"
docker compose up --build
```

The API is on <http://localhost:8000> (set `WEB_PORT` in `.env` if that port is taken). The container
applies migrations on start. Create an admin user with
`docker compose exec web python manage.py createsuperuser`.

### 3. Run the React frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173, proxies API calls to localhost:8000
```

### Tests and checks

```bash
pytest -q                            # 298 tests (SQLite by default)
ruff check . && ruff format --check .
python manage.py makemigrations --check --dry-run
```

To run the tests against PostgreSQL, as CI does:

```bash
docker compose up -d db              # needs DJANGO_SECRET_KEY set, see above
DATABASE_URL=postgres://expense:expense@localhost:5432/expense_tracker pytest -q
```

### Scheduled budget alerts

```bash
python manage.py send_budget_alerts --dry-run          # show who would be emailed
python manage.py send_budget_alerts                    # current month
python manage.py send_budget_alerts --month 5 --year 2026
```

Because an email is only sent when a budget's level gets worse, it is safe to run this daily, for example
with cron: `0 8 * * * cd /app && python manage.py send_budget_alerts`.

## Configuration

Settings are read from environment variables (or a local `.env` file). See [`.env.example`](.env.example).

| Variable | Used in | Purpose |
|---|---|---|
| `DJANGO_SECRET_KEY` | prod (required), dev (has a default) | Signing key for sessions and JWTs; use 32+ random characters |
| `DJANGO_ALLOWED_HOSTS` | prod (required) | Comma-separated host names |
| `DATABASE_URL` | all | e.g. `postgres://user:pass@host:5432/db`; SQLite when unset |
| `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` | prod | Browser origins allowed to call the API |
| `USE_HTTPS` | prod | `true` by default; `false` only for plain-http local runs (docker compose) |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL` | all | SMTP (Gmail) credentials; console output when unset |
| `POSTGRES_PASSWORD`, `WEB_PORT`, `DB_PORT` | docker compose | Container settings |

## Testing

298 tests cover:

- **Authentication and ownership:** token handling, expired and invalid tokens, and that one user can never read, change or
  delete another user's data
- **Filters and pagination:** date ranges, periods, categories, page limits, invalid input
- **Analytics and budgets:** aggregation results, alert thresholds, and exact **query counts** (no N+1)
- **Cache:** hits, per-user separation, invalidation on create, update and delete
- **Emails and command:** when an email is sent, deduplication, failure handling
- **Exports and admin:** CSV and PDF content, spreadsheet-formula safety, admin lists, search and actions
- **API docs:** the schema must generate without warnings and match the API contract

CI (GitHub Actions) runs lint, the tests on PostgreSQL 16, the migration and deploy checks, and builds and starts the
Docker stack.

## Design notes and known limitations

- **Alerts are sent inside the request** that changes the data (as the original API did). Failures are logged and
  never break the request. A background worker such as Celery would be the next step.
- **The cache is local memory** (per process). Several server processes would each keep their own cache; use Redis
  for that. Bulk operations such as `QuerySet.update()` do not send signals, so they would not invalidate the cache
  (the app does not use them for expenses).
- **PDF export is built in memory** and refuses more than 5000 rows; CSV export streams and has no such limit.
- **Passwords** are checked with Django's validators, which is stricter than a plain minimum length.
- **Migrations run when the container starts.** That is fine for a single instance; with several instances, run
  them as a separate release step.

## License

MIT, see [LICENSE](LICENSE).
