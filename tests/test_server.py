"""Tests for HTTP server: /metrics, /healthz, /readyz, record_poll."""

import http.client
import socket
import threading
import time

import pytest

import oci_exporter.server as srv


def _find_free_port() -> int:
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(autouse=True)
def clean_state():
    with srv._lock:
        srv._consecutive_errors = 0
    yield
    with srv._lock:
        srv._consecutive_errors = 0


@pytest.fixture()
def server_port():
    port = _find_free_port()
    t = threading.Thread(
        target=srv.start, kwargs={"host": "127.0.0.1", "port": port}, daemon=True
    )
    t.start()
    time.sleep(0.05)
    return port


# ── record_poll / readiness state ────────────────────────────────────────────

class TestRecordPoll:
    def test_success_resets_consecutive_errors(self):
        srv.record_poll(False)
        srv.record_poll(True)
        with srv._lock:
            assert srv._consecutive_errors == 0

    def test_failure_increments_consecutive_errors(self):
        srv.record_poll(False)
        srv.record_poll(False)
        with srv._lock:
            assert srv._consecutive_errors == 2

    def test_three_failures_mark_unready(self):
        for _ in range(srv._UNHEALTHY_THRESHOLD):
            srv.record_poll(False)
        with srv._lock:
            assert srv._consecutive_errors == srv._UNHEALTHY_THRESHOLD

    def test_success_after_failures_marks_ready(self):
        for _ in range(5):
            srv.record_poll(False)
        srv.record_poll(True)
        with srv._lock:
            assert srv._consecutive_errors == 0


# ── HTTP endpoints ────────────────────────────────────────────────────────────

class TestHTTPEndpoints:
    def _get(self, port: int, path: str) -> http.client.HTTPResponse:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        conn.request("GET", path)
        return conn.getresponse()

    def test_healthz_always_200(self, server_port):
        resp = self._get(server_port, "/healthz")
        assert resp.status == 200
        assert resp.read() == b"ok"

    def test_readyz_200_when_healthy(self, server_port):
        resp = self._get(server_port, "/readyz")
        assert resp.status == 200

    def test_readyz_503_when_unhealthy(self, server_port):
        for _ in range(srv._UNHEALTHY_THRESHOLD):
            srv.record_poll(False)
        resp = self._get(server_port, "/readyz")
        assert resp.status == 503

    def test_metrics_returns_prometheus_content_type(self, server_port):
        resp = self._get(server_port, "/metrics")
        assert resp.status == 200
        assert "text/plain" in (resp.getheader("Content-Type") or "")

    def test_root_returns_metrics(self, server_port):
        resp = self._get(server_port, "/")
        assert resp.status == 200

    def test_unknown_path_returns_404(self, server_port):
        resp = self._get(server_port, "/nonexistent")
        assert resp.status == 404