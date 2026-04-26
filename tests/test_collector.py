"""Tests for OCI collector: retry logic, poll loop, stale cleanup."""

import time
from unittest.mock import MagicMock, patch

import pytest

from oci_exporter.collector import (
    _RETRY_ATTEMPTS,
    _RETRY_BASE,
    _STALE_CYCLES,
    Collector,
    _query_with_retry,
    build_client,
)
from oci_exporter.config import AuthConfig, Config, MetricConfig, NamespaceConfig


def _make_config(**kwargs) -> Config:
    defaults = dict(
        compartment_ids=("ocid1.tenancy.oc1..test",),
        region="eu-frankfurt-2",
        namespaces=(
            NamespaceConfig(
                name="oci_computeagent",
                metrics=(MetricConfig(name="cpu", query="CpuUtilization[1m].mean()"),),
            ),
        ),
        auth=AuthConfig(type="ApiKey"),
        polling_frequency_seconds=60,
    )
    defaults.update(kwargs)
    return Config(**defaults)


def _svc_err(status: int):
    from oci.exceptions import ServiceError
    return ServiceError(status, "err", {}, "error")


def _mock_collector(cfg: Config) -> Collector:
    with patch("oci_exporter.collector.build_client"):
        return Collector(cfg)


def _mock_response(value: float = 1.0, resource_id: str = "r1") -> MagicMock:
    dp = MagicMock()
    dp.value = value
    item = MagicMock()
    item.aggregated_datapoints = [dp]
    item.dimensions = {"resourceId": resource_id}
    resp = MagicMock()
    resp.data = [item]
    return resp


# ── build_client ─────────────────────────────────────────────────────────────

class TestBuildClient:
    def test_instance_principal_uses_signer(self):
        cfg = _make_config(auth=AuthConfig(type="InstancePrincipal"))
        mock_signer = MagicMock()
        mock_client = MagicMock()
        signer_path = (
            "oci_exporter.collector.oci.auth.signers.InstancePrincipalsSecurityTokenSigner"
        )
        with (
            patch(signer_path, return_value=mock_signer) as mock_signer_cls,
            patch("oci_exporter.collector.oci.monitoring.MonitoringClient",
                  return_value=mock_client) as mock_client_cls,
        ):
            result = build_client(cfg)

        mock_signer_cls.assert_called_once()
        _, kwargs = mock_client_cls.call_args
        assert kwargs["signer"] is mock_signer
        assert result is mock_client

    def test_api_key_reads_oci_config(self):
        cfg = _make_config(auth=AuthConfig(type="ApiKey"))
        with (
            patch("oci_exporter.collector.oci.config.from_file", return_value={}) as mock_ff,
            patch("oci_exporter.collector.oci.monitoring.MonitoringClient",
                  return_value=MagicMock()),
        ):
            build_client(cfg)
        mock_ff.assert_called_once()

    def test_telemetry_endpoint_passed_as_kwarg(self):
        cfg = _make_config(
            auth=AuthConfig(type="ApiKey"),
            telemetry_endpoint="https://telemetry.example.com",
        )
        with (
            patch("oci_exporter.collector.oci.config.from_file", return_value={}),
            patch("oci_exporter.collector.oci.monitoring.MonitoringClient",
                  return_value=MagicMock()) as mock_cls,
        ):
            build_client(cfg)
        _, kwargs = mock_cls.call_args
        assert kwargs["service_endpoint"] == "https://telemetry.example.com"


# ── _query_with_retry ─────────────────────────────────────────────────────────

class TestQueryWithRetry:
    def _call(self, client):
        return _query_with_retry(client, "compartment", "ns", "query", "start", "end")

    def test_success_on_first_attempt(self):
        client = MagicMock()
        expected = MagicMock()
        client.summarize_metrics_data.return_value = expected
        result = self._call(client)
        assert result is expected
        assert client.summarize_metrics_data.call_count == 1

    def test_retries_on_429(self):
        client = MagicMock()
        ok = MagicMock()
        client.summarize_metrics_data.side_effect = [_svc_err(429), ok]
        with patch("time.sleep") as mock_sleep:
            result = self._call(client)
        assert result is ok
        assert client.summarize_metrics_data.call_count == 2
        mock_sleep.assert_called_once_with(_RETRY_BASE ** 0 * 2.0)

    def test_retries_on_500(self):
        client = MagicMock()
        ok = MagicMock()
        client.summarize_metrics_data.side_effect = [_svc_err(500), ok]
        with patch("time.sleep") as mock_sleep:
            result = self._call(client)
        assert result is ok
        mock_sleep.assert_called_once_with(_RETRY_BASE ** 0 * 1.0)

    def test_non_retryable_error_raises_immediately(self):
        from oci.exceptions import ServiceError
        client = MagicMock()
        client.summarize_metrics_data.side_effect = _svc_err(404)
        with patch("time.sleep"):
            with pytest.raises(ServiceError) as exc_info:
                self._call(client)
        assert exc_info.value.status == 404
        assert client.summarize_metrics_data.call_count == 1

    def test_exhausted_retries_raise_runtime_error(self):
        client = MagicMock()
        client.summarize_metrics_data.side_effect = _svc_err(429)
        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="retries exhausted"):
                self._call(client)
        assert client.summarize_metrics_data.call_count == _RETRY_ATTEMPTS

    def test_generic_exception_retries(self):
        client = MagicMock()
        ok = MagicMock()
        client.summarize_metrics_data.side_effect = [ValueError("boom"), ok]
        with patch("time.sleep"):
            result = self._call(client)
        assert result is ok
        assert client.summarize_metrics_data.call_count == 2


# ── Collector.poll ────────────────────────────────────────────────────────────

class TestCollectorPoll:
    def test_happy_path_sets_gauge(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        mock_gauge = MagicMock()
        with (
            patch("oci_exporter.collector._query_with_retry",
                  return_value=_mock_response(42.0)),
            patch("oci_exporter.collector.m.get_or_create", return_value=mock_gauge),
            patch("time.sleep"),
        ):
            result = collector.poll()

        assert result is True
        mock_gauge.labels.assert_called_once_with(
            compartment_id="ocid1.tenancy.oc1..test",
            resource_id="r1",
        )
        mock_gauge.labels.return_value.set.assert_called_once_with(42.0)

    def test_missing_datapoints_skipped(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        item = MagicMock()
        item.aggregated_datapoints = []
        resp = MagicMock()
        resp.data = [item]
        mock_gauge = MagicMock()
        with (
            patch("oci_exporter.collector._query_with_retry", return_value=resp),
            patch("oci_exporter.collector.m.get_or_create", return_value=mock_gauge),
            patch("time.sleep"),
        ):
            collector.poll()

        mock_gauge.labels.assert_not_called()

    def test_error_increments_errors_total(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        mock_counter = MagicMock()
        with (
            patch("oci_exporter.collector._query_with_retry",
                  side_effect=RuntimeError("fail")),
            patch("oci_exporter.collector.m.errors_total", mock_counter),
            patch("time.sleep"),
        ):
            collector.poll()

        mock_counter.labels.assert_called_once_with(
            compartment_id="ocid1.tenancy.oc1..test",
            namespace="oci_computeagent",
            metric="cpu",
        )
        mock_counter.labels.return_value.inc.assert_called_once()

    def test_returns_false_on_error(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        with (
            patch("oci_exporter.collector._query_with_retry",
                  side_effect=RuntimeError("fail")),
            patch("oci_exporter.collector.m.errors_total"),
            patch("time.sleep"),
        ):
            result = collector.poll()
        assert result is False

    def test_returns_true_on_full_success(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        with (
            patch("oci_exporter.collector._query_with_retry",
                  return_value=_mock_response()),
            patch("oci_exporter.collector.m.get_or_create", return_value=MagicMock()),
            patch("time.sleep"),
        ):
            result = collector.poll()
        assert result is True

    def test_rate_limit_sleep_called(self):
        # min_interval = 60 / 1 query * 0.8 = 48s; elapsed ≈ 0 → sleep(≈48)
        cfg = _make_config(polling_frequency_seconds=60)
        collector = _mock_collector(cfg)
        with (
            patch("oci_exporter.collector._query_with_retry",
                  return_value=_mock_response()),
            patch("oci_exporter.collector.m.get_or_create", return_value=MagicMock()),
            patch("time.sleep") as mock_sleep,
        ):
            collector.poll()

        mock_sleep.assert_called_once()
        sleep_arg = mock_sleep.call_args[0][0]
        assert 47.0 < sleep_arg <= 48.0


# ── Collector._cleanup_stale ──────────────────────────────────────────────────

class TestCleanupStale:
    def test_stale_label_removed(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        now = time.time()
        threshold = _STALE_CYCLES * cfg.polling_frequency_seconds
        key = ("ns", "cpu", "compartment", "r1")
        collector._last_seen[key] = now - threshold - 1

        with patch("oci_exporter.collector.m.remove_label") as mock_rm:
            collector._cleanup_stale(now)

        mock_rm.assert_called_once_with("ns", "cpu", "compartment", "r1")
        assert key not in collector._last_seen

    def test_fresh_label_kept(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        now = time.time()
        threshold = _STALE_CYCLES * cfg.polling_frequency_seconds
        key = ("ns", "cpu", "compartment", "r1")
        collector._last_seen[key] = now - threshold + 1

        with patch("oci_exporter.collector.m.remove_label") as mock_rm:
            collector._cleanup_stale(now)

        mock_rm.assert_not_called()
        assert key in collector._last_seen

    def test_threshold_is_three_cycles(self):
        cfg = _make_config()
        collector = _mock_collector(cfg)
        now = time.time()
        threshold = _STALE_CYCLES * cfg.polling_frequency_seconds
        key = ("ns", "cpu", "compartment", "r1")

        collector._last_seen[key] = now - threshold - 0.001
        with patch("oci_exporter.collector.m.remove_label") as mock_rm:
            collector._cleanup_stale(now)
        mock_rm.assert_called_once()

        collector._last_seen[key] = now - threshold + 0.001
        with patch("oci_exporter.collector.m.remove_label") as mock_rm:
            collector._cleanup_stale(now)
        mock_rm.assert_not_called()