# Guide Frontend — Interface Utilisateur

## Vue d'ensemble

Le frontend est une application FastAPI séparée qui sert d'interface utilisateur pour interagir avec l'API principale. Actuellement à l'état de squelette, il est conçu pour être développé en une interface chat complète.

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Layer                           │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │               frontend/app.py                         │  │
│  │                                                       │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌───────────┐ │  │
│  │  │   Index     │    │  /static    │    │  Config   │ │  │
│  │  │   (JSON)    │    │  (vide)     │    │  API_URL  │ │  │
│  │  └─────────────┘    └─────────────┘    └───────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              Backend API (port 8000)                  │  │
│  │  /api/chat  /api/feedback  /api/health  /api/metrics  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Architecture Actuelle

**Fichier** : [`frontend/app.py`](../frontend/app.py)

Le frontend est un squelette FastAPI minimal :

```python
app = FastAPI(title="AI App Frontend")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    return {
        "message": "Production AI App Frontend",
        "api_url": os.getenv("API_URL", "http://localhost:8000"),
    }
```

### État actuel

| Composant | Statut | Description |
|-----------|--------|-------------|
| `app.py` | ✅ Squelette | Retourne JSON avec `API_URL` |
| `/static` | ❌ Vide | Répertoire inexistant |
| UI HTML/CSS/JS | ❌ Non implémenté | Interface chat à créer |
| Dockerfile | ✅ Minimal | Build du squelette |

## Intégration avec l'API Backend

### Endpoints disponibles

| Endpoint | Méthode | Usage |
|----------|---------|-------|
| `/api/chat` | POST | Envoyer une requête et recevoir une réponse |
| `/api/feedback` | POST | Soumettre un feedback (rating 1-5) |
| `/api/health` | GET | Vérifier la santé du service |
| `/api/metrics` | GET | Métriques Prometheus |

### Format de requête chat

```json
{
  "query": "What is machine learning?",
  "conversation_id": "optional-uuid",
  "stream": false
}
```

### Format de réponse chat

```json
{
  "text": "Machine learning is...",
  "sources": [
    {
      "id": "doc_001",
      "content": "...",
      "score": 0.95,
      "metadata": {}
    }
  ],
  "conversation_id": "optional-uuid",
  "trace_id": "trace-123",
  "input_tokens": 150,
  "output_tokens": 80,
  "latency_ms": 1200.5
}
```

## Développement Futur

### Interface Chat Recommandée

```
┌──────────────────────────────────────────────┐
│  Production AI App                           │
├──────────────────────────────────────────────┤
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  User: What is machine learning?       │  │
│  │                                        │  │
│  │  AI: Machine learning is a type of...  │  │
│  │  [1] Source document 1                 │  │
│  │  [2] Source document 2                 │  │
│  │                                        │  │
│  │  👍 👁️ 💬                              │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │  Type your message...            [Send]│  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

### Fonctionnalités à Implémenter

| Fonctionnalité | Description |
|----------------|-------------|
| **Interface chat** | Zone de messages avec historique conversationnel |
| **Streaming SSE** | Affichage progressif de la réponse (champ `stream: true`) |
| **Affichage des sources** | Documents sources avec score de pertinence |
| **Feedback utilisateur** | Boutons 👍/👎 liés à `/api/feedback` |
| **Indicateur de chargement** | Spin pendant le traitement |
| **Gestion des erreurs** | Affichage des erreurs (400, 500) |
| **Historique des conversations** | Sélecteur de `conversation_id` |

### Streaming SSE

Le champ `stream` existe dans `ChatRequest` mais **n'est pas implémenté** dans le backend. Pour activer le streaming :

1. Backend : Implémenter `StreamingResponse` avec `async generator`
2. Frontend : Utiliser `EventSource` ou `fetch` avec lecture progressive

## Conteneurisation

**Fichier** : [`frontend/Dockerfile`](../frontend/Dockerfile)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 3000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]
```

### Configuration Docker Compose

```yaml
frontend:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  ports:
    - "3000:3000"
  environment:
    - API_URL=http://app:8000
  depends_on:
    - app
```

### Dépendances Frontend

**Fichier** : [`frontend/requirements.txt`](../frontend/requirements.txt)

```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
```

## Bonnes Pratiques

1. **Séparation des services** : Le frontend est un service indépendant conteneurisé séparément
2. **Configuration par environnement** : `API_URL` est configurable via variable d'environnement
3. **Montage de fichiers statiques** : Utiliser `StaticFiles` pour servir HTML/CSS/JS
4. **Communication API** : Le frontend communique avec le backend via HTTP, jamais directement avec les bases de données
5. **CORS** : Le backend configure `ALLOWED_ORIGINS` pour autoriser le frontend

## Voir Aussi

- [Guide de Construction](guide-construction.md) — Vue d'ensemble de l'architecture
- [Guide des Services](guide-services.md) — API backend consommée par le frontend
- [Guide de Déploiement](deployment.md) — Déploiement Docker Compose du frontend
