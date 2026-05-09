.PHONY: dev lint format test build

dev:
	uv sync --all-groups

lint:
	uv run ruff format --check && uv run ruff check .

format:
	uv run ruff format .

test:
	uv run pytest -x

test-cov:
	uv run pytest --cov=quick_capture --cov-fail-under=80

build:
	uv build