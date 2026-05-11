"""Online monitoring for production metrics and drift detection."""

from collections import deque
from datetime import datetime, timedelta
from typing import Deque, List

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class MonitoringMetrics(BaseModel):
    """Current monitoring metrics snapshot."""

    total_queries: int = 0
    cache_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    error_rate: float = 0.0
    feedback_score: float = 0.0
    queries_per_minute: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class DriftAlert(BaseModel):
    """Alert for detected performance drift."""

    alert_type: str
    severity: str
    message: str
    current_value: float
    baseline_value: float
    threshold: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class OnlineMonitor:
    """Monitors production metrics and detects performance drift.

    Features:
    - Real-time latency tracking (avg, p95, p99)
    - Cache hit rate monitoring
    - Feedback score aggregation
    - Query throughput tracking
    - Automatic drift detection with alerts
    - Sliding window metrics
    """

    def __init__(
        self,
        window_minutes: int = 15,
        latency_threshold_ms: float = 3000.0,
        cache_hit_threshold: float = 0.3,
        feedback_threshold: float = 3.0,
    ):
        """Initialize online monitor.

        Args:
            window_minutes: Sliding window for metrics.
            latency_threshold_ms: Max acceptable latency.
            cache_hit_threshold: Min acceptable cache hit rate.
            feedback_threshold: Min acceptable feedback score.
        """
        self._window_minutes = window_minutes
        self._latency_threshold_ms = latency_threshold_ms
        self._cache_hit_threshold = cache_hit_threshold
        self._feedback_threshold = feedback_threshold

        self._latencies: Deque[tuple[datetime, float]] = deque()
        self._cache_hits: Deque[tuple[datetime, bool]] = deque()
        self._feedback_scores: Deque[tuple[datetime, int]] = deque()
        self._query_timestamps: Deque[datetime] = deque()
        self._errors: Deque[datetime] = deque()

        self._baseline_latency: float = 0.0
        self._baseline_cache_hit_rate: float = 0.0
        self._baseline_feedback_score: float = 0.0

        logger.info("Initialized online monitor")

    def initialize(self):
        """Initialize online monitor."""
        logger.info("Online monitor initialized")

    def record_query(self, latency_ms: float, is_cache_hit: bool):
        """Record a query execution.

        Args:
            latency_ms: Query latency in milliseconds.
            is_cache_hit: Whether response was from cache.
        """
        now = datetime.utcnow()
        self._latencies.append((now, latency_ms))
        self._cache_hits.append((now, is_cache_hit))
        self._query_timestamps.append(now)

        self._cleanup_old_entries(now)

        logger.debug(
            "Query recorded",
            latency_ms=latency_ms,
            cache_hit=is_cache_hit,
        )

    def record_error(self):
        """Record a query error."""
        now = datetime.utcnow()
        self._errors.append(now)
        self._cleanup_old_entries(now)

    def record_feedback(self, rating: int):
        """Record user feedback.

        Args:
            rating: Feedback rating (1-5).
        """
        now = datetime.utcnow()
        self._feedback_scores.append((now, rating))
        self._cleanup_old_entries(now)

        logger.debug("Feedback recorded", rating=rating)

    def get_current_metrics(self) -> MonitoringMetrics:
        """Get current monitoring metrics.

        Returns:
            MonitoringMetrics with current values.
        """
        now = datetime.utcnow()
        self._cleanup_old_entries(now)

        total_queries = len(self._query_timestamps)

        # Latency calculations
        latency_values = [lat for _, lat in self._latencies]
        if latency_values:
            avg_latency = sum(latency_values) / len(latency_values)
            sorted_latencies = sorted(latency_values)
            p95_idx = int(len(sorted_latencies) * 0.95)
            p99_idx = int(len(sorted_latencies) * 0.99)
            p95_latency = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
            p99_latency = sorted_latencies[min(p99_idx, len(sorted_latencies) - 1)]
        else:
            avg_latency = 0.0
            p95_latency = 0.0
            p99_latency = 0.0

        # Cache hit rate
        cache_values = [hit for _, hit in self._cache_hits]
        cache_hit_rate = (
            sum(cache_values) / len(cache_values) if cache_values else 0.0
        )

        # Error rate
        error_rate = (
            len(self._errors) / total_queries if total_queries > 0 else 0.0
        )

        # Feedback score
        feedback_values = [score for _, score in self._feedback_scores]
        feedback_score = (
            sum(feedback_values) / len(feedback_values) if feedback_values else 0.0
        )

        # Queries per minute
        if self._query_timestamps:
            time_span = (now - self._query_timestamps[0]).total_seconds() / 60.0
            queries_per_minute = total_queries / time_span if time_span > 0 else 0.0
        else:
            queries_per_minute = 0.0

        return MonitoringMetrics(
            total_queries=total_queries,
            cache_hit_rate=round(cache_hit_rate, 3),
            avg_latency_ms=round(avg_latency, 2),
            p95_latency_ms=round(p95_latency, 2),
            p99_latency_ms=round(p99_latency, 2),
            error_rate=round(error_rate, 3),
            feedback_score=round(feedback_score, 2),
            queries_per_minute=round(queries_per_minute, 2),
            last_updated=now,
        )

    def check_drift(self) -> List[DriftAlert]:
        """Check for performance drift against baselines.

        Returns:
            List of DriftAlert objects if drift detected.
        """
        alerts = []
        metrics = self.get_current_metrics()

        if not self._query_timestamps:
            return alerts

        if self._baseline_latency == 0.0 and metrics.avg_latency_ms > 0:
            self._baseline_latency = metrics.avg_latency_ms
            self._baseline_cache_hit_rate = metrics.cache_hit_rate
            self._baseline_feedback_score = metrics.feedback_score
            return alerts

        alerts.extend(self._check_latency_drift(metrics))
        alerts.extend(self._check_cache_drift(metrics))
        alerts.extend(self._check_feedback_drift(metrics))
        alerts.extend(self._check_threshold_violations(metrics))

        if alerts:
            logger.warning("Drift alerts generated", count=len(alerts))

        return alerts

    def _check_latency_drift(self, metrics: MonitoringMetrics) -> List[DriftAlert]:
        """Check for latency degradation."""
        alerts = []
        if self._baseline_latency <= 0:
            return alerts

        latency_increase = (
            (metrics.avg_latency_ms - self._baseline_latency)
            / self._baseline_latency
            * 100
        )
        if latency_increase > 50:
            alerts.append(DriftAlert(
                alert_type="latency_degradation",
                severity="high" if latency_increase > 100 else "medium",
                message=f"Average latency increased by {latency_increase:.1f}%",
                current_value=metrics.avg_latency_ms,
                baseline_value=self._baseline_latency,
                threshold=50.0,
            ))
        return alerts

    def _check_cache_drift(self, metrics: MonitoringMetrics) -> List[DriftAlert]:
        """Check for cache hit rate degradation."""
        alerts = []
        if self._baseline_cache_hit_rate > 0:
            cache_drop = self._baseline_cache_hit_rate - metrics.cache_hit_rate
            if cache_drop > 0.2:
                alerts.append(DriftAlert(
                    alert_type="cache_hit_rate_drop",
                    severity="medium",
                    message=f"Cache hit rate dropped by {cache_drop:.1%}",
                    current_value=metrics.cache_hit_rate,
                    baseline_value=self._baseline_cache_hit_rate,
                    threshold=0.2,
                ))
        return alerts

    def _check_feedback_drift(self, metrics: MonitoringMetrics) -> List[DriftAlert]:
        """Check for feedback score degradation."""
        alerts = []
        if self._baseline_feedback_score <= 0:
            return alerts

        feedback_drop = self._baseline_feedback_score - metrics.feedback_score
        if feedback_drop > 1.0:
            alerts.append(DriftAlert(
                alert_type="feedback_score_drop",
                severity="high",
                message=f"Feedback score dropped by {feedback_drop:.1f}",
                current_value=metrics.feedback_score,
                baseline_value=self._baseline_feedback_score,
                threshold=1.0,
            ))
        return alerts

    def _check_threshold_violations(self, metrics: MonitoringMetrics) -> List[DriftAlert]:
        """Check for absolute threshold violations."""
        alerts = []

        if metrics.avg_latency_ms > self._latency_threshold_ms:
            alerts.append(DriftAlert(
                alert_type="latency_threshold_exceeded",
                severity="critical",
                message=(
                    f"Average latency {metrics.avg_latency_ms:.0f}ms exceeds "
                    f"threshold {self._latency_threshold_ms:.0f}ms"
                ),
                current_value=metrics.avg_latency_ms,
                baseline_value=self._latency_threshold_ms,
                threshold=self._latency_threshold_ms,
            ))

        if metrics.cache_hit_rate < self._cache_hit_threshold and len(self._cache_hits) > 10:
            alerts.append(DriftAlert(
                alert_type="low_cache_hit_rate",
                severity="low",
                message=(
                    f"Cache hit rate {metrics.cache_hit_rate:.1%} below "
                    f"threshold {self._cache_hit_threshold:.1%}"
                ),
                current_value=metrics.cache_hit_rate,
                baseline_value=self._cache_hit_threshold,
                threshold=self._cache_hit_threshold,
            ))

        if metrics.error_rate > 0.1 and metrics.total_queries > 10:
            alerts.append(DriftAlert(
                alert_type="high_error_rate",
                severity="critical",
                message=f"Error rate {metrics.error_rate:.1%} exceeds 10%",
                current_value=metrics.error_rate,
                baseline_value=0.0,
                threshold=0.1,
            ))

        return alerts

    def update_baselines(self):
        """Update baseline metrics from current values."""
        metrics = self.get_current_metrics()
        self._baseline_latency = metrics.avg_latency_ms
        self._baseline_cache_hit_rate = metrics.cache_hit_rate
        self._baseline_feedback_score = metrics.feedback_score
        logger.info("Baselines updated")

    def reset(self):
        """Reset all monitoring data."""
        self._latencies.clear()
        self._cache_hits.clear()
        self._feedback_scores.clear()
        self._query_timestamps.clear()
        self._errors.clear()
        self._baseline_latency = 0.0
        self._baseline_cache_hit_rate = 0.0
        self._baseline_feedback_score = 0.0
        logger.info("Online monitor reset")

    def _cleanup_old_entries(self, now: datetime):
        """Remove entries outside the sliding window.

        Args:
            now: Current timestamp.
        """
        cutoff = now - timedelta(minutes=self._window_minutes)

        while self._latencies and self._latencies[0][0] < cutoff:
            self._latencies.popleft()

        while self._cache_hits and self._cache_hits[0][0] < cutoff:
            self._cache_hits.popleft()

        while self._feedback_scores and self._feedback_scores[0][0] < cutoff:
            self._feedback_scores.popleft()

        while self._query_timestamps and self._query_timestamps[0] < cutoff:
            self._query_timestamps.popleft()

        while self._errors and self._errors[0] < cutoff:
            self._errors.popleft()


# Singleton instance
online_monitor = OnlineMonitor()
