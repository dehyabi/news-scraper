# ========== Configuration ==========
ENV_FILE=.env
DOCKER_ENV_FILE=.env.docker
DOCKER_COMPOSE=docker-compose

# ========== Commands ==========

# Run local Flask app (tanpa Docker)
run-local:
	@echo "Running app locally with Flask..."
	@export $(shell cat $(ENV_FILE) | xargs) && gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Build images, clean start (tanpa hapus volume)
docker-build:
	@echo "Rebuilding containers..."
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) --env-file $(DOCKER_ENV_FILE) build
	docker image prune -f
	$(DOCKER_COMPOSE) --env-file $(DOCKER_ENV_FILE) up

# Build images with no cache, clean start (tanpa hapus volume)
docker-build-clean:
	@echo "Rebuilding containers with no cache..."
	$(DOCKER_COMPOSE) down
	$(DOCKER_COMPOSE) --env-file $(DOCKER_ENV_FILE) build --no-cache
	docker image prune -f
	$(DOCKER_COMPOSE) --env-file $(DOCKER_ENV_FILE) up

# Start Docker Compose (tanpa build ulang)
docker-up:
	@echo "Starting containers..."
	$(DOCKER_COMPOSE) --env-file $(DOCKER_ENV_FILE) up

# Stop containers (tanpa hapus network & volume)
docker-stop:
	@echo "Stopping containers..."
	$(DOCKER_COMPOSE) stop

# Stop & remove containers, network (volume tetap aman)
docker-down:
	@echo "Stopping and removing containers and network..."
	$(DOCKER_COMPOSE) down

# Reset total (hapus semua containers, volumes, networks)
reset:
	@echo "Resetting Docker Compose (remove containers & volumes)..."
	$(DOCKER_COMPOSE) down -v --remove-orphans

# View container logs
logs:
	$(DOCKER_COMPOSE) logs -f

# Remove dangling images
prune-images:
	@echo "Pruning unused Docker images..."
	docker image prune -f

# Remove all unused Docker data (⚠️ hati-hati)
prune-all:
	@echo "Pruning ALL unused Docker data (containers, images, networks, volumes)..."
	docker system prune -a -f --volumes

# ========== Help ==========
help:
	@echo ""
	@echo "Available commands:"
	@echo "  make run-local       		Run app locally (requires virtualenv & dependencies)"
	@echo "  make docker-up       		Start containers (no rebuild)"
	@echo "  make docker-build    		Build & start containers (keep volumes)"
	@echo "  make docker-build-clean	Clean build & start containers (no-cache, keep volumes)"
	@echo "  make docker-stop     		Stop containers"
	@echo "  make docker-down     		Stop & remove containers & network"
	@echo "  make reset           		Stop and remove all containers & volumes"
	@echo "  make logs            		Tail logs from Docker Compose"
	@echo "  make prune-images    		Remove dangling Docker images"
	@echo "  make prune-all       		Remove all unused Docker data (⚠️ irreversible)"
	@echo ""
