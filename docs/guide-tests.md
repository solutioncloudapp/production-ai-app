# Guide des Tests — Stratégie et Patterns

## Vue d'ensemble

La suite de tests couvre l'ensemble des couches de l'architecture avec 137 tests. Cette documentation décrit les tests existants, les patterns utilisés et la couverture actuelle.

```
┌─────────────────────────────────────────────────────────────┐
│                      Test Suite                             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ test_agents  │  │ test_api     │  │ test_cache       │  │
│  │              │  │              │  │                  │  │
│  │ 11 tests     │  │ 17 tests     │  │ 6 tests          │  │
│  │              │  │              │  │                  │  │
│  │ • Grader     │  │ • Health     │  │ • Store          │  │
│  │ • Decomposer │  │ • Chat       │  │ • Lookup         │  │
│  │              │  │ • Feedback   │  │ • Invalidate     │  │
│  │              │  │ • Documents  │  │ • Clear          │  │
│  │              │  │ • Metrics    │  │ • Cosine sim     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ test_eval    │  │ test_obs     │  │ test_prompts     │  │
│  │              │  │              │  │                  │  │
│  │ 18 tests     │  │ 18 tests     │  │ 13 tests         │  │
│  │              │  │              │  │                  │  │
│  │ • Offline    │  │ • Tracer     │  │ • Templates      │  │
│  │ • Online     │  │ • Feedback   │  │ • Registry       │  │
│  │              │  │ • Cost       │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ test_retriev │  │ test_routing │  │ test_security    │  │
│  │              │  │              │  │                  │  │
│  │ 4 tests      │  │ 11 tests     │  │ 20 tests         │  │
│  │              │  │              │  │                  │  │
│  │ • Reranker   │  │ • QueryRouter│  │ • InputGuard     │  │
│  │ • Hybrid     │  │ • Adaptive   │  │ • ContentFilter  │  │
│  │              │  │              │  │ • OutputFilter   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  Couverture actuelle : ~70% du code                         │
│  Objectif : 80%+                                            │
└─────────────────────────────────────────────────────────────┘
```

## Tests Existants

### API — `tests/test_api.py` (17 tests)

**Fichier testé** : `app/main.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestHealthEndpoint` | 1 | Health check endpoint |
| `TestChatEndpoint` | 5 | Chat endpoint (succès, injection, conversation_id, sources) |
| `TestFeedbackEndpoint` | 1 | Soumission de feedback |
| `TestDocumentEndpoints` | 4 | Upload, delete, validation |
| `TestConversationEndpoints` | 2 | Récupération, suppression de conversation |
| `TestMetricsEndpoints` | 3 | Cost, feedback, monitoring metrics |
| `TestExceptionHandling` | 1 | Gestion globale des exceptions |

### Agents — `tests/test_agents.py` (11 tests)

**Fichiers testés** : `app/agents/document_grader.py`, `app/agents/query_decomposer.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestDocumentGrader` | 3 | Grading documents vides, filtrage, metadata |
| `TestQueryDecomposer` | 8 | Décomposition, déduplication, parsing de réponses |

### Cache — `tests/test_cache.py` (6 tests)

**Fichier testé** : `app/services/semantic_cache.py`

| Test | Description |
|------|-------------|
| `test_store_and_lookup` | Stockage et récupération d'une entrée cache |
| `test_cache_miss` | Miss pour requête sémantiquement différente |
| `test_invalidate` | Suppression d'une entrée spécifique |
| `test_clear` | Vidage complet du cache |
| `test_get_stats` | Statistiques du cache |
| `test_cosine_similarity` | Calcul de similarité cosinus (vecteurs identiques et orthogonaux) |

### Évaluation — `tests/test_evaluation.py` (18 tests)

**Fichiers testés** : `evaluation/offline_eval.py`, `evaluation/online_monitor.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestOfflineEvaluator` | 5 | Dataset loading, évaluation, métriques |
| `TestOnlineMonitor` | 13 | Requêtes, feedback, drift detection, reset |

### Observabilité — `tests/test_observability.py` (18 tests)

**Fichiers testés** : `observability/tracer.py`, `observability/feedback.py`, `observability/cost_tracker.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestTracer` | 9 | Spans, attributs, durée, export |
| `TestFeedbackCollector` | 9 | Feedback recording, stats, trends, export |
| `TestCostTracker` | 9 | Cost recording, budget, breakdown, reset |

### Prompts — `tests/test_prompts.py` (13 tests)

**Fichiers testés** : `app/prompts/templates.py`, `app/prompts/registry.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestPromptTemplates` | 5 | Structure, variables, versions |
| `TestPromptRegistry` | 8 | Registration, retrieval, compilation, versions |

### Retrieval — `tests/test_retrieval.py` (4 tests)

**Fichiers testés** : `app/components/reranker.py`, `app/components/hybrid_retriever.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestCrossEncoderReranker` | 2 | Reranking vide, ordonnancement par score |
| `TestHybridRetriever` | 2 | Combinaison vector + BM25, format SourceDocument |

### Routage — `tests/test_routing.py` (11 tests)

**Fichiers testés** : `app/services/query_router.py`, `app/agents/adaptive_router.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestQueryRouter` | 6 | Routage LLM (code, web, conversation), fallbacks synchrones |
| `TestAdaptiveRouter` | 5 | Sélection d'outils, complexité, exécution |

### Sécurité — `tests/test_security.py` (20 tests)

**Fichiers testés** : `app/security/input_guard.py`, `app/security/content_filter.py`, `app/security/output_filter.py`

| Classe | Tests | Description |
|--------|-------|-------------|
| `TestInputGuard` | 11 | Injection, PII (email, SSN, carte), sanitization |
| `TestContentFilter` | 6 | Toxicité, contenu sexuel, violence, self-harm |
| `TestOutputFilter` | 9 | Formatage, troncature, HTML, JSON validation |

## Patterns de Test

### Fixtures

```python
@pytest.fixture
def cache():
    """Create cache instance for testing."""
    return SemanticCache(
        similarity_threshold=0.95,
        ttl_seconds=3600,
    )
```

Les fixtures créent des instances isolées pour chaque test.

### Mocking LLM

```python
@pytest.mark.asyncio
async def test_route_code_query(self, query_router):
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(
        return_value=AsyncMock(
            intent="code",
            confidence=0.9,
            tools=["code_search"],
            reasoning="Code-related query",
        )
    )
    object.__setattr__(query_router.llm, "with_structured_output", lambda *args, **kwargs: mock_llm)
    result = await query_router.route("How do I write a Python function?")

    assert result.intent == IntentType.CODE
    assert "code_search" in result.tools
```

Les appels LLM sont mockés avec `AsyncMock` et `object.__setattr__` pour éviter les appels API réels et les erreurs de validation Pydantic.

### Tests Async

```python
@pytest.mark.asyncio
async def test_store_and_lookup(self, cache, sample_embedding, sample_source):
    # ...
```

Tous les tests asynchrones utilisent le décorateur `@pytest.mark.asyncio`.

### Classes de Test

Les tests sont organisés en classes (`TestQueryRouter`, `TestSemanticCache`, etc.) pour regrouper les tests par composant.

## Tests Manquants

| Composant | Fichier | Tests estimés |
|-----------|---------|---------------|
| **RAG Pipeline** | `tests/test_pipeline.py` | 8 |
| **Conversation Memory** | `tests/test_conversation.py` | 6 |
| **Query Rewriter** | `tests/test_rewriter.py` | 5 |
| **Vector Store** | `tests/test_vector_store.py` | 5 |
| **Rate Limiter** | `tests/test_rate_limiter.py` | 5 |
| **Auth** | `tests/test_auth.py` | 5 |

**Total estimé** : ~34 tests manquants pour atteindre une couverture de 80%+.

## Configuration des Outils

### Ruff (linting)

**Fichier** : `pyproject.toml`

```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C", "RUF"]
```

| Règle | Description |
|-------|-------------|
| `E` | Erreurs pycodestyle |
| `F` | Erreurs pyflakes |
| `I` | Ordonnancement des imports (isort) |
| `N` | Conventions de nommage |
| `W` | Avertissements pycodestyle |
| `B` | Bugbears (bugs potentiels) |
| `C` | Complexité cyclomatique |
| `RUF` | Règles spécifiques à Ruff |

### Mypy (typage)

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
warn_unused_ignores = false

[[tool.mypy.overrides]]
module = "sentence_transformers.*"
ignore_missing_imports = true
ignore_errors = true
```

Le mode `strict` active toutes les vérifications de type. Une override est configurée pour `sentence_transformers` qui ne fournit pas de stubs de type.

### Pytest

```toml
dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
]
```

### Configuration des Tests

Les variables d'environnement sont configurées dans `tests/conftest.py` et dans le workflow CI :

```python
# tests/conftest.py
os.environ["OPENAI_API_KEY"] = "sk-mock-key-for-testing-only"
os.environ["ENVIRONMENT"] = "development"
os.environ["API_SECRET_KEY"] = ""
os.environ["API_SECONDARY_KEY"] = ""
```

En CI, le mode `test` est activé avec `ENVIRONMENT: test` et les clés API sont vides pour désactiver l'authentification.

## Commandes de Test

| Commande | Description |
|----------|-------------|
| `uv run pytest` | Exécuter tous les tests |
| `uv run pytest tests/test_routing.py` | Exécuter un fichier de tests |
| `uv run pytest -k "test_route_code"` | Exécuter un test spécifique |
| `uv run pytest --cov=app` | Exécuter avec couverture de code |
| `uv run pytest --cov-report=html` | Rapport HTML de couverture |
| `uv run ruff check .` | Linting |
| `uv run mypy .` | Vérification de typage |

## Bonnes Pratiques

1. **Isolation** : Chaque test utilise ses propres fixtures, pas de partage d'état
2. **Mocking systématique** : Tous les appels externes (LLM, API, DB) sont mockés
3. **Noms descriptifs** : Les noms de tests décrivent le scénario testé
4. **Assertions ciblées** : Chaque test vérifie un comportement spécifique
5. **Classes de test** : Regrouper les tests par composant dans des classes
6. **Fixtures réutilisables** : Extraire les fixtures communes dans `conftest.py`
7. **Couverture cible** : Viser 80%+ de couverture de code

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide CI/CD](guide-cicd.md) — Intégration des tests dans le pipeline
- [Guide des Services](guide-services.md) — Services à tester
