# Makefile für einfache CI/CD Commands

.PHONY: help test build deploy-local deploy-remote pipeline clean

# Default target
help:
	@echo "🚀 WiSo Chatbot CI/CD Commands"
	@echo "================================================"
	@echo ""
	@echo "Local Development:"
	@echo "  make test           - Run all tests"
	@echo "  make build          - Verify build"
	@echo "  make deploy-local   - Deploy locally (no Docker)"
	@echo "  make pipeline       - Run full CI/CD pipeline locally"
	@echo ""
	@echo "Remote Deployment:"
	@echo "  make deploy-remote  - Push and trigger GitHub Actions"
	@echo "  make deploy-force   - Force push and deploy"
	@echo ""
	@echo "Docker (if installed):"
	@echo "  make docker-build   - Build Docker image"
	@echo "  make docker-run     - Run with Docker Compose"
	@echo ""
	@echo "Utilities:"
	@echo "  make list           - List active deployments"
	@echo "  make stop           - Stop local deployment"
	@echo "  make clean          - Clean temporary files"
	@echo "  make logs           - Show deployment logs"

# Run tests
test:
	@echo "🧪 Running tests..."
	@source venv/bin/activate && python test_scraper_components.py
	@source venv/bin/activate && python -m pytest tests/ -v

# Verify build
build:
	@echo "🔨 Verifying build..."
	@source venv/bin/activate && python -c "import sys; sys.path.insert(0, '.'); from src.scraper.crawler_scraper_pipeline import *; print('✅ Build OK!')"

# Local deployment without Docker
deploy-local:
	@./deploy-local.sh

# Full local CI/CD pipeline
pipeline:
	@./run-ci-local.sh

# Deploy via GitHub Actions
deploy-remote:
	@echo "🚀 Deploying via GitHub Actions..."
	@git add -A
	@git status
	@read -p "Commit message: " msg; \
	git commit -m "$$msg" || true
	@git push origin $$(git branch --show-current)
	@echo "✅ Pushed to GitHub - CI/CD pipeline will run automatically"
	@echo "View progress: https://github.com/sebastianuzk/uzk-masterarbeit/actions"

# Force deploy
deploy-force:
	@git push origin $$(git branch --show-current) --force
	@echo "✅ Force pushed - CI/CD pipeline triggered"

# Docker build (if Docker is installed)
docker-build:
	@if command -v docker &> /dev/null; then \
		docker build -t wiso-chatbot .; \
	else \
		echo "❌ Docker not installed"; \
		exit 1; \
	fi

# Docker run
docker-run:
	@if command -v docker-compose &> /dev/null; then \
		docker-compose up -d; \
	else \
		echo "❌ Docker Compose not installed"; \
		exit 1; \
	fi

# List deployments
list:
	@./list-local.sh

# Stop deployment
stop:
	@./stop-local.sh

# Show logs
logs:
	@if [ -d logs ]; then \
		tail -f logs/*.log; \
	else \
		echo "No logs found"; \
	fi

# Clean temporary files
clean:
	@echo "🧹 Cleaning temporary files..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name ".DS_Store" -delete 2>/dev/null || true
	@rm -f docker-compose.feat-*.yml 2>/dev/null || true
	@echo "✅ Cleaned"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	@python3 -m venv venv || true
	@source venv/bin/activate && pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Setup project
setup: install
	@echo "🔧 Setting up project..."
	@chmod +x *.sh
	@mkdir -p logs data
	@echo "✅ Project setup complete"

# Quick start
start: deploy-local

# Status check
status:
	@echo "📊 Project Status"
	@echo "================================================"
	@echo "Branch: $$(git branch --show-current)"
	@echo "Python: $$(python3 --version)"
	@echo "Virtual Env: $${VIRTUAL_ENV:-Not activated}"
	@echo ""
	@./list-local.sh || true
