# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml .
# Install only runtime deps into a prefix we can copy cleanly
RUN pip install --no-cache-dir --prefix=/install \
    "oci>=2.100.0" \
    "prometheus-client>=0.19.0" \
    "pyyaml>=6.0"

# ── runtime image ────────────────────────────────────────────────────────────
FROM python:3.11-slim

RUN useradd -r -u 10001 -s /bin/false exporter

COPY --from=builder /install /usr/local
COPY oci_exporter/ /app/oci_exporter/

WORKDIR /app
USER exporter
EXPOSE 9090

ENTRYPOINT ["python", "-m", "oci_exporter"]
