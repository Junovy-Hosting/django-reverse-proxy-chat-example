.PHONY: help build up down logs shell migrate makemigrations collectstatic createsuperuser seed-users seed-rooms seed ngrok dev clean restart test

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose build

up: ## Start all services
	docker compose up -d

down: ## Stop all services
	docker compose down

logs: ## Tail logs for all services
	docker compose logs -f

shell: ## Open a Django shell in the web container
	docker compose exec web python manage.py shell

migrate: ## Run Django migrations
	docker compose exec web python manage.py migrate

makemigrations: ## Create new Django migrations
	docker compose exec web python manage.py makemigrations

collectstatic: ## Collect static files
	docker compose exec web python manage.py collectstatic --noinput

createsuperuser: ## Create a Django superuser
	docker compose exec web python manage.py createsuperuser

seed-users: ## Seed faerie users (10 users + 1 admin)
	docker compose exec web python manage.py seed_users

seed-rooms: ## Seed default chat rooms
	docker compose exec web python manage.py seed_rooms

seed: seed-users seed-rooms ## Seed users and rooms

ngrok: ## Start ngrok tunnel (requires ngrok installed)
	ngrok http --url=faeries.ngrok.app 80

dev: build up ## Full dev setup: build, start, wait for healthy, seed
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@$(MAKE) seed
	@echo ""
	@echo "Faerie Chat is ready!"
	@echo "  Local:  http://localhost"
	@echo "  Ngrok:  make ngrok (in another terminal)"
	@echo "  Login:  titania / faerie123"

clean: ## Stop services, remove volumes and images
	docker compose down -v --rmi local

restart: ## Restart all services
	docker compose restart

test: ## Run Django tests
	docker compose exec web python manage.py test
