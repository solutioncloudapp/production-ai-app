"""Tests for evaluation layer."""

from unittest.mock import MagicMock, patch

import pytest

from evaluation.offline_eval import OfflineEvaluator
from evaluation.online_monitor import MonitorMetrics, OnlineMonitor


class TestOfflineEvaluator:
    """Tests for OfflineEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return OfflineEvaluator()

    def test_load_dataset(self, evaluator):
        count = evaluator.load_dataset("evaluation/golden_dataset.json")
        assert count > 0
        assert len(evaluator._dataset) == count

    @pytest.mark.asyncio
    async def test_evaluate_case(self, evaluator):
        evaluator.load_dataset("evaluation/golden_dataset.json")

        case = evaluator._dataset[0]

        with patch.object(evaluator, "_get_answer") as mock_answer:
            mock_answer.return_value = "Mock answer"

            with patch.object(evaluator, "_score_relevance") as mock_rel:
                mock_rel.return_value = 4.0

                with patch.object(evaluator, "_score_faithfulness") as mock_faith:
                    mock_faith.return_value = 4.0

                    with patch.object(evaluator, "_score_answer_relevance") as mock_ans:
                        mock_ans.return_value = 4.0

                        result = await evaluator._evaluate_case(case)

                        assert result.query == case["query"]
                        assert result.relevance_score == 4.0
                        assert result.faithfulness_score == 4.0

    @pytest.mark.asyncio
    async def test_evaluate_subset_by_category(self, evaluator):
        evaluator.load_dataset("evaluation/golden_dataset.json")

        with patch.object(evaluator, "_evaluate_case") as mock_eval:
            mock_eval.return_value = MagicMock(
                query="test",
                expected_answer="test",
                actual_answer="test",
                relevance_score=4.0,
                faithfulness_score=4.0,
                answer_relevance_score=4.0,
                latency_ms=100.0,
            )

            _results, _metrics = await evaluator.evaluate_subset(category="factual")

            assert mock_eval.call_count == sum(1 for c in evaluator._dataset if c.get("category") == "factual")

    @pytest.mark.asyncio
    async def test_evaluate_subset_by_difficulty(self, evaluator):
        evaluator.load_dataset("evaluation/golden_dataset.json")

        with patch.object(evaluator, "_evaluate_case") as mock_eval:
            mock_eval.return_value = MagicMock(
                query="test",
                expected_answer="test",
                actual_answer="test",
                relevance_score=4.0,
                faithfulness_score=4.0,
                answer_relevance_score=4.0,
                latency_ms=100.0,
            )

            _results, _metrics = await evaluator.evaluate_subset(difficulty="easy")

            assert mock_eval.call_count == sum(1 for c in evaluator._dataset if c.get("difficulty") == "easy")

    def test_compute_metrics(self, evaluator):
        from app.models import EvalResult

        results = [
            EvalResult(
                query="q1",
                expected_answer="a1",
                actual_answer="a1",
                relevance_score=4.0,
                faithfulness_score=4.0,
                answer_relevance_score=4.0,
                latency_ms=100.0,
            ),
            EvalResult(
                query="q2",
                expected_answer="a2",
                actual_answer="a2",
                relevance_score=3.0,
                faithfulness_score=3.0,
                answer_relevance_score=3.0,
                latency_ms=200.0,
            ),
        ]

        metrics = evaluator._compute_metrics(results)

        assert metrics.total_tests == 2
        assert metrics.passed_tests == 2  # Both >= 3.0
        assert metrics.avg_relevance == 3.5
        assert metrics.avg_latency_ms == 150.0

    def test_compute_metrics_empty(self, evaluator):
        metrics = evaluator._compute_metrics([])
        assert metrics.total_tests == 0
        assert metrics.pass_rate == 0


class TestOnlineMonitor:
    """Tests for OnlineMonitor."""

    @pytest.fixture
    def monitor(self):
        return OnlineMonitor(window_size=100)

    def test_record_query(self, monitor):
        monitor.record_query(latency_ms=150.0)
        assert monitor._total_queries == 1
        assert len(monitor._latencies) == 1

    def test_record_query_error(self, monitor):
        monitor.record_query(latency_ms=150.0, is_error=True)
        assert monitor._errors == 1

    def test_record_query_cache_hit(self, monitor):
        monitor.record_query(latency_ms=150.0, is_cache_hit=True)
        assert monitor._cache_hits == 1

    def test_record_feedback(self, monitor):
        monitor.record_feedback(4.5)
        assert len(monitor._feedback_scores) == 1

    def test_get_current_metrics_empty(self, monitor):
        metrics = monitor.get_current_metrics()
        assert metrics.total_queries == 0
        assert metrics.avg_latency_ms == 0.0

    def test_get_current_metrics(self, monitor):
        for i in range(10):
            monitor.record_query(latency_ms=100.0 + i * 10)

        metrics = monitor.get_current_metrics()
        assert metrics.total_queries == 10
        assert metrics.avg_latency_ms == pytest.approx(145.0)

    def test_get_current_metrics_percentiles(self, monitor):
        for i in range(100):
            monitor.record_query(latency_ms=float(i))

        metrics = monitor.get_current_metrics()
        assert metrics.p95_latency_ms >= metrics.avg_latency_ms
        assert metrics.p99_latency_ms >= metrics.p95_latency_ms

    def test_get_current_metrics_error_rate(self, monitor):
        monitor.record_query(latency_ms=100.0, is_error=False)
        monitor.record_query(latency_ms=100.0, is_error=True)

        metrics = monitor.get_current_metrics()
        assert metrics.error_rate == pytest.approx(0.5)

    def test_get_current_metrics_cache_hit_rate(self, monitor):
        monitor.record_query(latency_ms=100.0, is_cache_hit=True)
        monitor.record_query(latency_ms=100.0, is_cache_hit=False)
        monitor.record_query(latency_ms=100.0, is_cache_hit=True)

        metrics = monitor.get_current_metrics()
        assert metrics.cache_hit_rate == pytest.approx(2 / 3)

    def test_set_baseline(self, monitor):
        baseline = MonitorMetrics(avg_latency_ms=200.0, error_rate=0.05)
        monitor.set_baseline(baseline)
        assert monitor._baseline_metrics == baseline

    def test_check_drift_no_baseline(self, monitor):
        alerts = monitor.check_drift()
        assert alerts == []

    def test_check_drift_latency(self, monitor):
        baseline = MonitorMetrics(avg_latency_ms=100.0, error_rate=0.01, avg_feedback_score=4.0)
        monitor.set_baseline(baseline)

        # Record much higher latencies
        for _ in range(20):
            monitor.record_query(latency_ms=500.0)

        alerts = monitor.check_drift()
        latency_alerts = [a for a in alerts if a.metric == "latency"]
        assert len(latency_alerts) == 1

    def test_check_drift_error_rate(self, monitor):
        baseline = MonitorMetrics(avg_latency_ms=100.0, error_rate=0.01, avg_feedback_score=4.0)
        monitor.set_baseline(baseline)

        # Record many errors
        for _ in range(20):
            monitor.record_query(latency_ms=100.0, is_error=True)

        alerts = monitor.check_drift()
        error_alerts = [a for a in alerts if a.metric == "error_rate"]
        assert len(error_alerts) == 1

    def test_check_drift_feedback(self, monitor):
        baseline = MonitorMetrics(avg_latency_ms=100.0, error_rate=0.01, avg_feedback_score=4.5)
        monitor.set_baseline(baseline)

        # Record low feedback scores
        for _ in range(15):
            monitor.record_query(latency_ms=100.0)
            monitor.record_feedback(1.0)

        alerts = monitor.check_drift()
        feedback_alerts = [a for a in alerts if a.metric == "feedback_score"]
        assert len(feedback_alerts) == 1

    def test_reset(self, monitor):
        monitor.record_query(latency_ms=100.0, is_error=True, is_cache_hit=True)
        monitor.record_feedback(4.0)
        monitor.reset()

        assert monitor._total_queries == 0
        assert monitor._errors == 0
        assert monitor._cache_hits == 0
        assert len(monitor._feedback_scores) == 0
