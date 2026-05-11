# AGENTS.md

This project is a 9-layer AI production architecture. When working on this codebase, follow these guidelines:

## Project Structure

```
production-ai-app/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Centralized configuration
│   ├── models.py            # Pydantic schemas
│   ├── components/          # Retrieval components
│   ├── services/            # Business logic (5 files)
│   ├── prompts/             # Versioned prompt registry
│   ├── agents/              # Self-correcting agents
│   └── security/            # Three-layer security
├── evaluation/              # Golden dataset + eval pipelines
├── observability/           # Tracing, feedback, cost tracking
└── tests/                   # CI-ready test suite
```

## Key Conventions

1. **Never hardcode prompts** - All prompts live in `app/prompts/` and are registered through the registry
2. **Always add tests** - New features require tests in `tests/`
3. **Security first** - All user input passes through `app/security/` guards
4. **Trace everything** - Use the observability layer for all operations
5. **Type everything** - All functions must have type hints

## Service Layer Files

- `services/rag_pipeline.py` - Main RAG orchestration
- `services/semantic_cache.py` - Embedding-based caching
- `services/conversation.py` - Memory management
- `services/query_rewriter.py` - Query enhancement
- `services/query_router.py` - Intent routing

## Agent Layer Files

- `agents/document_grader.py` - Relevance scoring with self-correction
- `agents/query_decomposer.py` - Complex query breakdown
- `agents/adaptive_router.py` - Dynamic tool selection

## Security Layer Files

- `security/input_guard.py` - Input validation and sanitization
- `security/content_filter.py` - Content policy enforcement
- `security/output_filter.py` - Output validation

## Evaluation Layer

- `evaluation/golden_dataset.json` - Ground truth test cases
- `evaluation/offline_eval.py` - Batch evaluation pipeline
- `evaluation/online_monitor.py` - Production monitoring

## Observability Layer

- `observability/tracer.py` - Distributed tracing
- `observability/feedback.py` - User feedback collection
- `observability/cost_tracker.py` - Cost accounting
