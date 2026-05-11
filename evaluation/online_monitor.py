"""Online monitoring for production evaluation and drift detection."""

from collections import deque
from datetime import datetime
from typing import Deque, List, Optional

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class MonitorMetrics(BaseModel):
    """Real-time monitoring metrics."""

    total_queries: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0
    avg_feedback_score: float = 0.0
    window_start: datetime = Field(default_factory=datetime.utcnow)


class DriftAlert(BaseModel):
    """Alert for detected drift."""

    metric: str
    current_value: float
    baseline_value: float
    deviation: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: str = "warning"


class OnlineMonitor:
    """Monitors production metrics and detects drift.

    Tracks:
    - Latency percentiles
    - Error rates
    - Cache hit rates
    - User feedback scores
    - Response quality drift
    """

    def __init__(
        self,
        window_size: int = 1000,
        alert_threshold: float = 0.2,
    ):
        """Initialize online monitor.

        Args:
            window_size: Number of recent queries to track.
            alert_threshold: Deviation threshold for alerts.
        """
        self.window_size = window_size
        self.alert_threshold = alert_threshold
        self._latencies: Deque[float] = deque(maxlen=window_size)
        self._feedback_scores: Deque[float] = deque(maxlen=window_size)
        self._errors: int = 0
        self._cache_hits: int = 0
        self._total_queries: int = 0
        self._baseline_metrics: Optional[MonitorMetrics] = None
        logger.info(
            "Initialized online monitor",
            window_size=window_size,
            alert_threshold=alert_threshold,
        )

    def set_baseline(self, metrics: MonitorMetrics):
        """Set baseline metrics for drift detection.

        Args:
            metrics: Baseline metrics from offline evaluation.
        """
        self._baseline_metrics = metrics
        logger.info("Baseline metrics set", avg_latency=metrics.avg_latency_ms)

    def record_query(
        self,
        latency_ms: float,
        is_error: bool = False,
        is_cache_hit: bool = False,
    ):
        """Record a query execution.

        Args:
            latency_ms: Query latency in milliseconds.
            is_error: Whether the query resulted in an error.
            is_cache_hit: Whether the query was a cache hit.
        """
        self._latencies.append(latency_ms)
        self._total_queries += 1

        if is_error:
            self._errors += 1
        if is_cache_hit:
            self._cache_hits += 1

    def record_feedback(self, score: float):
        """Record user feedback score.

        Args:
            score: Feedback score (1-5).
        """
        self._feedback_scores.append(score)

    def get_current_metrics(self) -> MonitorMetrics:
        """Get current monitoring metrics.

        Returns:
            Current MonitorMetrics.
        """
        latencies = list(self._latencies)
        feedback = list(self._feedback_scores)

        if not latencies:
            return MonitorMetrics()

        sorted_latencies = sorted(latencies)
        p95_idx = int(len(sorted_latencies) * 0.95)
        p99_idx = int(len(sorted_latencies) * 0.99)

        return MonitorMetrics(
            total_queries=self._total_queries,
            avg_latency_ms=sum(latencies) / len(latencies),
            p95_latency_ms=sorted_latencies[p95_idx] if sorted_latencies else 0,
            p99_latency_ms=sorted_latencies[p99_idx] if sorted_latencies else 0,
            error_rate=self._errors / max(self._total_queries, 1),
            cache_hit_rate=self._cache_hits / max(self._total_queries, 1),
            avg_feedback_score=sum(feedback) / len(feedback) if feedback else 0,
        )

    def check_drift(self) -> List[DriftAlert]:
        """Check for metric drift from baseline.

        Returns:
            List of drift alerts.
        """
        if not self._baseline_metrics:
            return []

        alerts = []
        current = self.get_current_metrics()

        # Check latency drift
        if self._baseline_metrics.avg_latency_ms > 0:
            latency_deviation = abs(
                current.avg_latency_ms - self._baseline_metrics.avg_latency_ms
            ) / self._baseline_metrics.avg_latency_ms

            if latency_deviation > self.alert_threshold:
                alerts.append(DriftAlert(
                    metric="latency",
                    current_value=current.avg_latency_ms,
                    baseline_value=self._baseline_metrics.avg_latency_ms,
                    deviation=latency_deviation,
                    severity="critical" if latency_deviation > 0.5 else "warning",
                ))

        # Check error rate drift
        if current.error_rate > 0.1:  # More than 10% errors
            alerts.append(DriftAlert(
                metric="error_rate",
                current_value=current.error_rate,
                baseline_value=self._baseline_metrics.error_rate,
                deviation=current.error_rate,
                severity="critical",
            ))

        # Check feedback score drift
        if (
            self._baseline_metrics.avg_feedback_score > 0
            and len(self._feedback_scores) > 10
        ):
            feedback_deviation = abs(
                current.avg_feedback_score - self._baseline_metrics.avg_feedback_score
            ) / max(self._baseline_metrics.avg_feedback_score, 0.1)

            if feedback_deviation > self.alert_threshold:
                alerts.append(DriftAlert(
                    metric="feedback_score",
                    current_value=current.avg_feedback_score,
                    baseline_value=self._baseline_metrics.avg_feedback_score,
                    deviation=feedback_deviation,
                ))

        if alerts:
            logger.warning(
                "Drift detected",
                num_alerts=len(alerts),
                alerts=[a.metric for a in alerts],
            )

        return alerts

    def reset(self):
        """Reset monitoring state."""
        self._latencies.clear()
        self._feedback_scores.clear()
        self._errors = 0
        self._cache_hits = 0
        self._total_queries = 0
        logger.info("Monitor state reset")


# Singleton instance
online_monitor = OnlineMonitor()
