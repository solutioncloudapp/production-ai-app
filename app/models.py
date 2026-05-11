"""Pydantic schemas for request/response models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class IntentType(str, Enum):
    """Query intent types for routing."""

    GENERAL = "general"
    DOCUMENT = "document"
    CODE = "code"
    WEB_SEARCH = "web_search"
    CONVERSATIONAL = "conversational"


class SourceDocument(BaseModel):
    """Retrieved source document."""

    id: str
    content: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    """Chat request model."""

    query: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat response model."""

    text: str
    sources: List[SourceDocument] = Field(default_factory=list)
    conversation_id: Optional[str] = None
    trace_id: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


class GuardResult(BaseModel):
    """Result from security guard."""

    is_valid: bool
    sanitized_query: str = ""
    reason: Optional[str] = None


class ContentFilterResult(BaseModel):
    """Result from content filter."""

    is_safe: bool
    sanitized_content: str = ""
    flags: List[str] = Field(default_factory=list)


class RouteResult(BaseModel):
    """Result from query router."""

    intent: IntentType
    confidence: float
    tools: List[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    """Result from RAG pipeline execution."""

    response: str
    sources: List[SourceDocument] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit: bool = False
    latency_ms: float = 0.0


class FeedbackRecord(BaseModel):
    """User feedback record."""

    trace_id: str
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CostRecord(BaseModel):
    """Cost tracking record."""

    conversation_id: Optional[str]
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EvalResult(BaseModel):
    """Evaluation result for a test case."""

    query: str
    expected_answer: str
    actual_answer: str
    relevance_score: float
    faithfulness_score: float
    answer_relevance_score: float
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None


class CacheEntry(BaseModel):
    """Semantic cache entry."""

    query_embedding: List[float]
    response: str
    sources: List[SourceDocument] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ttl_seconds: int = 3600


class ConversationMessage(BaseModel):
    """Single conversation message."""

    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ConversationState(BaseModel):
    """Full conversation state."""

    conversation_id: str
    messages: List[ConversationMessage] = Field(default_factory=list)
    summary: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PromptTemplate(BaseModel):
    """Versioned prompt template."""

    id: str
    version: str
    template: str
    variables: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TracerSpan(BaseModel):
    """Observability span record."""

    trace_id: str
    span_id: str
    name: str
    parent_id: Optional[str] = None
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    status: str = "ok"
