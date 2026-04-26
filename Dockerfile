# syntax=docker/dockerfile:1
FROM python@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2 AS builder

WORKDIR /build
COPY pyproject.toml .
COPY oci_exporter/ ./oci_exporter/
RUN pip install --no-cache-dir --prefix=/install .

# ── runtime image ────────────────────────────────────────────────────────────
FROM python@sha256:6d85378d88a19cd4d76079817532d62232be95757cb45945a99fec8e8084b9c2

RUN useradd -r -u 10001 -s /bin/false exporter

COPY --from=builder /install /usr/local

WORKDIR /app
USER exporter
EXPOSE 9090

ENTRYPOINT ["oci-exporter"]