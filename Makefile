.PHONY: dev lint format test check build

dev:
	uv sync --all-groups

lint:
	uv run ruff check .
	uv run ty check src/

format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

test:
	uv run pytest

test-cov:
	uv run pytest --cov

check: lint format-check test

build:
	uv build