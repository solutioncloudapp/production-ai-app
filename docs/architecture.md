# Architecture Documentation

## Overview

This is a 9-layer AI production architecture designed for building robust, observable, and secure RAG (Retrieval-Augmented Generation) applications.

## Layer Architecture

```
─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                          │
│              (UI, containerized separately)                 │
├─────────────────────────────────────────────────────────────┤
│                      API Layer                              │
│           (FastAPI entry, config, schemas)                  │
├─────────────────────────────────────────────────────────────┤
│                    Services Layer                           │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │   RAG    │ Semantic │ Convers- │  Query   │  Query   │  │
│  │ Pipeline │  Cache   │  ation   │ Rewriter │  Router  │  │
│  └──────────┴────────────────────┴──────────┴──────────  │
├─────────────────────────────────────────────────────────────┤
│                     Agents Layer                            │
│  ┌──────────┬──────────┬──────────┐                         │
│  │ Document │  Query   │ Adaptive │                         │
│  │  Grader  │Decomposer│  Router  │                         │
│  └──────────┴──────────┴──────────┘                         │
─────────────────────────────────────────────────────────────┤
│                    Prompts Layer                            │
│         (Versioned, type-specific, hot-swappable)           │
├─────────────────────────────────────────────────────────────┤
│                    Security Layer                           │
│  ┌──────────┬──────────┬──────────┐                         │
│  │  Input   │ Content  │  Output  │                         │
│  │  Guard   │  Filter  │  Filter  │                         │
│  └──────────┴──────────┴──────────┘                         │
├─────────────────────────────────────────────────────────────┤
│                  Evaluation Layer                           │
│  ┌──────────┬──────────┬──────────┐                         │
│  │  Golden  │ Offline  │  Online  │                         │
│  │ Dataset  │  Eval    │ Monitor  │                         │
│  └──────────┴──────────┴──────────┘                         │
├─────────────────────────────────────────────────────────────┤
│                  Observability Layer                        │
│  ┌──────────┬──────────┬──────────┐                         │
│  │  Tracer  │ Feedback │   Cost   │                         │
│  │          │Collector │ Tracker  │                         │
│  └──────────┴──────────┴──────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## Request Flow

1. **Input Guard** validates and sanitizes user input
2. **Query Router** determines intent and selects tools
3. **Query Rewriter** adds conversation context
4. **Query Decomposer** breaks complex queries into sub-questions
5. **Hybrid Retriever** fetches documents (vector + BM25)
6. **Document Grader** filters and scores retrieved documents
7. **RAG Pipeline** generates response using graded documents
8. **Content Filter** checks response for policy violations
9. **Output Filter** formats and validates final response
10. **Tracer** records all stages for observability
11. **Cost Tracker** records token usage and costs

## Key Design Decisions

### Why Hybrid Retrieval?
Vector search alone misses keyword matches. BM25 alone misses semantic matches. Combining both with reciprocal rank fusion gives better recall.

### Why Self-Correcting Agents?
LLM outputs can be inconsistent. The document grader re-evaluates borderline cases with stricter criteria, improving reliability.

### Why Three-Layer Security?
- Input guard catches malicious prompts before they reach the LLM
- Content filter ensures generated content is safe
- Output filter validates and formats responses

### Why Semantic Cache?
Exact match caching misses semantically similar queries. Embedding-based caching with similarity threshold catches more cache hits while maintaining accuracy.

## Scaling Considerations

- **Horizontal scaling**: Stateless services can be scaled independently
- **Cache layer**: Redis for distributed semantic caching
- **Vector store**: ChromaDB with persistence for document storage
- **Rate limiting**: Per-user rate limiting at the API layer
