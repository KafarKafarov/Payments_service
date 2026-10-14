.PHONY: install-dev format lint typecheck check test build build-d down

install:
	poetry install

format:
	poetry run ruff check --select I --fix app tests alembic
	poetry run ruff format app tests alembic

lint:
	poetry run ruff check app tests alembic

type:
	poetry run mypy app

build:
	docker compose up --build

build-d:
	docker compose up -d --build

down:
	docker compose down
