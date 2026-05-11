# Production AI App

9-layer AI production architecture with RAG pipeline, self-correcting agents, three-layer security, evaluation framework, and full observability.

## Architecture Layers

```
production-ai-app/
├── app/                    # FastAPI entry, config, schemas, containerized
│   ├── components/         # Custom retrieval: hybrid search + reranking
│   ├── services/           # Core business logic: pipeline, cache, memory, rewriting, routing
│   ├── prompts/            # Versioned, type-specific, hot-swappable
│   ├── agents/             # Intelligence layer: self-correcting retrieval
│   ├── security/           # Three guard layers: input, content, output
├── evaluation/             # Golden test set, offline + online pipelines
├── observability/          # Per-stage tracing, feedback capture, cost breakdown
├── data/                   # Raw → processed → index config
├── scripts/                # Seed, migrate, healthcheck
├── frontend/               # UI, containerized separately
├── tests/                  # Retrieval, cache, routing tests. CI-ready.
├── docs/                   # Architecture, API ref, deployment guide
└── .claude/                # AI coding agent context, rules, project memory
```

## Quick Start

```bash
# Install dependencies
uv sync

# Set environment variables
cp .env.example .env
# Edit .env with your API keys

# Run migrations and seed data
uv run python scripts/migrate.py
uv run python scripts/seed.py

# Start the server
uv run uvicorn app.main:app --reload

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run mypy .
```

## Layer Details

### 1. Services Layer
- **RAG Pipeline**: Orchestrates retrieval, grading, and generation
- **Semantic Cache**: Embedding-based cache with TTL and similarity threshold
- **Conversation Memory**: Sliding window with summarization
- **Query Rewriter**: Multi-turn context injection and intent clarification
- **Query Router**: Intent classification with fallback to general RAG

### 2. Agents Layer
- **Document Grader**: Relevance scoring with self-correction loop
- **Query Decomposer**: Breaks complex queries into sub-questions
- **Adaptive Router**: Dynamic tool selection based on query type

### 3. Prompts Layer
- Versioned prompt templates
- Type-specific prompts registered in a central registry
- Hot-swappable without code changes

### 4. Security Layer
- **Input Guard**: Injection detection, PII redaction, rate limiting
- **Content Filter**: Toxicity and policy compliance checking
- **Output Filter**: Response sanitization and format validation

### 5. Evaluation Layer
- Golden dataset for regression testing
- Offline evaluation pipeline with metrics
- Online monitoring with drift detection

### 6. Observability Layer
- Per-stage distributed tracing
- User feedback linked to traces
- Cost tracking per query and per component

## Documentation

| Document | Description |
|----------|-------------|
| [Guide de Construction](docs/guide-construction.md) | Architecture 9 couches, ordre de construction, dépendances |
| [Guide des Services](docs/guide-services.md) | RAG pipeline, cache sémantique, mémoire, réécriture, routage |
| [Guide des Agents](docs/guide-agents.md) | Évaluateur, décomposeur, routeur adaptatif, outils |
| [Guide de Sécurité](docs/guide-securite.md) | Triple couche : input guard, content filter, output filter |
| [Guide d'Observabilité](docs/guide-observabilite.md) | Traçage distribué, feedback, suivi des coûts |
| [Guide d'Évaluation](docs/guide-evaluation.md) | Dataset de référence, évaluation offline, monitoring online |
| [Guide Base de Données](docs/guide-base-de-donnees.md) | ChromaDB, Redis, PostgreSQL, Docker Compose |
| [Guide Frontend](docs/guide-frontend.md) | Interface utilisateur, intégration API, conteneurisation |
| [Guide des Tests](docs/guide-tests.md) | Stratégie de test, patterns, couverture |
| [Guide CI/CD](docs/guide-cicd.md) | Linting, tests, build Docker, déploiement |
| [Architecture](docs/architecture.md) | Diagramme d'architecture et flux de requête |
| [API Reference](docs/api-reference.md) | Endpoints, requêtes, réponses, codes d'erreur |
| [Deployment](docs/deployment.md) | Déploiement Docker Compose, scaling, monitoring |

## Configuration

All configuration lives in `app/config.py` and is managed through environment variables. See `.env.example` for required variables.

## Deployment

See `docs/deployment.md` for containerized deployment with Docker Compose.
