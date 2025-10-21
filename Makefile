# CalBot Makefile - Common commands for development and deployment

.PHONY: help install dev build up down logs clean test lint deploy-prod deploy-dev

# Default target
help:
	@echo "CalBot - Available Commands"
	@echo "============================"
	@echo ""
	@echo "Development:"
	@echo "  make install       - Install all dependencies"
	@echo "  make dev           - Run in development mode with hot reload"
	@echo "  make test          - Run all tests"
	@echo "  make lint          - Run linters"
	@echo ""
	@echo "Docker:"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start production containers"
	@echo "  make down          - Stop all containers"
	@echo "  make logs          - View container logs"
	@echo "  make restart       - Restart containers"
	@echo "  make clean         - Remove containers and volumes"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-prod   - Deploy to production"
	@echo "  make deploy-dev    - Deploy development environment"
	@echo "  make health        - Check application health"
	@echo ""

# Install dependencies
install:
	@echo "Installing backend dependencies..."
	cd backend && pip install -r requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "✅ All dependencies installed"

# Run in development mode
dev:
	@echo "Starting development environment..."
	docker-compose -f docker-compose.dev.yml up

# Build Docker images
build:
	@echo "Building Docker images..."
	docker-compose build

# Start production containers
up:
	@echo "Starting production containers..."
	docker-compose up -d
	@echo "✅ Containers started"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend:  http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"

# Stop containers
down:
	@echo "Stopping containers..."
	docker-compose down
	@echo "✅ Containers stopped"

# View logs
logs:
	docker-compose logs -f

# Restart containers
restart:
	@echo "Restarting containers..."
	docker-compose restart
	@echo "✅ Containers restarted"

# Clean up containers and volumes
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete"

# Run tests
test:
	@echo "Running backend tests..."
	cd backend && pytest
	@echo "Running frontend tests..."
	cd frontend && npm test
	@echo "✅ All tests passed"

# Run linters
lint:
	@echo "Linting backend..."
	cd backend && flake8 app/
	@echo "Linting frontend..."
	cd frontend && npm run lint
	@echo "✅ Linting complete"

# Deploy to production
deploy-prod:
	@echo "Deploying to production..."
	git pull origin main
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d
	@echo "✅ Production deployment complete"

# Deploy development environment
deploy-dev:
	@echo "Deploying development environment..."
	docker-compose -f docker-compose.dev.yml down
	docker-compose -f docker-compose.dev.yml build
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✅ Development deployment complete"

# Check application health
health:
	@echo "Checking application health..."
	@curl -f http://localhost:8000/health && echo "✅ Backend is healthy" || echo "❌ Backend is down"
	@curl -f http://localhost:3000 && echo "✅ Frontend is healthy" || echo "❌ Frontend is down"

# Database migrations
migrate:
	@echo "Running database migrations..."
	@echo "Please run migrations in Supabase SQL Editor"
	@echo "Location: backend/migrations/"

# View Docker stats
stats:
	docker stats calbot-backend calbot-frontend

# Shell into backend container
shell-backend:
	docker-compose exec backend sh

# Shell into frontend container
shell-frontend:
	docker-compose exec frontend sh

# Backup volumes
backup:
	@echo "Creating backup..."
	mkdir -p backups
	docker run --rm -v calbot_backend_cache:/data -v $(PWD)/backups:/backup alpine tar czf /backup/backup-$(shell date +%Y%m%d-%H%M%S).tar.gz /data
	@echo "✅ Backup created in ./backups/"

# Pull latest images
pull:
	@echo "Pulling latest images..."
	docker-compose pull
	@echo "✅ Images updated"

# Check environment variables
check-env:
	@echo "Checking environment variables..."
	@test -f .env && echo "✅ .env file exists" || echo "❌ .env file missing - copy from .env.example"
	@grep -q "SUPABASE_URL" .env && echo "✅ SUPABASE_URL set" || echo "⚠️  SUPABASE_URL not set"
	@grep -q "GOOGLE_CLIENT_ID" .env && echo "✅ GOOGLE_CLIENT_ID set" || echo "⚠️  GOOGLE_CLIENT_ID not set"
	@grep -q "SECRET_KEY" .env && echo "✅ SECRET_KEY set" || echo "⚠️  SECRET_KEY not set"
	@grep -q "ANTHROPIC_API_KEY" .env && echo "✅ ANTHROPIC_API_KEY set" || echo "⚠️  ANTHROPIC_API_KEY not set"
