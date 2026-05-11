# Guide de Construction — Architecture 9 Couches

## Vue d'ensemble

Ce projet implémente une architecture AI productionnelle en 9 couches conçue pour construire des applications RAG (Retrieval-Augmented Generation) robustes, observables et sécurisées.

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                         │
│              (UI, conteneurisé séparément)                │
├───────────────────────────────────────────────────────────┤
│                      API Layer                            │
│           (FastAPI, config, schémas Pydantic)             │
├───────────────────────────────────────────────────────────┤
│                    Services Layer                         │
│  ┌──────────┬──────────┬──────────┬──────────┬─────────┐ │
│  │   RAG    │ Semantic │ Convers- │  Query   │  Query  │ │
│  │ Pipeline │  Cache   │  ation   │ Rewriter │ Router  │ │
│  └──────────┴──────────┴──────────┴──────────┴─────────┘ │
├───────────────────────────────────────────────────────────┤
│                     Agents Layer                          │
│  ┌──────────┬──────────┬──────────┐                       │
│  │ Document │  Query   │ Adaptive │                       │
│  │  Grader  │Decomposer│  Router  │                       │
│  └──────────┴──────────┴──────────┘                       │
├───────────────────────────────────────────────────────────┤
│                    Prompts Layer                          │
│         (Versionnés, typés, interchangeables à chaud)     │
├───────────────────────────────────────────────────────────┤
│                    Security Layer                         │
│  ┌──────────┬──────────┬──────────┐                       │
│  │  Input   │ Content  │  Output  │                       │
│  │  Guard   │  Filter  │  Filter  │                       │
│  └──────────┴──────────┴──────────┘                       │
├───────────────────────────────────────────────────────────┤
│                  Evaluation Layer                         │
│  ┌──────────┬──────────┬──────────┐                       │
│  │  Golden  │ Offline  │  Online  │                       │
│  │ Dataset  │  Eval    │ Monitor  │                       │
│  └──────────┴──────────┴──────────┘                       │
├───────────────────────────────────────────────────────────┤
│                  Observability Layer                      │
│  ┌──────────┬──────────┬──────────┐                       │
│  │  Tracer  │ Feedback │   Cost   │                       │
│  │          │Collector │ Tracker  │                       │
│  └──────────┴──────────┴──────────┘                       │
└───────────────────────────────────────────────────────────┘
```

## Structure du Projet

```
production-ai-app/
├── app/                          # Application FastAPI
│   ├── main.py                   # Point d'entrée (4 endpoints)
│   ├── config.py                 # Configuration centralisée (18 paramètres)
│   ├── models.py                 # 15 schémas Pydantic
│   ├── Dockerfile                # Image Docker (Python 3.11-slim)
│   ├── agents/                   # Couche agents intelligents
│   │   ├── document_grader.py    # Évaluation de pertinence avec auto-correction
│   │   ├── query_decomposer.py   # Décomposition de requêtes complexes
│   │   ├── adaptive_router.py    # Routage dynamique d'outils
│   │   └── tools/                # Outils spécialisés
│   │       ├── vector_search.py  # Recherche sémantique
│   │       ├── web_search.py     # Recherche web (API Serper)
│   │       └── code_search.py    # Recherche dans le code
│   ├── components/               # Composants de retrieval
│   │   ├── hybrid_retriever.py   # Vector + BM25 avec fusion de rang
│   │   └── reranker.py           # Reranking cross-encoder
│   ├── prompts/                  # Registre de prompts versionnés
│   │   ├── registry.py           # Registre central avec compilation
│   │   └── templates.py          # 11 templates de prompts
│   ├── security/                 # Triple couche de sécurité
│   │   ├── input_guard.py        # Détection d'injection, PII
│   │   ├── content_filter.py     # Filtrage de contenu toxique
│   │   └── output_filter.py      # Sanitisation de sortie
│   └── services/                 # Logique métier principale
│       ├── rag_pipeline.py       # Pipeline RAG en 6 étapes
│       ├── semantic_cache.py     # Cache par similarité sémantique
│       ├── conversation.py       # Mémoire conversationnelle
│       ├── query_rewriter.py     # Réécriture de requêtes
│       └── query_router.py       # Classification d'intention
├── evaluation/                   # Couche évaluation
│   ├── golden_dataset.json       # 8 cas de test de référence
│   ├── offline_eval.py           # Pipeline d'évaluation batch
│   └── online_monitor.py         # Monitoring production + drift
├── observability/                # Couche observabilité
│   ├── tracer.py                 # Traçage distribué par spans
│   ├── feedback.py               # Collecte de feedback utilisateur
│   └── cost_tracker.py           # Suivi des coûts par modèle
├── frontend/                     # Interface utilisateur
│   ├── app.py                    # Squelette FastAPI
│   └── Dockerfile                # Image frontend
├── scripts/                      # Scripts utilitaires
│   ├── healthcheck.py            # Vérification de santé des services
│   ├── migrate.py                # Migrations de base de données (stub)
│   └── seed.py                   # Seed de données initiales (partiel)
├── tests/                        # Suite de tests
│   ├── test_routing.py           # 11 tests de routage
│   ├── test_cache.py             # 6 tests de cache
│   └── test_retrieval.py         # 5 tests de retrieval
├── docs/                         # Documentation
├── data/                         # Données et configuration d'index
├── .env.example                  # Variables d'environnement de référence
├── docker-compose.yml            # Orchestration 5 services
├── pyproject.toml                # Dépendances et configuration outils
└── README.md                     # Documentation principale
```

## Ordre de Construction Recommandé

### Étape 1 : Configuration

**Fichiers** : `app/config.py`, `.env.example`

Configuration centralisée via `pydantic-settings` avec 18 paramètres chargés depuis les variables d'environnement :

- **LLM** : `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBEDDING_MODEL`
- **Base de données** : `DATABASE_URL`, `REDIS_URL`, `CHROMA_HOST`, `CHROMA_PORT`
- **Application** : `APP_HOST`, `APP_PORT`, `LOG_LEVEL`, `ENVIRONMENT`
- **Sécurité** : `MAX_INPUT_LENGTH`, `RATE_LIMIT_PER_MINUTE`, `ALLOWED_ORIGINS`
- **Cache** : `CACHE_TTL_SECONDS`, `CACHE_SIMILARITY_THRESHOLD`
- **Évaluation** : `EVAL_MODEL`, `EVAL_DATASET_PATH`
- **Observabilité** : `OTEL_EXPORTER_OTLP_ENDPOINT`, `ENABLE_COST_TRACKING`

Le pattern singleton utilise `@lru_cache` pour garantir une seule instance de configuration.

### Étape 2 : Modèles Pydantic

**Fichier** : `app/models.py`

15 schémas Pydantic définissent tous les types de données de l'application :

| Modèle | Rôle |
|--------|------|
| `IntentType` | Énumération des 5 intentions de requête |
| `SourceDocument` | Document récupéré avec score et métadonnées |
| `ChatRequest` / `ChatResponse` | Requêtes et réponses de l'API chat |
| `GuardResult` / `ContentFilterResult` | Résultats des gardes de sécurité |
| `RouteResult` / `PipelineResult` | Résultats du routage et du pipeline |
| `FeedbackRecord` / `CostRecord` | Enregistrements d'observabilité |
| `EvalResult` | Résultat d'évaluation d'un cas de test |
| `CacheEntry` | Entrée du cache sémantique |
| `ConversationMessage` / `ConversationState` | État conversationnel |
| `PromptTemplate` / `TracerSpan` | Templates de prompts et spans de tracing |

### Étape 3 : Registre de Prompts

**Fichiers** : `app/prompts/registry.py`, `app/prompts/templates.py`

Système de gestion de prompts versionnés avec 11 templates :

- **Génération** : `rag_generation`
- **Réécriture** : `query_rewrite`, `query_expand`, `query_clarify`
- **Routage** : `query_route`
- **Évaluation** : `document_grade`, `query_decompose`
- **Sécurité** : `input_guard`, `content_filter`
- **Métriques** : `eval_relevance`, `eval_faithfulness`

Le registre compile les templates en `ChatPromptTemplate` LangChain et permet l'accès versionné.

### Étape 4 : Couche Sécurité

**Fichiers** : `app/security/input_guard.py`, `app/security/content_filter.py`, `app/security/output_filter.py`

Triple couche de défense :

1. **InputGuard** : 8 patterns d'injection de prompts, 3 patterns PII (SSN, carte bancaire, email), limite de longueur
2. **ContentFilter** : Détection de toxicité, contenu sexuel, violence, auto-mutilation
3. **OutputFilter** : Sanitisation Markdown, suppression HTML/JS, vérification des citations, limite de longueur

### Étape 5 : Couche Services

**Fichiers** : `app/services/` (5 fichiers)

Cinq services constituent le cœur métier :

- **RAG Pipeline** : Orchestration en 6 étapes (cache → réécriture → décomposition → retrieval+grading → génération → cache store)
- **Semantic Cache** : Cache par similarité d'embeddings OpenAI (seuil 0.95, TTL 3600s)
- **Conversation Memory** : Fenêtre glissante de 10 messages avec auto-résumé à 20 messages
- **Query Rewriter** : Réécriture contextuelle, expansion en 3 alternatives, clarification
- **Query Router** : Classification LLM structurée avec fallback par mots-clés, 5 intentions

### Étape 6 : Couche Agents

**Fichiers** : `app/agents/` (3 agents + 3 outils)

Agents intelligents avec capacités d'auto-correction :

- **Document Grader** : Évaluation RELEVANT/PARTIAL/IRRELEVANT avec re-évaluation stricte pour les cas limites
- **Query Decomposer** : Décomposition en sous-requêtes (max 4) avec court-circuit heuristique pour les requêtes courtes
- **Adaptive Router** : Registre d'outils dynamique, détection de complexité, chaînes de fallback

Outils spécialisés :

- **VectorSearchTool** : Recherche sémantique avec filtrage metadata
- **WebSearchTool** : Recherche web via API Serper
- **CodeSearchTool** : Indexation et recherche dans les dépôts de code (13 extensions)

### Étape 7 : Composants de Retrieval

**Fichiers** : `app/components/hybrid_retriever.py`, `app/components/reranker.py`

- **HybridRetriever** : Combine recherche vectorielle et BM25 avec fusion de rang réciproque (poids 0.7/0.3)
- **CrossEncoderReranker** : Reranking avec modèle `cross-encoder/ms-marco-MiniLM-L-6-v2`

### Étape 8 : Couche Observabilité

**Fichiers** : `observability/` (3 fichiers)

- **Tracer** : Spans hiérarchiques avec context vars, context manager `SpanContext` pour cycle de vie automatique
- **FeedbackCollector** : Feedback lié aux traces (rating 1-5), statistiques, tendances, export fine-tuning
- **CostTracker** : 6 modèles tarifés, suivi par requête/conversation/jour, alertes budget

### Étape 9 : Couche Évaluation

**Fichiers** : `evaluation/` (3 fichiers)

- **Golden Dataset** : 8 cas de test couvrant 5 catégories et 3 niveaux de difficulté
- **OfflineEvaluator** : Évaluation batch avec 3 métriques (pertinence, fidélité, pertinence de réponse)
- **OnlineMonitor** : Monitoring en temps réel avec fenêtre glissante, percentiles p95/p99, détection de drift

### Étape 10 : API FastAPI

**Fichier** : `app/main.py`

Point d'entrée avec 4 endpoints et middleware de sécurité :

| Endpoint | Méthode | Rôle |
|----------|---------|------|
| `/api/chat` | POST | Requête principale avec chaîne de sécurité complète |
| `/api/feedback` | POST | Collecte de feedback utilisateur |
| `/api/health` | GET | Vérification de santé |
| `/api/metrics` | GET | Métriques Prometheus |

Le flux de traitement suit l'ordre : InputGuard → AdaptiveRouter → RAGPipeline → ContentFilter → OutputFilter → CostTracker.

## Dépendances

**Fichier** : `pyproject.toml`

30 dépendances principales organisées par catégorie :

| Catégorie | Packages |
|-----------|----------|
| **API** | `fastapi`, `uvicorn[standard]` |
| **Validation** | `pydantic`, `pydantic-settings` |
| **LLM** | `langchain`, `langchain-core`, `langchain-openai`, `langchain-community`, `langgraph`, `openai` |
| **Vector Store** | `chromadb`, `sentence-transformers`, `rank-bm25`, `tiktoken` |
| **HTTP** | `httpx` |
| **Cache/DB** | `redis` |
| **Templates** | `pyyaml`, `jinja2` |
| **Logging** | `structlog` |
| **Observabilité** | `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `prometheus-client` |
| **Dev** | `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `mypy` |

## Points d'Intégration entre Couches

```
Requête utilisateur
       │
       ▼
┌──────────────┐
│  InputGuard  │ ←─ security/input_guard.py
└──────┬───────┘
       │ query validée
       ▼
┌──────────────────┐
│ AdaptiveRouter   │ ←─ agents/adaptive_router.py
│   └─ QueryRouter │ ←─ services/query_router.py
└──────┬───────────┘
       │ route (intent + tools)
       ▼
┌──────────────────┐
│   RAGPipeline    │ ←─ services/rag_pipeline.py
│   ├─ SemanticCache  │ ←─ services/semantic_cache.py
│   ├─ QueryRewriter  │ ←─ services/query_rewriter.py
│   ├─ QueryDecomposer│ ←─ agents/query_decomposer.py
│   ├─ HybridRetriever│ ←─ components/hybrid_retriever.py
│   │   └─ Reranker   │ ←─ components/reranker.py
│   ├─ DocumentGrader │ ←─ agents/document_grader.py
│   └─ PromptRegistry │ ←─ prompts/registry.py
└──────┬───────────┘
       │ réponse brute
       ▼
┌──────────────────┐
│  ContentFilter   │ ←─ security/content_filter.py
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  OutputFilter    │ ←─ security/output_filter.py
└──────┬───────────┘
       │ réponse formatée
       ▼
┌──────────────────┐
│  CostTracker     │ ←─ observability/cost_tracker.py
│  Tracer          │ ←─ observability/tracer.py
└──────────────────┘
```

## Configuration Docker

**Fichier** : `docker-compose.yml`

5 services orchestrés :

| Service | Image | Port | Rôle |
|---------|-------|------|------|
| `app` | Python 3.11-slim (custom) | 8000 | API FastAPI principale |
| `frontend` | Python 3.11-slim (custom) | 3000 | Interface utilisateur |
| `redis` | redis:7-alpine | 6379 | Cache distribué |
| `db` | postgres:16-alpine | 5432 | Base de données relationnelle |
| `chromadb` | chromadb/chroma:latest | 8001 | Vector store |

## Bonnes Pratiques

1. **Jamais de prompts en dur** — Tous les prompts résident dans `app/prompts/templates.py` et sont enregistrés via le registre
2. **Tout typer** — Toutes les fonctions ont des hints de type (configuration mypy strict)
3. **Sécurité d'abord** — Toutes les entrées utilisateur passent par `app/security/`
4. **Tracer tout** — Utiliser la couche observabilité pour toutes les opérations
5. **Singletons** — Chaque composant majeur exporte une instance singleton au niveau module
6. **Async-first** — Toutes les opérations I/O utilisent `async def`
7. **Logging structuré** — Utiliser `structlog` pour tous les logs

## Voir Aussi

- [Guide des Services](guide-services.md) — Détails de la couche services
- [Guide des Agents](guide-agents.md) — Agents auto-correctifs et outils
- [Guide de Sécurité](guide-securite.md) — Triple couche de sécurité
- [Guide d'Observabilité](guide-observabilite.md) — Traçage, feedback, coûts
- [Guide d'Évaluation](guide-evaluation.md) — Dataset de référence et pipelines
- [Guide Base de Données](guide-base-de-donnees.md) — ChromaDB, Redis, PostgreSQL
- [Guide Frontend](guide-frontend.md) — Interface utilisateur
- [Guide des Tests](guide-tests.md) — Stratégie de test
- [Guide CI/CD](guide-cicd.md) — Pipeline d'intégration continue
