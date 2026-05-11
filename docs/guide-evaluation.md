# Guide d'Évaluation — Dataset de Référence et Pipelines

## Vue d'ensemble

La couche d'évaluation permet de mesurer et monitorer la qualité des réponses du système via un dataset de référence, un pipeline d'évaluation offline et un monitoring online avec détection de drift.

```
┌─────────────────────────────────────────────────────────────┐
│                   Evaluation Layer                          │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  Golden Dataset │  │  Offline Eval   │  │  Online     │ │
│  │                 │  │                 │  │  Monitor    │ │
│  │ • 8 cas de test │  │ • Pertinence    │  │ • Latence   │ │
│  │ • 5 catégories  │  │ • Fidélité      │  │ • p95/p99   │ │
│  │ • 3 difficultés │  │ • Pert. réponse │  │ • Erreurs   │ │
│  │                 │  │ • Latence       │  │ • Drift     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Dataset de Référence (Golden Dataset)

**Fichier** : [`evaluation/golden_dataset.json`](../evaluation/golden_dataset.json)

Collection de 8 cas de test servant de référence pour évaluer la qualité du système.

### Structure d'un cas de test

```json
{
  "id": "eval_001",
  "query": "What is the capital of France?",
  "expected_answer": "The capital of France is Paris.",
  "category": "factual",
  "difficulty": "easy",
  "expected_sources": ["france_geography"],
  "metadata": {
    "topic": "geography",
    "created_at": "2024-01-15"
  }
}
```

### Répartition des cas

| ID | Catégorie | Difficulté | Sujet |
|----|-----------|------------|-------|
| `eval_001` | factual | easy | Géographie |
| `eval_002` | explanation | medium | Machine learning |
| `eval_003` | comparison | hard | Python vs JavaScript |
| `eval_004` | product | easy | Fonctionnalités produit |
| `eval_005` | howto | easy | Support utilisateur |
| `eval_006` | explanation | medium | Apprentissage supervisé vs non-supervisé |
| `eval_007` | code | easy | Fonction factorielle Python |
| `eval_008` | explanation | hard | Sécurité API |

### Catégories

| Catégorie | Description |
|-----------|-------------|
| `factual` | Questions factuelles avec réponse courte et précise |
| `explanation` | Explications de concepts |
| `comparison` | Comparaisons entre éléments |
| `product` | Questions sur le produit |
| `howto` | Guides et procédures |
| `code` | Questions de programmation |
| `security` | Bonnes pratiques de sécurité |

### Niveaux de difficulté

| Niveau | Description |
|--------|-------------|
| `easy` | Réponse directe, contexte minimal requis |
| `medium` | Explication structurée, compréhension conceptuelle |
| `hard` | Analyse comparative, synthèse de multiples sources |

## Évaluation Offline

**Fichier** : [`evaluation/offline_eval.py`](../evaluation/offline_eval.py)

Pipeline d'évaluation batch qui exécute le système sur le dataset de référence et calcule des métriques de qualité.

### Métriques évaluées

| Métrique | Méthode | Échelle | Description |
|----------|---------|---------|-------------|
| **Pertinence** | LLM (prompt `eval_relevance`) | 1-5 | Dans quelle mesure la réponse adresse la question |
| **Fidélité** | LLM (prompt `eval_faithfulness`) | 1-5 | La réponse est-elle fidèle au contexte (pas d'hallucination) |
| **Pertinence de réponse** | Similarité cosinus embeddings | 1-5 | Similarité sémantique entre question et réponse |
| **Latence** | Chronométrage | ms | Temps de réponse |

### Calcul de la pertinence de réponse

```
Question → Embedding
                │
                ▼
           Similarité cosinus
                │
                ▼
           Score = 1 + (similarité × 4)  →  échelle 1-5
```

### Métriques agrégées

```python
EvalMetrics(
    total_tests=8,
    passed_tests=6,           # pertinence ≥ 3.0 ET fidélité ≥ 3.0
    avg_relevance=4.1,
    avg_faithfulness=3.8,
    avg_answer_relevance=3.9,
    avg_latency_ms=1250.5,
    pass_rate=75.0,           # (passed / total) × 100
    timestamp=datetime.utcnow()
)
```

### Modes d'évaluation

| Mode | Description |
|------|-------------|
| `evaluate_all()` | Évalue tous les cas du dataset |
| `evaluate_subset(category, difficulty)` | Évalue un sous-ensemble filtré |

### Sauvegarde des résultats

Les résultats sont sauvegardés en JSON horodaté dans `evaluation/eval_results/` :
- `results_YYYYMMDD_HHMMSS.json` — Résultats individuels
- `metrics_YYYYMMDD_HHMMSS.json` — Métriques agrégées

## Monitoring Online

**Fichier** : [`evaluation/online_monitor.py`](../evaluation/online_monitor.py)

Monitor les métriques en production en temps réel avec une fenêtre glissante et détection de drift.

### Métriques monitorées

| Métrique | Calcul |
|----------|--------|
| `total_queries` | Nombre total de requêtes traitées |
| `avg_latency_ms` | Moyenne des latences |
| `p95_latency_ms` | 95e percentile des latences |
| `p99_latency_ms` | 99e percentile des latences |
| `error_rate` | Requêtes en erreur / total |
| `cache_hit_rate` | Cache hits / total |
| `avg_feedback_score` | Moyenne des scores de feedback |

### Fenêtre glissante

Le monitor utilise des `deque` avec `maxlen=1000` pour ne conserver que les 1000 requêtes les plus récentes.

### Détection de Drift

Le monitor compare les métriques courantes à une baseline définie via `set_baseline()` et génère des alertes si la déviation dépasse le seuil (20% par défaut).

#### Alertes de drift

| Métrique | Condition | Sévérité |
|----------|-----------|----------|
| **Latence** | Déviation > 20% de la baseline | `warning` |
| **Latence** | Déviation > 50% de la baseline | `critical` |
| **Taux d'erreur** | > 10% d'erreurs | `critical` |
| **Score feedback** | Déviation > 20% de la baseline (min 10 feedbacks) | `warning` |

### Structure d'une alerte

```python
DriftAlert(
    metric="latency",
    current_value=2500.0,
    baseline_value=1200.0,
    deviation=1.08,
    timestamp=datetime.utcnow(),
    severity="critical"
)
```

### Configuration

| Paramètre | Valeur par défaut | Description |
|-----------|-------------------|-------------|
| `window_size` | 1000 | Nombre de requêtes dans la fenêtre glissante |
| `alert_threshold` | 0.2 (20%) | Seuil de déviation pour les alertes |

## Flux d'Évaluation Complet

```
Golden Dataset ──► OfflineEvaluator ──► Métriques de référence
                        │
                        ▼
                   Baseline pour OnlineMonitor
                        │
                        ▼
              Production ──► OnlineMonitor ──► Détection de drift
                        │                          │
                        ▼                          ▼
                   Feedback ──► Alertes si déviation
```

## Modèles de Données Associés

**Fichier** : [`app/models.py`](../app/models.py)

| Modèle | Contenu |
|--------|---------|
| `EvalResult` | `query`, `expected_answer`, `actual_answer`, 3 scores, `latency_ms`, `timestamp` |

## Bonnes Pratiques

1. **Dataset représentatif** : Couvrir toutes les catégories et niveaux de difficulté attendus en production
2. **Évaluation régulière** : Exécuter le pipeline offline avant chaque déploiement
3. **Baseline mise à jour** : Recalibrer la baseline du monitor après les améliorations majeures
4. **Alertes actionnables** : Configurer les seuils d'alerte pour déclencher des actions concrètes
5. **Export pour fine-tuning** : Utiliser `export_for_finetuning()` pour collecter des exemples de haute qualité

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide d'Observabilité](guide-observabilite.md) — Feedback collector utilisé par le monitor
- [Guide CI/CD](guide-cicd.md) — Évaluation automatique dans le pipeline
