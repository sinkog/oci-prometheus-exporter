"""OCI Monitoring API polling with retry/backoff and stale-metric cleanup."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import oci
import oci.exceptions

from . import metrics as m
from .config import Config

log = logging.getLogger(__name__)

_RETRY_ATTEMPTS = 3
_RETRY_BASE = 2.0
_OCI_TIMEOUT = 30
_STALE_CYCLES = 3

# OCI status codes that warrant a retry
_RETRYABLE = {429, 500, 502, 503, 504}


def build_client(cfg: Config) -> oci.monitoring.MonitoringClient:
    kwargs: dict = {"timeout": _OCI_TIMEOUT}
    if cfg.telemetry_endpoint:
        kwargs["service_endpoint"] = cfg.telemetry_endpoint

    if cfg.auth.type == "InstancePrincipal":
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        client = oci.monitoring.MonitoringClient({"region": cfg.region}, signer=signer, **kwargs)
    else:
        client = oci.monitoring.MonitoringClient(oci.config.from_file(), **kwargs)

    log.info("MonitoringClient endpoint: %s", client.base_client.endpoint)
    return client


def _query_with_retry(
    client: oci.monitoring.MonitoringClient,
    compartment_id: str,
    ns: str,
    query: str,
    start_str: str,
    end_str: str,
):
    details = oci.monitoring.models.SummarizeMetricsDataDetails(
        namespace=ns,
        query=query,
        start_time=start_str,
        end_time=end_str,
        resolution="1m",
    )
    last_exc: Exception | None = None
    for attempt in range(_RETRY_ATTEMPTS):
        try:
            return client.summarize_metrics_data(
                compartment_id=compartment_id,
                summarize_metrics_data_details=details,
            )
        except oci.exceptions.ServiceError as exc:
            last_exc = exc
            if exc.status in _RETRYABLE:
                wait = _RETRY_BASE ** attempt * (2.0 if exc.status == 429 else 1.0)
                log.warning(
                    "OCI %d for %s, retry %d/%d in %.1fs",
                    exc.status, ns, attempt + 1, _RETRY_ATTEMPTS, wait,
                )
                time.sleep(wait)
            else:
                raise
        except Exception as exc:
            last_exc = exc
            wait = _RETRY_BASE ** attempt
            log.warning(
                "OCI error (%s): %s — retry %d/%d in %.1fs",
                ns, exc, attempt + 1, _RETRY_ATTEMPTS, wait,
            )
            time.sleep(wait)
    raise RuntimeError(f"All {_RETRY_ATTEMPTS} retries exhausted for {ns}") from last_exc


class Collector:
    def __init__(self, cfg: Config) -> None:
        self._cfg = cfg
        self._client = build_client(cfg)
        self._last_seen: dict[tuple[str, str, str, str], float] = {}

    @property
    def polling_frequency(self) -> float:
        return self._cfg.polling_frequency_seconds

    def poll(self) -> bool:
        """Run one full poll cycle. Returns True if no errors occurred."""
        cfg = self._cfg
        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=5)
        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = end.strftime("%Y-%m-%dT%H:%M:%SZ")
        now = time.time()

        # Spread queries evenly across the polling window (80% budget)
        min_interval = cfg.polling_frequency_seconds / max(cfg.total_queries, 1) * 0.8

        had_error = False
        for compartment_id in cfg.compartment_ids:
            for ns_cfg in cfg.namespaces:
                for metric in ns_cfg.metrics:
                    t0 = time.time()
                    try:
                        resp = _query_with_retry(
                            self._client, compartment_id,
                            ns_cfg.name, metric.query,
                            start_str, end_str,
                        )
                        gauge = m.get_or_create(ns_cfg.name, metric.name)
                        for item in resp.data:
                            if not item.aggregated_datapoints:
                                continue
                            dims = item.dimensions or {}
                            resource_id = dims.get("resourceId", dims.get("instanceId", "global"))
                            val = item.aggregated_datapoints[-1].value
                            gauge.labels(
                                compartment_id=compartment_id,
                                resource_id=resource_id,
                            ).set(val)
                            key = (ns_cfg.name, metric.name, compartment_id, resource_id)
                            self._last_seen[key] = now
                    except Exception as exc:
                        had_error = True
                        m.errors_total.labels(
                            compartment_id=compartment_id,
                            namespace=ns_cfg.name,
                            metric=metric.name,
                        ).inc()
                        log.warning(
                            "[%s…] %s/%s: %s",
                            compartment_id[:20], ns_cfg.name, metric.name, exc,
                        )

                    elapsed = time.time() - t0
                    if elapsed < min_interval:
                        time.sleep(min_interval - elapsed)

        self._cleanup_stale(now)
        return not had_error

    def _cleanup_stale(self, now: float) -> None:
        threshold = _STALE_CYCLES * self._cfg.polling_frequency_seconds
        stale = [k for k, ts in self._last_seen.items() if now - ts > threshold]
        for key in stale:
            ns, metric_name, compartment_id, resource_id = key
            m.remove_label(ns, metric_name, compartment_id, resource_id)
            del self._last_seen[key]
            log.info(
                "Removed stale label: %s/%s compartment=%s… resource=%s",
                ns, metric_name, compartment_id[:20], resource_id,
            )
