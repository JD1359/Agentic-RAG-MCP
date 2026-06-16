.PHONY: help install up down build test lint eval ingest-demo logs

help:
	@echo "Targets:"
	@echo "  install     - pip install -e .[dev]"
	@echo "  up          - docker compose up --build"
	@echo "  down        - docker compose down"
	@echo "  test        - pytest -q --cov"
	@echo "  lint        - ruff + mypy"
	@echo "  eval        - python eval/run.py demo"
	@echo "  ingest-demo - ingest example docs into 'demo' collection"

install:
	pip install -e ".[dev]"

up:
	docker compose up --build

down:
	docker compose down

test:
	pytest -q --cov=agentic_rag_mcp

lint:
	ruff check src tests
	mypy src

eval:
	python eval/run.py demo

ingest-demo:
	python examples/ingest_docs.py examples/sample-docs demo

logs:
	docker compose logs -f server
