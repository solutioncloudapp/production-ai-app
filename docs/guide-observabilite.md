# Guide d'Observabilité — Traçage, Feedback et Coûts

## Vue d'ensemble

La couche d'observabilité fournit une visibilité complète sur le fonctionnement de l'application : traçage distribué des opérations, collecte de feedback utilisateur et suivi des coûts d'utilisation des modèles.

```
┌─────────────────────────────────────────────────────────────┐
│                  Observability Layer                        │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │     Tracer      │  │   Feedback      │  │    Cost     │ │
│  │                 │  │   Collector     │  │   Tracker   │ │
│  │ • Spans         │  │ • Ratings 1-5   │  │ • 6 modèles │ │
│  │ • Hiérarchie    │  │ • Tendances     │  │ • Par query │ │
│  │ • Context vars  │  │ • Fine-tuning   │  │ • Budget    │ │
│  │ • Export        │  │                 │  │ • Alerts    │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Tracer — Traçage Distribué

**Fichier** : [`observability/tracer.py`](../observability/tracer.py)

Système de traçage hiérarchique qui enregistre chaque étape du traitement avec des spans imbriquées.

### Architecture des Spans

```
Trace ID: abc-123
│
├── Span: http_request (parent)
│   ├── Span: chat_request
│   │   ├── Span: rag_pipeline
│   │   │   ├── Span: cache_check
│   │   │   ├── Span: query_rewrite
│   │   │   ├── Span: query_decompose
│   │   │   ├── Span: retrieve_and_grade
│   │   │   └── Span: generate_response
│   │   └── Span: content_filter
│   └── Span: cost_tracking
```

### Composants clés

| Classe | Rôle |
|--------|------|
| `Span` | Représente une unité de travail avec nom, timestamps, attributs et statut |
| `SpanContext` | Context manager pour le cycle de vie automatique des spans (`__enter__`/`__exit__`) |
| `Tracer` | Gestionnaire central des spans actives et des traces complétées |

### Utilisation

```python
from observability.tracer import tracer

with tracer.start_span("nom_de_l_operation") as span:
    span.set_attribute("cle", "valeur")
    # ... opération ...
# La span se termine automatiquement (ok ou error selon exception)
```

### Propagation du Trace ID

Le trace ID est propagé via une `ContextVar` (`current_trace_id`) pour assurer la cohérence à travers les appels asynchrones.

### Attributs tracés

| Attribut | Exemple | Source |
|----------|---------|--------|
| `http.method` | `POST` | Middleware HTTP |
| `http.url` | `/api/chat` | Middleware HTTP |
| `http.status_code` | `200` | Middleware HTTP |
| `query_length` | `45` | RAG Pipeline |
| `cache_hit` | `true/false` | RAG Pipeline |
| `rewritten_query` | `"..."` | RAG Pipeline |
| `num_sub_queries` | `2` | RAG Pipeline |
| `num_documents` | `5` | RAG Pipeline |
| `input_tokens` | `1500` | RAG Pipeline |
| `output_tokens` | `300` | RAG Pipeline |
| `latency_ms` | `1250.5` | RAG Pipeline |
| `blocked` | `true` | Input Guard |
| `route` | `general` | Adaptive Router |

### Export

Les traces complétées peuvent être exportées via `tracer.export_trace(trace_id)` et sont stockées dans `tracer.get_traces()`.

## Feedback Collector — Collecte de Feedback

**Fichier** : [`observability/feedback.py`](../observability/feedback.py)

Collecte et analyse le feedback utilisateur lié aux traces pour l'amélioration continue.

### Enregistrement de feedback

```python
from observability.feedback import feedback_collector

feedback_collector.record(
    trace_id="abc-123",
    rating=5,
    comment="Excellente réponse !"
)
```

### Fonctionnalités

| Méthode | Description |
|---------|-------------|
| `record(trace_id, rating, comment)` | Enregistre un feedback (rating 1-5) |
| `get_feedback(trace_id)` | Récupère le feedback d'une trace |
| `get_all_feedback()` | Retourne tous les enregistrements |
| `get_stats()` | Statistiques (total, moyenne, distribution) |
| `get_low_rated(threshold=3)` | Feedbacks avec rating < seuil |
| `export_for_finetuning()` | Export des feedbacks ≥4 pour fine-tuning |
| `get_trend(window_hours=24)` | Tendances horaires sur une fenêtre |

### Statistiques produites

```python
{
    "total": 150,
    "avg_rating": 4.2,
    "rating_distribution": {5: 80, 4: 40, 3: 20, 2: 8, 1: 2},
    "with_comments": 45
}
```

### Analyse de tendances

La méthode `get_trend()` agrège les feedbacks par heure sur une fenêtre glissante, permettant de détecter les variations de qualité dans le temps.

## Cost Tracker — Suivi des Coûts

**Fichier** : [`observability/cost_tracker.py`](../observability/cost_tracker.py)

Calcule et suit les coûts d'utilisation des modèles LLM et d'embedding.

### Tarification des modèles (par million de tokens)

| Modèle | Input | Output |
|--------|-------|--------|
| `gpt-4o` | $5.00 | $15.00 |
| `gpt-4o-mini` | $0.15 | $0.60 |
| `gpt-4` | $30.00 | $60.00 |
| `gpt-3.5-turbo` | $0.50 | $1.50 |
| `text-embedding-3-small` | $0.02 | $0.00 |
| `text-embedding-3-large` | $0.13 | $0.00 |

### Suivi multi-niveau

| Niveau | Méthode | Description |
|--------|---------|-------------|
| **Par requête** | `record()` | Enregistre le coût d'une invocation |
| **Par conversation** | `get_conversation_cost(id)` | Coût total d'une conversation |
| **Par jour** | `get_daily_cost()` | Coût cumulé du jour (reset automatique) |
| **Par modèle** | `get_model_breakdown()` | Breakdown avec tokens et nombre de requêtes |

### Alertes budget

```python
cost_tracker = CostTracker(budget_limit=100.0)

# Si le coût quotidien dépasse le budget :
# → Log warning avec daily_cost et limit
```

### Statistiques de budget

```python
{
    "daily_cost": 12.45,
    "budget_limit": 100.0,
    "remaining": 87.55,
    "utilization_pct": 12.45
}
```

## Intégration dans le Pipeline

```
Requête ──► Tracer: start_span("chat_request")
                │
                ▼
           Input Guard ──► Tracer: set_attribute("blocked", true/false)
                │
                ▼
           RAG Pipeline ──► Tracer: spans imbriquées pour chaque étape
                │              │
                │              └─► Cost Tracker: record(model, tokens)
                ▼
           Content Filter
                │
                ▼
           Output Filter ──► Tracer: set_attribute("response_length", n)
                │
                ▼
           Réponse ──► Tracer: end_span()
```

## Modèles de Données Associés

**Fichier** : [`app/models.py`](../app/models.py)

| Modèle | Contenu |
|--------|---------|
| `TracerSpan` | `trace_id`, `span_id`, `name`, `parent_id`, `start_time`, `end_time`, `attributes`, `status` |
| `FeedbackRecord` | `trace_id`, `rating` (1-5), `comment`, `timestamp` |
| `CostRecord` | `conversation_id`, `model`, `input_tokens`, `output_tokens`, `cost_usd`, `timestamp` |

## Bonnes Pratiques

1. **Context manager** : Toujours utiliser `with tracer.start_span()` pour garantir la fermeture des spans
2. **Attributs riches** : Ajouter des attributs pertinents à chaque span pour le débogage
3. **Trace ID unique** : Générer un trace ID par requête HTTP pour corréler toutes les opérations
4. **Budget alerts** : Configurer des limites budgétaires adaptées à l'utilisation attendue
5. **Feedback lié aux traces** : Associer chaque feedback à un trace_id pour permettre l'analyse rétrospective
6. **Reset quotidien** : Le CostTracker reset automatiquement les coûts quotidiens à minuit UTC

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide des Services](guide-services.md) — Services tracés par l'observabilité
- [Guide d'Évaluation](guide-evaluation.md) — Monitoring online qui utilise les métriques d'observabilité
