# ROADMAP — oci-prometheus-exporter

Status: `pending` · `in_progress` · `done`

---

## Fixes & improvements (code review findings)

| # | Status | Title | File | Notes |
|---|--------|-------|------|-------|
| F1 | done | Missing tests: collector | `tests/test_collector.py` | retry logic, stale cleanup, poll loop — no coverage at all |
| F2 | done | Missing tests: metrics | `tests/test_metrics.py` | `get_or_create`, `remove_label` |
| F3 | done | Missing tests: server | `tests/test_server.py` | `/metrics`, `/healthz`, `/readyz`, `record_poll` |
| F4 | done | `remove_label` silently swallows exceptions | `metrics.py:62` | `except Exception: pass` → at least `log.debug` |
| F5 | done | `/readyz` data race on error body | `server.py:48–50` | `_consecutive_errors` read twice across separate lock sections |
| F6 | done | Private attribute access across module boundary | `__main__.py:23` | `collector._cfg` → add `Collector.polling_frequency` property |
| F7 | done | Dockerfile: package not installed via pip | `Dockerfile` | runtime stage only copies source — `oci-exporter` CLI entrypoint unavailable in container |

---

## Bugs

| # | Status | Title | File | Notes |
|---|--------|-------|------|-------|
| B1 | done | YAML config kulcsok következetlenség | `config.py`, `collector.py` | snake_case lett a canonical (`compartment_ids`, `polling_frequency_seconds`, `telemetry_endpoint`); camelCase backward compat alias-ként megmarad; `generate_config` snake_case-t ír ki |
| B2 | done | `generate_config` mindenre `.mean()` aggr. | `collector.py` | `_default_query()` heurisztika: gauge hint (active, stored, status, percent…) → mean(); counter hint (bytes, ops, packets, drops…) → sum(); gauge hint prioritást élvez |

---

## Features

| # | Status | Title | Notes |
|---|--------|-------|-------|

---

## Done

| # | Title |
|---|-------|
