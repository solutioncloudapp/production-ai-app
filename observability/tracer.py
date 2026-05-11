"""Distributed tracing for per-stage observability."""

import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()

# Context variable for current trace ID
current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


class Span:
    """Represents a single trace span."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        parent_id: Optional[str] = None,
    ):
        """Initialize span.

        Args:
            name: Span name.
            trace_id: Parent trace ID.
            parent_id: Optional parent span ID.
        """
        self.trace_id = trace_id
        self.span_id = str(uuid.uuid4())[:12]
        self.name = name
        self.parent_id = parent_id
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.attributes: Dict[str, Any] = {}
        self.status = "ok"

    def set_attribute(self, key: str, value: Any):
        """Set span attribute.

        Args:
            key: Attribute key.
            value: Attribute value.
        """
        self.attributes[key] = value

    def end(self, status: str = "ok"):
        """End the span.

        Args:
            status: Span status (ok/error).
        """
        self.end_time = datetime.utcnow()
        self.status = status

    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds.

        Returns:
            Duration in ms.
        """
        if not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds() * 1000

    def to_dict(self) -> Dict:
        """Convert span to dictionary.

        Returns:
            Dictionary representation.
        """
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "status": self.status,
        }


class Tracer:
    """Distributed tracer for per-stage observability.

    Features:
    - Hierarchical span tracking
    - Attribute attachment
    - Export to OTLP or local storage
    - Trace ID propagation
    """

    def __init__(self):
        """Initialize tracer."""
        self._active_spans: Dict[str, Span] = {}
        self._completed_traces: List[Dict] = []
        self._exporter = None
        logger.info("Initialized tracer")

    def initialize(self):
        """Initialize tracer with exporter."""
        logger.info("Tracer initialized")

    def start_span(
        self,
        name: str,
        parent_id: Optional[str] = None,
    ) -> "SpanContext":
        """Start a new span.

        Args:
            name: Span name.
            parent_id: Optional parent span ID.

        Returns:
            SpanContext for use as context manager.
        """
        trace_id = current_trace_id.get() or str(uuid.uuid4())[:12]
        span = Span(name=name, trace_id=trace_id, parent_id=parent_id)
        self._active_spans[span.span_id] = span
        return SpanContext(self, span)

    def get_current_trace_id(self) -> str:
        """Get current trace ID.

        Returns:
            Current trace ID.
        """
        return current_trace_id.get()

    def set_trace_id(self, trace_id: str):
        """Set current trace ID.

        Args:
            trace_id: Trace ID to set.
        """
        current_trace_id.set(trace_id)

    def export_trace(self, trace_id: str) -> List[Dict]:
        """Export all spans for a trace.

        Args:
            trace_id: Trace ID to export.

        Returns:
            List of span dictionaries.
        """
        spans = [
            s.to_dict()
            for s in self._active_spans.values()
            if s.trace_id == trace_id and s.end_time
        ]
        self._completed_traces.extend(spans)
        return spans

    def get_traces(self) -> List[Dict]:
        """Get all completed traces.

        Returns:
            List of completed trace spans.
        """
        return self._completed_traces

    def clear(self):
        """Clear all trace data."""
        self._active_spans.clear()
        self._completed_traces.clear()


class SpanContext:
    """Context manager for spans."""

    def __init__(self, tracer: Tracer, span: Span):
        """Initialize span context.

        Args:
            tracer: Parent tracer.
            span: Span to manage.
        """
        self.tracer = tracer
        self.span = span

    def __enter__(self) -> Span:
        """Enter span context.

        Returns:
            The span.
        """
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit span context.

        Args:
            exc_type: Exception type if any.
            exc_val: Exception value if any.
            exc_tb: Exception traceback if any.
        """
        status = "error" if exc_type else "ok"
        self.span.end(status=status)
        if exc_type:
            self.span.set_attribute("error", str(exc_val))


# Singleton instance
tracer = Tracer()
