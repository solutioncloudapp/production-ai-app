"""Tests for observability layer."""

import pytest

from observability.cost_tracker import CostTracker
from observability.feedback import FeedbackCollector
from observability.tracer import Tracer


class TestTracer:
    """Tests for Tracer."""

    @pytest.fixture
    def tracer(self):
        t = Tracer()
        t.clear()
        return t

    def test_start_span(self, tracer):
        with tracer.start_span("test_operation") as span:
            assert span.name == "test_operation"
            assert span.trace_id is not None
            assert span.span_id is not None

    def test_span_attributes(self, tracer):
        with tracer.start_span("test_operation") as span:
            span.set_attribute("key", "value")
            span.set_attribute("count", 42)

        assert span.attributes["key"] == "value"
        assert span.attributes["count"] == 42

    def test_span_duration(self, tracer):
        with tracer.start_span("test_operation") as span:
            pass  # End immediately

        assert span.duration_ms >= 0

    def test_span_error_status(self, tracer):
        try:
            with tracer.start_span("test_operation") as span:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert span.status == "error"
        assert "Test error" in span.attributes.get("error", "")

    def test_span_ok_status(self, tracer):
        with tracer.start_span("test_operation") as span:
            pass

        assert span.status == "ok"

    def test_export_trace(self, tracer):
        with tracer.start_span("test_operation") as span:
            span.set_attribute("key", "value")

        trace_id = span.trace_id
        exported = tracer.export_trace(trace_id)

        assert len(exported) == 1
        assert exported[0]["name"] == "test_operation"

    def test_get_traces(self, tracer):
        with tracer.start_span("op1") as span1:
            pass
        with tracer.start_span("op2") as span2:
            pass

        tracer.export_trace(span1.trace_id)
        tracer.export_trace(span2.trace_id)

        traces = tracer.get_traces()
        assert len(traces) == 2

    def test_set_trace_id(self, tracer):
        tracer.set_trace_id("custom-trace-123")
        assert tracer.get_current_trace_id() == "custom-trace-123"

    def test_to_dict(self, tracer):
        with tracer.start_span("test") as span:
            span.set_attribute("key", "value")

        d = span.to_dict()
        assert "trace_id" in d
        assert "span_id" in d
        assert "name" in d
        assert "duration_ms" in d
        assert "attributes" in d


class TestFeedbackCollector:
    """Tests for FeedbackCollector."""

    @pytest.fixture
    def collector(self):
        return FeedbackCollector()

    def test_record_feedback(self, collector):
        record = collector.record("trace-1", 5, "Great response!")
        assert record.trace_id == "trace-1"
        assert record.rating == 5
        assert record.comment == "Great response!"

    def test_get_feedback(self, collector):
        collector.record("trace-1", 4)
        record = collector.get_feedback("trace-1")
        assert record is not None
        assert record.rating == 4

    def test_get_nonexistent_feedback(self, collector):
        record = collector.get_feedback("nonexistent")
        assert record is None

    def test_get_all_feedback(self, collector):
        collector.record("trace-1", 5)
        collector.record("trace-2", 3)
        collector.record("trace-3", 4)

        all_feedback = collector.get_all_feedback()
        assert len(all_feedback) == 3

    def test_get_stats(self, collector):
        collector.record("trace-1", 5)
        collector.record("trace-2", 3)
        collector.record("trace-3", 4)

        stats = collector.get_stats()
        assert stats["total"] == 3
        assert stats["avg_rating"] == 4.0
        assert 5 in stats["rating_distribution"]

    def test_get_stats_empty(self, collector):
        stats = collector.get_stats()
        assert stats["total"] == 0
        assert stats["avg_rating"] == 0

    def test_get_low_rated(self, collector):
        collector.record("trace-1", 5)
        collector.record("trace-2", 2)
        collector.record("trace-3", 1)
        collector.record("trace-4", 4)

        low_rated = collector.get_low_rated(threshold=3)
        assert len(low_rated) == 2
        assert all(r.rating < 3 for r in low_rated)

    def test_export_for_finetuning(self, collector):
        collector.record("trace-1", 5, "Excellent")
        collector.record("trace-2", 2, "Bad")
        collector.record("trace-3", 4, "Good")

        exported = collector.export_for_finetuning()
        assert len(exported) == 2  # Only ratings >= 4
        assert all(e["rating"] >= 4 for e in exported)

    def test_get_trend(self, collector):
        collector.record("trace-1", 5)
        collector.record("trace-2", 4)

        trend = collector.get_trend(window_hours=24)
        assert len(trend) >= 1
        assert "hour" in trend[0]
        assert "count" in trend[0]
        assert "avg_rating" in trend[0]


class TestCostTracker:
    """Tests for CostTracker."""

    @pytest.fixture
    def tracker(self):
        return CostTracker(budget_limit=100.0)

    def test_record_cost(self, tracker):
        record = tracker.record(
            conversation_id="conv-1",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=500,
        )
        assert record.model == "gpt-4o"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.cost_usd > 0

    def test_record_cost_unknown_model(self, tracker):
        record = tracker.record(
            conversation_id="conv-1",
            model="unknown-model",
            input_tokens=1000,
            output_tokens=500,
        )
        assert record.cost_usd > 0  # Uses default pricing

    def test_get_conversation_cost(self, tracker):
        tracker.record("conv-1", "gpt-4o", 1000, 500)
        tracker.record("conv-1", "gpt-4o", 2000, 1000)

        cost = tracker.get_conversation_cost("conv-1")
        assert cost > 0

    def test_get_conversation_cost_nonexistent(self, tracker):
        cost = tracker.get_conversation_cost("nonexistent")
        assert cost == 0.0

    def test_get_daily_cost(self, tracker):
        tracker.record("conv-1", "gpt-4o", 1000, 500)
        daily = tracker.get_daily_cost()
        assert daily > 0

    def test_get_model_breakdown(self, tracker):
        tracker.record("conv-1", "gpt-4o", 1000, 500)
        tracker.record("conv-2", "gpt-4o-mini", 2000, 1000)

        breakdown = tracker.get_model_breakdown()
        assert "gpt-4o" in breakdown
        assert "gpt-4o-mini" in breakdown
        assert breakdown["gpt-4o"]["queries"] == 1

    def test_get_budget_status(self, tracker):
        tracker.record("conv-1", "gpt-4o", 1000, 500)

        status = tracker.get_budget_status()
        assert "daily_cost" in status
        assert "budget_limit" in status
        assert "remaining" in status
        assert "utilization_pct" in status
        assert status["budget_limit"] == 100.0

    def test_budget_warning(self, tracker, caplog):
        tracker.budget_limit = 0.00001  # Very low limit
        tracker.record("conv-1", "gpt-4o", 1000000, 500000)

        status = tracker.get_budget_status()
        assert status["daily_cost"] > status["budget_limit"]

    def test_reset(self, tracker):
        tracker.record("conv-1", "gpt-4o", 1000, 500)
        tracker.reset()

        assert tracker.get_daily_cost() == 0.0
        assert tracker.get_conversation_cost("conv-1") == 0.0
