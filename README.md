# oci-prometheus-exporter

Prometheus exporter for [Oracle Cloud Infrastructure (OCI)](https://www.oracle.com/cloud/) metrics.
Queries the [OCI Monitoring API](https://docs.oracle.com/en-us/iaas/api/#/en/monitoring/20180401/) and exposes the results as Prometheus gauges.

## Features

- Multi-compartment scraping
- InstancePrincipal auth (no API key needed in Kubernetes)
- Retry with exponential backoff (rate-limit and 5xx aware)
- Stale resource cleanup — labels disappear when OCI stops reporting them
- Rich self-metrics (`oci_exporter_up`, `oci_exporter_errors_total`, …)
- Separate `/healthz` (liveness) and `/readyz` (readiness) endpoints
- Prometheus-safe metric name sanitization

## Exposed endpoints

| Path | Description |
|------|-------------|
| `/metrics` | Prometheus metrics |
| `/healthz` | Liveness — always `200 ok` while the process is alive |
| `/readyz` | Readiness — `503` if the last N poll cycles all failed |

## Self-metrics

| Metric | Type | Description |
|--------|------|-------------|
| `oci_exporter_up` | Gauge | 1 if last poll cycle succeeded |
| `oci_exporter_last_scrape_success` | Gauge | Unix timestamp of last full success |
| `oci_exporter_last_scrape_timestamp` | Gauge | Unix timestamp of last attempt |
| `oci_exporter_last_scrape_duration_seconds` | Gauge | Duration of last cycle |
| `oci_exporter_errors_total` | Counter | Per-metric error count |

## Configuration

Copy `config.example.yaml` and adjust:

```yaml
compartmentIds:
  - "ocid1.compartment.oc1..example"  # list compartments to scrape explicitly

region: "eu-frankfurt-2"

auth:
  type: InstancePrincipal   # or ApiKey (reads ~/.oci/config)

metricsPollingFrequencyInSeconds: 60

# Required for dedicated / sovereign cloud regions (OC19 etc.)
# telemetryEndpoint: "https://telemetry.eu-frankfurt-2.oraclecloud.eu"

namespaces:
  - name: oci_computeagent
    metrics:
      - name: cpu_utilization
        query: "CpuUtilization[1m].mean()"
```

### Metric naming

`oci_<namespace>_<metric>` — all non-alphanumeric characters are replaced with `_`.
Namespaces that already start with `oci_` are not double-prefixed.

## Running

### Docker

```bash
docker run --rm \
  -v /path/to/config.yaml:/etc/oci-exporter/config.yaml:ro \
  -p 9090:9090 \
  oci-prometheus-exporter:latest
```

### Kubernetes

Deploy a `ConfigMap` with your `config.yaml`, a `Deployment` referencing the image, and a `Service` + `ServiceMonitor` for Prometheus scraping.

Minimal `Deployment` snippet:

```yaml
containers:
  - name: oci-exporter
    image: <your-registry>/oci-prometheus-exporter:latest
    args: ["--config", "/etc/oci-exporter/config.yaml", "--port", "9090"]
    volumeMounts:
      - name: config
        mountPath: /etc/oci-exporter
        readOnly: true
volumes:
  - name: config
    configMap:
      name: oci-exporter-config
```

### IAM (InstancePrincipal)

The OKE worker node needs read access to OCI Monitoring:

```
Allow dynamic-group <oke-nodes> to read metrics in tenancy
Allow dynamic-group <oke-nodes> to use metrics in tenancy
```

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# lint
ruff check .

# tests
pytest

# run locally (ApiKey auth)
oci-exporter --config config.example.yaml
```

### Building the Docker image

```bash
docker build -t oci-prometheus-exporter:latest .
```

## Signing and Release

This project uses the [CentralInfraCore](https://github.com/CentralInfraCore/base-repo/tree/main/tools) Vault-based commit-signing toolchain.

### Initial setup (once per clone)

```bash
tools/init-hooks.sh
```

This symlinks `tools/git_hook_commit-msg.sh` into `.git/hooks/commit-msg`. Every commit is then signed with ECDSA-SHA256 via HashiCorp Vault Transit and the signature is appended to the commit message.

### Starting the signing agent

The signing agent runs a temporary in-memory Vault instance that holds your private key for the duration of the session:

```bash
tools/vault-sign-agent.sh \
  -k /path/to/my-signing-key.pem \
  -c /path/to/my-cert.crt \
  --root-ca-file /path/to/ca.crt

# Stop when done
tools/vault-sign-agent.sh --stop
```

See [`tools/vault-sign-agent.md`](tools/vault-sign-agent.md) for full documentation.

### Release process

The `project.yaml` at the repo root tracks version, owner, and signing metadata. Update `metadata.version` and run the signing agent before tagging a release.

### Tools provenance

| Tool | Source |
|------|--------|
| `tools/git_hook_commit-msg.sh` | [CentralInfraCore/base-repo](https://github.com/CentralInfraCore/base-repo/tree/main/tools) |
| `tools/vault-sign-agent.sh` | [CentralInfraCore/base-repo](https://github.com/CentralInfraCore/base-repo/tree/main/tools) |
| `tools/vault-rootCA-sign-agent.sh` | [CentralInfraCore/base-repo](https://github.com/CentralInfraCore/base-repo/tree/main/tools) |
| `tools/init-hooks.sh` | Adapted from [CentralInfraCore/base-repo](https://github.com/CentralInfraCore/base-repo/tree/main/tools) |

## License

MIT
