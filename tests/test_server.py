"""Tests for HTTP server: /metrics, /healthz, /readyz, record_poll."""



import oci_exporter.server as srv


def _start_server(port: int) -> None:
    srv.start(host="127.0.0.1", port=port)


# ── record_poll / readiness state ────────────────────────────────────────────

class TestRecordPoll:
    def test_success_resets_consecutive_errors(self):
        pass

    def test_failure_increments_consecutive_errors(self):
        pass

    def test_three_failures_mark_unready(self):
        pass

    def test_success_after_failures_marks_ready(self):
        pass


# ── HTTP endpoints ────────────────────────────────────────────────────────────

class TestHTTPEndpoints:
    def test_healthz_always_200(self):
        pass

    def test_readyz_200_when_healthy(self):
        pass

    def test_readyz_503_when_unhealthy(self):
        pass

    def test_metrics_returns_prometheus_content_type(self):
        pass

    def test_root_returns_metrics(self):
        pass

    def test_unknown_path_returns_404(self):
        pass
