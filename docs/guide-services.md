# Guide des Services — Couche Métier

## Vue d'ensemble

La couche services constitue le cœur métier de l'application. Elle orchestre le pipeline RAG, gère le cache sémantique, la mémoire conversationnelle, la réécriture et le routage des requêtes.

```
┌─────────────────────────────────────────────────────────────┐
│                      Services Layer                         │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐ │
│  │  RAG Pipeline│◄───│ Query        │◄───│ Conversation  │ │
│  │  (6 étapes)  │    │ Rewriter     │    │ Memory        │ │
│  └──────┬───────┘    └──────┬───────┘    └───────────────┘ │
│         │                   │                               │
│  ┌──────▼───────┐    ┌──────▼───────┐                       │
│  │ Semantic     │    │ Query        │                       │
│  │ Cache        │    │ Router       │                       │
│  └──────────────┘    └──────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

Les 5 services sont implémentés comme des singletons au niveau module et communiquent entre eux via des appels directs ou le registre de prompts.

## RAG Pipeline

**Fichier** : [`app/services/rag_pipeline.py`](../app/services/rag_pipeline.py)

Le pipeline RAG orchestre les 6 étapes du traitement d'une requête :

```
┌─────────┐    ┌──────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────┐    ┌─────────────┐
│ 1. Cache│───►│ 2. Rewrite│───►│ 3. Decompose │───►│ 4. Retrieve+Grade│───►│ 5. Generate│───►│ 6. Store    │
│  Check  │    │  Query    │    │  Query        │    │  Documents       │    │  Response  │    │  in Cache   │
└─────────┘    └──────────┘    └──────────────┘    └──────────────────┘    └────────────┘    └─────────────┘
```

### Étapes détaillées

| Étape | Action | Composant utilisé |
|-------|--------|-------------------|
| 1 | Vérification du cache sémantique | `SemanticCache.lookup()` |
| 2 | Réécriture avec contexte conversationnel | `QueryRewriter.rewrite()` |
| 3 | Décomposition en sous-requêtes | `QueryDecomposer.decompose()` |
| 4 | Retrieval hybride + grading | `HybridRetriever.retrieve()` + `DocumentGrader.grade()` |
| 5 | Génération de réponse | `ChatOpenAI.ainvoke()` avec prompt `rag_generation` |
| 6 | Stockage dans le cache | `SemanticCache.store()` |

### Caractéristiques

- **Déduplication** : Les documents récupérés sont dédupliqués en conservant le score le plus élevé
- **Limitation des sources** : Maximum 5 documents utilisés pour la génération
- **Tracking des tokens** : Input/output tokens extraits des métadonnées de réponse
- **Tracing** : Chaque étape est tracée via `tracer.start_span()`
- **Cache hit** : Retour immédiat si la requête est trouvée dans le cache sémantique

### Configuration

```python
rag_pipeline = RAGPipeline()
rag_pipeline.set_retriever(hybrid_retriever)  # Injection du retriever
```

## Cache Sémantique

**Fichier** : [`app/services/semantic_cache.py`](../app/services/semantic_cache.py)

Cache les réponses basé sur la similarité sémantique des requêtes plutôt que sur une correspondance exacte.

### Fonctionnement

```
Requête → Embedding (OpenAI) → Comparaison cosinus → Seuil 0.95 → Cache hit/miss
```

### Opérations

| Méthode | Description |
|---------|-------------|
| `lookup(query)` | Recherche une réponse cache avec similarité ≥ seuil |
| `store(query, response, sources)` | Stocke une nouvelle entrée avec son embedding |
| `invalidate(query)` | Supprime une entrée spécifique |
| `clear()` | Vide tout le cache |
| `get_stats()` | Statistiques (nombre d'entrées, seuil, TTL) |

### Paramètres

- **Seuil de similarité** : 0.95 (configurable via `CACHE_SIMILARITY_THRESHOLD`)
- **TTL** : 3600 secondes (configurable via `CACHE_TTL_SECONDS`)
- **Modèle d'embedding** : `text-embedding-3-small`

### Optimisation

Les embeddings des requêtes sont mis en cache localement via un hash MD5 pour éviter des appels répétés à l'API OpenAI.

## Mémoire Conversationnelle

**Fichier** : [`app/services/conversation.py`](../app/services/conversation.py)

Gère l'historique des conversations avec une fenêtre glissante et une auto-résumation.

### Architecture

```
Messages ──► Fenêtre glissante (10 messages)
                │
                ▼ (seuil atteint : 20 messages)
           Auto-résumé par LLM
                │
                ▼
   Résumé + 10 derniers messages → Contexte pour le LLM
```

### Fonctionnalités

| Méthode | Description |
|---------|-------------|
| `add_message(conversation_id, role, content)` | Ajoute un message à l'historique |
| `get_context(conversation_id)` | Retourne (résumé, messages_récents) |
| `get_state(conversation_id)` | Retourne l'état complet de la conversation |
| `clear(conversation_id)` | Supprime une conversation |
| `to_langchain_messages(conversation_id)` | Conversion en messages LangChain |

### Auto-résumation

Lorsque le nombre de messages atteint le seuil (20), un résumé en 2-3 phrases est généré par le LLM et les anciens messages sont supprimés, ne conservant que les 10 plus récents.

## Réécriture de Requête

**Fichier** : [`app/services/query_rewriter.py`](../app/services/query_rewriter.py)

Améliore les requêtes en injectant le contexte conversationnel et en générant des alternatives.

### Méthodes

| Méthode | Rôle | Prompt utilisé |
|---------|------|----------------|
| `rewrite(query, conversation_id)` | Réécrit la requête avec le contexte conversationnel (résout les pronoms, références) | `query_rewrite` |
| `expand(query)` | Génère 3 alternatives pour élargir le retrieval | `query_expand` |
| `clarify(query)` | Détecte si la requête est ambiguë et propose une question de clarification | `query_clarify` |
| `normalize(query)` | Normalise (whitespace, casing) | — |

### Flux de réécriture

```
Requête brute ──► Normalisation
                      │
                      ▼ (si conversation_id présent)
                 Récupération contexte
                      │
                      ▼
                 Réécriture LLM (résumé + messages récents)
                      │
                      ▼
                 Requête autonome (self-contained)
```

## Routage de Requête

**Fichier** : [`app/services/query_router.py`](../app/services/query_router.py)

Classifie l'intention des requêtes et sélectionne les outils appropriés.

### Intentions supportées

| Intention | Outils associés | Exemple |
|-----------|-----------------|---------|
| `general` | `vector_search` | "Qu'est-ce que le machine learning ?" |
| `document` | `vector_search`, `document_search` | "Que dit le document sur..." |
| `code` | `code_search`, `vector_search` | "Comment écrire une fonction Python ?" |
| `web_search` | `web_search` | "Quelle est la météo aujourd'hui ?" |
| `conversational` | — | "Bonjour, comment vas-tu ?" |

### Modes de routage

**Mode LLM (principal)** : Utilise `ChatOpenAI.with_structured_output()` pour obtenir une décision structurée (`RouteDecision`) avec intention, confiance, outils et raisonnement.

**Mode mots-clés (fallback)** : Routage synchrone basé sur des mots-clés lorsque le LLM n'est pas disponible :

| Mots-clés | Intention détectée |
|-----------|-------------------|
| `code`, `function`, `api`, `python`, `javascript` | `code` |
| `current`, `latest`, `today`, `news`, `weather` | `web_search` |
| `hi`, `hello`, `help`, `thanks` | `conversational` |
| Autres | `general` |

## Modèles de Données Associés

**Fichier** : [`app/models.py`](../app/models.py)

| Modèle | Utilisé par |
|--------|-------------|
| `PipelineResult` | RAG Pipeline — résultat d'exécution |
| `CacheEntry` | Semantic Cache — entrée de cache |
| `ConversationState` / `ConversationMessage` | Conversation Memory — état conversationnel |
| `RouteResult` | Query Router — résultat de routage |

## Bonnes Pratiques

1. **Injection de dépendances** : Le retriever est injecté via `set_retriever()` pour faciliter les tests
2. **Single Responsibility** : Chaque service a une responsabilité unique et bien définie
3. **Logging structuré** : Tous les services utilisent `structlog` avec des attributs contextuels
4. **Gestion d'erreurs** : Les services retournent des valeurs par défaut plutôt que de lever des exceptions
5. **Async-first** : Toutes les opérations I/O sont asynchrones (`async def`)

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide des Agents](guide-agents.md) — Agents auto-correctifs utilisés par le pipeline
- [Guide d'Observabilité](guide-observabilite.md) — Traçage des étapes du pipeline
- [Guide Base de Données](guide-base-de-donnees.md) — Configuration du cache et des stores
