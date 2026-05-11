"""Feedback collection linked to traces for continuous improvement."""

from datetime import datetime
from typing import Dict, List, Optional

import structlog

from app.models import FeedbackRecord

logger = structlog.get_logger()


class FeedbackCollector:
    """Collects and analyzes user feedback linked to traces.

    Features:
    - Feedback linked to trace IDs
    - Aggregation by conversation and time window
    - Export for model fine-tuning
    - Trend analysis
    """

    def __init__(self):
        """Initialize feedback collector."""
        self._feedback: List[FeedbackRecord] = []
        self._trace_feedback: Dict[str, FeedbackRecord] = {}
        logger.info("Initialized feedback collector")

    def record(
        self,
        trace_id: str,
        rating: int,
        comment: Optional[str] = None,
    ) -> FeedbackRecord:
        """Record user feedback.

        Args:
            trace_id: Trace ID to link feedback to.
            rating: Rating score (1-5).
            comment: Optional feedback comment.

        Returns:
            Recorded FeedbackRecord.
        """
        record = FeedbackRecord(
            trace_id=trace_id,
            rating=rating,
            comment=comment,
        )
        self._feedback.append(record)
        self._trace_feedback[trace_id] = record

        logger.info(
            "Feedback recorded",
            trace_id=trace_id,
            rating=rating,
        )

        return record

    def get_feedback(self, trace_id: str) -> Optional[FeedbackRecord]:
        """Get feedback for a specific trace.

        Args:
            trace_id: Trace ID.

        Returns:
            FeedbackRecord or None.
        """
        return self._trace_feedback.get(trace_id)

    def get_all_feedback(self) -> List[FeedbackRecord]:
        """Get all recorded feedback.

        Returns:
            List of all feedback records.
        """
        return self._feedback

    def get_stats(self) -> Dict:
        """Get feedback statistics.

        Returns:
            Dictionary with feedback stats.
        """
        if not self._feedback:
            return {
                "total": 0,
                "avg_rating": 0,
                "rating_distribution": {},
            }

        ratings = [f.rating for f in self._feedback]
        distribution = {}
        for r in ratings:
            distribution[r] = distribution.get(r, 0) + 1

        return {
            "total": len(self._feedback),
            "avg_rating": sum(ratings) / len(ratings),
            "rating_distribution": distribution,
            "with_comments": sum(1 for f in self._feedback if f.comment),
        }

    def get_low_rated(self, threshold: int = 3) -> List[FeedbackRecord]:
        """Get feedback with ratings below threshold.

        Args:
            threshold: Rating threshold.

        Returns:
            List of low-rated feedback records.
        """
        return [f for f in self._feedback if f.rating < threshold]

    def export_for_finetuning(self) -> List[Dict]:
        """Export high-rated feedback for fine-tuning.

        Returns:
            List of examples suitable for fine-tuning.
        """
        high_rated = [f for f in self._feedback if f.rating >= 4]
        return [
            {
                "trace_id": f.trace_id,
                "rating": f.rating,
                "comment": f.comment,
                "timestamp": f.timestamp.isoformat(),
            }
            for f in high_rated
        ]

    def get_trend(self, window_hours: int = 24) -> List[Dict]:
        """Get feedback trend over time window.

        Args:
            window_hours: Time window in hours.

        Returns:
            List of hourly aggregated stats.
        """
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        recent = [f for f in self._feedback if f.timestamp >= cutoff]

        if not recent:
            return []

        # Group by hour
        hourly: Dict[str, List[int]] = {}
        for f in recent:
            hour_key = f.timestamp.strftime("%Y-%m-%d %H:00")
            if hour_key not in hourly:
                hourly[hour_key] = []
            hourly[hour_key].append(f.rating)

        trend = []
        for hour, ratings in sorted(hourly.items()):
            trend.append({
                "hour": hour,
                "count": len(ratings),
                "avg_rating": sum(ratings) / len(ratings),
            })

        return trend


# Singleton instance
feedback_collector = FeedbackCollector()
