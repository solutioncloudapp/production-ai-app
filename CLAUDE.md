# CLAUDE.md

You are working on a 9-layer AI production architecture. This document provides essential context for working with this codebase.

## Architecture Overview

This is a production-grade RAG (Retrieval-Augmented Generation) system with:

1. **Services Layer** - Core business logic for RAG pipeline, caching, memory, query rewriting, and routing
2. **Agents Layer** - Self-correcting agents for document grading, query decomposition, and adaptive routing
3. **Prompts Layer** - Versioned, type-specific prompt templates managed through a central registry
4. **Security Layer** - Three-guard architecture: input validation, content filtering, output sanitization
5. **Evaluation Layer** - Golden dataset testing, offline evaluation, and online monitoring
6. **Observability Layer** - Per-stage tracing, feedback linking, and cost tracking

## Code Style

- Use type hints for all function signatures
- Follow PEP 8 naming conventions
- Use Pydantic models for all data schemas
- Prefer composition over inheritance
- Write docstrings for all public functions and classes
- Use `structlog` for structured logging

## Important Patterns

### Prompt Management
Never hardcode prompts. All prompts must be:
- Defined in `app/prompts/templates.py`
- Registered in `app/prompts/registry.py`
- Accessed through the registry with version control

### Security
All user input must pass through:
1. `InputGuard` - Validates and sanitizes input
2. `ContentFilter` - Checks content policy compliance
3. `OutputFilter` - Validates and formats output

### Error Handling
- Use custom exceptions from `app/models.py`
- Log errors with structured logging
- Return appropriate HTTP status codes
- Never expose internal errors to users

### Testing
- All new features require tests
- Use `pytest` with `pytest-asyncio` for async tests
- Mock external services (LLM APIs, vector stores)
- Test both happy path and error cases

## Dependencies

Key dependencies:
- FastAPI for the web framework
- LangChain/LangGraph for LLM orchestration
- ChromaDB for vector storage
- Redis for semantic caching
- OpenTelemetry for observability

## Environment Variables

Required environment variables:
- `OPENAI_API_KEY` - OpenAI API key
- `REDIS_URL` - Redis connection string
- `DATABASE_URL` - PostgreSQL connection string
- `CHROMA_HOST` / `CHROMA_PORT` - ChromaDB connection

See `.env.example` for the complete list.
