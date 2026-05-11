# API Reference

## Endpoints

### POST /api/chat

Main chat endpoint for querying the AI system.

**Request:**
```json
{
  "query": "What is machine learning?",
  "conversation_id": "optional-uuid",
  "stream": false
}
```

**Response:**
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

### POST /api/feedback

Submit user feedback for a response.

**Request:**
```json
{
  "trace_id": "trace-123",
  "rating": 5,
  "comment": "Great answer!"
}
```

**Response:**
```json
{
  "status": "ok"
}
```

### GET /api/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

### GET /api/metrics

Prometheus metrics endpoint.

**Response:** Plain text Prometheus metrics format.

## Error Responses

All endpoints return errors in this format:

```json
{
  "error": "Error type",
  "detail": "Optional details (development only)"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad request (validation failed, content blocked) |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
