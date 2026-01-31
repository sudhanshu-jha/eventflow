.PHONY: help dev prod up down logs restart scale build push deploy k8s-dev k8s-prod clean

# Default target
help:
	@echo "EventFlow - Scaling Commands"
	@echo ""
	@echo "Docker Compose Commands:"
	@echo "  make dev          - Start development environment"
	@echo "  make prod         - Start production environment"
	@echo "  make up           - Start all services"
	@echo "  make down         - Stop all services"
	@echo "  make logs         - View logs (follow mode)"
	@echo "  make restart      - Restart all services"
	@echo "  make clean        - Remove all containers and volumes"
	@echo ""
	@echo "Scaling Commands:"
	@echo "  make scale-backend N=3    - Scale backend to N replicas"
	@echo "  make scale-frontend N=2   - Scale frontend to N replicas"
	@echo "  make scale-workers N=3    - Scale all Celery workers to N replicas"
	@echo "  make scale-events N=5     - Scale events workers to N replicas"
	@echo ""
	@echo "Build Commands:"
	@echo "  make build        - Build all Docker images"
	@echo "  make push         - Push images to registry"
	@echo ""
	@echo "Kubernetes Commands:"
	@echo "  make k8s-dev      - Deploy to Kubernetes (dev)"
	@echo "  make k8s-prod     - Deploy to Kubernetes (prod)"
	@echo "  make k8s-status   - Check Kubernetes deployment status"
	@echo "  make k8s-delete   - Delete Kubernetes deployment"

# ==================== Docker Compose ====================

# Development environment
dev:
	docker-compose up -d
	@echo "Development environment started"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Backend:  http://localhost:6543"
	@echo "  Jaeger:   http://localhost:16686"
	@echo "  Nginx:    http://localhost:80"

# Production environment
prod:
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
	@echo "Production environment started"

# Start services
up:
	docker-compose up -d

# Stop services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Restart services
restart:
	docker-compose restart

# Clean everything
clean:
	docker-compose down -v --rmi local
	docker system prune -f

# ==================== Scaling ====================

# Scale backend
scale-backend:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-backend N=3"; exit 1; fi
	docker-compose up -d --scale backend=$(N) --no-recreate
	@echo "Scaled backend to $(N) replicas"

# Scale frontend
scale-frontend:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-frontend N=2"; exit 1; fi
	docker-compose up -d --scale frontend=$(N) --no-recreate
	@echo "Scaled frontend to $(N) replicas"

# Scale all Celery workers
scale-workers:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-workers N=3"; exit 1; fi
	docker-compose up -d \
		--scale celery_worker_events=$(N) \
		--scale celery_worker_notifications=$(N) \
		--scale celery_worker_reports=$(N) \
		--no-recreate
	@echo "Scaled all workers to $(N) replicas each"

# Scale events workers only
scale-events:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-events N=5"; exit 1; fi
	docker-compose up -d --scale celery_worker_events=$(N) --no-recreate
	@echo "Scaled events workers to $(N) replicas"

# Scale notifications workers only
scale-notifications:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-notifications N=3"; exit 1; fi
	docker-compose up -d --scale celery_worker_notifications=$(N) --no-recreate
	@echo "Scaled notifications workers to $(N) replicas"

# Scale reports workers only
scale-reports:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-reports N=2"; exit 1; fi
	docker-compose up -d --scale celery_worker_reports=$(N) --no-recreate
	@echo "Scaled reports workers to $(N) replicas"

# Show current scale
scale-status:
	@echo "Current replica counts:"
	@docker-compose ps --format "table {{.Service}}\t{{.Status}}" | grep -E "(backend|frontend|celery)" || true

# ==================== Build ====================

# Build all images
build:
	docker-compose build

# Build backend only
build-backend:
	docker-compose build backend

# Build frontend only
build-frontend:
	docker-compose build frontend

# Push images to registry
push:
	@if [ -z "$(REGISTRY)" ]; then echo "Usage: make push REGISTRY=your-registry.com"; exit 1; fi
	docker tag eventflow-backend:latest $(REGISTRY)/eventflow-backend:latest
	docker tag eventflow-frontend:latest $(REGISTRY)/eventflow-frontend:latest
	docker push $(REGISTRY)/eventflow-backend:latest
	docker push $(REGISTRY)/eventflow-frontend:latest

# ==================== Kubernetes ====================

# Deploy to Kubernetes (dev)
k8s-dev:
	kubectl apply -k k8s/overlays/dev/
	@echo "Deployed to Kubernetes (dev)"

# Deploy to Kubernetes (prod)
k8s-prod:
	kubectl apply -k k8s/overlays/prod/
	@echo "Deployed to Kubernetes (prod)"

# Check deployment status
k8s-status:
	@echo "=== Deployments ==="
	kubectl get deployments -n eventflow
	@echo ""
	@echo "=== Pods ==="
	kubectl get pods -n eventflow
	@echo ""
	@echo "=== Services ==="
	kubectl get services -n eventflow
	@echo ""
	@echo "=== HPA ==="
	kubectl get hpa -n eventflow

# Delete Kubernetes deployment
k8s-delete:
	kubectl delete -k k8s/base/
	@echo "Deleted Kubernetes deployment"

# Port forward for local access
k8s-port-forward:
	@echo "Starting port forwards..."
	kubectl port-forward -n eventflow svc/frontend 5173:5173 &
	kubectl port-forward -n eventflow svc/backend 6543:6543 &
	kubectl port-forward -n eventflow svc/jaeger-query 16686:16686 &
	@echo "Port forwards started:"
	@echo "  Frontend: http://localhost:5173"
	@echo "  Backend:  http://localhost:6543"
	@echo "  Jaeger:   http://localhost:16686"

# Scale Kubernetes deployment
k8s-scale-backend:
	@if [ -z "$(N)" ]; then echo "Usage: make k8s-scale-backend N=5"; exit 1; fi
	kubectl scale deployment backend -n eventflow --replicas=$(N)

k8s-scale-frontend:
	@if [ -z "$(N)" ]; then echo "Usage: make k8s-scale-frontend N=3"; exit 1; fi
	kubectl scale deployment frontend -n eventflow --replicas=$(N)

# ==================== Database ====================

# Run database migrations
migrate:
	docker-compose exec backend alembic upgrade head

# Create a new migration
migration:
	@if [ -z "$(MSG)" ]; then echo "Usage: make migration MSG='description'"; exit 1; fi
	docker-compose exec backend alembic revision --autogenerate -m "$(MSG)"

# ==================== Testing ====================

# Run backend tests
test:
	docker-compose exec backend pytest

# Run with coverage
test-coverage:
	docker-compose exec backend pytest --cov=analytics --cov-report=html

# ==================== Monitoring ====================

# Open Jaeger UI
jaeger:
	@echo "Opening Jaeger UI..."
	open http://localhost:16686 || xdg-open http://localhost:16686 || echo "Visit http://localhost:16686"

# View OTEL collector metrics
otel-metrics:
	curl -s http://localhost:8889/metrics | head -50

# Check service health
health:
	@echo "Backend health:"
	@curl -s http://localhost:6543/health | jq . || echo "Backend not responding"
	@echo ""
	@echo "Nginx health:"
	@curl -s http://localhost/nginx-health || echo "Nginx not responding"
