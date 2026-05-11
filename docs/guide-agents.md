# Guide des Agents — Couche Intelligente

## Vue d'ensemble

La couche agents implémente des composants intelligents avec des capacités d'auto-correction. Ces agents améliorent la qualité du retrieval, décomposent les requêtes complexes et sélectionnent dynamiquement les outils.

```
┌─────────────────────────────────────────────────────────────┐
│                      Agents Layer                           │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │ Document Grader │  │ Query           │  │ Adaptive    │ │
│  │                 │  │ Decomposer      │  │ Router      │ │
│  │ • Scoring       │  │                 │  │             │ │
│  │ • Auto-correction│  │ • Décomposition │  │ • Registre  │ │
│  │ • Filtrage      │  │ • Déduplication │  │ • Complexité│ │
│  └────────┬────────┘  │ • Contexte      │  │ • Fallback  │ │
│           │           └────────┬────────┘  └──────┬──────┘ │
│           ▼                    ▼                   ▼        │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    Tools Registry                     │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │  │
│  │  │ Vector Search│  │  Web Search  │  │Code Search │  │  │
│  │  └──────────────┘  └──────────────┘  └────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Évaluateur de Documents (Document Grader)

**Fichier** : [`app/agents/document_grader.py`](../app/agents/document_grader.py)

Évalue la pertinence des documents récupérés par rapport à la requête utilisateur avec un mécanisme d'auto-correction pour les cas limites.

### Système de notation

| Grade | Score | Signification |
|-------|-------|---------------|
| `RELEVANT` | 0.9 | Le document répond directement et complètement à la requête |
| `PARTIAL` | 0.5 | Le document contient des informations utiles mais incomplètes |
| `IRRELEVANT` | 0.1 | Le document n'aide pas à répondre à la requête |

### Boucle d'auto-correction

```
Document ──► Évaluation initiale (LLM)
                 │
                 ▼
            Score proche du seuil (0.7 ± 0.1) ?
                 │
            ┌────┴────┐
           NON        OUI
            │          │
            ▼          ▼
        Résultat    Ré-évaluation stricte
        final       (critères renforcés)
                         │
                         ▼
                    Résultat final
```

### Paramètres

- **Seuil de confiance** : 0.7 (déclenche l'auto-correction si le score est dans ±0.1)
- **Retries maximum** : 2 tentatives d'auto-correction
- **Longueur maximale du document** : 2000 caractères pour l'évaluation

### Flux de traitement

1. Chaque document est évalué individuellement
2. Les documents `IRRELEVANT` sont filtrés
3. Les documents `RELEVANT` et `PARTIAL` sont conservés avec leur score
4. Les résultats sont triés par score décroissant
5. Les métadonnées sont enrichies avec `grade`, `grade_score`, `grade_reason`

## Décomposeur de Requêtes (Query Decomposer)

**Fichier** : [`app/agents/query_decomposer.py`](../app/agents/query_decomposer.py)

Décompose les requêtes complexes en sous-requêtes indépendantes pour améliorer la qualité du retrieval.

### Stratégie de décomposition

```
Requête ──► ≤ 5 mots ? ──► OUI ──► Retourner [requête] (court-circuit)
                │
                NON
                │
                ▼
           Décomposition LLM (max 4 sous-requêtes)
                │
                ▼
           Déduplication (préserve l'ordre)
                │
                ▼
           Résultat (ou [requête] si décomposition invalide)
```

### Caractéristiques

- **Court-circuit heuristique** : Les requêtes de ≤5 mots sont considérées comme simples et retournées telles quelles
- **Maximum de sous-requêtes** : 4 (configurable)
- **Déduplication** : Supprime les doublons tout en préservant l'ordre original
- **Fallback** : Si la décomposition semble incorrecte (0 ou 1 résultat identique à l'original), la requête originale est retournée

### Variante contextuelle

La méthode `decompose_with_context(query, context)` permet d'inclure un contexte additionnel pour générer des sous-requêtes plus pertinentes, utile pour les requêtes spécifiques à un document.

### Parsing de la réponse LLM

Le décomposeur gère divers formats de réponse :
- Numérotation (`1.`, `2.`, etc.)
- Puces (`-`, `*`)
- Guillemets
- Lignes vides

## Routeur Adaptatif (Adaptive Router)

**Fichier** : [`app/agents/adaptive_router.py`](../app/agents/adaptive_router.py)

Sélectionne dynamiquement les outils en fonction de l'intention et de la complexité de la requête.

### Architecture

```
Requête ──► QueryRouter (classification d'intention)
                │
                ▼
           Route de base (intent + tools)
                │
                ▼
           Sélection adaptative d'outils
                │
                ├── Ajout de fallbacks selon l'intention
                ├── Détection de complexité
                │     └── Ajout d'outils supplémentaires si complexe
                │
                ▼
           Résultat final (max 4 outils)
```

### Détection de complexité

Une requête est considérée comme complexe si :

| Indicateur | Condition |
|------------|-----------|
| Questions multiples | Plus d'un point d'interrogation |
| Conjonctions de comparaison | `compare`, `difference`, `versus`, `vs`, `pros and cons`, `advantages and disadvantages` |
| Questions explicatives | `how does`, `why does`, `explain how` |
| Longueur | Plus de 20 mots |

### Registre d'outils

Les outils sont enregistrés dynamiquement via `register_tool(name, handler)` :

```python
adaptive_router.register_tool("vector_search", vector_search_handler)
adaptive_router.register_tool("web_search", web_search_handler)
adaptive_router.execute_tool("vector_search", query="...")
```

### Chaînes de fallback

| Intention | Outils primaires | Fallbacks |
|-----------|------------------|-----------|
| `general` | `vector_search` | — |
| `document` | `vector_search`, `document_search` | `vector_search` |
| `code` | `code_search`, `vector_search` | `vector_search` |
| `web_search` | `web_search` | `vector_search` |
| `conversational` | — | — |

## Outils (Tools)

### Vector Search

**Fichier** : [`app/agents/tools/vector_search.py`](../app/agents/tools/vector_search.py)

Recherche sémantique dans le vector store avec support de filtrage par métadonnées.

```python
tool = VectorSearchTool(retriever=vector_store)
results = await tool.search(query="...", top_k=5, filter_metadata={"source": "docs"})
```

### Web Search

**Fichier** : [`app/agents/tools/web_search.py`](../app/agents/tools/web_search.py)

Recherche web en temps réel via l'API Serper.

```python
tool = WebSearchTool(api_key="serper-key")
results = await tool.search(query="...", num_results=5)
# Retourne : [{"title": "...", "snippet": "...", "url": "..."}]
```

### Code Search

**Fichier** : [`app/agents/tools/code_search.py`](../app/agents/tools/code_search.py)

Indexation et recherche dans les dépôts de code avec support de 13 extensions.

```python
tool = CodeSearchTool(repo_path="/path/to/repo")
await tool.index_repository("/path/to/repo")
results = await tool.search(query="factorial function", language="python")
```

**Extensions supportées** : `.py`, `.js`, `.ts`, `.jsx`, `.tsx`, `.java`, `.go`, `.rs`, `.rb`, `.php`, `.c`, `.cpp`, `.h`, `.cs`, `.swift`, `.kt`

## Modèles de Données Associés

**Fichier** : [`app/models.py`](../app/models.py)

| Modèle | Utilisé par |
|--------|-------------|
| `SourceDocument` | Document Grader — documents évalués |
| `RouteResult` | Adaptive Router — résultat de routage |

## Bonnes Pratiques

1. **Auto-correction** : Le Document Grader re-évalue les cas limites avec des critères plus stricts pour améliorer la fiabilité
2. **Court-circuit** : Le Query Decomposer évite les appels LLM inutiles pour les requêtes simples
3. **Filtrage précoce** : Les documents jugés `IRRELEVANT` sont immédiatement exclus du pipeline
4. **Registre dynamique** : L'Adaptive Router permet l'ajout d'outils à l'exécution via `register_tool()`
5. **Limitation** : Maximum 4 outils sélectionnés pour éviter la surcharge du contexte

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide des Services](guide-services.md) — Services qui utilisent les agents
- [Guide de Sécurité](guide-securite.md) — Filtrage des entrées et sorties
- [Guide des Tests](guide-tests.md) — Tests des agents (routage, retrieval)
