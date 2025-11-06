# RAG Service V2 - Core Orchestration Layer

**Location:** `/volume1/docker/greenfrog-rag/backend/app/services/rag_service_v2.py`

## Overview

RAG Service V2 is the **main orchestration layer** that brings together all the services we've built for the GreenFrog RAG system. It provides a unified interface for querying documents with intelligent caching, hybrid retrieval, reranking, and streaming capabilities.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      RAGServiceV2                               │
│                  (Core Orchestrator)                            │
└────────┬────────┬────────┬────────┬────────┬────────────────────┘
         │        │        │        │        │
         ▼        ▼        ▼        ▼        ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │ Cache  │ │ Ollama │ │Retrieval│ │Rerank │ │ Stream │
    │Service │ │Service │ │Service │ │Service│ │Service │
    └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
         │          │          │          │          │
         ▼          ▼          ▼          ▼          ▼
     Redis     Ollama    ChromaDB    Score    SSE
              (LLM)    BM25 Index   Based   Events
```

## Pipeline Flow

### Non-Streaming Query Pipeline

```
1. User Query
   ↓
2. Semantic Cache Lookup (if enabled)
   ├─ Cache Hit → Return cached response (fast path)
   └─ Cache Miss → Continue to retrieval
       ↓
3. Hybrid Document Retrieval (BM25 + Semantic)
   ├─ Generate query embedding (Ollama)
   ├─ Parallel search: BM25 + Semantic
   └─ Reciprocal Rank Fusion (RRF)
       ↓
4. Document Reranking (if enabled)
   └─ Score-based sorting
       ↓
5. Context Construction
   └─ Format top-k documents with metadata
       ↓
6. Prompt Building
   └─ Inject context + question into template
       ↓
7. LLM Generation (Ollama)
   └─ Generate response with system prompt
       ↓
8. Response Caching (if enabled)
   └─ Store in Redis for future queries
       ↓
9. Return Response with Metadata
   └─ Response + sources + timing + metadata
```

### Streaming Query Pipeline

Same as above, but step 7 uses:
- **SSE Streaming:** Yields tokens as they're generated
- **Background Caching:** Caches full response after streaming completes

## Features

### 1. Cache-First Architecture
- **Semantic similarity caching** via Redis
- Embedding-based query matching (not just exact match)
- Configurable similarity threshold (default: 0.95)
- TTL-based cache expiration (default: 1 hour)
- Cache hit returns instant response (< 50ms)

### 2. Hybrid Retrieval
- **BM25 keyword search** for exact term matching
- **Semantic vector search** via ChromaDB
- **Reciprocal Rank Fusion (RRF)** for result combination
- Configurable weights for each method
- Automatic embedding generation via Ollama

### 3. Intelligent Reranking
- **Score-based reranking** (baseline)
- Filters by minimum score threshold
- Top-k selection
- Placeholder for FlashRank neural reranking (future)

### 4. Streaming Support
- **Server-Sent Events (SSE)** for real-time tokens
- Metrics tracking (tokens/sec, elapsed time)
- Error handling in stream
- Background caching after stream completion

### 5. Rich Metadata
Every response includes:
- **Sources:** Retrieved documents with scores
- **Timing:** Breakdown of each pipeline stage
- **Model info:** Which LLM was used
- **Cache status:** Hit or miss
- **Context length:** For debugging

### 6. Context Window Management
- Model-specific token limits (phi3:mini = 4096)
- Automatic context truncation (future)
- Document count limiting

## Usage

### Basic Example

```python
import asyncio
from app.services import (
    CacheService,
    OllamaService,
    RetrievalService,
    RerankService,
    StreamService,
    RAGServiceV2,
)

async def basic_query():
    # Initialize services
    cache = CacheService()
    ollama = OllamaService(model="phi3:mini")
    retrieval = RetrievalService(ollama_service=ollama)
    rerank = RerankService()
    stream = StreamService()

    # Initialize RAG service
    rag = RAGServiceV2(
        cache_service=cache,
        ollama_service=ollama,
        retrieval_service=retrieval,
        rerank_service=rerank,
        stream_service=stream,
        use_cache=True,
        use_rerank=True,
    )

    try:
        # Query
        response = await rag.query(
            question="What is machine learning?",
            workspace="greenfrog",
            k=5,  # Retrieve top 5 documents
            stream=False,
            temperature=0.7,
            max_tokens=512,
        )

        print(f"Response: {response['response']}")
        print(f"Sources: {len(response['sources'])}")
        print(f"Cached: {response['metadata']['cached']}")
        print(f"Total time: {response['metadata']['total_time_ms']:.2f}ms")

    finally:
        await rag.close()

asyncio.run(basic_query())
```

### Streaming Example

```python
async def streaming_query():
    # ... initialize services ...

    rag = RAGServiceV2(
        cache_service=cache,
        ollama_service=ollama,
        retrieval_service=retrieval,
        rerank_service=rerank,
        stream_service=stream,
        use_cache=False,  # Typically disable for streaming
    )

    try:
        # Stream the response
        stream = await rag.query(
            question="Explain neural networks",
            k=3,
            stream=True,
        )

        # Process SSE events
        import json
        async for sse_event in stream:
            if sse_event.startswith("data: "):
                data = json.loads(sse_event[6:])

                if "token" in data:
                    print(data["token"], end="", flush=True)
                elif data.get("done"):
                    print("\n\nDone!")

    finally:
        await rag.close()
```

### Custom Prompts

```python
custom_system = """You are a friendly AI tutor.
Always provide clear explanations with examples."""

custom_template = """Context:
{context}

Question: {question}

Please explain in simple terms:"""

rag = RAGServiceV2(
    cache_service=cache,
    ollama_service=ollama,
    retrieval_service=retrieval,
    rerank_service=rerank,
    stream_service=stream,
    system_prompt=custom_system,
    prompt_template=custom_template,
)
```

## API Reference

### `RAGServiceV2.__init__(...)`

Initialize the RAG orchestrator.

**Parameters:**
- `cache_service` (CacheService): Redis caching service
- `ollama_service` (OllamaService): LLM generation service
- `retrieval_service` (RetrievalService): Hybrid search service
- `rerank_service` (RerankService): Document reranking service
- `stream_service` (StreamService): SSE streaming service
- `model` (str): Default LLM model (default: "phi3:mini")
- `use_cache` (bool): Enable semantic caching (default: True)
- `use_rerank` (bool): Enable reranking (default: True)
- `system_prompt` (str, optional): Custom system prompt
- `prompt_template` (str, optional): Custom prompt template

### `async query(...)`

Main RAG query method.

**Parameters:**
- `question` (str): User question
- `workspace` (str): Workspace/collection name (default: "greenfrog")
- `k` (int): Number of documents to retrieve (default: 5)
- `stream` (bool): Enable SSE streaming (default: False)
- `temperature` (float): LLM sampling temperature 0-1 (default: 0.7)
- `max_tokens` (int): Maximum tokens to generate (default: 1024)
- `min_score` (float): Minimum retrieval score (default: 0.0)
- `model` (str, optional): Override default model

**Returns:**
- If `stream=False`: `Dict[str, Any]` with response, sources, metadata
- If `stream=True`: `AsyncIterator[str]` yielding SSE events

**Response Format (non-streaming):**
```python
{
    "response": "The AI-generated answer...",
    "sources": [
        {
            "id": "doc_123",
            "text": "Document excerpt...",
            "score": 0.8523,
            "metadata": {"source": "paper.pdf", "page": 5},
            "method": "hybrid"
        },
        # ... more sources
    ],
    "metadata": {
        "cached": False,
        "retrieval_method": "hybrid",
        "retrieval_time_ms": 45.23,
        "rerank_time_ms": 12.45,
        "generation_time_ms": 1523.67,
        "total_time_ms": 1581.35,
        "model": "phi3:mini",
        "context_length": 1245,
        "source_count": 5,
        "use_cache": True,
        "use_rerank": True
    },
    "timestamp": "2025-11-04T12:34:56.789Z"
}
```

### `async health_check()`

Check health of all sub-services.

**Returns:**
```python
{
    "cache": True,      # or False or "disabled"
    "ollama": True,
    "retrieval": True,
    "rerank": True,     # or "disabled"
    "overall": True     # All critical services healthy
}
```

### `async get_stats()`

Get aggregate statistics from all services.

**Returns:**
```python
{
    "cache": {
        "exact_entries": 42,
        "embedding_entries": 42,
        "response_entries": 42,
        "workspace": "greenfrog"
    },
    "retrieval": {
        "name": "greenfrog",
        "count": 1234,
        "metadata": {}
    },
    "model": "phi3:mini",
    "use_cache": True,
    "use_rerank": True
}
```

### `async close()`

Close all service connections. Always call in `finally` block.

## Performance Characteristics

### Cache Hit (Best Case)
- **Latency:** 20-50ms
- **No retrieval, no generation**
- Instant response from Redis

### Cache Miss (Typical Case)
- **Latency:** 1.5-3 seconds
- **Breakdown:**
  - Retrieval: 50-200ms (hybrid search + embedding)
  - Reranking: 10-50ms (score-based)
  - Generation: 1-2.5s (depends on model and length)

### Streaming Mode
- **Time to first token:** 300-800ms
- **Tokens per second:** 15-30 (phi3:mini on CPU)
- **Total time:** Similar to non-streaming, but perceived as faster

## Configuration

### Environment Variables

```bash
# Redis (Cache)
REDIS_URL=redis://greenfrog-redis:6379

# Ollama (LLM)
OLLAMA_API=http://host.docker.internal:11434

# ChromaDB (Retrieval)
CHROMADB_URL=http://chromadb:8000
```

### Model Selection

```python
# Fast, small model (4K context)
rag = RAGServiceV2(..., model="phi3:mini")

# Larger model (8K context)
rag = RAGServiceV2(..., model="llama3.2:3b")
```

### Caching Strategy

```python
# Enable caching (recommended for production)
rag = RAGServiceV2(..., use_cache=True)

# Disable caching (e.g., for streaming demos)
rag = RAGServiceV2(..., use_cache=False)

# Custom cache settings
cache = CacheService(
    similarity_threshold=0.95,  # Higher = stricter matching
    ttl_seconds=7200,           # 2 hours
)
```

### Retrieval Tuning

```python
# More documents = better context, slower generation
response = await rag.query(question="...", k=10)

# Fewer documents = faster, less context
response = await rag.query(question="...", k=3)

# Filter low-quality results
response = await rag.query(question="...", min_score=0.5)
```

## Error Handling

The service handles errors gracefully at each stage:

### No Documents Found
```python
{
    "response": "I couldn't find any relevant information...",
    "sources": [],
    "metadata": {
        "no_context_found": True,
        "total_time_ms": 123.45
    }
}
```

### Service Failures
- **Cache failure:** Continues without cache
- **Retrieval failure:** Raises exception (critical)
- **Rerank failure:** Falls back to retrieval scores
- **Generation failure:** Raises exception (critical)

### Streaming Errors
```json
data: {"error": "Streaming error: Connection timeout", "done": true}
```

## Best Practices

### 1. Always Use Context Managers

```python
async def safe_query():
    rag = RAGServiceV2(...)
    try:
        result = await rag.query(...)
        return result
    finally:
        await rag.close()  # Clean up connections
```

### 2. Cache Warming

```python
# Pre-warm cache with common queries
common_questions = [
    "What is machine learning?",
    "How do neural networks work?",
    "What is deep learning?"
]

for q in common_questions:
    await rag.query(question=q, workspace="greenfrog")
```

### 3. Monitor Performance

```python
response = await rag.query(...)

# Log slow queries
if response["metadata"]["total_time_ms"] > 3000:
    logger.warning(
        "slow_query",
        question=question[:50],
        time_ms=response["metadata"]["total_time_ms"]
    )
```

### 4. Tune for Your Use Case

**Fast responses (< 1s):**
- Enable caching
- Use smaller k (3-5)
- Use phi3:mini model
- Lower max_tokens (256-512)

**High quality answers:**
- Larger k (7-10)
- Enable reranking
- Use llama3.2:3b model
- Higher max_tokens (1024-2048)

## Testing

See `/volume1/docker/greenfrog-rag/backend/examples/rag_service_v2_example.py` for comprehensive examples.

```bash
# Run examples
cd /volume1/docker/greenfrog-rag/backend
python examples/rag_service_v2_example.py
```

## Future Enhancements

### Planned Features
1. **FlashRank integration** for neural reranking
2. **Automatic context truncation** for large documents
3. **Multi-turn conversation** support
4. **Query expansion** for better retrieval
5. **Hybrid caching** (Redis + in-memory)
6. **Rate limiting** for production API
7. **A/B testing framework** for prompt optimization

### Performance Improvements
1. **Parallel cache + retrieval** (speculative execution)
2. **Batch query processing**
3. **GPU acceleration** for embeddings
4. **Streaming cache writes** (don't wait for completion)

## Troubleshooting

### "Collection not found"
```bash
# Ensure ChromaDB collection exists
docker exec -it chromadb curl http://localhost:8000/api/v1/collections
```

### Slow generation
```python
# Use smaller model or reduce max_tokens
rag = RAGServiceV2(..., model="phi3:mini")
response = await rag.query(..., max_tokens=256)
```

### Cache not working
```python
# Check Redis connection
health = await rag.health_check()
print(health["cache"])  # Should be True

# Check cache stats
stats = await rag.get_stats()
print(stats["cache"])
```

### High memory usage
```python
# Reduce k and max_tokens
response = await rag.query(
    question="...",
    k=3,              # Fewer documents
    max_tokens=512,   # Shorter responses
)
```

## Related Documentation

- [Cache Service](./CACHE_SERVICE.md) - Redis semantic caching
- [Retrieval Service](./RETRIEVAL_SERVICE.md) - Hybrid search
- [Ollama Service](./OLLAMA_SERVICE.md) - LLM integration
- [Stream Service](./STREAM_SERVICE.md) - SSE streaming
- [Rerank Service](./RERANK_SERVICE.md) - Document reranking

## Support

For issues or questions, see:
- GitHub Issues: [greenfrog-rag/issues](https://github.com/your-org/greenfrog-rag/issues)
- Documentation: `/volume1/docker/greenfrog-rag/backend/docs/`
- Examples: `/volume1/docker/greenfrog-rag/backend/examples/`
