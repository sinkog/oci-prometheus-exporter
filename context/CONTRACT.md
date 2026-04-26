# Contract — oci-prometheus-exporter

## I/O

**Input:** YAML config file (`/etc/oci-exporter/config.yaml` or `--config PATH`)
**Output:** Prometheus metrics on `GET /metrics` (Prometheus text exposition format)

## Invariants

1. **Metric naming** — all gauge names go through `_prom_name(ns, metric)` in `metrics.py`; namespaces already starting with `oci_` are not double-prefixed.
2. **Stale cleanup** — label sets not seen for `3 × polling_frequency_seconds` are removed via `_cleanup_stale()` in `collector.py`.
3. **Rate limiting** — inter-query sleep = `polling_frequency_seconds / total_queries * 0.8`; never skip this.
4. **Config errors** — validation failures call `sys.exit(1)`, never raise exceptions upstream.
5. **Auth** — InstancePrincipal never receives `service_endpoint` inside the OCI config dict; passed as a separate kwarg only.
6. **Registry** — all metrics registered to `REGISTRY` in `metrics.py`, never to the default global prometheus registry.

## Error behaviour

- OCI API errors (retryable: 429, 500–504): exponential backoff, 3 attempts, then log + increment `oci_exporter_errors_total`.
- Non-retryable OCI errors: re-raised immediately.
- Poll-level errors: recorded in `oci_exporter_up` and `server._consecutive_errors`; 3 consecutive failures → `/readyz` returns 503.
