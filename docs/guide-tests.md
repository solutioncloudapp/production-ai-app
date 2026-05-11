# Guide des Tests — Stratégie et Patterns

## Vue d'ensemble

La suite de tests couvre actuellement le routage, le cache et le retrieval avec 22 tests. Cette documentation décrit les tests existants, les patterns utilisés et les tests manquants.

```
┌─────────────────────────────────────────────────────────────┐
│                      Test Suite                             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ test_routing │  │ test_cache   │  │ test_retrieval   │  │
│  │              │  │              │  │                  │  │
│  │ 11 tests     │  │ 6 tests      │  │ 5 tests          │  │
│  │              │  │              │  │                  │  │
│  │ • QueryRouter│  │ • Store      │  │ • Reranker       │  │
│  │ • Adaptive   │  │ • Lookup     │  │ • Hybrid         │  │
│  │ • Complexité │  │ • Invalidate │  │ • Source docs    │  │
│  │ • Tools      │  │ • Clear      │  │                  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                             │
│  Couverture actuelle : ~30% du code                         │
│  Objectif : 80%+                                            │
└─────────────────────────────────────────────────────────────┘
```

## Tests Existants

### Routage — `tests/test_routing.py` (11 tests)

**Fichiers testés** : `app/services/query_router.py`, `app/agents/adaptive_router.py`

| Test | Classe | Description |
|------|--------|-------------|
| `test_route_code_query` | `TestQueryRouter` | Routage LLM pour requêtes code |
| `test_route_web_search_query` | `TestQueryRouter` | Routage LLM pour recherche web |
| `test_route_conversational_query` | `TestQueryRouter` | Routage LLM pour conversation |
| `test_route_sync_fallback_code` | `TestQueryRouter` | Fallback mots-clés pour code |
| `test_route_sync_fallback_web` | `TestQueryRouter` | Fallback mots-clés pour web |
| `test_route_sync_fallback_general` | `TestQueryRouter` | Fallback mots-clés pour général |
| `test_route_with_tool_selection` | `TestAdaptiveRouter` | Sélection adaptative d'outils |
| `test_is_complex_query` | `TestAdaptiveRouter` | Détection de requêtes complexes |
| `test_register_tool` | `TestAdaptiveRouter` | Enregistrement d'outils |
| `test_execute_tool` | `TestAdaptiveRouter` | Exécution d'outils |
| `test_execute_missing_tool` | `TestAdaptiveRouter` | Exécution d'outil inexistant |

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

### Retrieval — `tests/test_retrieval.py` (5 tests)

**Fichiers testés** : `app/components/reranker.py`, `app/components/hybrid_retriever.py`

| Test | Classe | Description |
|------|--------|-------------|
| `test_rerank_empty` | `TestCrossEncoderReranker` | Reranking avec liste vide |
| `test_rerank_orders_by_score` | `TestCrossEncoderReranker` | Ordonnancement par score |
| `test_retrieve_combines_sources` | `TestHybridRetriever` | Combinaison vector + BM25 |
| `test_retrieve_returns_source_documents` | `TestHybridRetriever` | Format SourceDocument correct |

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
with patch.object(query_router.llm, "with_structured_output") as mock_output:
    mock_output.return_value.ainvoke = AsyncMock(return_value=AsyncMock(
        intent="code",
        confidence=0.9,
        tools=["code_search"],
        reasoning="Code-related query",
    ))
    result = await query_router.route("How do I write a Python function?")
```

Les appels LLM sont mockés avec `AsyncMock` pour éviter les appels API réels.

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

| Composant | Fichier à créer | Tests estimés |
|-----------|-----------------|---------------|
| **Input Guard** | `tests/test_security.py` | 8 |
| **Content Filter** | `tests/test_security.py` | 5 |
| **Output Filter** | `tests/test_security.py` | 6 |
| **Document Grader** | `tests/test_agents.py` | 6 |
| **Query Decomposer** | `tests/test_agents.py` | 5 |
| **RAG Pipeline** | `tests/test_pipeline.py` | 8 |
| **Conversation Memory** | `tests/test_conversation.py` | 6 |
| **Query Rewriter** | `tests/test_rewriter.py` | 5 |
| **Tracer** | `tests/test_observability.py` | 5 |
| **Feedback Collector** | `tests/test_observability.py` | 5 |
| **Cost Tracker** | `tests/test_observability.py` | 6 |
| **Offline Evaluator** | `tests/test_evaluation.py` | 5 |
| **Online Monitor** | `tests/test_evaluation.py` | 5 |
| **Prompt Registry** | `tests/test_prompts.py` | 5 |
| **Fixtures partagées** | `tests/conftest.py` | — |

**Total estimé** : ~80 tests manquants pour atteindre une couverture de 80%+.

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
```

Le mode `strict` active toutes les vérifications de type.

### Pytest

```toml
dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
]
```

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
