.PHONY: up down drop logs infra weave web test

up:
	docker compose up --build

down:
	docker compose down

drop:
	docker compose down -v

logs:
	docker compose logs -f

infra:
	docker compose up -d postgres redis

weave:
	cd python/weave && uv run uvicorn weave.main:app --host 0.0.0.0 --port 8080

web:
	cd web && npm run dev

test:
	cd python/weave && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run python -m pytest tests/ -q
