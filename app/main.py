"""FastAPI application entry point."""

import uuid
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Awaitable, Callable

import structlog
from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from app.agents.adaptive_router import adaptive_router
from app.components.hybrid_retriever import HybridRetriever
from app.components.vector_store import ChromaVectorStore
from app.config import settings
from app.models import ErrorResponse
from app.prompts.registry import prompt_registry
from app.security.auth import authenticate_health_check, authenticate_request
from app.security.content_filter import ContentFilter
from app.security.input_guard import InputGuard
from app.security.output_filter import OutputFilter
from app.security.rate_limiter import RateLimitMiddleware
from app.services.conversation import conversation_memory
from app.services.rag_pipeline import rag_pipeline
from observability.cost_tracker import cost_tracker
from observability.online_monitor import online_monitor
from observability.tracer import tracer

logger = structlog.get_logger()

input_guard = InputGuard()
content_filter = ContentFilter()
output_filter = OutputFilter()
vector_store = ChromaVectorStore()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    logger.info("Starting application")
    prompt_registry.initialize()
    tracer.initialize()
    cost_tracker.initialize()

    # Initialize vector store
    await vector_store.initialize()

    # Create hybrid retriever with vector store
    retriever = await vector_store.to_langchain_retriever()

    # Seed sample documents if collection is empty
    stats = vector_store.get_stats()
    if stats["count"] == 0:
        await _seed_documents()

    # Initialize hybrid retriever with sample documents for BM25
    from langchain_core.documents import Document

    sample_docs = [
        Document(
            page_content="Python is a programming language known for readability.",
            metadata={"id": "doc_001", "source": "python_docs"},
        ),
        Document(
            page_content="Machine learning enables systems to learn from data.",
            metadata={"id": "doc_002", "source": "ml_basics"},
        ),
        Document(
            page_content="FastAPI is a modern Python web framework for APIs.",
            metadata={"id": "doc_003", "source": "fastapi_docs"},
        ),
        Document(
            page_content="Semantic caching finds responses by embedding similarity.",
            metadata={"id": "doc_004", "source": "cache_docs"},
        ),
        Document(
            page_content="RAG combines retrieval with LLM generation.",
            metadata={"id": "doc_005", "source": "rag_docs"},
        ),
    ]
    hybrid_retriever = HybridRetriever(
        vector_retriever=retriever,
        documents=sample_docs,
        top_k=5,
    )
    rag_pipeline.set_retriever(hybrid_retriever)

    yield
    logger.info("Shutting down application")
    await rag_pipeline.shutdown()


async def _seed_documents() -> None:
    """Seed initial documents into the vector store."""
    from langchain_core.documents import Document

    documents = [
        Document(
            page_content=(
                "Python is a programming language known for readability. "
                "It supports procedural, object-oriented, and functional paradigms."
            ),
            metadata={"id": "seed_001", "source": "python_docs", "category": "programming"},
        ),
        Document(
            page_content=(
                "Machine learning enables systems to learn from data. "
                "Types include supervised, unsupervised, and reinforcement learning."
            ),
            metadata={"id": "seed_002", "source": "ml_basics", "category": "ai"},
        ),
        Document(
            page_content=(
                "FastAPI is a modern Python web framework for APIs. "
                "It features automatic OpenAPI docs and dependency injection."
            ),
            metadata={"id": "seed_003", "source": "fastapi_docs", "category": "web"},
        ),
        Document(
            page_content=(
                "Semantic caching finds responses by embedding similarity, "
                "not exact matches. This improves response times."
            ),
            metadata={"id": "seed_004", "source": "cache_docs", "category": "optimization"},
        ),
        Document(
            page_content=(
                "RAG combines retrieval from knowledge bases with LLM generation "
                "to produce accurate, grounded responses."
            ),
            metadata={"id": "seed_005", "source": "rag_docs", "category": "architecture"},
        ),
        Document(
            page_content=(
                "Security uses three layers: input guard, content filter, and output filter for response sanitization."
            ),
            metadata={"id": "seed_006", "source": "security_docs", "category": "security"},
        ),
    ]

    await vector_store.add_documents(documents)
    logger.info("Seeded documents", count=len(documents))


app = FastAPI(
    title="Production AI App",
    description="9-layer AI production architecture",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)


@app.middleware("http")
async def trace_requests(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """Add tracing to all requests."""
    with tracer.start_span("http_request") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        response = await call_next(request)
        span.set_attribute("http.status_code", response.status_code)
        return response


@app.post("/api/chat", response_model=None)
async def chat(
    request: Request,
    auth: dict[str, Any] = Depends(authenticate_request),
) -> JSONResponse | dict[str, Any]:
    """Main chat endpoint with full security and observability."""
    body = await request.json()
    query = body.get("query", "")
    conversation_id = body.get("conversation_id") or str(uuid.uuid4())[:12]

    with tracer.start_span("chat_request") as span:
        span.set_attribute("conversation_id", conversation_id)

        # Layer 1: Input guard
        guard_result = input_guard.validate(query)
        if not guard_result.is_valid:
            span.set_attribute("blocked", True)
            return JSONResponse(
                status_code=400,
                content={"error": guard_result.reason},
            )

        # Store user message in conversation memory
        await conversation_memory.add_message(
            conversation_id=conversation_id,
            role="user",
            content=guard_result.sanitized_query,
        )

        # Layer 2: Route query
        route = await adaptive_router.route(guard_result.sanitized_query)
        span.set_attribute("route", route.intent)

        # Layer 3: Execute pipeline
        result = await rag_pipeline.execute(
            query=guard_result.sanitized_query,
            conversation_id=conversation_id,
            route=route,
        )

        # Store assistant message in conversation memory
        await conversation_memory.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=result.response,
        )

        # Layer 4: Content filter
        filter_result = content_filter.check(result.response)
        if not filter_result.is_safe:
            return JSONResponse(
                status_code=400,
                content={"error": "Response blocked by content filter"},
            )

        # Layer 5: Output filter
        final_response = output_filter.format(
            filter_result.sanitized_content,
            result.sources,
            conversation_id=conversation_id,
        )
        final_response.conversation_id = conversation_id

        # Track cost
        cost_tracker.record(
            conversation_id=conversation_id,
            model=settings.openai_model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

        # Record online monitoring
        online_monitor.record_query(
            latency_ms=result.latency_ms if hasattr(result, "latency_ms") else 0,
            is_cache_hit=result.cache_hit,
        )

        span.set_attribute("response_length", len(final_response.text))
        return final_response.model_dump()


@app.post("/api/chat/stream", response_model=None)
async def chat_stream(
    request: Request,
    auth: dict[str, Any] = Depends(authenticate_request),
) -> JSONResponse | StreamingResponse:
    """Streaming chat endpoint with Server-Sent Events."""
    body = await request.json()
    query = body.get("query", "")
    conversation_id = body.get("conversation_id") or str(uuid.uuid4())[:12]

    # Input guard
    guard_result = input_guard.validate(query)
    if not guard_result.is_valid:
        return JSONResponse(
            status_code=400,
            content={"error": guard_result.reason},
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events."""
        with tracer.start_span("chat_stream") as span:
            span.set_attribute("conversation_id", conversation_id)

            # Store user message
            await conversation_memory.add_message(
                conversation_id=conversation_id,
                role="user",
                content=guard_result.sanitized_query,
            )

            # Route query
            route = await adaptive_router.route(guard_result.sanitized_query)

            # Send conversation ID
            import json

            yield f"data: {json.dumps({'event': 'conversation_id', 'data': conversation_id})}\n\n"

            # Execute pipeline
            result = await rag_pipeline.execute(
                query=guard_result.sanitized_query,
                conversation_id=conversation_id,
                route=route,
            )

            # Store assistant message
            await conversation_memory.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=result.response,
            )

            # Content filter
            filter_result = content_filter.check(result.response)
            if not filter_result.is_safe:
                yield f"data: {json.dumps({'event': 'error', 'data': 'Response blocked by content filter'})}\n\n"
                return

            # Send response
            response_data = {
                "event": "response",
                "data": {
                    "text": filter_result.sanitized_content,
                    "sources": [s.model_dump() for s in result.sources],
                    "conversation_id": conversation_id,
                },
            }
            yield f"data: {json.dumps(response_data)}\n\n"

            # Track cost
            cost_tracker.record(
                conversation_id=conversation_id,
                model=settings.openai_model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )

            yield 'data: {"event": "done"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/feedback")
async def submit_feedback(
    request: Request,
    auth: dict[str, Any] = Depends(authenticate_request),
) -> dict[str, str]:
    """Submit user feedback linked to trace."""
    body = await request.json()
    trace_id = body.get("trace_id")
    rating = body.get("rating")
    comment = body.get("comment", "")

    from observability.feedback import feedback_collector

    feedback_collector.record(trace_id, rating, comment)

    # Record feedback in online monitor
    online_monitor.record_feedback(rating)

    return {"status": "ok"}


@app.post("/api/documents", response_model=None)
async def upload_documents(
    request: Request,
    auth: dict[str, Any] = Depends(authenticate_request),
) -> JSONResponse | dict[str, Any]:
    """Upload documents to the vector store."""
    body = await request.json()
    documents = body.get("documents", [])
    metadata = body.get("metadata", {})

    if not documents:
        return JSONResponse(
            status_code=400,
            content={"error": "No documents provided"},
        )

    from langchain_core.documents import Document

    doc_objects = []
    for _i, doc in enumerate(documents):
        doc_id = doc.get("id", f"upload_{str(uuid.uuid4())[:8]}")
        content = doc.get("content", "")
        doc_metadata = {**metadata, **doc.get("metadata", {}), "id": doc_id}

        if content:
            doc_objects.append(Document(page_content=content, metadata=doc_metadata))

    if not doc_objects:
        return JSONResponse(
            status_code=400,
            content={"error": "No valid documents to upload"},
        )

    ids = await vector_store.add_documents(doc_objects)

    return {
        "status": "ok",
        "uploaded": len(ids),
        "ids": ids,
    }


@app.get("/api/documents/stats")
async def document_stats(auth: dict[str, Any] = Depends(authenticate_request)) -> dict[str, Any]:
    """Get vector store statistics."""
    stats = vector_store.get_stats()
    return stats


@app.delete("/api/documents", response_model=None)
async def delete_documents(
    request: Request,
    auth: dict[str, Any] = Depends(authenticate_request),
) -> JSONResponse | dict[str, Any]:
    """Delete documents from the vector store."""
    body = await request.json()
    ids = body.get("ids", [])

    if not ids:
        return JSONResponse(
            status_code=400,
            content={"error": "No document IDs provided"},
        )

    await vector_store.delete(ids)

    return {"status": "ok", "deleted": len(ids)}


@app.get("/api/conversations/{conversation_id}", response_model=None)
async def get_conversation(
    conversation_id: str,
    auth: dict[str, Any] = Depends(authenticate_request),
) -> JSONResponse | dict[str, Any]:
    """Get conversation history."""
    state = conversation_memory.get_state(conversation_id)
    if not state:
        return JSONResponse(
            status_code=404,
            content={"error": "Conversation not found"},
        )
    return state.model_dump()


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    auth: dict[str, Any] = Depends(authenticate_request),
) -> dict[str, str]:
    """Delete conversation history."""
    await conversation_memory.clear(conversation_id)
    return {"status": "ok"}


@app.get("/api/metrics/cost")
async def cost_metrics(auth: dict[str, Any] = Depends(authenticate_request)) -> dict[str, Any]:
    """Get cost tracking metrics."""
    return {
        "budget": cost_tracker.get_budget_status(),
        "breakdown": cost_tracker.get_model_breakdown(),
    }


@app.get("/api/metrics/feedback")
async def feedback_metrics(auth: dict[str, Any] = Depends(authenticate_request)) -> dict[str, Any]:
    """Get feedback metrics."""
    from observability.feedback import feedback_collector

    return feedback_collector.get_stats()


@app.get("/api/metrics/monitoring")
async def monitoring_metrics(auth: dict[str, Any] = Depends(authenticate_request)) -> dict[str, Any]:
    """Get online monitoring metrics."""
    metrics = online_monitor.get_current_metrics()
    alerts = online_monitor.check_drift()
    return {
        "metrics": metrics.model_dump(),
        "alerts": [a.model_dump() for a in alerts],
    }


@app.get("/api/health")
async def health(auth: dict[str, Any] = Depends(authenticate_health_check)) -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/metrics")
async def metrics(auth: dict[str, Any] = Depends(authenticate_request)) -> Response:
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest

    return Response(content=generate_latest(), media_type="text/plain")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler."""
    logger.error("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if settings.environment == "development" else None,
        ).model_dump(),
    )
