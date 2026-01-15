# Eventflow
## Async Analytics & Notification Platform

A production-grade backend system built using **Pyramid**, **GraphQL**, **Celery**, **Redis**, **PostgreSQL**, and **Alembic** with a **React** frontend.

This platform simulates an analytics and notification system where user events are ingested, processed asynchronously, aggregated into reports, and exposed via a GraphQL API.

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

## Features

- **Event Tracking**: Track page views, clicks, and custom events
- **GraphQL API**: Full-featured API for querying events, statistics, and managing webhooks
- **JWT Authentication**: Secure token-based authentication
- **Async Processing**: Celery workers for event processing and notifications
- **Webhooks**: Real-time event notifications to external services
- **Email Notifications**: SMTP-based email delivery
- **In-app Notifications**: Real-time notifications in the dashboard
- **Analytics Dashboard**: Visualize event statistics with charts

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
- Frontend: http://localhost:5173
- GraphQL Playground: http://localhost:6543/graphql
- API Health: http://localhost:6543/health

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
mini_mixpanel/
├── backend/
│   ├── analytics/
│   │   ├── models/          # SQLAlchemy models
│   │   ├── graphql/         # GraphQL schema
│   │   ├── tasks/           # Celery tasks
│   │   ├── services/        # Business logic
│   │   └── views.py         # API endpoints
│   ├── alembic/             # Database migrations
│   ├── development.ini      # Pyramid config
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   ├── graphql/         # Apollo queries/mutations
│   │   └── context/         # React context
│   └── package.json
├── docker-compose.yml
└── README.md
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
