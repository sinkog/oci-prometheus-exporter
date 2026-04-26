"""Tests for config loading and validation."""

import textwrap
import pytest
from pathlib import Path

from oci_exporter.config import load


def _write(tmp_path: Path, content: str) -> str:
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(content))
    return str(p)


def test_minimal_config(tmp_path):
    path = _write(tmp_path, """
        compartmentId: ocid1.tenancy.oc1..example
        region: eu-frankfurt-2
        namespaces:
          - name: oci_computeagent
            metrics:
              - name: cpu_utilization
                query: "CpuUtilization[1m].mean()"
    """)
    cfg = load(path)
    assert cfg.region == "eu-frankfurt-2"
    assert len(cfg.compartment_ids) == 1
    assert len(cfg.namespaces) == 1
    assert cfg.namespaces[0].metrics[0].name == "cpu_utilization"


def test_backward_compat_single_compartment_id(tmp_path):
    path = _write(tmp_path, """
        compartmentId: ocid1.tenancy.oc1..example
        region: eu-frankfurt-2
        namespaces: []
    """)
    cfg = load(path)
    assert cfg.compartment_ids == ("ocid1.tenancy.oc1..example",)


def test_multiple_compartments(tmp_path):
    path = _write(tmp_path, """
        compartmentIds:
          - ocid1.tenancy.oc1..aaa
          - ocid1.compartment.oc1..bbb
        region: eu-frankfurt-2
        namespaces: []
    """)
    cfg = load(path)
    assert len(cfg.compartment_ids) == 2


def test_missing_region_exits(tmp_path):
    path = _write(tmp_path, """
        compartmentId: ocid1.tenancy.oc1..example
        namespaces: []
    """)
    with pytest.raises(SystemExit):
        load(path)


def test_missing_compartment_exits(tmp_path):
    path = _write(tmp_path, """
        region: eu-frankfurt-2
        namespaces: []
    """)
    with pytest.raises(SystemExit):
        load(path)


def test_prom_name_sanitization():
    from oci_exporter.metrics import _prom_name
    assert _prom_name("oci_computeagent", "cpu_utilization") == "oci_computeagent_cpu_utilization"
    assert _prom_name("oci_vcn", "vnic_bytes_in") == "oci_vcn_vnic_bytes_in"
    # namespace without oci_ prefix gets it prepended
    assert _prom_name("custom_ns", "my-metric") == "oci_custom_ns_my_metric"
    # special chars sanitized
    assert _prom_name("oci_ns", "value/rate") == "oci_ns_value_rate"


def test_total_queries(tmp_path):
    path = _write(tmp_path, """
        compartmentIds:
          - ocid1.tenancy.oc1..aaa
          - ocid1.tenancy.oc1..bbb
        region: eu-frankfurt-2
        namespaces:
          - name: oci_computeagent
            metrics:
              - name: cpu
                query: "CpuUtilization[1m].mean()"
              - name: mem
                query: "MemoryUtilization[1m].mean()"
    """)
    cfg = load(path)
    # 2 compartments × 2 metrics = 4
    assert cfg.total_queries == 4
