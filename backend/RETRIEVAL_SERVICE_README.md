# GreenFrog RAG - Retrieval Service Documentation

## Overview

The Retrieval Service implements a **hybrid search system** that combines BM25 keyword search with semantic vector search using Reciprocal Rank Fusion (RRF) for optimal document retrieval from ChromaDB.

## Features

- **Hybrid Search**: Combines semantic similarity and keyword matching
- **BM25 Keyword Search**: Traditional TF-IDF based keyword ranking
- **Semantic Vector Search**: Deep learning embeddings via ChromaDB + Ollama
- **Reciprocal Rank Fusion**: Intelligent fusion of multiple ranking methods
- **Automatic Document Loading**: Lazy-loaded BM25 index from ChromaDB
- **Configurable Weights**: Adjust semantic vs keyword importance

## Architecture

```
Query
  |
  ├─> Ollama (Embedding Generation)
  |     |
  |     v
  ├─> Semantic Search (ChromaDB Vector Query)
  |     |
  |     └─> Top-K Results with Similarity Scores
  |
  └─> BM25 Search (In-Memory Keyword Index)
        |
        └─> Top-K Results with BM25 Scores
              |
              v
        Reciprocal Rank Fusion
              |
              v
        Final Ranked Results
```

## Installation

### 1. Install Dependencies

```bash
pip install rank-bm25 chromadb-client numpy
```

### 2. Environment Variables

```bash
CHROMADB_URL=http://chromadb:8000
OLLAMA_API=http://host.docker.internal:11434
```

## Usage

### Basic Example

```python
from app.services.retrieval_service import RetrievalService
from app.services.ollama_service import OllamaService

# Initialize services
ollama = OllamaService()
retrieval = RetrievalService(
    chromadb_url="http://chromadb:8000",
    ollama_service=ollama,
    collection_name="greenfrog"
)

# Perform hybrid search
results = await retrieval.hybrid_search(
    query="What is sustainability?",
    k=10,
    rrf_k=60,
    weights=(0.5, 0.5)  # Equal weight to semantic and BM25
)

for result in results:
    print(f"RRF Score: {result['rrf_score']:.4f}")
    print(f"Text: {result['text'][:100]}...")
    print()
```

### API Endpoints

#### 1. Hybrid Search (POST)

```bash
curl -X POST "http://localhost:8000/api/retrieval/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "carbon emissions reduction",
    "k": 10,
    "method": "hybrid",
    "rrf_k": 60,
    "weights": [0.5, 0.5],
    "min_score": 0.0
  }'
```

#### 2. Simple Search (GET)

```bash
curl "http://localhost:8000/api/retrieval/search?q=sustainability&k=5&method=hybrid"
```

#### 3. Semantic-Only Search

```bash
curl "http://localhost:8000/api/retrieval/search?q=renewable%20energy&k=5&method=semantic"
```

#### 4. BM25-Only Search

```bash
curl "http://localhost:8000/api/retrieval/search?q=climate%20change&k=5&method=bm25"
```

#### 5. Reload Documents

```bash
curl -X POST "http://localhost:8000/api/retrieval/reload"
```

#### 6. Collection Info

```bash
curl "http://localhost:8000/api/retrieval/collection"
```

#### 7. Health Check

```bash
curl "http://localhost:8000/api/retrieval/health"
```

#### 8. Statistics

```bash
curl "http://localhost:8000/api/retrieval/stats"
```

## Search Methods

### 1. Hybrid Search (Recommended)

Combines semantic and keyword search using Reciprocal Rank Fusion.

**Best for**: Most queries, balances semantic understanding with keyword precision

```python
results = await retrieval.hybrid_search(
    query="sustainable energy solutions",
    k=10,
    rrf_k=60,
    weights=(0.6, 0.4)  # 60% semantic, 40% BM25
)
```

### 2. Semantic Search

Pure vector similarity search using embeddings.

**Best for**: Conceptual queries, finding semantically similar content

```python
results = await retrieval.semantic_search(
    query="environmentally friendly practices",
    k=10
)
```

### 3. BM25 Keyword Search

Traditional keyword-based ranking.

**Best for**: Exact term matching, specific names/acronyms

```python
results = await retrieval.keyword_search(
    query="GRI reporting standards",
    k=10
)
```

## Reciprocal Rank Fusion (RRF)

RRF combines rankings from multiple methods using the formula:

```
RRF_score(d) = Σ [ weight_method × (1 / (k + rank_method(d))) ]
```

Where:
- `d` = document
- `k` = constant (typically 60)
- `rank_method(d)` = rank of document d in that method's results

### Advantages

1. **Method-agnostic**: Works with any number of ranking methods
2. **No score normalization needed**: Uses ranks, not raw scores
3. **Robust**: Handles missing scores gracefully
4. **Tunable**: Adjust weights to favor semantic vs keyword

### Example

Given:
- Semantic results: [doc_A, doc_B, doc_C]
- BM25 results: [doc_C, doc_A, doc_D]
- k = 60, weights = (0.5, 0.5)

```
doc_A: 0.5×(1/(60+1)) + 0.5×(1/(60+2)) = 0.0164
doc_B: 0.5×(1/(60+2)) + 0.0 = 0.0081
doc_C: 0.5×(1/(60+3)) + 0.5×(1/(60+1)) = 0.0162
doc_D: 0.0 + 0.5×(1/(60+3)) = 0.0079

Final ranking: [doc_A, doc_C, doc_B, doc_D]
```

## Configuration

### Weights Tuning

Adjust `weights` parameter to balance semantic vs keyword search:

```python
# Favor semantic understanding (good for conceptual queries)
weights=(0.7, 0.3)

# Equal balance (default)
weights=(0.5, 0.5)

# Favor keyword matching (good for specific terms)
weights=(0.3, 0.7)
```

### RRF Constant (k)

Default: 60 (standard in literature)

- **Lower k** (e.g., 20): More emphasis on top-ranked documents
- **Higher k** (e.g., 100): More even distribution of scores

### Minimum Score Threshold

Filter out low-quality results:

```python
results = await retrieval.hybrid_search(
    query="sustainability",
    k=20,
    min_score=0.005  # Only return documents with RRF score >= 0.005
)
```

## Performance

### Document Loading

- **First query**: Loads all documents from ChromaDB and builds BM25 index (~2-5s for 500 docs)
- **Subsequent queries**: Uses cached index (instant)
- **Force reload**: `await retrieval.load_documents(force_reload=True)`

### Search Speed

| Method | Documents | Typical Latency |
|--------|-----------|----------------|
| Semantic | 500 | 100-200ms |
| BM25 | 500 | 10-30ms |
| Hybrid (RRF) | 500 | 150-300ms |

### Optimization Tips

1. **Pre-load documents** on startup:
   ```python
   await retrieval.load_documents()
   ```

2. **Limit k** for faster searches:
   ```python
   results = await retrieval.hybrid_search(query, k=5)  # Faster than k=50
   ```

3. **Use appropriate search method**:
   - Semantic: Slower but better understanding
   - BM25: Faster but keyword-only
   - Hybrid: Best quality, moderate speed

## Response Format

```json
{
  "query": "sustainability",
  "method": "hybrid",
  "count": 3,
  "took_ms": 287.45,
  "results": [
    {
      "id": "doc-uuid-123",
      "text": "Document content...",
      "metadata": {
        "title": "What is Sustainability",
        "url": "https://...",
        "published": "11/1/2025"
      },
      "score": 0.789,
      "method": "hybrid",
      "rrf_score": 0.0082,
      "semantic_score": 0.789,
      "semantic_rank": 1,
      "bm25_score": 3.046,
      "bm25_rank": 1,
      "distance": 0.267
    }
  ]
}
```

### Field Descriptions

- `rrf_score`: Combined score from RRF algorithm (higher is better)
- `semantic_score`: Similarity score from vector search (0-1, higher = more similar)
- `semantic_rank`: Rank in semantic results (1 = top)
- `bm25_score`: BM25 keyword score (higher = more relevant)
- `bm25_rank`: Rank in BM25 results (1 = top)
- `distance`: Vector distance from query (lower = more similar)
- `method`: "hybrid", "semantic", or "bm25"

## Troubleshooting

### Collection Not Found

```python
# Error: Collection 'greenfrog' not found
# Solution: Check collection name in ChromaDB
curl http://localhost:8001/api/v2/collections
```

### Documents Not Loading

```python
# Check ChromaDB health
await retrieval.health_check()

# Force reload
await retrieval.load_documents(force_reload=True)
```

### Ollama Connection Error

```python
# Error: Failed to generate query embedding
# Solution: Ensure Ollama is running and accessible
curl http://localhost:11434/api/tags
```

### Poor Search Quality

1. **Adjust weights**:
   ```python
   # Try semantic-first
   results = await retrieval.hybrid_search(query, weights=(0.8, 0.2))
   ```

2. **Increase k** for more results:
   ```python
   results = await retrieval.hybrid_search(query, k=20)
   ```

3. **Try different search methods**:
   ```python
   # Compare results
   semantic = await retrieval.semantic_search(query, k=10)
   bm25 = await retrieval.keyword_search(query, k=10)
   hybrid = await retrieval.hybrid_search(query, k=10)
   ```

## Best Practices

1. **Pre-load documents** on application startup for faster first query
2. **Use hybrid search** as default for best quality
3. **Tune weights** based on your use case:
   - Academic/research: Favor semantic (0.7, 0.3)
   - Technical docs: Favor BM25 (0.3, 0.7)
   - General queries: Balanced (0.5, 0.5)
4. **Set reasonable k** values (5-20 for most cases)
5. **Monitor latency** and adjust if needed
6. **Cache results** for common queries (using CacheService)

## Future Enhancements

- [ ] Add reranking with cross-encoder models
- [ ] Support for multi-lingual embeddings
- [ ] Query expansion for better recall
- [ ] Result diversity filtering
- [ ] Automatic weight tuning based on query type
- [ ] Distributed BM25 index for large collections
- [ ] GPU-accelerated embedding generation

## References

- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Reciprocal Rank Fusion](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Ollama Embeddings](https://ollama.ai/docs/embeddings)

## Files

- `/backend/app/services/retrieval_service.py` - Main service implementation
- `/backend/app/routers/retrieval.py` - FastAPI endpoints
- `/backend/test_retrieval.py` - Test script
- `/backend/RETRIEVAL_SERVICE_README.md` - This file

## Support

For issues or questions:
1. Check logs: `docker logs greenfrog-backend --tail 100`
2. Test health: `curl http://localhost:8000/api/retrieval/health`
3. Review ChromaDB: `docker logs greenfrog-chromadb --tail 100`

---

**Version**: 1.0.0
**Last Updated**: 2025-11-04
**Status**: Production Ready
