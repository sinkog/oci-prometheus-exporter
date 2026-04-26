"""Configuration loading and validation."""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field

import yaml

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricConfig:
    name: str
    query: str


@dataclass(frozen=True)
class NamespaceConfig:
    name: str
    metrics: tuple[MetricConfig, ...]


@dataclass(frozen=True)
class AuthConfig:
    type: str = "InstancePrincipal"


@dataclass(frozen=True)
class Config:
    compartment_ids: tuple[str, ...]
    region: str
    namespaces: tuple[NamespaceConfig, ...]
    auth: AuthConfig = field(default_factory=AuthConfig)
    polling_frequency_seconds: int = 60
    telemetry_endpoint: str | None = None

    @property
    def total_queries(self) -> int:
        return sum(len(ns.metrics) for ns in self.namespaces) * len(self.compartment_ids)


def _get(raw: dict, snake: str, camel: str, default=None):
    """Look up a config key by snake_case (canonical) then camelCase (legacy alias)."""
    v = raw.get(snake)
    return v if v is not None else raw.get(camel, default)


def load(path: str = "/etc/oci-exporter/config.yaml") -> Config:
    with open(path) as fh:
        raw = yaml.safe_load(fh)

    errors: list[str] = []

    # Accept snake_case (canonical), camelCase (legacy), and singular compartmentId
    if "compartmentId" in raw and "compartment_ids" not in raw and "compartmentIds" not in raw:
        compartment_ids = [raw["compartmentId"]]
    else:
        compartment_ids = _get(raw, "compartment_ids", "compartmentIds") or []

    if not compartment_ids:
        errors.append("compartment_ids (or compartmentIds) is required")

    region = raw.get("region", "")
    if not region:
        errors.append("region is required")

    namespaces: list[NamespaceConfig] = []
    for ns_raw in raw.get("namespaces", []):
        metrics: list[MetricConfig] = []
        for m in ns_raw.get("metrics", []):
            if not m.get("query"):
                errors.append(f"missing query for {ns_raw['name']}/{m.get('name', '?')}")
            else:
                metrics.append(MetricConfig(name=m["name"], query=m["query"]))
        namespaces.append(NamespaceConfig(name=ns_raw["name"], metrics=tuple(metrics)))

    if errors:
        for e in errors:
            log.error("Config error: %s", e)
        sys.exit(1)

    auth_raw = raw.get("auth", {})
    freq = int(_get(raw, "polling_frequency_seconds", "metricsPollingFrequencyInSeconds", 60))

    cfg = Config(
        compartment_ids=tuple(compartment_ids),
        region=region,
        namespaces=tuple(namespaces),
        auth=AuthConfig(type=auth_raw.get("type", "InstancePrincipal")),
        polling_frequency_seconds=freq,
        telemetry_endpoint=_get(raw, "telemetry_endpoint", "telemetryEndpoint"),
    )

    if cfg.total_queries > 0 and freq < cfg.total_queries:
        log.warning(
            "metricsPollingFrequencyInSeconds=%d is shorter than total query count=%d; "
            "consider increasing it to avoid OCI rate limits",
            freq,
            cfg.total_queries,
        )

    log.info(
        "Config: %d compartment(s), %d metric(s)/compartment, poll every %ds",
        len(cfg.compartment_ids),
        sum(len(ns.metrics) for ns in cfg.namespaces),
        cfg.polling_frequency_seconds,
    )
    return cfg
