# RAG V2 API Guide

**Production-Ready FastAPI Router for Advanced RAG Capabilities**

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration](#configuration)
4. [API Endpoints](#api-endpoints)
5. [Request/Response Examples](#requestresponse-examples)
6. [Feature Flags](#feature-flags)
7. [Error Handling](#error-handling)
8. [Performance Tuning](#performance-tuning)
9. [Monitoring & Observability](#monitoring--observability)

---

## Overview

RAG V2 provides next-generation retrieval-augmented generation with:

- **Semantic Caching**: Redis + embeddings for intelligent cache hits
- **Hybrid Retrieval**: BM25 + semantic search for better context
- **Optional Reranking**: Score-based document reranking
- **SSE Streaming**: Real-time token streaming via Server-Sent Events
- **Rich Metadata**: Detailed timing and performance metrics
- **Production-Ready**: Comprehensive error handling, logging, health checks

### Key Improvements over V1

| Feature | V1 (AnythingLLM) | V2 (Native Pipeline) |
|---------|------------------|---------------------|
| Caching | None | Semantic (Redis + embeddings) |
| Retrieval | Semantic only | Hybrid (BM25 + semantic) |
| Reranking | No | Optional score-based |
| Streaming | Basic | SSE with metrics |
| Metadata | Limited | Comprehensive timing |
| Control | Black box | Full pipeline control |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Router                        │
│                    (chat_v2.py - 500 LOC)                   │
└─────────────┬───────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────┐
│                     RAGServiceV2 (Orchestrator)              │
└─────┬─────┬─────────┬──────────┬──────────┬─────────────────┘
      │     │         │          │          │
      ▼     ▼         ▼          ▼          ▼
  ┌─────┐ ┌────┐ ┌──────┐  ┌────────┐ ┌────────┐
  │Cache│ │Ollama│ │Retrieval│ │Rerank│ │Stream│
  │(Redis)│ │(LLM)│ │(Qdrant)│ │Service│ │Service│
  └─────┘ └────┘ └──────┘  └────────┘ └────────┘
```

### Pipeline Flow

1. **Request** → Validate with Pydantic
2. **Cache Check** → Semantic similarity lookup (if enabled)
3. **Retrieval** → Hybrid search (BM25 + semantic)
4. **Reranking** → Score-based reordering (if enabled)
5. **Context Building** → Format top-k documents
6. **Generation** → LLM response (streaming or non-streaming)
7. **Caching** → Store response for future queries
8. **Response** → Return with sources and metadata

---

## Configuration

### Environment Variables

```bash
# Feature Flags
USE_RAG_V2=true           # Enable V2 endpoints
USE_CACHE=true            # Enable semantic caching
USE_RERANK=true           # Enable document reranking

# Redis Configuration
REDIS_URL=redis://greenfrog-redis:6379
CACHE_TTL_SECONDS=3600    # 1 hour
CACHE_SIMILARITY_THRESHOLD=0.95  # 95% similarity required

# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=phi3:mini
OLLAMA_TIMEOUT=120

# Qdrant Configuration
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=greenfrog
EMBEDDING_MODEL=nomic-embed-text:latest
```

### Service Initialization

Services are initialized as a singleton on first request:

```python
# Automatic initialization via dependency injection
async def get_rag_service() -> RAGServiceV2:
    global _rag_service
    if _rag_service is None:
        # Initialize all sub-services
        cache_service = CacheService(...)
        ollama_service = OllamaService(...)
        retrieval_service = RetrievalService(...)
        rerank_service = RerankService()
        stream_service = StreamService()

        _rag_service = RAGServiceV2(
            cache_service=cache_service,
            ollama_service=ollama_service,
            retrieval_service=retrieval_service,
            rerank_service=rerank_service,
            stream_service=stream_service,
            model=os.getenv("OLLAMA_MODEL", "phi3:mini"),
            use_cache=True,
            use_rerank=True
        )
    return _rag_service
```

---

## API Endpoints

### Base URL

```
http://localhost:8000/api/v2/chat
```

### Endpoint Summary

| Endpoint | Method | Purpose | Response Type |
|----------|--------|---------|---------------|
| `/query` | POST | Non-streaming query | JSON |
| `/stream` | POST | Streaming query | SSE (text/event-stream) |
| `/health` | GET | Service health check | JSON |
| `/stats` | GET | Aggregate statistics | JSON |
| `/cache/invalidate` | POST | Clear cache (admin) | JSON |

---

## Request/Response Examples

### 1. Non-Streaming Query

**Request:**

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

**Request Schema:**

```json
{
  "message": "string (1-10000 chars)",
  "workspace": "string (default: greenfrog)",
  "k": "integer (1-20, default: 5)",
  "stream": "boolean (default: false)",
  "temperature": "float (0.0-2.0, default: 0.7)",
  "max_tokens": "integer (1-4096, default: 1024)",
  "use_cache": "boolean | null (override service default)",
  "use_rerank": "boolean | null (override service default)",
  "model": "string | null (override default model)"
}
```

**Response:**

```json
{
  "response": "Sustainable agriculture is a farming approach that focuses on producing food while minimizing environmental impact...",
  "sources": [
    {
      "id": "doc_42",
      "text": "Sustainable agriculture integrates three main goals...",
      "score": 0.9234,
      "metadata": {
        "source": "sustainability_guide.pdf",
        "page": 15,
        "chunk_id": "chunk_42"
      },
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

**Response Schema:**

```typescript
interface ChatResponseV2 {
  response: string;                    // Generated answer
  sources: SourceMetadata[];           // Source documents
  metadata: ResponseMetadata;          // Pipeline metadata
  timestamp: string;                   // ISO 8601 timestamp
}

interface SourceMetadata {
  id: string;                          // Document ID
  text: string;                        // Document snippet (truncated)
  score: number;                       // Relevance score (0-1)
  metadata: Record<string, any>;       // Document metadata
  method: string;                      // Retrieval method (bm25/semantic/hybrid)
}

interface ResponseMetadata {
  cached: boolean;                     // Cache hit?
  retrieval_method: string;            // Retrieval strategy
  retrieval_time_ms: number;          // Retrieval time
  rerank_time_ms: number;             // Reranking time
  generation_time_ms: number;         // LLM generation time
  total_time_ms: number;              // Total pipeline time
  model: string;                       // LLM model used
  context_length: number;             // Context string length
  source_count: number;               // Number of sources
  use_cache: boolean;                 // Cache enabled?
  use_rerank: boolean;                // Rerank enabled?
  cache_time_ms?: number;             // Cache lookup time (if applicable)
  no_context_found?: boolean;         // No relevant documents?
}
```

---

### 2. Streaming Query (SSE)

**Request:**

```bash
curl -X POST http://localhost:8000/api/v2/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain renewable energy",
    "workspace": "greenfrog",
    "k": 5,
    "stream": true
  }'
```

**Response (SSE Stream):**

```
data: {"token": "Renewable", "done": false, "metrics": {"token_count": 1, "elapsed_ms": 45}}

data: {"token": " energy", "done": false, "metrics": {"token_count": 2, "elapsed_ms": 67}}

data: {"token": " comes", "done": false, "metrics": {"token_count": 3, "elapsed_ms": 89}}

...

data: {"done": true, "stats": {"token_count": 156, "total_characters": 847, "elapsed_ms": 2340, "tokens_per_second": 66.67}}

```

**JavaScript Client Example:**

```javascript
const eventSource = new EventSource('http://localhost:8000/api/v2/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: "What is climate change?",
    workspace: "greenfrog",
    k: 5
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.done) {
    console.log('Stream complete:', data.stats);
    eventSource.close();
  } else if (data.error) {
    console.error('Stream error:', data.error);
    eventSource.close();
  } else {
    process.stdout.write(data.token);  // Print token in real-time
  }
};
```

---

### 3. Health Check

**Request:**

```bash
curl http://localhost:8000/api/v2/chat/health
```

**Response (Healthy):**

```json
{
  "status": "healthy",
  "services": {
    "cache": true,
    "ollama": true,
    "retrieval": true,
    "rerank": true,
    "overall": true
  },
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

**Response (Degraded):**

```json
{
  "status": "unhealthy",
  "services": {
    "cache": true,
    "ollama": false,          // Ollama is down!
    "retrieval": true,
    "rerank": "disabled",
    "overall": false
  },
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

**HTTP Status Codes:**

- `200 OK`: All services healthy
- `503 Service Unavailable`: One or more critical services down

---

### 4. Statistics

**Request:**

```bash
curl http://localhost:8000/api/v2/chat/stats
```

**Response:**

```json
{
  "cache": {
    "exact_entries": 142,
    "embedding_entries": 142,
    "response_entries": 142,
    "workspace": "greenfrog"
  },
  "retrieval": {
    "collection_name": "greenfrog",
    "vector_count": 5842,
    "indexed_documents": 1234,
    "embedding_model": "nomic-embed-text:latest"
  },
  "model": "phi3:mini",
  "use_cache": true,
  "use_rerank": true,
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

---

### 5. Cache Invalidation (Admin)

**Clear Specific Query:**

```bash
curl -X POST http://localhost:8000/api/v2/chat/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": "greenfrog",
    "query": "What is sustainable agriculture?"
  }'
```

**Clear All Workspace Cache:**

```bash
curl -X POST http://localhost:8000/api/v2/chat/cache/invalidate \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": "greenfrog",
    "query": null
  }'
```

**Response:**

```json
{
  "keys_deleted": 3,
  "workspace": "greenfrog",
  "timestamp": "2025-01-15T10:30:45.123456"
}
```

---

## Feature Flags

### Global Feature Flags (Environment)

```bash
# Enable/disable entire V2 router
USE_RAG_V2=true

# Enable/disable caching
USE_CACHE=true

# Enable/disable reranking
USE_RERANK=true
```

### Per-Request Overrides

You can override feature flags on a per-request basis:

```json
{
  "message": "What is renewable energy?",
  "use_cache": false,      // Bypass cache for this request
  "use_rerank": true       // Force reranking for this request
}
```

**Use Cases:**

- **Development/Testing**: `use_cache: false` to always get fresh responses
- **High-Priority Queries**: `use_rerank: true` to maximize quality
- **Performance Testing**: Toggle features to measure impact

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | When |
|------|---------|------|
| 200 | OK | Successful query |
| 400 | Bad Request | Validation error (empty message, invalid params) |
| 422 | Unprocessable Entity | Pydantic validation failure |
| 500 | Internal Server Error | Pipeline failure (LLM error, etc.) |
| 503 | Service Unavailable | Dependency unavailable (Redis, Ollama, Qdrant) |
| 504 | Gateway Timeout | Request timeout (Ollama took too long) |

### Error Response Format

```json
{
  "detail": "Validation error: Message cannot be empty"
}
```

### Example Error Scenarios

**Empty Message:**

```bash
curl -X POST http://localhost:8000/api/v2/chat/query \
  -H "Content-Type: application/json" \
  -d '{"message": ""}'

# Response: 422 Unprocessable Entity
{
  "detail": [
    {
      "loc": ["body", "message"],
      "msg": "ensure this value has at least 1 characters",
      "type": "value_error.any_str.min_length"
    }
  ]
}
```

**Service Unavailable:**

```bash
# Ollama is down
curl -X POST http://localhost:8000/api/v2/chat/query \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# Response: 503 Service Unavailable
{
  "detail": "Failed to initialize RAG service: Cannot connect to Ollama"
}
```

---

## Performance Tuning

### Cache Hit Rate Optimization

**Increase Similarity Threshold** (stricter matching):
```bash
CACHE_SIMILARITY_THRESHOLD=0.98  # Very strict (fewer hits, higher quality)
```

**Decrease Similarity Threshold** (more permissive):
```bash
CACHE_SIMILARITY_THRESHOLD=0.90  # More permissive (more hits, may be less accurate)
```

**Recommended**: 0.95 (good balance)

---

### Retrieval Performance

**Adjust k (number of documents):**

```json
{
  "message": "query",
  "k": 3              // Faster, less context
}
```

```json
{
  "message": "query",
  "k": 10             // Slower, more context
}
```

**Reranking Trade-off:**

- **Enabled**: Higher quality, +10-50ms latency
- **Disabled**: Faster, potentially lower quality

---

### Streaming vs Non-Streaming

**Non-Streaming** (GET complete response):
- Better for: Short queries, batch processing
- Latency: Higher (wait for full generation)
- Use case: API integrations, analytics

**Streaming** (SSE token-by-token):
- Better for: Chat interfaces, real-time UX
- Latency: Lower (first token arrives faster)
- Use case: Web chat, interactive apps

---

## Monitoring & Observability

### Structured Logging

All events are logged with structured data:

```python
logger.info(
    "rag_v2_query_success",
    response_length=len(response.response),
    source_count=len(response.sources),
    cached=response.metadata.cached,
    total_time_ms=round(request_time_ms, 2)
)
```

**Key Log Events:**

- `rag_v2_query_request`: Query received
- `rag_v2_query_success`: Query completed
- `rag_v2_query_error`: Query failed
- `rag_cache_hit`: Cache hit
- `rag_cache_miss`: Cache miss
- `rag_retrieval_complete`: Documents retrieved
- `rag_rerank_complete`: Documents reranked

---

### Metadata Analysis

Response metadata provides rich performance insights:

```json
{
  "metadata": {
    "retrieval_time_ms": 45.23,      // Qdrant lookup time
    "rerank_time_ms": 12.56,         // Reranking time
    "generation_time_ms": 342.78,    // LLM generation time
    "total_time_ms": 400.57,         // End-to-end time
    "cached": false,                 // Cache status
    "source_count": 5                // Documents used
  }
}
```

**Performance Benchmarks:**

- Retrieval: 20-100ms (depends on k and collection size)
- Reranking: 10-50ms (depends on document count)
- Generation: 200-2000ms (depends on max_tokens and model)
- Cache lookup: 5-20ms (semantic similarity)

---

## Production Deployment Checklist

- [ ] Set `USE_RAG_V2=true` in production environment
- [ ] Configure Redis with persistence for cache durability
- [ ] Set appropriate `CACHE_TTL_SECONDS` (1-24 hours)
- [ ] Tune `CACHE_SIMILARITY_THRESHOLD` based on use case
- [ ] Enable `USE_CACHE=true` for performance
- [ ] Enable `USE_RERANK=true` for quality
- [ ] Set `OLLAMA_TIMEOUT` to appropriate value (120s default)
- [ ] Configure proper CORS origins
- [ ] Set up monitoring for health check endpoint
- [ ] Implement authentication for `/cache/invalidate` endpoint
- [ ] Monitor cache hit rate via `/stats` endpoint
- [ ] Set up log aggregation for structured logs
- [ ] Load test with expected concurrent users
- [ ] Configure rate limiting (FastAPI middleware)

---

## Troubleshooting

### Cache Not Working

```bash
# Check Redis connection
docker exec greenfrog-redis redis-cli ping
# Should return: PONG

# Check cache stats
curl http://localhost:8000/api/v2/chat/stats

# Clear cache
curl -X POST http://localhost:8000/api/v2/chat/cache/invalidate \
  -d '{"workspace": "greenfrog"}'
```

---

### Poor Retrieval Quality

```bash
# Try increasing k
{"k": 10}

# Enable reranking
{"use_rerank": true}

# Check document count
curl http://localhost:8000/api/v2/chat/stats
# Look at: retrieval.vector_count
```

---

### Slow Response Times

```bash
# Check component timing
# Look at metadata.retrieval_time_ms, generation_time_ms, etc.

# Disable reranking if not needed
{"use_rerank": false}

# Reduce k
{"k": 3}

# Enable caching
{"use_cache": true}
```

---

## API Reference Links

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

---

## File Locations

- **Router**: `/volume1/docker/greenfrog-rag/backend/app/routers/chat_v2.py`
- **RAG Service**: `/volume1/docker/greenfrog-rag/backend/app/services/rag_service_v2.py`
- **Cache Service**: `/volume1/docker/greenfrog-rag/backend/app/services/cache_service.py`
- **Config Example**: `/volume1/docker/greenfrog-rag/.env.v2.example`

---

**Version**: 2.0.0
**Last Updated**: 2025-11-04
**Author**: Claude Code (API Designer Agent)
