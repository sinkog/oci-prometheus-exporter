# ROADMAP — oci-prometheus-exporter

Status: `pending` · `in_progress` · `done`

---

## Fixes & improvements (code review findings)

| # | Status | Title | File | Notes |
|---|--------|-------|------|-------|
| F1 | pending | Missing tests: collector | `tests/test_collector.py` | retry logic, stale cleanup, poll loop — no coverage at all |
| F2 | pending | Missing tests: metrics | `tests/test_metrics.py` | `get_or_create`, `remove_label` |
| F3 | pending | Missing tests: server | `tests/test_server.py` | `/metrics`, `/healthz`, `/readyz`, `record_poll` |
| F4 | pending | `remove_label` silently swallows exceptions | `metrics.py:62` | `except Exception: pass` → at least `log.debug` |
| F5 | pending | `/readyz` data race on error body | `server.py:48–50` | `_consecutive_errors` read twice across separate lock sections |
| F6 | pending | Private attribute access across module boundary | `__main__.py:23` | `collector._cfg` → add `Collector.polling_frequency` property |
| F7 | pending | Dockerfile: package not installed via pip | `Dockerfile` | runtime stage only copies source — `oci-exporter` CLI entrypoint unavailable in container |

---

## Features

| # | Status | Title | Notes |
|---|--------|-------|-------|

---

## Done

| # | Title |
|---|-------|
