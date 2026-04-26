"""Entry point: wire config, collector, and HTTP server together."""

from __future__ import annotations

import argparse
import logging
import threading
import time

from . import metrics as m
from .collector import Collector
from .config import load
from . import server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger(__name__)


def _collector_loop(collector: Collector) -> None:
    freq = collector._cfg.polling_frequency_seconds
    while True:
        t0 = time.time()
        m.last_timestamp.set(t0)
        try:
            success = collector.poll()
        except Exception as exc:
            log.error("Fatal poll error: %s", exc)
            success = False

        elapsed = time.time() - t0
        m.scrape_duration.set(elapsed)
        m.up.set(1 if success else 0)
        if success:
            m.last_success.set(t0)
        server.record_poll(success)

        remaining = freq - elapsed
        if remaining > 0:
            time.sleep(remaining)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prometheus exporter for Oracle Cloud Infrastructure metrics"
    )
    parser.add_argument(
        "--config",
        default="/etc/oci-exporter/config.yaml",
        metavar="PATH",
        help="Config file path (default: /etc/oci-exporter/config.yaml)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9090,
        help="HTTP listen port (default: 9090)",
    )
    args = parser.parse_args()

    cfg = load(args.config)
    collector = Collector(cfg)

    threading.Thread(target=_collector_loop, args=(collector,), daemon=True).start()
    server.start(port=args.port)


if __name__ == "__main__":
    main()
