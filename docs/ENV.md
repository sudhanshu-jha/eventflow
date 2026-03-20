# Environment Variables

**Last Updated:** 2026-03-20

Reference for all environment variables used by EventFlow. Configuration can come from environment variables or `development.ini` (local development).

## Database Configuration

### DATABASE_URL

- **Type**: Connection string
- **Required**: Yes
- **Default**: `postgresql://postgres:postgres@localhost:5432/analytics` (from `development.ini`)
- **Docker**: `postgresql://postgres:postgres@postgres:5432/analytics`
- **Example**: `postgresql://user:password@host:5432/dbname`
- **Used by**: SQLAlchemy ORM, Alembic migrations

When set as an environment variable, overrides the `sqlalchemy.url` setting from `development.ini`.

## Cache & Message Broker

### REDIS_URL

- **Type**: Connection string
- **Required**: Yes
- **Default**: `redis://localhost:6379/0` (from `development.ini`)
- **Docker**: `redis://redis:6379/0`
- **Example**: `redis://localhost:6379/0`
- **Used by**: Session caching, rate limiting

### CELERY_BROKER_URL

- **Type**: Connection string
- **Required**: Yes
- **Default**: `redis://localhost:6379/1` (from `development.ini`)
- **Docker**: `redis://redis:6379/1`
- **Example**: `redis://localhost:6379/1`
- **Used by**: Celery workers for task queuing

**Note**: Uses Redis database 1 (separate from cache db 0) to avoid data collision.

## Authentication

### JWT_SECRET

- **Type**: String (random bytes encoded as hex or base64)
- **Required**: Yes
- **Default**: `your-super-secret-key-change-in-production` (from `development.ini`)
- **Environment**: `change-this-in-production` (in Docker)
- **Best practice**: Generate 32+ random bytes
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```
- **Used by**: PyJWT for access/refresh token signing
- **Security**: Must be different in production; never commit actual value to git

### JWT_ALGORITHM

- **Type**: String
- **Default**: `HS256`
- **Options**: `HS256`, `HS512` (HMAC), or `RS256`, `RS512` (RSA with public/private keys)
- **Used by**: PyJWT algorithm selection
- **Note**: Must match algorithm used when tokens are created

### JWT_EXPIRATION

- **Type**: Integer (seconds)
- **Default**: `3600` (1 hour)
- **Used by**: Access token TTL

## CORS Configuration

### CORS.ORIGINS (development.ini)

- **Type**: Comma-separated list of origins
- **Required**: Yes
- **Default** (local): `http://localhost:5173,https://sudhanshu.anlytics.dev,http://sudhanshu.anlytics.dev`
- **Example**: `http://localhost:5173,https://app.example.com`
- **Used by**: CORS header validation in `add_cors_headers()`
- **Exposed headers**: `traceparent, tracestate` (for OpenTelemetry correlation)

Requests from unlisted origins will receive the first allowed origin as fallback.

## OpenTelemetry Configuration

All OTEL environment variables follow the [OpenTelemetry specification](https://opentelemetry.io/docs/reference/specification/protocol/exporter/).

### OTEL_SERVICE_NAME

- **Type**: String
- **Required**: Yes
- **Docker values**:
  - Backend: `eventflow-backend`
  - Celery workers: `eventflow-celery-{events|notifications|reports}`
  - Celery beat: `eventflow-celery-beat`
- **Used by**: Service identification in traces and metrics

### OTEL_EXPORTER_OTLP_ENDPOINT

- **Type**: URL (gRPC or HTTP)
- **Required**: Yes
- **Default**: `http://localhost:4317` (gRPC)
- **Docker**: `http://otel-collector:4317`
- **Used by**: OpenTelemetry SDK to export traces and metrics

### OTEL_EXPORTER_OTLP_PROTOCOL

- **Type**: String (`grpc` or `http/protobuf`)
- **Default**: `grpc`
- **Docker**: `grpc`
- **Used by**: OTLP exporter transport protocol

### OTEL_TRACES_EXPORTER

- **Type**: String
- **Default**: `otlp`
- **Options**: `otlp`, `jaeger`, `zipkin`, `none`
- **Used by**: Trace exporter selection

### OTEL_METRICS_EXPORTER

- **Type**: String
- **Default**: `otlp`
- **Options**: `otlp`, `prometheus`, `none`
- **Used by**: Metrics exporter selection

### OTEL_LOGS_EXPORTER

- **Type**: String
- **Default**: `otlp`
- **Options**: `otlp`, `none`
- **Used by**: Logs exporter selection

### OTEL_PYTHON_LOG_CORRELATION

- **Type**: Boolean (`true` or `false`)
- **Default**: `true`
- **Docker**: `true`
- **Used by**: Correlate Python logs with trace IDs

### OTEL_RESOURCE_ATTRIBUTES

- **Type**: Comma-separated key=value pairs
- **Default**: `service.namespace=eventflow,deployment.environment=development`
- **Example**: `service.namespace=eventflow,deployment.environment=production,service.version=1.0.0`
- **Used by**: Resource labeling in spans and metrics

## Frontend (Vite) Configuration

### VITE_OTEL_EXPORTER_OTLP_ENDPOINT

- **Type**: URL (HTTP only, gRPC not supported in browsers)
- **Default**: `http://localhost:4318`
- **Docker**: `http://localhost:4318`
- **Example**: `https://otel.example.com:443`
- **Used by**: Browser-side OpenTelemetry SDK
- **Note**: Must use HTTP (port 4318), not gRPC (4317)

### VITE_OTEL_SERVICE_NAME

- **Type**: String
- **Default**: `eventflow-frontend`
- **Used by**: Frontend trace identification

### VITE_API_URL

- **Type**: URL (GraphQL backend)
- **Default**: `http://localhost:6543`
- **Docker**: `http://localhost:6543`
- **Example**: `https://api.example.com`
- **Used by**: Apollo Client for GraphQL queries/mutations

### VITE_ALLOWED_HOSTS

- **Type**: Comma-separated list
- **Default**: `localhost,sudhanshu.anlytics.dev`
- **Used by**: Runtime validation (if applicable)

## Summary Table

| Variable | Required | Docker Default | Development Default | Used By |
|----------|----------|-----------------|-------------------|---------|
| DATABASE_URL | Yes | `postgres:5432/analytics` | `localhost:5432/analytics` | SQLAlchemy, Alembic |
| REDIS_URL | Yes | `redis:6379/0` | `localhost:6379/0` | Session cache, rate limit |
| CELERY_BROKER_URL | Yes | `redis:6379/1` | `localhost:6379/1` | Celery workers |
| JWT_SECRET | Yes | `change-this-in-production` | `your-super-secret-key...` | PyJWT signing |
| JWT_ALGORITHM | No | `HS256` | `HS256` | PyJWT verification |
| JWT_EXPIRATION | No | (unset) | `3600` | Token TTL |
| OTEL_SERVICE_NAME | Yes | Service-specific | (unset) | OTEL identification |
| OTEL_EXPORTER_OTLP_ENDPOINT | Yes | `otel-collector:4317` | (unset) | OTEL export |
| OTEL_EXPORTER_OTLP_PROTOCOL | No | `grpc` | (unset) | OTEL protocol |
| OTEL_TRACES_EXPORTER | No | `otlp` | (unset) | Trace export |
| OTEL_METRICS_EXPORTER | No | `otlp` | (unset) | Metrics export |
| OTEL_LOGS_EXPORTER | No | `otlp` | (unset) | Logs export |
| OTEL_PYTHON_LOG_CORRELATION | No | `true` | (unset) | Log correlation |
| OTEL_RESOURCE_ATTRIBUTES | No | `service.namespace=eventflow,...` | (unset) | Resource labels |
| VITE_OTEL_EXPORTER_OTLP_ENDPOINT | Yes (frontend) | `localhost:4318` | (unset) | Frontend OTEL |
| VITE_OTEL_SERVICE_NAME | No | `eventflow-frontend` | (unset) | Frontend service name |
| VITE_API_URL | Yes (frontend) | `localhost:6543` | (unset) | Apollo Client endpoint |
| VITE_ALLOWED_HOSTS | No | `localhost,sudhanshu.anlytics.dev` | (unset) | Host validation |

## Configuration Sources (Priority Order)

1. **Environment variables** (highest priority)
2. **`development.ini`** (local development, read by Pyramid)
3. **`.env` file** (if using python-dotenv, not currently configured)
4. **Hardcoded defaults** (fallback, should be avoided for production)

## Setting Environment Variables

### Using Docker Compose

Environment variables are set in `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
      - JWT_SECRET=change-this
      - OTEL_SERVICE_NAME=eventflow-backend
```

### Without Docker (Local Development)

Create a `.env` file in the backend directory (not tracked in git):

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/analytics"
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/1"
export JWT_SECRET="your-super-secret-key-change-in-production"
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
export OTEL_SERVICE_NAME="eventflow-backend"
```

Then load it:

```bash
source .env
```

### Production Deployment

Use your platform's secret management:

- **AWS**: Systems Manager Parameter Store, Secrets Manager
- **Azure**: Azure Key Vault
- **Google Cloud**: Secret Manager
- **Kubernetes**: Secrets resource
- **Render/Heroku**: Dashboard environment variable configuration

---

**All environment variables are case-sensitive and required unless marked as optional.**
