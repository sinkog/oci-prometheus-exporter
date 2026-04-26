# CLAUDE.md — oci-prometheus-exporter

## Project layout

```
oci_exporter/       Python package
  config.py         Config loading and validation (dataclasses, sys.exit on error)
  collector.py      OCI Monitoring API polling, retry/backoff, stale cleanup
  metrics.py        Prometheus registry, gauge management, _prom_name()
  server.py         HTTP server: /metrics /healthz /readyz
  __main__.py       CLI entry point (--config, --port)
tools/              CentralInfraCore signing toolchain
  git_hook_commit-msg.sh   Vault commit-signing hook (active via symlink)
  vault-sign-agent.sh      Start/stop local Vault signing server
  vault-rootCA-sign-agent.sh
  init-hooks.sh     One-shot hook setup after clone
project.yaml        CentralInfraCore release metadata
```

## Development setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

```bash
ruff check .          # lint
pytest                # tests
pytest --cov          # tests with coverage
oci-exporter --config config.example.yaml   # run locally (ApiKey auth)
docker build -t oci-prometheus-exporter:latest .
```

## Commit signing

Every commit must be signed by the Vault hook. Before committing:

```bash
tools/vault-sign-agent.sh -k <key.pem> -c <cert.crt> --root-ca-file <ca.crt>
```

The hook appends `[signing-metadata]` and `[certificate]` blocks to the commit message automatically. Never use `--no-verify`.

After cloning, run `tools/init-hooks.sh` once to activate the hook.

## Key conventions

- Metric names: `_prom_name(namespace, metric)` in `metrics.py` — namespaces already starting with `oci_` are not double-prefixed
- Auth: InstancePrincipal auto-detects OC19 realm (`oraclecloud.eu`) — never hardcode `service_endpoint` in the OCI client config dict
- Stale cleanup: labels are removed after 3 missed poll cycles (`_cleanup_stale()` in `collector.py`)
- Rate limiting: inter-query sleep = `polling_frequency / total_queries * 0.8`
- Config validation fails with `sys.exit(1)`, not exceptions — intentional

## Git commits

- Never add `Co-Authored-By` or any AI-related lines to commit messages
- Commit message must contain the Vault `[signing-metadata]` block (added by hook)
