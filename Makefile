SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
MAKEFLAGS += --warn-undefined-variables

COVERAGE_MIN ?= 80
BUILDER := docker compose run --rm builder

.PHONY: help lint fmt test cov cov-check check run docker-build clean

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-14s %s\n", $$1, $$2}'

# ── quality & test (hermetic, pinned Python) ──────────────────────────────────

lint: ## Lint with ruff (builder container)
	$(BUILDER) sh -c 'ruff check .'

fmt: ## Format with ruff (builder container)
	$(BUILDER) sh -c 'ruff format .'

test: ## Run tests (builder container)
	$(BUILDER) sh -c 'pytest'

cov: ## Run tests with coverage report (builder container)
	$(BUILDER) sh -c 'pytest --cov=oci_exporter --cov-report=term-missing'

cov-check: ## Fail if coverage is below COVERAGE_MIN% (builder container)
	@$(BUILDER) sh -c '\
		pytest --cov=oci_exporter --cov-report=term-missing -q 2>&1 | tee /tmp/cov_out.txt; \
		pct=$$(grep -oP "TOTAL\s+\d+\s+\d+\s+\K\d+" /tmp/cov_out.txt || echo 0); \
		echo "Coverage: $${pct}%  (min: $(COVERAGE_MIN)%)"; \
		[ "$${pct}" -ge "$(COVERAGE_MIN)" ] || { echo "FAIL: below threshold"; exit 1; }'

check: lint test ## Lint + test — CI judge (hermetic)

# ── run / build ───────────────────────────────────────────────────────────────

run: ## Run locally with example config (needs local OCI credentials)
	python -m oci_exporter --config config.example.yaml

docker-build: ## Build production Docker image
	docker build -t oci-prometheus-exporter:latest .

# ── housekeeping ──────────────────────────────────────────────────────────────

clean: ## Remove build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -name '*.pyc' -delete
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info/
