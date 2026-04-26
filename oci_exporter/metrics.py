"""Prometheus metrics registry."""

from __future__ import annotations

import logging
import re

from prometheus_client import CollectorRegistry, Counter, Gauge

REGISTRY = CollectorRegistry()

up = Gauge(
    "oci_exporter_up",
    "1 if the last poll cycle succeeded entirely",
    registry=REGISTRY,
)
last_success = Gauge(
    "oci_exporter_last_scrape_success",
    "Unix timestamp of the last fully successful scrape",
    registry=REGISTRY,
)
last_timestamp = Gauge(
    "oci_exporter_last_scrape_timestamp",
    "Unix timestamp of the last scrape attempt",
    registry=REGISTRY,
)
scrape_duration = Gauge(
    "oci_exporter_last_scrape_duration_seconds",
    "Duration in seconds of the last scrape cycle",
    registry=REGISTRY,
)
errors_total = Counter(
    "oci_exporter_errors_total",
    "Total number of per-metric scrape errors",
    ["compartment_id", "namespace", "metric"],
    registry=REGISTRY,
)

log = logging.getLogger(__name__)

_gauges: dict[tuple[str, str], Gauge] = {}


def _prom_name(ns: str, metric: str) -> str:
    prefix = ns if ns.startswith("oci_") else f"oci_{ns}"
    return re.sub(r"[^a-zA-Z0-9_]", "_", f"{prefix}_{metric}")


def get_or_create(ns: str, metric: str) -> Gauge:
    key = (ns, metric)
    if key not in _gauges:
        _gauges[key] = Gauge(
            _prom_name(ns, metric),
            f"OCI metric: {ns}/{metric}",
            ["compartment_id", "resource_id"],
            registry=REGISTRY,
        )
    return _gauges[key]


def remove_label(ns: str, metric: str, compartment_id: str, resource_id: str) -> None:
    key = (ns, metric)
    if key in _gauges:
        try:
            _gauges[key].remove(compartment_id, resource_id)
        except Exception as exc:
            log.debug(
                "remove_label %s/%s [%s %s]: %s",
                ns, metric, compartment_id, resource_id, exc,
            )
