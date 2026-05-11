# Guide Base de Données — ChromaDB, Redis, PostgreSQL

## Vue d'ensemble

L'application utilise trois systèmes de stockage pour couvrir les besoins de vector store, cache distribué et base de données relationnelle.

```
┌─────────────────────────────────────────────────────────────┐
│                    Storage Layer                            │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   ChromaDB   │  │    Redis     │  │   PostgreSQL     │  │
│  │              │  │              │  │                  │  │
│  │ Vector Store │  │ Cache        │  │ Données          │  │
│  │              │  │ Distribué    │  │ Relationnelles   │  │
│  │ Port: 8001   │  │ Port: 6379   │  │ Port: 5432       │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## ChromaDB — Vector Store

**Configuration** : `CHROMA_HOST=localhost`, `CHROMA_PORT=8001`

ChromaDB stocke les embeddings des documents pour la recherche sémantique.

### Rôle dans l'architecture

```
Documents ──► Embedding (OpenAI) ──► ChromaDB
                                        │
                                        ▼
                              Recherche par similarité
                                        │
                                        ▼
                              Documents les plus pertinents
```

### Configuration Docker

```yaml
chromadb:
  image: chromadb/chroma:latest
  ports:
    - "8001:8000"
  volumes:
    - chroma_data:/chroma/chroma
```

### Persistance

Les données sont persistées via le volume Docker `chroma_data` monté sur `/chroma/chroma`.

### Intégration actuelle

ChromaDB est configuré dans `docker-compose.yml` mais **n'est pas encore intégré au code de l'application**. Le `HybridRetriever` attend un `vector_retriever` injecté qui doit être connecté à ChromaDB.

### Configuration d'index

Le répertoire `data/index_config/` est prévu pour contenir :
- `collections.json` — Configuration des collections
- `metadata_schema.json` — Schéma des métadonnées
- `embedding_config.json` — Configuration des embeddings

Ces fichiers sont **documentés mais non encore créés**.

## Redis — Cache Distribué

**Configuration** : `REDIS_URL=redis://localhost:6379`

Redis est prévu pour le cache distribué et la gestion de sessions.

### Configuration Docker

```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

### État actuel

Le package `redis` est inclus dans les dépendances (`pyproject.toml`) et l'URL est configurée dans `app/config.py`, mais **le SemanticCache utilise actuellement un dictionnaire en mémoire** plutôt que Redis.

### Migration vers Redis

Pour passer du cache mémoire au cache Redis :

1. Remplacer le dictionnaire `_cache` par des commandes Redis (`SET`, `GET`, `EXPIRE`)
2. Stocker les embeddings dans Redis (ou un vector store Redis avec RediSearch)
3. Utiliser la connexion Redis configurée via `settings.redis_url`

### Persistance

Les données Redis sont persistées via le volume Docker `redis_data` monté sur `/data`.

## PostgreSQL — Base de Données Relationnelle

**Configuration** : `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_app`

PostgreSQL est prévu pour stocker les conversations, feedbacks, coûts et métadonnées.

### Configuration Docker

```yaml
db:
  image: postgres:16-alpine
  ports:
    - "5432:5432"
  environment:
    - POSTGRES_USER=postgres
    - POSTGRES_PASSWORD=postgres
    - POSTGRES_DB=ai_app
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

### État actuel

L'URL de connexion est configurée dans `app/config.py` mais **aucune intégration SQLAlchemy n'existe** dans le code. Les scripts de migration et de seed sont des stubs.

### Scripts de base de données

**Fichier** : [`scripts/migrate.py`](../scripts/migrate.py) — **Stub**

3 migrations sont définies mais toutes sont des opérations no-op (uniquement des logs) :
1. Création des tables de base
2. Ajout d'index
3. Mise à jour du schéma

**Fichier** : [`scripts/seed.py`](../scripts/seed.py) — **Partiel**

- 3 documents exemples sont définis mais **non insérés dans ChromaDB** (uniquement loggés)
- Le seeding des prompts fonctionne via le registre

### Tables prévues

| Table | Données stockées |
|-------|------------------|
| `conversations` | Historique des conversations |
| `messages` | Messages individuels |
| `feedback` | Feedback utilisateur lié aux traces |
| `cost_records` | Enregistrements de coûts |
| `eval_results` | Résultats d'évaluation |

## Docker Compose — Orchestration

**Fichier** : [`docker-compose.yml`](../docker-compose.yml)

5 services orchestrés avec dépendances et volumes persistants :

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Frontend │───►│   App    │───►│  Redis   │
│ (port    │    │ (port    │    │ (port    │
│  3000)   │    │  8000)   │    │  6379)   │
└──────────┘    └────┬─────┘    └──────────┘
                     │
              ┌──────┴──────┐
              ▼             ▼
       ┌──────────┐  ┌──────────┐
       │PostgreSQL│  │ ChromaDB │
       │ (port    │  │ (port    │
       │  5432)   │  │  8001)   │
       └──────────┘  └──────────┘
```

### Volumes persistants

| Volume | Service | Données |
|--------|---------|---------|
| `redis_data` | Redis | Cache Redis |
| `postgres_data` | PostgreSQL | Tables et index |
| `chroma_data` | ChromaDB | Collections et embeddings |

### Dépendances entre services

| Service | Dépend de |
|---------|-----------|
| `app` | `redis`, `db` |
| `frontend` | `app` |
| `redis` | — |
| `db` | — |
| `chromadb` | — |

## Healthcheck

**Fichier** : [`scripts/healthcheck.py`](../scripts/healthcheck.py)

Vérifie la santé des services :

| Check | Méthode | URL/Connection |
|-------|---------|----------------|
| API | HTTP GET | `http://localhost:8000/api/health` |
| Redis | Ping | `redis://localhost:6379` |
| Database | Log (stub) | `DATABASE_URL` |

## Résumé de l'État d'Intégration

| Composant | Configuration | Intégration code | Statut |
|-----------|---------------|------------------|--------|
| **ChromaDB** | ✅ docker-compose + config | ❌ Non intégré | À implémenter |
| **Redis** | ✅ docker-compose + config + dépendance | ❌ Cache mémoire | À migrer |
| **PostgreSQL** | ✅ docker-compose + config | ❌ Aucun modèle SQLAlchemy | À implémenter |

## Bonnes Pratiques

1. **Configuration par environnement** : Utiliser les variables d'environnement pour les URLs de connexion
2. **Volumes persistants** : Toujours utiliser des volumes Docker pour la persistance des données
3. **Healthchecks** : Vérifier la connectivité de chaque service avant le démarrage de l'application
4. **Migrations versionnées** : Utiliser Alembic pour gérer les migrations de schéma
5. **Connexions poolées** : Utiliser des connection pools pour Redis et PostgreSQL en production

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide des Services](guide-services.md) — Services qui utilisent le cache et le retrieval
- [Guide de Déploiement](deployment.md) — Déploiement avec Docker Compose
