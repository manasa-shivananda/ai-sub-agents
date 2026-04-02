"""Tests for the tracer -- pure logic, no mocks needed."""

import time

from src.tracer import PRICING, Tracer


class TestTracer:
    def test_record_dispatch_and_success(self):
        t = Tracer()
        t.record_dispatch("job_analyzer")
        t.record_tokens("job_analyzer", "claude-haiku-4-5-20251001", 1000, 500)
        t.record_success("job_analyzer", 2.0)

        trace = t.build_trace()
        assert trace.agents_succeeded == 1
        assert trace.agents_failed == 0
        assert trace.total_tokens == 1500

    def test_record_retry(self):
        t = Tracer()
        t.record_dispatch("company_researcher")
        t.record_retry("company_researcher", "rate limited")

        trace = t.build_trace()
        assert trace.retries_used == 1

    def test_record_failure(self):
        t = Tracer()
        t.record_dispatch("gap_analyzer")
        t.record_failure("gap_analyzer", "timeout", 30.0)

        trace = t.build_trace()
        assert trace.agents_failed == 1
        assert trace.agents_succeeded == 0

    def test_cost_estimation(self):
        t = Tracer()
        t.record_dispatch("job_analyzer")
        t.record_tokens("job_analyzer", "claude-haiku-4-5-20251001", 1000, 500)
        t.record_success("job_analyzer", 1.0)

        trace = t.build_trace()
        # Haiku: 1000 * 0.80/1M + 500 * 4.00/1M = 0.0008 + 0.002 = 0.0028
        assert trace.total_cost_usd == pytest.approx(0.0028, abs=0.0001)

    def test_parallel_detection(self):
        """Two dispatches at the same time should both appear in the trace."""
        t = Tracer()
        t.record_dispatch("gap_analyzer")
        t.record_dispatch("company_researcher")

        dispatches = [e for e in t._entries if e.status == "dispatched"]
        assert len(dispatches) == 2
        # Both should have the same timestamp (same monotonic moment)
        assert dispatches[0].timestamp_s == dispatches[1].timestamp_s

    def test_multiple_agents_full_flow(self):
        t = Tracer()

        # Agent 1: success
        t.record_dispatch("job_analyzer")
        t.record_tokens("job_analyzer", "claude-haiku-4-5-20251001", 1000, 500)
        t.record_success("job_analyzer", 2.0)

        # Agent 2: retry then success
        t.record_dispatch("company_researcher")
        t.record_retry("company_researcher", "error")
        t.record_tokens("company_researcher", "claude-sonnet-4-6", 400, 600)
        t.record_success("company_researcher", 3.0)

        # Agent 3: failure
        t.record_dispatch("gap_analyzer")
        t.record_failure("gap_analyzer", "timeout", 30.0)

        trace = t.build_trace()
        assert trace.agents_succeeded == 2
        assert trace.agents_failed == 1
        assert trace.retries_used == 1
        assert trace.total_tokens == 2500  # 1500 + 1000 (only from successes)


class TestPricing:
    def test_pricing_has_haiku(self):
        assert "claude-haiku-4-5-20251001" in PRICING

    def test_pricing_has_sonnet(self):
        assert "claude-sonnet-4-6" in PRICING

    def test_pricing_values_positive(self):
        for model, prices in PRICING.items():
            assert prices["input"] > 0, f"{model} input price should be positive"
            assert prices["output"] > 0, f"{model} output price should be positive"


# Need this import for pytest.approx
import pytest
