.PHONY: up down logs build gen-wms fmt lint test install

COMPOSE := docker compose -f infra/docker-compose.yml

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

build:
	$(COMPOSE) build

ps:
	$(COMPOSE) ps

gen-wms:
	curl -s -X POST http://localhost:8000/apps \
	  -H "Content-Type: application/json" \
	  -d @docs/prompts/wms.json | jq .

install:
	cd services/generator && uv sync
	cd apps/dashboard && npm install

fmt:
	cd services/generator && uv run ruff format . && uv run ruff check --fix .
	cd apps/dashboard && npm run lint -- --fix || true

lint:
	cd services/generator && uv run ruff check .
	cd apps/dashboard && npm run lint

test:
	cd services/generator && uv run pytest -q
