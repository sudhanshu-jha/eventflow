# Operations Runbook

**Last Updated:** 2026-03-20

Guide for deploying, scaling, monitoring, and troubleshooting EventFlow in production and development environments.

## Service Ports & Endpoints

### Local Development (Docker Compose)

| Service | Port | URL | Purpose |
|---------|------|-----|---------|
| **Nginx (load balancer)** | 80 | http://localhost | Frontend/backend reverse proxy |
| **Nginx Metrics** | 8080 | http://localhost:8080/stub_status | Nginx metrics (Prometheus format) |
| **Frontend** | 5173 | http://localhost:5173 | React dev server (direct access) |
| **Backend** | 6543 | http://localhost:6543 | Pyramid/GraphQL API (direct access) |
| **GraphQL Playground** | 6543 | http://localhost:6543/graphql | Interactive GraphQL IDE |
| **Jaeger UI** | 16686 | http://localhost:16686 | Trace visualization |
| **OTEL Collector (gRPC)** | 4317 | grpc://localhost:4317 | OpenTelemetry traces/metrics (gRPC) |
| **OTEL Collector (HTTP)** | 4318 | http://localhost:4318 | OpenTelemetry traces/metrics (HTTP) |
| **OTEL Metrics** | 8889 | http://localhost:8889/metrics | Prometheus-format metrics export |
| **OTEL Health** | 13133 | http://localhost:13133 | Collector health check |
| **OTEL zPages** | 55679 | http://localhost:55679 | Collector debug pages |
| **PostgreSQL** | 5433 | postgres://localhost:5433/analytics | Database (external; use for admin access) |
| **Redis** | 6380 | redis://localhost:6380 | Cache/broker (external; use for admin access) |

### Backend Endpoints

```
POST /graphql          # GraphQL queries & mutations
GET  /graphql          # GraphQL Playground (IDE)
POST /api/track        # Event tracking REST endpoint
GET  /health           # Health check
```

## Deployment Procedures

### Starting Development Environment

```bash
# All-in-one start
make dev

# Or with docker-compose directly
docker-compose up -d

# View logs
make logs

# Verify all services are running
docker-compose ps
```

Verify the system is healthy:

```bash
make health
```

This checks:
- Backend at :6543/health
- Nginx at :80/nginx-health

### Running Migrations

```bash
# Apply all pending migrations
make migrate

# Create a new migration
make migration MSG="add user preferences table"

# View migration history
docker-compose exec backend alembic current
```

### Seeding Demo Data

```bash
# Seed with defaults (3 users, realistic event distribution)
docker-compose exec backend python scripts/seed.py --reset

# Seed with specific number of users
docker-compose exec backend python scripts/seed.py --reset --users 10

# Seed without reset (append to existing data)
docker-compose exec backend python scripts/seed.py --users 5
```

**Demo Credentials** (from default seed):
- alice@demo.com / AlicePass1!
- bob@demo.com / BobPass1!
- charlie@demo.com / CharlieP1!

### Production Deployment (Docker Compose)

For production environments, use the production compose override:

```bash
make prod

# Or directly
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# View logs
make logs
```

The production configuration includes:
- Production-grade database/Redis settings
- HTTPS ready (Nginx SSL termination prepared)
- Resource limits on containers
- Service restart policies

### Kubernetes Deployment

Deploy to Kubernetes using Kustomize overlays:

```bash
# Development deployment
make k8s-dev

# Production deployment
make k8s-prod

# Check deployment status
make k8s-status

# Port forward for local access
make k8s-port-forward

# Delete deployment
make k8s-delete
```

Kubernetes configurations are in `k8s/`:
- `k8s/base/` — Base manifests
- `k8s/overlays/dev/` — Development overrides
- `k8s/overlays/prod/` — Production overrides

Includes:
- Deployments for backend, frontend, Celery workers
- Services (ClusterIP, Ingress)
- StatefulSets for PostgreSQL, Redis
- HorizontalPodAutoscaler (HPA) for auto-scaling
- ConfigMaps/Secrets for configuration

## Scaling

### Docker Compose Scaling

Scale individual services without stopping others:

```bash
# Scale backend replicas to 3
make scale-backend N=3

# Scale frontend replicas to 2
make scale-frontend N=2

# Scale all Celery workers to 4 each
make scale-workers N=4

# Scale specific worker queues
make scale-events N=5        # events queue only
make scale-notifications N=3  # notifications queue only
make scale-reports N=2       # reports queue only

# View current scale
make scale-status
```

**Note:** Nginx automatically load-balances across replicas.

### Kubernetes Scaling

Scale deployments on Kubernetes:

```bash
# Scale backend to 5 replicas
make k8s-scale-backend N=5

# Scale frontend to 3 replicas
make k8s-scale-frontend N=3

# Or use kubectl directly
kubectl scale deployment backend -n eventflow --replicas=5
kubectl scale deployment frontend -n eventflow --replicas=3
```

Kubernetes HPA will also auto-scale based on CPU/memory thresholds. Check HPA status:

```bash
kubectl get hpa -n eventflow
kubectl describe hpa backend -n eventflow
```

## Monitoring & Observability

### Health Checks

```bash
# Quick health check (from Makefile)
make health

# Backend health
curl http://localhost:6543/health

# Nginx health
curl http://localhost:80/nginx-health

# Jaeger health check
curl http://localhost:13133

# OTEL Collector health
docker-compose exec otel-collector curl localhost:13133
```

### Viewing Traces

```bash
# Open Jaeger UI
make jaeger

# Or directly visit
open http://localhost:16686
```

In Jaeger:
1. Select service from dropdown (e.g., `eventflow-backend`)
2. Choose operation (e.g., `graphql.query`, `graphql.mutation`, `track_event`)
3. Filter by tags (e.g., `span.kind=server`)
4. View trace waterfall and spans

### Viewing Metrics

OTEL Collector exports metrics in Prometheus format:

```bash
# View metrics
make otel-metrics

# Or directly
curl http://localhost:8889/metrics | head -50

# Common metrics to look for
# eventflow_events_total          — Total events received
# eventflow_events_processed      — Total events processed
# eventflow_event_processing_duration_seconds — Processing latency
```

### Logs

```bash
# Tail all logs
make logs

# Tail specific service
docker-compose logs -f backend
docker-compose logs -f celery_worker_events
docker-compose logs -f otel-collector

# View logs with timestamps
docker-compose logs -f --timestamps

# View last 100 lines
docker-compose logs backend --tail=100
```

### Celery Worker Status

Check if workers are processing tasks:

```bash
# From Docker
docker-compose exec celery_worker_events celery -A analytics.tasks.celery_app inspect active

# Check worker pool
docker-compose exec celery_worker_events celery -A analytics.tasks.celery_app inspect stats
```

## Backup & Recovery

### Database Backup

```bash
# Backup to file
docker-compose exec postgres pg_dump -U postgres analytics > backup.sql

# Backup with compression
docker-compose exec postgres pg_dump -U postgres -F c analytics > backup.dump
```

### Database Restore

```bash
# Restore from SQL
docker-compose exec -T postgres psql -U postgres analytics < backup.sql

# Restore from compressed dump
docker-compose exec -T postgres pg_restore -U postgres -d analytics backup.dump
```

### Redis Backup

```bash
# Redis auto-saves to volume; backup the volume
docker run --rm -v eventflow_redis_data:/data -v $(pwd):/backup \
  alpine cp -r /data /backup/redis_backup
```

## Troubleshooting

### General Troubleshooting Steps

```bash
# 1. Check service status
docker-compose ps

# 2. View recent logs
docker-compose logs --tail=50

# 3. Verify database connectivity
docker-compose exec backend psql $DATABASE_URL -c "SELECT 1"

# 4. Verify Redis connectivity
docker-compose exec redis redis-cli ping

# 5. Check disk space
docker system df
```

### Backend Won't Start

**Symptoms**: Backend container exits immediately or logs show "Connection refused"

```bash
# 1. Check database is running and healthy
docker-compose exec postgres pg_isready -U postgres

# 2. Verify DATABASE_URL is correct
docker-compose exec backend echo $DATABASE_URL

# 3. Check if migrations are pending
docker-compose exec backend alembic current

# 4. Run migrations
make migrate

# 5. Restart backend
docker-compose restart backend
```

### Celery Workers Not Processing Tasks

**Symptoms**: Tasks queued in Redis but not processing

```bash
# 1. Verify workers are running
docker-compose ps | grep celery

# 2. Check if Redis connection is working
docker-compose exec celery_worker_events redis-cli -u redis://redis:6379/1 ping

# 3. Check worker logs
docker-compose logs -f celery_worker_events

# 4. Inspect active tasks
docker-compose exec celery_worker_events celery -A analytics.tasks.celery_app inspect active

# 5. Restart workers
docker-compose restart celery_worker_events celery_worker_notifications celery_worker_reports
```

### GraphQL Queries Return Errors

**Symptoms**: 500 errors or "Internal Server Error" in GraphQL response

```bash
# 1. Check backend logs for SQL errors
docker-compose logs backend | grep -i error

# 2. Verify database has tables
docker-compose exec postgres psql -U postgres analytics -c "\dt"

# 3. Check if user is authenticated (for mutations)
# Add Authorization header: "Bearer <token>"

# 4. View detailed GraphQL error
# Use GraphQL Playground at http://localhost:6543/graphql
```

### Frontend Can't Reach Backend

**Symptoms**: Frontend shows "Failed to fetch" or CORS errors

```bash
# 1. Check CORS configuration
docker-compose exec backend grep -A2 "cors.origins" development.ini

# 2. Verify backend is accessible
curl -X POST http://localhost:6543/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{__typename}"}'

# 3. Check Nginx configuration
docker-compose exec nginx cat /etc/nginx/nginx.conf

# 4. Verify CORS headers are being sent
curl -v -X OPTIONS http://localhost:80/graphql | grep "Access-Control"
```

### Out of Memory

**Symptoms**: Services crashing with "Cannot allocate memory"

```bash
# 1. Check container memory usage
docker stats

# 2. Identify large processes
docker-compose exec backend ps aux --sort=-%mem

# 3. Clean up unused images/volumes
docker system prune -a

# 4. Increase Docker memory limit
# (In Docker Desktop: Preferences > Resources > Memory)

# 5. Scale down replicas
make scale-backend N=1
make scale-workers N=1
```

### High Latency in GraphQL Queries

**Symptoms**: Queries take >1 second

```bash
# 1. Check database query performance
docker-compose exec postgres psql -U postgres analytics -c "EXPLAIN ANALYZE SELECT ..."

# 2. Check if indexes exist
docker-compose logs backend | grep -i index

# 3. View Jaeger traces for slow spans
# Open http://localhost:16686 and look for long durations

# 4. Check Redis latency
docker-compose exec redis redis-cli --latency

# 5. Review query complexity in GraphQL (avoid N+1)
```

### Disk Space Running Low

```bash
# Check Docker disk usage
docker system df

# Remove unused volumes
docker volume prune

# Remove unused images
docker image prune -a

# Check database size
docker-compose exec postgres psql -U postgres -c "\l+"
```

### Reset Everything

```bash
# Complete reset (DELETE DATA!)
make clean

# Then start fresh
make dev
make migrate
docker-compose exec backend python scripts/seed.py --reset
```

## Common Operations

### Adding a User (Manual)

```bash
docker-compose exec backend python -c "
from analytics.models.user import User
from analytics.services.auth import AuthService
from analytics import get_engine, get_session_factory, get_tm_session
import os

settings = {'jwt.secret': os.environ.get('JWT_SECRET', 'dev')}
auth = AuthService(settings)
user = User(
    email='user@example.com',
    password_hash=auth.hash_password('SecurePass1!'),
    api_key=auth.generate_api_key(),
    name='Example User'
)
print(f'Created user: {user.email} with API key: {user.api_key}')
"
```

### Triggering Manual Event Processing

```bash
# Send event via REST API
curl -X POST http://localhost:6543/api/track \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <api_key>" \
  -d '{
    "event_name": "test_event",
    "event_type": "custom",
    "properties": {"test": true}
  }'
```

### Clearing Redis Cache

```bash
# Clear entire Redis DB 0 (cache)
docker-compose exec redis redis-cli -n 0 FLUSHDB

# Clear entire Redis DB 1 (Celery broker)
docker-compose exec redis redis-cli -n 1 FLUSHDB

# Clear all databases
docker-compose exec redis redis-cli FLUSHALL
```

### Viewing Database Schema

```bash
# List all tables
docker-compose exec postgres psql -U postgres analytics -c "\dt"

# Describe specific table
docker-compose exec postgres psql -U postgres analytics -c "\d users"

# View column details
docker-compose exec postgres psql -U postgres analytics -c "\d+ events"
```

## Performance Tuning

### PostgreSQL

```bash
# Check active queries
docker-compose exec postgres psql -U postgres analytics -c "SELECT pid, query FROM pg_stat_statements ORDER BY calls DESC LIMIT 10;"

# View cache hit ratio (target >99%)
docker-compose exec postgres psql -U postgres analytics -c "
  SELECT
    sum(heap_blks_read) as heap_read,
    sum(heap_blks_hit) as heap_hit,
    sum(heap_blks_hit) / (sum(heap_blks_hit) + sum(heap_blks_read)) as ratio
  FROM pg_statio_user_tables;
"
```

### Redis

```bash
# Check memory usage
docker-compose exec redis redis-cli INFO memory

# Check key count
docker-compose exec redis redis-cli DBSIZE

# Identify large keys
docker-compose exec redis redis-cli --bigkeys
```

### Python Application

```bash
# Profile CPU usage (using cProfile)
docker-compose exec backend python -m cProfile -s cumulative -c "import analytics"

# Memory profiling (if py-spy installed)
docker-compose exec backend py-spy record -o profile.svg -- pserve development.ini
```

## Shutdown Procedures

### Graceful Shutdown

```bash
# Stop services (allows graceful termination)
docker-compose stop

# Wait a few seconds for tasks to complete
sleep 5

# View stopped services
docker-compose ps

# Restart or remove
docker-compose restart
docker-compose down
```

### Hard Shutdown (if stuck)

```bash
# Force kill all containers
docker-compose kill

# Remove containers
docker-compose rm -f
```

---

**For more information, see CONTRIBUTING.md, ENV.md, or CLAUDE.md**
