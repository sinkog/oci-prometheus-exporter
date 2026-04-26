# CLI Reference

## `oci-exporter`

```
oci-exporter [--config PATH] [--port PORT] [--validate] [--generate-config]
```

### Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--config PATH` | `/etc/oci-exporter/config.yaml` | Path to the YAML configuration file. |
| `--port PORT` | `9090` | TCP port to listen on for Prometheus scrapes. |
| `--validate` | — | Validate the config against the OCI Monitoring API and exit. |
| `--generate-config` | — | Discover all available OCI metrics and print a complete `config.yaml` to stdout, then exit. |

### Normal operation

```bash
oci-exporter --config /etc/oci-exporter/config.yaml --port 9090
```

Loads config, connects to OCI, starts the poll loop, and serves metrics on `http://0.0.0.0:<port>/metrics`.

### Validate before deploy

Checks that every namespace and metric name in the config actually exists in OCI for the configured compartments. Exit code 0 = all OK, 1 = at least one metric missing or API error.

```bash
oci-exporter --config config.yaml --validate
```

Example output:

```
Compartment: ocid1.tenancy.oc19...

  Namespace: oci_compute_infrastructure_health
    [OK]      instance_status
    [OK]      maintenance_status

  Namespace: oci_vcn
    [OK]      vnic_bytes_in
    [MISSING] nonexistent_metric

Result: 3 OK, 1 MISSING, 0 WARN
```

Status codes in output:

| Status | Meaning |
|--------|---------|
| `[OK]` | Metric found in OCI for this compartment. |
| `[MISSING]` | Metric not found — check the metric name and MQL query. |
| `[WARN]` | Namespace returned no metrics — no active resources in this compartment, or namespace name is wrong. Cannot verify individual metrics. |
| `[ERROR]` | OCI API error when querying the namespace (permissions, endpoint, etc.). |

### Generate config from discovery

Queries OCI `list_metrics` for all namespaces and metrics visible in the configured compartments, then emits a ready-to-use `config.yaml` with `[1m].mean()` queries as defaults.

```bash
# Create a minimal seed config first
cat > seed.yaml <<EOF
compartmentIds:
  - "ocid1.tenancy.oc1..example"
region: "eu-frankfurt-2"
auth:
  type: ApiKey
namespaces: []
EOF

oci-exporter --config seed.yaml --generate-config > config.full.yaml
```

Review and trim the output — not every discovered metric is useful for every environment. Counter-like metrics (bytes, packets, ops) may benefit from `.sum()` or `.rate()` instead of the default `.mean()`.