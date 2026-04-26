"""Tests for Prometheus registry and gauge management."""

from oci_exporter import metrics as m

# ── get_or_create ─────────────────────────────────────────────────────────────

class TestGetOrCreate:
    def test_same_key_returns_same_gauge(self):
        g1 = m.get_or_create("oci_tst_ns_a", "metric_a")
        g2 = m.get_or_create("oci_tst_ns_a", "metric_a")
        assert g1 is g2

    def test_different_keys_return_different_gauges(self):
        g1 = m.get_or_create("oci_tst_ns_b", "metric_x")
        g2 = m.get_or_create("oci_tst_ns_b", "metric_y")
        assert g1 is not g2

    def test_gauge_registered_to_custom_registry(self):
        from prometheus_client import generate_latest
        m.get_or_create("oci_tst_ns_c", "metric_c")
        output = generate_latest(m.REGISTRY).decode()
        assert "oci_tst_ns_c_metric_c" in output


# ── remove_label ──────────────────────────────────────────────────────────────

class TestRemoveLabel:
    def test_removes_existing_label_set(self):
        g = m.get_or_create("oci_tst_ns_d", "metric_d")
        g.labels(compartment_id="cid1", resource_id="rid1").set(1.0)
        m.remove_label("oci_tst_ns_d", "metric_d", "cid1", "rid1")

    def test_no_error_when_gauge_not_found(self):
        m.remove_label("no_such_ns", "no_such_metric", "cid", "rid")

    def test_no_error_when_label_set_not_found(self):
        m.get_or_create("oci_tst_ns_e", "metric_e")
        m.remove_label("oci_tst_ns_e", "metric_e", "no_cid", "no_rid")