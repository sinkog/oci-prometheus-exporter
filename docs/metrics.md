# Metrics Reference

## HTTP endpoints

| Path | Method | Description |
|------|--------|-------------|
| `/metrics` | GET | Prometheus text exposition format — OCI metrics + self-metrics. |
| `/healthz` | GET | Liveness probe. Always returns `200 ok` as long as the process is running. |
| `/readyz` | GET | Readiness probe. Returns `503` if the last 3 consecutive poll cycles all failed. |

## Self-metrics

These are always present regardless of config.

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `oci_exporter_up` | Gauge | — | `1` if the last poll cycle completed without errors, `0` otherwise. |
| `oci_exporter_last_scrape_success` | Gauge | — | Unix timestamp of the last fully successful poll. |
| `oci_exporter_last_scrape_timestamp` | Gauge | — | Unix timestamp of the last poll attempt (success or failure). |
| `oci_exporter_last_scrape_duration_seconds` | Gauge | — | Wall-clock duration of the last poll cycle in seconds. |
| `oci_exporter_errors_total` | Counter | `compartment_id`, `namespace`, `metric` | Cumulative error count per metric per compartment. Incremented when OCI returns an error after all retries are exhausted. |

## OCI metric gauges

Each metric configured under `namespaces` becomes a Prometheus Gauge:

```
oci_<namespace>_<metric_name>{compartment_id="...", resource_id="..."}
```

Labels:

| Label | Source | Description |
|-------|--------|-------------|
| `compartment_id` | Config | The compartment OCID being scraped. |
| `resource_id` | OCI response | The `resourceId` dimension from OCI (falls back to `instanceId`, then `global`). |

### Stale label cleanup

When OCI stops reporting a resource (e.g. an instance is terminated), its label set is removed from the gauge after `3 × metricsPollingFrequencyInSeconds` seconds. This prevents phantom metrics from staying in Prometheus indefinitely.

## Metric naming rules

1. Prefix: `oci_` + namespace + `_` + metric name.
2. If the namespace already starts with `oci_`, it is not prefixed again.
3. All non-alphanumeric characters (including `.`, `-`, space) are replaced with `_`.

Examples:

| Namespace | Metric name (config) | Prometheus name |
|-----------|---------------------|-----------------|
| `oci_computeagent` | `cpu_utilization` | `oci_computeagent_cpu_utilization` |
| `oci_vcn` | `vnic_bytes_in` | `oci_vcn_vnic_bytes_in` |
| `custom.namespace` | `my-metric` | `oci_custom_namespace_my_metric` |