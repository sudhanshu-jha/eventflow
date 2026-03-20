# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EventFlow is an async analytics and notification platform. The backend is a **Pyramid 2.0** WSGI app serving a **Graphene 3.x GraphQL** API, backed by **PostgreSQL** (via SQLAlchemy 2.0) and **Redis**. Async work runs on **Celery** workers split across three dedicated queues. The frontend is **React 18 + Vite** using **Apollo Client** for GraphQL. Full **OpenTelemetry** observability ships with every request.

## Common Commands

### Using Docker Compose (primary workflow)

```bash
make dev              # Start all services
make down             # Stop all services
make logs             # Follow logs
make restart          # Restart all services
make build            # Rebuild images
make migrate          # Apply DB migrations (alembic upgrade head)
make migration MSG="add new column"  # Create a new migration
make test             # Run backend pytest suite
make test-coverage    # Run tests with HTML coverage report
make health           # Check backend and nginx health
make jaeger           # Open Jaeger trace UI in browser
```

### Backend (without Docker)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -e ".[testing]"
alembic upgrade head
pserve development.ini --reload          # Start API server on :6543

# Run a specific test file or test
pytest analytics/tests/test_views.py
pytest -k "test_track_event"

# Celery workers (separate terminals)
celery -A analytics.tasks.celery_app worker --loglevel=info -Q events
celery -A analytics.tasks.celery_app worker --loglevel=info -Q notifications
celery -A analytics.tasks.celery_app worker --loglevel=info -Q reports
celery -A analytics.tasks.celery_app beat --loglevel=info
```

### Frontend (without Docker)

```bash
cd frontend
npm install
npm run dev      # Dev server on :5173
npm run build    # Production build
npm run lint     # ESLint check
```

## Testing & Demo Data

### Running Tests

```bash
make test              # Run full test suite with pytest
make test-coverage     # Run tests with HTML coverage report (target: 80%+)

# Without Docker (from backend directory)
pytest                          # Run all tests
pytest -k "test_register"       # Run specific test by pattern
pytest analytics/tests/test_views.py  # Run specific test file
pytest -v                       # Verbose output
pytest -x                       # Stop on first failure
```

Tests use **pytest** with fixtures in `backend/analytics/tests/conftest.py`:
- `engine` — SQLite in-memory database (session-scoped)
- `dbsession` — Per-test transactional session (rolled back after each test)
- `make_user` — Factory to create User instances
- `gql_context` — GraphQL context dict for `schema.execute()` calls
- `webtest_app` — Full Pyramid WSGI app for endpoint testing

Test files are organized by module:
- `test_views.py` — GraphQL/REST endpoint tests
- `test_mutations/auth.py` — Auth mutation tests (register, login, refresh, updateProfile, changePassword)
- `test_queries/events.py` — Event query tests
- `test_tasks/` — Celery task tests

### Seed Data

Populate database with realistic demo data:

```bash
# In Docker
docker-compose exec backend python scripts/seed.py --reset

# Without Docker (from backend directory)
python scripts/seed.py --reset --users 5
```

Seed script (`backend/scripts/seed.py`) creates:
- **Users** (with hashed passwords and API keys) — default: alice@demo.com, bob@demo.com, charlie@demo.com
- **Events** (~60 per user) — page views, clicks, form submissions, custom events, errors
- **Notifications** (in-app and email)
- **Webhooks** (with success/failure counts)

Options:
- `--reset` — Delete all existing data before seeding
- `--users N` — Create N users (default: 3 built-in; extras auto-generated)

Demo credentials:
- alice@demo.com / AlicePass1!
- bob@demo.com / BobPass1!
- charlie@demo.com / CharlieP1!

Check `backend/scripts/seed.py` for customizable event types, URLs, and templates.

## Architecture

### Backend Request Lifecycle

```
HTTP → Nginx (:80) → Backend (:6543)
                       ├── /graphql  → views.graphql_view → graphene schema.execute()
                       ├── /api/track → views.track_event (REST, API key auth)
                       └── /health   → views.health_check
```

The Pyramid app is assembled in `backend/analytics/__init__.py` (`main()` is the PasteDeploy entry point). After the WSGI app is constructed, OpenTelemetry middleware wraps it and `init_opentelemetry()` instruments SQLAlchemy, Redis, and the requests library.

### GraphQL Layer (`backend/analytics/graphql/`)

- `schema.py` — combines `Query` (from `queries/__init__.py`) and `Mutation` (from `mutations/`)
- All queries/mutations receive a `context` dict containing `request`, `dbsession`, and `user` (or `None`)
- Authentication is JWT via `Authorization: Bearer <token>`; the REST `/api/track` endpoint uses `X-API-Key`
- Mutations are split into `mutations/auth.py` (register/login/refresh/updateProfile/changePassword), `mutations/events.py`, `mutations/notifications.py`, and `mutations/__init__.py` (webhooks)

**Key Mutations:**
- `register(email, password, name)` — Create new account; returns tokens and user
- `login(email, password)` — Authenticate; returns tokens and user
- `refreshToken(refreshToken)` — Refresh access token
- `updateProfile(name)` — Update user name (requires auth)
- `changePassword(currentPassword, newPassword)` — Change password (requires auth; validates strength)
- `trackEvent(eventName, eventType, properties, ...)` — Create event via GraphQL (alt to REST `/api/track`)
- Webhook mutations: `createWebhook`, `updateWebhook`, `deleteWebhook`, `regenerateWebhookSecret`

### Celery Task Queues (`backend/analytics/tasks/`)

| Module | Queue | Purpose |
|--------|-------|---------|
| `event_processing.py` | `events` | Process and validate ingested events |
| `notifications.py` | `notifications` | Send email and in-app notifications |
| `aggregations.py` | `reports` | Daily report generation; old-event cleanup |

Celery beat schedules: daily report at 00:05 UTC, cleanup at 03:00 UTC. Each Celery worker process initializes its own OTEL session via `worker_process_init` signal in `celery_app.py`.

### Models (`backend/analytics/models/`)

- `user.py` — User with JWT auth, `api_key` field for REST access
- `event.py` — Tracked events with `is_processed` state (`pending`/`processed`/`failed`)
- `notification.py` — In-app and email notifications with `is_read` tracking
- `webhook.py` — Outbound webhook configs with delivery stats

### Frontend (`frontend/src/`)

- `index.jsx` — Entry point; calls `initTelemetry()` before rendering, registers `shutdownTelemetry()` on unload
- `App.jsx` — Route definitions with `ProtectedRoute` wrapper; calls `usePageTracking()` on every navigation
- `graphql/client.js` — Apollo Client configured to hit `/graphql`
- `context/AuthContext.jsx` — JWT token storage and refresh logic
- `hooks/useTelemetry.js` — `useTelemetry(componentName)` returns `{ trackAction, trackError, withSpan }`
- `telemetry.js` — OTEL SDK bootstrap; exports `withSpan`, `recordEvent`, `trackPageView`, `createComponentTracker`

### OpenTelemetry

Backend telemetry is configured in `backend/analytics/telemetry.py`:
- Use the `@traced("operation_name")` decorator to add a span to any function
- Use `get_tracer(__name__)` for manual span creation
- Custom metrics live in `EventFlowMetrics` class; get the singleton via `get_eventflow_metrics()`

Frontend telemetry uses W3C `traceparent` headers to correlate browser spans with backend spans. The CORS config in `__init__.py` explicitly exposes and allows `traceparent`/`tracestate` headers.

### Infrastructure

- **Ports** (Docker): Nginx :80 (main), Jaeger UI :16686, OTEL collector gRPC :4317 / HTTP :4318, Postgres :5433 (external), Redis :6380 (external)
- **Scaling**: `make scale-backend N=3`, `make scale-workers N=3`, etc. Production compose overrides in `docker-compose.prod.yml`
- **Kubernetes**: `k8s/base/` contains manifests; `k8s/overlays/dev|prod/` has Kustomize overlays. Deploy with `make k8s-dev` / `make k8s-prod`
- **Config**: Backend reads `DATABASE_URL`, `REDIS_URL`, `CELERY_BROKER_URL`, `JWT_SECRET`, and all `OTEL_*` env vars; falls back to `development.ini` values when running locally
