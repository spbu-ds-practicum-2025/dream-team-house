.PHONY: help up down restart logs clean build start-agents stop-agents

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: down up ## Restart all services

logs: ## Show logs from all services
	docker-compose logs -f

clean: ## Stop all services and remove volumes
	docker-compose down -v

build: ## Rebuild all Docker images
	docker-compose build

start-agents: ## Start 5 AI agents
	docker-compose up -d --scale ai-agent=5

stop-agents: ## Stop all AI agents
	docker-compose stop ai-agent

status: ## Show status of all services
	docker-compose ps

check-health: ## Check health of all services
	@echo "Checking service health..."
	@curl -s http://localhost/health || echo "Load balancer: DOWN"
	@curl -s http://localhost:3000 > /dev/null && echo "Frontend: UP" || echo "Frontend: DOWN"
