# CLAUDE.md — oci-prometheus-exporter

## AI collaboration

- **`ai/activation.txt`** — thinking mode and priorities
- **`context/CONTRACT.md`** — I/O contract and invariants (canonical truth)
- **`ai/SELF_CHECKLIST.md`** — pre-change checklist
- **`ai/ROADMAP.md`** — task backlog (fixes, features, status)

## Project layout

```
oci_exporter/       Python package
  config.py         Config loading and validation (dataclasses, sys.exit on error)
  collector.py      OCI Monitoring API polling, retry/backoff, stale cleanup
  metrics.py        Prometheus registry, gauge management, _prom_name()
  server.py         HTTP server: /metrics /healthz /readyz
  __main__.py       CLI entry point (--config, --port)
ai/                 AI collaboration context
  activation.txt    Thinking mode + priorities
  SELF_CHECKLIST.md Pre-change checklist
  ROADMAP.md        Task backlog (fixes, features, status)
context/            Contracts and invariants
  CONTRACT.md       I/O contract and system invariants
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
make check            # lint + test — hermetic, pinned Python (CI judge)
make lint             # ruff only (builder container)
make test             # pytest only (builder container)
make cov              # pytest with coverage report (builder container)
make cov-check        # fail if coverage < COVERAGE_MIN (default 80%)
make run              # run locally — only target requiring local Python + OCI creds
make docker-build     # build production Docker image
make clean            # remove build artifacts
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
