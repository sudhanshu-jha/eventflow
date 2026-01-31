# Eventflow
## Async Analytics & Notification Platform

A production-grade backend system built using **Pyramid**, **GraphQL**, **Celery**, **Redis**, **PostgreSQL**, and **Alembic** with a **React** frontend. Features complete **OpenTelemetry** observability with distributed tracing.

This platform simulates an analytics and notification system where user events are ingested, processed asynchronously, aggregated into reports, and exposed via a GraphQL API.

![EventFlow Dashboard](demo.png)

*Dashboard showing real-time event analytics with top events bar chart, events by type distribution, and recent activity feed.*

## Tech Stack

| Layer | Technology |
|-------|------------|
| Web Framework | Pyramid 2.0 |
| GraphQL | Graphene 3.x |
| ORM | SQLAlchemy 2.0 |
| Database | PostgreSQL 15 |
| Migrations | Alembic |
| Task Queue | Celery 5.x |
| Broker/Cache | Redis 7 |
| Auth | PyJWT + bcrypt |
| Frontend | React 18 + Vite |
| GraphQL Client | Apollo Client 3 |
| Styling | Tailwind CSS |
| Containerization | Docker Compose |
| **Observability** | **OpenTelemetry + Jaeger** |

## Features

- **Event Tracking**: Track page views, clicks, and custom events
- **GraphQL API**: Full-featured API for querying events, statistics, and managing webhooks
- **JWT Authentication**: Secure token-based authentication
- **Async Processing**: Celery workers for event processing and notifications
- **Webhooks**: Real-time event notifications to external services
- **Email Notifications**: SMTP-based email delivery
- **In-app Notifications**: Real-time notifications in the dashboard
- **Analytics Dashboard**: Visualize event statistics with charts
- **OpenTelemetry Observability**: Complete distributed tracing for backend and frontend

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

Access the application:
- **Frontend**: http://localhost:5173
- **GraphQL Playground**: http://localhost:6543/graphql
- **API Health**: http://localhost:6543/health
- **Jaeger UI** (Traces): http://localhost:16686
- **OTEL Collector Metrics**: http://localhost:8889/metrics

### Manual Setup

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Start PostgreSQL and Redis (use Docker or local installation)
docker run -d --name postgres -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=analytics postgres:15-alpine
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Run migrations
alembic upgrade head

# Start the backend
pserve development.ini --reload

# In a separate terminal, start Celery worker
celery -A analytics.tasks.celery_app worker --loglevel=info -Q events,notifications,reports
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## API Usage

### GraphQL Mutations

#### Register
```graphql
mutation {
  register(email: "user@example.com", password: "password123", name: "John") {
    success
    user { id email apiKey }
    tokens { accessToken refreshToken }
    error
  }
}
```

#### Login
```graphql
mutation {
  login(email: "user@example.com", password: "password123") {
    success
    user { id email apiKey }
    tokens { accessToken refreshToken }
    error
  }
}
```

#### Track Event
```graphql
mutation {
  trackEvent(
    eventType: "page_view"
    eventName: "home_page"
    properties: "{\"source\": \"organic\"}"
    url: "https://example.com"
  ) {
    success
    event { id eventName timestamp }
    error
  }
}
```

### GraphQL Queries

#### Get Event Statistics
```graphql
query {
  eventStats {
    totalEvents
    eventsToday
    eventsThisWeek
    uniqueSessions
    topEvents
    eventsByType
  }
}
```

#### Get Events with Filters
```graphql
query {
  events(eventType: "page_view", limit: 10) {
    events {
      id
      eventName
      eventType
      timestamp
      properties
    }
    totalCount
    hasNextPage
  }
}
```

### REST API (for SDKs)

Track events using the REST endpoint:

```bash
curl -X POST http://localhost:6543/api/track \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "event_type": "page_view",
    "event_name": "home_page",
    "properties": {"source": "organic"},
    "url": "https://example.com"
  }'
```

## Project Structure

```
eventflow/
├── backend/
│   ├── analytics/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── graphql/         # GraphQL schema
│   │   ├── tasks/           # Celery tasks
│   │   ├── services/        # Business logic
│   │   ├── telemetry.py     # OpenTelemetry configuration
│   │   └── views.py         # API endpoints
│   ├── alembic/             # Database migrations
│   ├── development.ini      # Pyramid config
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── graphql/         # Apollo queries/mutations
│   │   ├── hooks/           # React hooks (incl. useTelemetry)
│   │   ├── context/         # React context
│   │   └── telemetry.js     # OpenTelemetry browser config
│   └── package.json
├── otel-collector-config.yaml  # OTEL Collector configuration
├── docker-compose.yml
└── README.md
```

## OpenTelemetry Observability

EventFlow includes complete distributed tracing using OpenTelemetry, providing end-to-end visibility across all services.

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│    OTEL     │────▶│   Jaeger    │
│   (React)   │     │  Collector  │     │     UI      │
└─────────────┘     └─────────────┘     └─────────────┘
                          ▲
┌─────────────┐           │
│   Backend   │───────────┤
│  (Pyramid)  │           │
└─────────────┘           │
                          │
┌─────────────┐           │
│   Celery    │───────────┘
│   Workers   │
└─────────────┘
```

### What's Traced

**Backend (Python)**:
- All HTTP requests via WSGI middleware
- GraphQL operations with query details, operation names, and field selections
- SQLAlchemy database queries
- Celery task execution
- Redis operations
- Outbound HTTP requests

**Frontend (React)**:
- Fetch/XHR requests with backend trace correlation
- Document load performance
- User interactions (clicks, form submissions)
- Page navigation

### GraphQL Span Attributes

GraphQL operations include rich span attributes:

| Attribute | Description |
|-----------|-------------|
| `graphql.operation.type` | query, mutation, or subscription |
| `graphql.operation.name` | Named operation (e.g., Login, GetEvents) |
| `graphql.document` | Full GraphQL query (truncated) |
| `graphql.fields` | Top-level fields being queried |
| `graphql.variables` | Query variables (passwords redacted) |
| `graphql.response.has_errors` | Whether errors occurred |
| `user.id` / `user.email` | Authenticated user info |

### Viewing Traces

1. Open Jaeger UI: http://localhost:16686
2. Select service: `eventflow-backend` or `eventflow-frontend`
3. Click "Find Traces" to see recent traces
4. Click on a trace to see the full span waterfall

### Custom Instrumentation

**Backend** - Use the `@traced` decorator:

```python
from analytics.telemetry import traced

@traced("my_operation")
def my_function():
    # Your code here
    pass
```

**Frontend** - Use the telemetry hooks:

```jsx
import { useTelemetry } from './hooks/useTelemetry'

function MyComponent() {
  const { trackAction, withSpan } = useTelemetry('MyComponent')
  
  const handleClick = async () => {
    trackAction('button_clicked', { buttonId: 'submit' })
    
    await withSpan('fetch_data', async () => {
      // Traced async operation
    })
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://postgres:postgres@localhost:5432/analytics |
| REDIS_URL | Redis connection string | redis://localhost:6379/0 |
| CELERY_BROKER_URL | Celery broker URL | redis://localhost:6379/1 |
| JWT_SECRET | Secret key for JWT tokens | your-super-secret-key |
| SMTP_HOST | SMTP server host | localhost |
| SMTP_PORT | SMTP server port | 587 |
| **OTEL_SERVICE_NAME** | Service name for tracing | eventflow-backend |
| **OTEL_EXPORTER_OTLP_ENDPOINT** | OTLP collector endpoint | http://otel-collector:4317 |

## Development

### Running Tests

```bash
cd backend
pip install -e ".[testing]"
pytest
```

### Database Migrations

```bash
cd backend

# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```
