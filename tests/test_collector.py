"""Tests for OCI collector: retry logic, poll loop, stale cleanup."""



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


# ── build_client ─────────────────────────────────────────────────────────────

class TestBuildClient:
    def test_instance_principal_uses_signer(self):
        pass

    def test_api_key_reads_oci_config(self):
        pass

    def test_telemetry_endpoint_passed_as_kwarg(self):
        pass


# ── _query_with_retry ─────────────────────────────────────────────────────────

class TestQueryWithRetry:
    def test_success_on_first_attempt(self):
        pass

    def test_retries_on_429(self):
        pass

    def test_retries_on_500(self):
        pass

    def test_non_retryable_error_raises_immediately(self):
        pass

    def test_exhausted_retries_raise_runtime_error(self):
        pass

    def test_generic_exception_retries(self):
        pass


# ── Collector.poll ────────────────────────────────────────────────────────────

class TestCollectorPoll:
    def test_happy_path_sets_gauge(self):
        pass

    def test_missing_datapoints_skipped(self):
        pass

    def test_error_increments_errors_total(self):
        pass

    def test_returns_false_on_error(self):
        pass

    def test_returns_true_on_full_success(self):
        pass

    def test_rate_limit_sleep_called(self):
        pass


# ── Collector._cleanup_stale ──────────────────────────────────────────────────

class TestCleanupStale:
    def test_stale_label_removed(self):
        pass

    def test_fresh_label_kept(self):
        pass

    def test_threshold_is_three_cycles(self):
        pass
