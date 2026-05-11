# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- OpenAI API key
- Python 3.11+

## Local Development

```bash
# Clone and setup
git clone <repo>
cd production-ai-app

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run migrations and seed
uv run python scripts/migrate.py
uv run python scripts/seed.py

# Start server
uv run uvicorn app.main:app --reload
```

## Docker Compose Deployment

```bash
# Build and start all services
docker compose up -d

# Check status
docker compose ps

# View logs
docker compose logs -f app

# Run healthcheck
docker compose exec app python scripts/healthcheck.py
```

## Production Deployment

### Environment Variables

Required:
```
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379
```

Optional:
```
ENVIRONMENT=production
LOG_LEVEL=warning
ENABLE_COST_TRACKING=true
```

### Scaling

```bash
# Scale API instances
docker compose up -d --scale app=3

# Scale with load balancer (external)
# Use nginx or cloud load balancer
```

### Monitoring

1. **Health Checks**: `/api/health` endpoint
2. **Metrics**: `/api/metrics` for Prometheus scraping
3. **Tracing**: OTLP endpoint for distributed tracing
4. **Logs**: Structured JSON logs via structlog

### Backup

```bash
# Backup PostgreSQL
docker compose exec db pg_dump -U postgres ai_app > backup.sql

# Backup ChromaDB
docker compose cp chromadb:/chroma/chroma ./backup/chroma
```

### Rolling Updates

```bash
# Build new image
docker compose build app

# Rolling update
docker compose up -d --no-deps app

# Verify
docker compose exec app python scripts/healthcheck.py
```

## Security Checklist

- [ ] Set strong database passwords
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS properly
- [ ] Set rate limits
- [ ] Enable input validation
- [ ] Rotate API keys regularly
- [ ] Monitor for injection attempts
