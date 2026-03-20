# Contributing to EventFlow

**Last Updated:** 2026-03-20

Thank you for contributing to EventFlow! This guide covers setup, development workflow, testing, and code standards.

## Prerequisites

- **Docker & Docker Compose** (recommended for development)
- **Python 3.9+** (for direct backend development)
- **Node.js 18+** (for frontend development)
- **Git**

## Development Environment Setup

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repo-url>
cd eventflow

# Start all services
make dev

# View logs
make logs

# Run migrations and seed data
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed.py --reset
```

Access the application:
- **Frontend**: http://localhost or http://localhost:5173 (direct)
- **Backend GraphQL**: http://localhost:6543/graphql
- **Jaeger UI** (traces): http://localhost:16686
- **Health Check**: http://localhost:6543/health

### Backend Setup (Without Docker)

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (including testing extras)
pip install -e ".[testing]"

# Configure database (create local PostgreSQL database)
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/analytics"

# Run migrations
alembic upgrade head

# Seed demo data
python scripts/seed.py --reset --users 3

# Start the backend server
pserve development.ini --reload

# In separate terminals, start Celery workers
celery -A analytics.tasks.celery_app worker --loglevel=info -Q events
celery -A analytics.tasks.celery_app worker --loglevel=info -Q notifications
celery -A analytics.tasks.celery_app worker --loglevel=info -Q reports

# Start Celery beat scheduler (for periodic tasks)
celery -A analytics.tasks.celery_app beat --loglevel=info
```

### Frontend Setup (Without Docker)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```

## Available Make Commands

<!-- AUTO-GENERATED: Generated from Makefile -->

### Docker Compose

| Command | Purpose |
|---------|---------|
| `make dev` | Start development environment |
| `make prod` | Start production environment with prod overrides |
| `make up` | Start all services |
| `make down` | Stop all services |
| `make logs` | Follow service logs in real-time |
| `make restart` | Restart all services |
| `make clean` | Remove containers and volumes |

### Database

| Command | Purpose |
|---------|---------|
| `make migrate` | Run Alembic migrations (upgrade head) |
| `make migration MSG="description"` | Create a new migration |

### Testing

| Command | Purpose |
|---------|---------|
| `make test` | Run all backend tests with pytest |
| `make test-coverage` | Run tests with coverage report (HTML) |

### Scaling

| Command | Purpose |
|---------|---------|
| `make scale-backend N=3` | Scale backend to N replicas |
| `make scale-frontend N=2` | Scale frontend to N replicas |
| `make scale-workers N=3` | Scale all Celery workers to N replicas |
| `make scale-events N=5` | Scale events workers to N replicas |
| `make scale-notifications N=3` | Scale notifications workers to N replicas |
| `make scale-reports N=2` | Scale reports workers to N replicas |
| `make scale-status` | Show current replica counts |

### Build & Registry

| Command | Purpose |
|---------|---------|
| `make build` | Build all Docker images |
| `make build-backend` | Build backend image only |
| `make build-frontend` | Build frontend image only |
| `make push REGISTRY=<url>` | Push images to Docker registry |

### Kubernetes

| Command | Purpose |
|---------|---------|
| `make k8s-dev` | Deploy to Kubernetes (dev overlay) |
| `make k8s-prod` | Deploy to Kubernetes (prod overlay) |
| `make k8s-status` | Check K8s deployment status |
| `make k8s-delete` | Delete K8s deployment |
| `make k8s-port-forward` | Start port forwards for local access |
| `make k8s-scale-backend N=5` | Scale backend deployment |
| `make k8s-scale-frontend N=3` | Scale frontend deployment |

### Monitoring

| Command | Purpose |
|---------|---------|
| `make jaeger` | Open Jaeger UI in browser |
| `make otel-metrics` | View OTEL collector metrics |
| `make health` | Check backend and Nginx health |

<!-- END AUTO-GENERATED -->

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage report
make test-coverage

# Run specific test file (from backend directory)
pytest analytics/tests/test_views.py

# Run specific test by name
pytest -k "test_graphql_register"

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

### Test Structure

Tests use **pytest** with fixtures defined in `backend/analytics/tests/conftest.py`:

- **Unit tests**: Test individual functions and services
- **Integration tests**: Test API endpoints and database operations
- **Fixtures**:
  - `engine` — SQLite in-memory database
  - `dbsession` — Per-test transactional session
  - `make_user` — Factory to create test users
  - `gql_context` — GraphQL context dict
  - `webtest_app` — Full Pyramid app for endpoint tests

### Test Coverage Target

Aim for **80%+ code coverage**. Generate coverage reports:

```bash
make test-coverage
# Open coverage report: open htmlcov/index.html
```

## Code Standards

### Python Backend

- **Style**: PEP 8 with black formatting (run `black .`)
- **Type hints**: Use where possible for clarity
- **Docstrings**: Google-style for public functions/classes
- **Error handling**: Never silently swallow exceptions; log or propagate with context
- **Database queries**: Use SQLAlchemy ORM, parameterized queries
- **Authentication**: Check `info.context.get('user')` in GraphQL mutations; use `X-API-Key` header for REST endpoints

### JavaScript/React Frontend

- **Style**: ESLint configured; run `npm run lint`
- **Components**: Functional components with hooks
- **State management**: React Context for auth, Apollo Client for GraphQL
- **Error handling**: Catch and display errors to users
- **Telemetry**: Use `useTelemetry()` hook to track user actions and errors

### File Organization

- **Small, focused files** — 200-400 lines typical, max 800
- **High cohesion, low coupling** — Files organized by feature/domain, not by type
- **Clear naming** — File/function/variable names should be self-documenting
- **No deep nesting** — Prefer early returns and helper functions

## Seed Data

Generate realistic demo data for testing and development:

```bash
# In Docker
docker-compose exec backend python scripts/seed.py --reset

# Without Docker (from backend directory)
python scripts/seed.py --reset --users 5
```

Demo credentials (from seed):
- alice@demo.com / AlicePass1!
- bob@demo.com / BobPass1!
- charlie@demo.com / CharlieP1!

The seed script creates:
- Users with API keys
- Events (page views, clicks, form submissions, custom events)
- Notifications (in-app and email)
- Webhooks (with success/failure counts)

Options:
- `--reset` — Delete all existing data before seeding
- `--users N` — Create N users (default: 3, max built-in: 3)

## Database Migrations

### Creating Migrations

```bash
# Auto-generate migration from model changes
make migration MSG="add user.last_login field"

# Without Docker
cd backend
alembic revision --autogenerate -m "add user.last_login field"
```

### Running Migrations

```bash
# Apply all pending migrations
make migrate

# Without Docker
cd backend
alembic upgrade head
```

### Migration Best Practices

- Always test migrations on a backup database first
- Write both `upgrade()` and `downgrade()` steps
- Keep migrations small and focused
- Add data migrations before schema changes when needed

## API Documentation

### REST Endpoints

| Endpoint | Method | Authentication | Purpose |
|----------|--------|----------------|---------|
| `/graphql` | POST | JWT or none | GraphQL API |
| `/api/track` | POST | X-API-Key header | Track events (client SDK) |
| `/health` | GET | None | Health check |

### GraphQL Queries

```graphql
# Current user (requires auth)
query {
  me {
    id email name apiKey isActive createdAt
  }
}

# Event statistics
query {
  eventStats {
    totalEvents eventsToday eventsThisWeek uniqueSessions
    topEvents { name count }
    eventsByType { type count }
  }
}

# Events with filtering
query {
  events(eventType: "click", limit: 50, offset: 0) {
    events {
      id eventType eventName properties timestamp isProcessed
    }
    totalCount hasNextPage
  }
}

# Notifications
query {
  notifications(unreadOnly: true) {
    id title content isRead createdAt
  }
  unreadNotificationCount
}

# Webhooks
query {
  webhooks {
    id name url events isActive successCount failureCount
  }
}
```

### GraphQL Mutations

```graphql
# Register
mutation {
  register(email: "user@example.com", password: "SecurePass1!", name: "User Name") {
    success tokens { accessToken refreshToken expiresIn }
    user { id email }
  }
}

# Login
mutation {
  login(email: "user@example.com", password: "SecurePass1!") {
    success tokens { accessToken refreshToken expiresIn }
    user { id email }
  }
}

# Refresh token
mutation {
  refreshToken(refreshToken: "...") {
    success tokens { accessToken refreshToken expiresIn }
  }
}

# Update profile
mutation {
  updateProfile(name: "New Name") {
    success user { id name }
  }
}

# Change password
mutation {
  changePassword(currentPassword: "Old1!", newPassword: "New1!") {
    success
  }
}

# Track event (REST)
POST /api/track
Headers: X-API-Key: your-api-key
Body: {
  "event_type": "click",
  "event_name": "button_clicked",
  "properties": { "button_id": "submit" },
  "session_id": "session123",
  "url": "https://app.example.com/page"
}
```

## Security Checklist

Before committing code:

- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated
- [ ] SQL injection prevented (use parameterized queries)
- [ ] XSS prevented (sanitized HTML output)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on auth endpoints
- [ ] Error messages don't leak sensitive data
- [ ] Dependencies checked for vulnerabilities

## Git Workflow

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

Examples:
```
feat: add webhook retry mechanism with exponential backoff
fix: prevent duplicate event processing in celery tasks
docs: update GraphQL mutation examples
test: add integration tests for register endpoint
```

### Pull Request Process

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make focused changes with clear commits
3. Push to remote: `git push -u origin feature/my-feature`
4. Open PR with detailed description
5. Address code review feedback
6. Merge after approval

## Troubleshooting

### Backend doesn't start

```bash
# Check logs
docker-compose logs backend

# Verify database is healthy
docker-compose ps postgres

# Verify Redis is healthy
docker-compose ps redis

# Rebuild and restart
make clean
make dev
```

### Tests fail with "too many connections"

Ensure you're using the in-memory SQLite database in tests (set in `conftest.py`). Run tests serially:

```bash
pytest -n0  # Disable parallelization if using xdist
```

### "Permission denied" on seed script

```bash
chmod +x backend/scripts/seed.py
docker-compose exec backend python scripts/seed.py --reset
```

### Celery tasks not processing

Check that workers are running:

```bash
docker-compose ps | grep celery

# If not, start them
docker-compose up -d celery_worker_events celery_worker_notifications celery_worker_reports
```

### Frontend hot reload not working

Ensure the frontend service has proper volume mounts:

```bash
docker-compose down
docker volume rm eventflow_node_modules  # If stuck
make dev
```

## Support

For questions or issues:
1. Check existing GitHub issues
2. Search documentation in `/docs`
3. Review CLAUDE.md for architecture details
4. Ask in team chat or create a GitHub discussion

---

**Happy coding!**
