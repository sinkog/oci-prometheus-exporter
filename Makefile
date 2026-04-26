.PHONY: help lint fmt test cov check run docker-build clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

lint: ## Lint with ruff
	ruff check .

fmt: ## Format with ruff
	ruff format .

test: ## Run tests
	pytest

cov: ## Run tests with coverage report
	pytest --cov=oci_exporter --cov-report=term-missing

check: lint test ## Lint + test (CI judge)

run: ## Run locally with example config (ApiKey auth)
	python -m oci_exporter --config config.example.yaml

docker-build: ## Build Docker image
	docker build -t oci-prometheus-exporter:latest .

clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name '*.pyc' -delete
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info/
