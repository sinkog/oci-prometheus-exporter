"""HTTP server exposing /metrics, /healthz, and /readyz."""

from __future__ import annotations

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from . import metrics as m

log = logging.getLogger(__name__)

_UNHEALTHY_THRESHOLD = 3
_consecutive_errors = 0
_lock = threading.Lock()


def record_poll(success: bool) -> None:
    global _consecutive_errors
    with _lock:
        _consecutive_errors = 0 if success else _consecutive_errors + 1


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # silence access log
        pass

    def _send(
        self, code: int, body: bytes, content_type: str = "text/plain; charset=utf-8"
    ) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/healthz":
            self._send(200, b"ok")
        elif self.path == "/readyz":
            with _lock:
                errs = _consecutive_errors
            if errs < _UNHEALTHY_THRESHOLD:
                self._send(200, b"ok")
            else:
                self._send(503, f"unhealthy: {errs} consecutive poll errors\n".encode())
        elif self.path in ("/metrics", "/"):
            self._send(200, generate_latest(m.REGISTRY), CONTENT_TYPE_LATEST)
        else:
            self._send(404, b"not found\n")


def start(host: str = "", port: int = 9090) -> None:
    log.info("Listening on %s:%d", host or "0.0.0.0", port)
    HTTPServer((host, port), _Handler).serve_forever()
