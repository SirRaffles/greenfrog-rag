# RAG V2 Quick Reference Card

**One-page reference for RAG V2 API endpoints**

---

## Base URL
```
http://localhost:8000/api/v2/chat
```

---

## Endpoints At-a-Glance

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/query` | POST | Non-streaming query |
| `/stream` | POST | Streaming query (SSE) |
| `/health` | GET | Service health check |
| `/stats` | GET | Statistics |
| `/cache/invalidate` | POST | Clear cache (admin) |

---

## Quick Start Examples

### 1. Simple Query
```bash
curl -X POST http://localhost:8000/api/v2/chat/query \
  -H "Content-Type: application/json" \
  -d '{"message": "What is renewable energy?"}'
```

### 2. Query with Options
```bash
curl -X POST http://localhost:8000/api/v2/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is sustainable agriculture?",
    "workspace": "greenfrog",
    "k": 5,
    "temperature": 0.7,
    "max_tokens": 1024,
    "use_cache": true,
    "use_rerank": true
  }'
```

### 3. Streaming Query
```bash
curl -X POST http://localhost:8000/api/v2/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain climate change"}'
```

### 4. Health Check
```bash
curl http://localhost:8000/api/v2/chat/health
```

### 5. Statistics
```bash
curl http://localhost:8000/api/v2/chat/stats
```

### 6. Clear Cache
```bash
curl -X POST http://localhost:8000/api/v2/chat/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{"workspace": "greenfrog"}'
```

---

## Request Parameters

### ChatRequestV2

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `message` | string | **required** | 1-10000 | User query |
| `workspace` | string | `"greenfrog"` | - | Workspace ID |
| `k` | integer | `5` | 1-20 | Documents to retrieve |
| `stream` | boolean | `false` | - | Enable SSE streaming |
| `temperature` | float | `0.7` | 0.0-2.0 | LLM temperature |
| `max_tokens` | integer | `1024` | 1-4096 | Max response tokens |
| `use_cache` | boolean? | `null` | - | Override cache setting |
| `use_rerank` | boolean? | `null` | - | Override rerank setting |
| `model` | string? | `null` | - | Override LLM model |

---

## Response Format

```json
{
  "response": "Generated answer...",
  "sources": [
    {
      "id": "doc_123",
      "text": "Document snippet...",
      "score": 0.92,
      "metadata": {"source": "file.pdf", "page": 42},
      "method": "hybrid"
    }
  ],
  "metadata": {
    "cached": false,
    "retrieval_method": "hybrid",
    "retrieval_time_ms": 45.23,
    "rerank_time_ms": 12.56,
    "generation_time_ms": 342.78,
    "total_time_ms": 400.57,
    "model": "phi3:mini",
    "context_length": 1523,
    "source_count": 5,
    "use_cache": true,
    "use_rerank": true
  },
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

---

## Environment Variables

```bash
# Master Switches
USE_RAG_V2=true              # Enable V2 endpoints
USE_CACHE=true               # Enable caching
USE_RERANK=true              # Enable reranking

# Service URLs
REDIS_URL=redis://greenfrog-redis:6379
OLLAMA_BASE_URL=http://ollama:11434
QDRANT_URL=http://qdrant:6333

# Configuration
OLLAMA_MODEL=phi3:mini
CACHE_TTL_SECONDS=3600
CACHE_SIMILARITY_THRESHOLD=0.95
OLLAMA_TIMEOUT=120
```

---

## HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Success |
| 400 | Bad Request | Validation error |
| 422 | Unprocessable Entity | Pydantic validation failed |
| 500 | Internal Server Error | Pipeline error |
| 503 | Service Unavailable | Service down |
| 504 | Gateway Timeout | Request timeout |

---

## JavaScript/TypeScript Example

```typescript
// Non-streaming
async function queryRAG(message: string) {
  const response = await fetch('http://localhost:8000/api/v2/chat/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      workspace: 'greenfrog',
      k: 5,
      temperature: 0.7
    })
  });

  const data = await response.json();
  return data;
}

// Streaming
async function streamRAG(message: string) {
  const response = await fetch('http://localhost:8000/api/v2/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        if (data.token) {
          process.stdout.write(data.token);
        }
        if (data.done) {
          console.log('\nDone:', data.stats);
        }
      }
    }
  }
}
```

---

## Python Example

```python
import requests

# Non-streaming
def query_rag(message: str):
    response = requests.post(
        'http://localhost:8000/api/v2/chat/query',
        json={
            'message': message,
            'workspace': 'greenfrog',
            'k': 5,
            'temperature': 0.7
        }
    )
    return response.json()

# Streaming
def stream_rag(message: str):
    response = requests.post(
        'http://localhost:8000/api/v2/chat/stream',
        json={'message': message},
        stream=True
    )

    for line in response.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            if 'token' in data:
                print(data['token'], end='', flush=True)
            if data.get('done'):
                print('\nDone:', data.get('stats'))
```

---

## Common Tasks

### Enable V2 in Production
```bash
# .env
USE_RAG_V2=true
USE_CACHE=true
USE_RERANK=true

# Restart
docker-compose restart backend
```

### Test Cache is Working
```bash
# Query twice with same message
curl -X POST http://localhost:8000/api/v2/chat/query \
  -d '{"message": "test", "use_cache": true}'

# Second request should have "cached": true in metadata
```

### Clear All Cache
```bash
curl -X POST http://localhost:8000/api/v2/chat/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{"workspace": "greenfrog"}'
```

### Check Service Health
```bash
curl http://localhost:8000/api/v2/chat/health | jq '.status'
```

### View Cache Stats
```bash
curl http://localhost:8000/api/v2/chat/stats | jq '.cache'
```

---

## Performance Tips

### Faster Queries
- Reduce `k` (fewer documents)
- Disable `use_rerank` (skip reranking)
- Enable `use_cache` (40x speedup on cache hit)
- Lower `max_tokens` (less generation time)

### Better Quality
- Increase `k` (more context)
- Enable `use_rerank` (better document ordering)
- Increase `temperature` (more creative)
- Use larger model (e.g., `llama3.2:3b`)

### Cache Optimization
- Increase `CACHE_SIMILARITY_THRESHOLD` (stricter matching)
- Decrease threshold (more permissive, more hits)
- Increase `CACHE_TTL_SECONDS` (longer cache lifetime)

---

## Troubleshooting

### Cache Not Working
```bash
# Check Redis
docker exec greenfrog-redis redis-cli ping

# View cache stats
curl http://localhost:8000/api/v2/chat/stats | jq '.cache'

# Clear and retry
curl -X POST http://localhost:8000/api/v2/chat/cache/invalidate \
  -d '{"workspace": "greenfrog"}'
```

### Slow Responses
```bash
# Check timing breakdown
curl -X POST http://localhost:8000/api/v2/chat/query \
  -d '{"message": "test"}' | jq '.metadata'

# Look at: retrieval_time_ms, generation_time_ms, etc.
```

### Service Unavailable (503)
```bash
# Check health
curl http://localhost:8000/api/v2/chat/health

# Check logs
docker logs -f greenfrog-backend | grep rag_v2

# Restart services
docker-compose restart redis ollama qdrant backend
```

---

## Files

- **Router**: `backend/app/routers/chat_v2.py`
- **Config**: `.env.v2.example`
- **Full Guide**: `RAG_V2_API_GUIDE.md`
- **Summary**: `RAG_V2_IMPLEMENTATION_SUMMARY.md`
- **Tests**: `test_rag_v2_api.sh`

---

## Resources

- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health**: http://localhost:8000/api/v2/chat/health
- **Stats**: http://localhost:8000/api/v2/chat/stats

---

**Version**: 2.0.0 | **Last Updated**: 2025-11-04
