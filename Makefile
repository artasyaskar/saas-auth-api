# Makefile for SaaS Auth API

.PHONY: help install dev test lint format clean migrate run

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make dev        - Run in development mode"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linting"
	@echo "  make format     - Format code"
	@echo "  make clean      - Clean cache files"
	@echo "  make migrate    - Run database migrations"
	@echo "  make run        - Start production server"

install:
	pip install -r requirements.txt

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	flake8 app/ tests/
	mypy app/

format:
	black app/ tests/
	isort app/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(message)"

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
