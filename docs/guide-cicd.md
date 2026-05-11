# Guide CI/CD — Pipeline d'Intégration Continue

## Vue d'ensemble

Ce document décrit les outils de linting, les commandes de test, le build Docker, le déploiement et les éléments manquants pour un pipeline CI/CD complet.

```
┌─────────────────────────────────────────────────────────────┐
│                      CI/CD Pipeline                         │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Lint    │─►│  Test    │─►│  Eval    │─►│  Build     │  │
│  │  (ruff)  │  │ (pytest) │  │ (offline)│  │  (Docker)  │  │
│  └──────────┘  └──────────┘  └──────────┘  └─────┬──────┘  │
│                                                   │         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────▼──────┐  │
│  │  Deploy  │◄─│  Health  │◄─│  Push    │◄─│  Tag       │  │
│  │  (roll)  │  │  Check   │  │  (image) │  │  (version) │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Linting

### Ruff

**Configuration** : `pyproject.toml`

```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "B", "C", "RUF"]
```

| Commande | Description |
|----------|-------------|
| `uv run ruff check .` | Vérifier le code |
| `uv run ruff check . --fix` | Corriger automatiquement |
| `uv run ruff format .` | Formater le code |

### Mypy

**Configuration** : `pyproject.toml`

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
```

| Commande | Description |
|----------|-------------|
| `uv run mypy .` | Vérifier les types |
| `uv run mypy app/` | Vérifier un répertoire |

## Tests

### Pytest

| Commande | Description |
|----------|-------------|
| `uv run pytest` | Exécuter tous les tests |
| `uv run pytest -v` | Mode verbeux |
| `uv run pytest --cov=app` | Avec couverture de code |
| `uv run pytest --cov-report=html` | Rapport HTML |
| `uv run pytest --cov-report=term-missing` | Lignes non couvertes |

### Couverture actuelle

| Fichier | Tests | Couverture estimée |
|---------|-------|-------------------|
| `test_routing.py` | 11 | QueryRouter, AdaptiveRouter |
| `test_cache.py` | 6 | SemanticCache |
| `test_retrieval.py` | 5 | Reranker, HybridRetriever |
| **Total** | **22** | **~30%** |

**Objectif** : 80%+ de couverture.

## Évaluation Automatique

### Pipeline Offline

```bash
uv run python evaluation/offline_eval.py
```

Exécute l'évaluation sur le dataset de référence et produit :
- `evaluation/eval_results/results_YYYYMMDD_HHMMSS.json`
- `evaluation/eval_results/metrics_YYYYMMDD_HHMMSS.json`

### Intégration CI Recommandée

Exécuter l'évaluation offline sur chaque pull request pour détecter les régressions de qualité.

## Build Docker

### Image Application

**Fichier** : `app/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY app/ ./app/
COPY evaluation/ ./evaluation/
COPY observability/ ./observability/
COPY scripts/ ./scripts/
COPY data/ ./data/
RUN pip install --no-cache-dir uv && uv pip install --system -e .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Image Frontend

**Fichier** : `frontend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 3000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]
```

### Commandes Docker

| Commande | Description |
|----------|-------------|
| `docker compose build` | Construire toutes les images |
| `docker compose build app` | Construire l'image app uniquement |
| `docker compose up -d` | Démarrer tous les services |
| `docker compose ps` | Voir le statut des services |
| `docker compose logs -f app` | Voir les logs de l'app |
| `docker compose down` | Arrêter tous les services |

## Déploiement

### Local

```bash
# Setup
uv sync
cp .env.example .env
# Éditer .env avec les clés API

# Migrations et seed
uv run python scripts/migrate.py
uv run python scripts/seed.py

# Démarrage
uv run uvicorn app.main:app --reload
```

### Docker Compose

```bash
# Démarrage
docker compose up -d

# Vérification
docker compose exec app python scripts/healthcheck.py

# Scaling
docker compose up -d --scale app=3
```

### Rolling Update

```bash
# Build nouvelle image
docker compose build app

# Update sans downtime
docker compose up -d --no-deps app

# Vérification
docker compose exec app python scripts/healthcheck.py
```

### Healthcheck

**Fichier** : `scripts/healthcheck.py`

Vérifie la santé de l'API et de Redis :

```bash
docker compose exec app python scripts/healthcheck.py
```

## Monitoring

| Endpoint | Usage |
|----------|-------|
| `/api/health` | Health check (GET) |
| `/api/metrics` | Métriques Prometheus (GET) |
| `docker compose logs -f` | Logs structurés (structlog) |

## Éléments Manquants

### CI/CD

| Élément | Statut | Description |
|---------|--------|-------------|
| `.github/workflows/` | ❌ Manquant | Workflows GitHub Actions |
| `Makefile` | ❌ Manquant | Commandes unifiées |
| `.gitignore` | ❌ Manquant | Fichiers à ignorer |

### Workflow GitHub Actions Recommandé

```yaml
name: CI

on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run ruff check .
      - run: uv run mypy .

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run pytest --cov=app

  eval:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv run python evaluation/offline_eval.py

  build:
    runs-on: ubuntu-latest
    needs: [lint, test, eval]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build
```

### Makefile Recommandé

```makefile
.PHONY: install lint test eval dev docker-build docker-up docker-down

install:
	uv sync

lint:
	uv run ruff check .
	uv run mypy .

test:
	uv run pytest --cov=app

eval:
	uv run python evaluation/offline_eval.py

dev:
	uv run uvicorn app.main:app --reload

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
```

### .gitignore Recommandé

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/

# Environment
.env
.env.local

# Evaluation results
evaluation/eval_results/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Docker
chroma_data/
postgres_data/
redis_data/
```

## Bonnes Pratiques

1. **Lint avant tout** : Exécuter ruff et mypy avant les tests
2. **Tests isolés** : Chaque test doit être indépendant et reproductible
3. **Évaluation sur PR** : Détecter les régressions de qualité avant merge
4. **Build conditionnel** : Ne build que si lint + test + eval passent
5. **Healthchecks** : Vérifier la santé après chaque déploiement
6. **Rolling updates** : Utiliser `--no-deps` pour éviter les restarts inutiles
7. **Logs structurés** : Utiliser structlog pour l'analyse automatisée

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide des Tests](guide-tests.md) — Stratégie de test détaillée
- [Guide d'Évaluation](guide-evaluation.md) — Pipeline d'évaluation offline
- [Guide de Déploiement](deployment.md) — Guide de déploiement complet
