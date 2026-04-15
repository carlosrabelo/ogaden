MAKEFLAGS += --no-print-directory

.DEFAULT_GOAL := help

.PHONY: clean docker-build docker-push docker-start docker-stop fmt help lint quality restart run-dashboard run-engine setup test typecheck

DOCKER_USER ?= carlosrabelo
VERSION ?= $(shell git rev-parse --short HEAD)

COMPOSE ?= docker compose

# ==============================================================================
# Help
# ==============================================================================

help: ## Show available targets
	@echo "ogaden - Available targets"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*## "} {printf "  %-15s %s\n", $$1, $$2}'

# ==============================================================================
# Setup & Installation
# ==============================================================================

setup: ## Create .venv and install all dependencies (including server)
	@./make/setup.sh



# ==============================================================================
# Execution
# ==============================================================================

run-engine: .venv/bin/python ## Run the trading engine locally
	@.venv/bin/python -m ogaden.engine

run-dashboard: .venv/bin/python ## Run the dashboard locally
	@.venv/bin/python -m ogaden.dashboard

# ==============================================================================
# Testing & Code Quality
# ==============================================================================

test: ## Run all tests
	@./make/test.sh

fmt: ## Format sources with ruff
	@.venv/bin/ruff format ogaden/ tests/

lint: ## Lint sources with ruff
	@./make/lint.sh

typecheck: ## Type-check with mypy
	@.venv/bin/mypy ogaden/

quality: fmt lint typecheck ## Run all quality checks

# ==============================================================================
# Docker Stack
# ==============================================================================

docker-start: ## Build and start the Docker stack
	@$(COMPOSE) up --detach --build --force-recreate

docker-stop: ## Stop the Docker stack and remove orphans
	@$(COMPOSE) down --remove-orphans --volumes

docker-restart: docker-stop docker-start ## Rebuild and restart the Docker stack

docker-build: ## Build docker images
	@DOCKER_USER=$(DOCKER_USER) VERSION=$(VERSION) ./make/docker-build.sh

docker-push: docker-build ## Push docker images to registry
	@DOCKER_USER=$(DOCKER_USER) VERSION=$(VERSION) ./make/docker-push.sh

# ==============================================================================
# Cleanup
# ==============================================================================

clean: ## Remove build artifacts and caches
	@rm -rf dist/ build/ *.egg-info
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.pyc' -delete

# ==============================================================================
# Hidden Targets
# ==============================================================================

.venv/bin/python:
	@./make/setup.sh
