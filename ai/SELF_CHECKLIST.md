# AI Self-Checklist

Before proposing or finalising any change:

## Code quality
- [ ] `ruff check .` passes with no errors
- [ ] `pytest` passes (all tests green)

## Conventions
- [ ] New metric names go through `_prom_name()` — never construct gauge names inline
- [ ] Config errors use `sys.exit(1)`, not `raise`
- [ ] No `service_endpoint` in the OCI client config dict — kwarg only
- [ ] All new gauges registered to `metrics.REGISTRY`, not the default global registry

## Scope
- [ ] Change does not add abstractions beyond what the task requires
- [ ] No backwards-compatibility shims for removed or changed code
- [ ] No comments explaining WHAT the code does — only WHY when non-obvious

## When uncertain
Propose a CLAUDE.md or CONTRACT.md diff instead of deviating silently.
