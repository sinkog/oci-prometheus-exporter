# Configuration Reference

## File location

Default: `/etc/oci-exporter/config.yaml`. Override with `--config PATH`.

## Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `compartmentIds` | list[string] | yes | — | OCID(s) of compartments to scrape. Use the tenancy OCID to cover all resources. |
| `region` | string | yes | — | OCI region identifier, e.g. `eu-frankfurt-2`. |
| `auth.type` | string | no | `InstancePrincipal` | Auth method. See [Auth](#auth). |
| `metricsPollingFrequencyInSeconds` | int | no | `60` | Poll interval in seconds. Must be ≥ total metric query count to avoid OCI rate limits. |
| `telemetryEndpoint` | string | no | null | Override OCI Monitoring endpoint. Required for sovereign/dedicated cloud regions. |
| `namespaces` | list | yes | — | Namespaces and metrics to collect. |
| `namespaces[].name` | string | yes | — | OCI Monitoring namespace (e.g. `oci_computeagent`, `oci_vcn`). |
| `namespaces[].metrics[].name` | string | yes | — | Logical metric name — used in the Prometheus metric name. |
| `namespaces[].metrics[].query` | string | yes | — | MQL query string (e.g. `CpuUtilization[1m].mean()`). |

## Auth

| `auth.type` | Behaviour |
|-------------|-----------|
| `InstancePrincipal` | Uses the OCI instance identity signer — no key file needed. Recommended for Kubernetes/OKE deployments. The instance must be in a dynamic group with `read metrics` permission. |
| `ApiKey` | Reads `~/.oci/config`. For local development and environments without instance identity. |

## Sovereign/dedicated cloud regions

OC19 (EU Sovereign Cloud) and other dedicated regions use a non-standard telemetry endpoint. Set `telemetryEndpoint` explicitly:

```yaml
telemetryEndpoint: "https://telemetry.eu-frankfurt-2.oraclecloud.eu"
```

The InstancePrincipal auth path auto-detects the OC19 realm from the IMDS token and sets the correct signer; only the monitoring endpoint needs the override.

## Rate limiting

OCI Monitoring enforces per-compartment rate limits. The exporter spreads queries evenly across the polling window at 80% of budget:

```
inter_query_sleep = metricsPollingFrequencyInSeconds / total_queries * 0.8
```

If `metricsPollingFrequencyInSeconds` is less than `total_queries`, the exporter logs a warning on startup. As a rule of thumb: set the frequency to at least `namespaces × metrics × compartments`.

## Metric naming

Prometheus metric names are built as:

```
oci_<namespace>_<metric_name>
```

All non-alphanumeric characters are replaced with `_`. Namespaces that already start with `oci_` are not double-prefixed (e.g. `oci_computeagent` → `oci_computeagent_cpu_utilization`, not `oci_oci_computeagent_...`).

The `namespaces[].metrics[].name` field controls only the Prometheus name suffix — the OCI metric identifier comes from the MQL `query`.

## Complete example

```yaml
compartmentIds:
  - "ocid1.tenancy.oc1..example"

region: "eu-frankfurt-2"

auth:
  type: InstancePrincipal

metricsPollingFrequencyInSeconds: 60

# telemetryEndpoint: "https://telemetry.eu-frankfurt-2.oraclecloud.eu"

namespaces:
  - name: oci_compute_infrastructure_health
    metrics:
      - name: instance_status
        query: "instance_status[1m].mean()"
      - name: maintenance_status
        query: "maintenance_status[1m].mean()"

  - name: oci_vcn
    metrics:
      - name: vnic_bytes_in
        query: "VnicFromNetworkBytes[1m].sum()"
      - name: vnic_bytes_out
        query: "VnicToNetworkBytes[1m].sum()"
      - name: vnic_ingress_drops_throttle
        query: "VnicIngressDropsThrottle[1m].sum()"
      - name: vnic_egress_drops_throttle
        query: "VnicEgressDropsThrottle[1m].sum()"

  - name: oci_blockstore
    metrics:
      - name: volume_read_ops
        query: "VolumeReadOps[1m].sum()"
      - name: volume_write_ops
        query: "VolumeWriteOps[1m].sum()"
      - name: volume_throttled_ios
        query: "VolumeThrottledIOs[1m].sum()"
```

## Generating a full config from OCI

Use the `--generate-config` flag to discover all available metrics in your compartments and produce a ready-to-edit config:

```bash
# Minimal seed config (auth + region + compartments only)
oci-exporter --config seed.yaml --generate-config > config.full.yaml
```

The seed config needs only `compartmentIds`, `region`, and `auth` — `namespaces` can be empty or absent.