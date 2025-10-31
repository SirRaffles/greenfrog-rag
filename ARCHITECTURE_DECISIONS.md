# GreenFrog RAG Avatar - Architecture Decisions

## Executive Summary

**100% Local | $0/month | CPU-Only Optimized**

## Hardware Profile

- **System**: UGREEN DXP 4800 Plus NAS
- **CPU**: Intel Pentium Gold 8505 (6 cores, up to 4.4GHz)
- **RAM**: 62GB DDR5 (52GB available, 10GB currently used)
- **GPU**: Intel UHD Graphics (integrated only, NO discrete GPU)
- **Storage**: NVMe + HDD bays

## Final Technology Stack

### 1. Large Language Model: **Ollama with llama3.1:8b** ✅

**Decision**: Use locally installed Ollama with llama3.1:8b as primary model

**Rationale**:
- Already installed and running on NAS
- 4.9GB model leaves 57GB RAM for other services
- CPU-optimized inference (~5-10 tokens/second)
- Perfect balance of quality vs speed for real-time chat
- Free, private, fully local

**Available Models**:
- `llama3.1:8b` (4.9GB) - **PRIMARY** for real-time chat
- `llama3.2:3b` (2.0GB) - Fast fallback
- `llama3.3:70b` (42GB) - High-quality mode for complex sustainability queries
- `mixtral:8x7b` (26GB) - Alternative reasoning model

**Configuration**:
```yaml
anythingllm:
  environment:
    LLM_PROVIDER: ollama
    OLLAMA_BASE_URL: http://host.docker.internal:11434
    OLLAMA_MODEL: llama3.1:8b
```

**Expected Performance**:
- Cold start: ~2-3 seconds
- Token generation: 5-10 tok/s (CPU-only)
- Memory usage: ~6GB during inference
- Concurrent requests: 3-5 users comfortably

---

### 2. Text-to-Speech: **Piper TTS** ✅

**Decision**: Use Piper TTS (rhasspy/piper) with CPU-only inference

**Rationale**:
- **CPU-friendly**: Runs on CPU with <1 second latency
- **Quality**: Among best open-source TTS (natural sounding)
- **Speed**: Processes short texts in under 1 second
- **Resource-efficient**: Minimal memory footprint
- **No GPU required**: Critical for your hardware

**Rejected Alternative**: Coqui XTTS-v2
- ❌ Requires 4GB GPU VRAM (you don't have discrete GPU)
- ❌ Higher resource requirements
- ✅ Better voice cloning (but not needed for GreenFrog)

**Configuration**:
```yaml
piper-tts:
  image: rhasspy/piper:latest
  voice_model: en_US-lessac-medium
  speaking_rate: 1.0
```

**Expected Performance**:
- Latency: 200-800ms for typical responses
- Quality: Near-human natural speech
- Memory: ~500MB
- CPU usage: Low (2-3 cores during generation)

---

### 3. Avatar Generation: **faster-SadTalker-API** ✅

**Decision**: Use faster-SadTalker-API (Docker container) with 10x speedup

**Rationale**:
- **10x faster** than original SadTalker (optimized for production)
- **CPU-compatible**: Can run on CPU (slower but functional)
- **Docker-ready**: RESTful API in Docker container
- **Proven stable**: More mature than MuseTalk (SadTalker since 2023)
- **Good quality**: Expressive talking heads with realistic lip-sync

**Rejected Alternative**: MuseTalk v1.5
- ❌ Requires NVIDIA GPU (V100) for real-time 30+ FPS
- ❌ Designed for GPU inference
- ✅ Slightly better quality (but not usable on CPU)

**Configuration**:
```yaml
sadtalker:
  image: kenwaytis/faster-sadtalker-api:latest
  pose_style: normal
  expression_scale: 1.0
  fps: 25
```

**Expected Performance**:
- Latency: 3-6 seconds per response (CPU)
- Quality: High-fidelity lip-sync, expressive
- Memory: ~4-6GB during generation
- CPU usage: High (all 6 cores during rendering)

**Note**: Avatar generation is the bottleneck. Consider:
- Pre-rendering common phrases
- Queue system for concurrent requests
- Lower FPS (20 instead of 25) for faster generation

---

### 4. Vector Database: **ChromaDB** ✅

**Decision**: Use ChromaDB (simpler) over Qdrant

**Rationale**:
- **Simplicity**: Easier setup and maintenance
- **Python-native**: Better integration with scraper
- **Sufficient performance**: Fast enough for <10k documents
- **2025 Rust rewrite**: 4x faster than old version

**Note**: Can migrate to Qdrant later if performance issues (3-4x faster)

---

### 5. RAG Framework: **AnythingLLM** ✅

**Decision**: Use AnythingLLM for complete RAG solution

**Rationale**:
- **All-in-one**: Document management, embedding, vector DB, LLM integration
- **Ollama support**: Native integration with local Ollama
- **Docker-ready**: Single container deployment
- **UI included**: Admin interface for managing documents
- **RAG-optimized**: Built specifically for retrieval-augmented generation

---

### 6. Web Scraping: **Custom Python + BeautifulSoup** ✅

**Decision**: Build custom scraper (NOT Firecrawl)

**Rationale**:
- **Cost**: $0 vs $16+/month for Firecrawl
- **Single website**: thematchainitiative.com structure is well-defined
- **Flexibility**: Full control over parsing logic
- **Change detection**: Custom hashing for incremental updates

**Scraper Features**:
- Sitemap-based crawling
- Category/taxonomy preservation
- PDF extraction (guides, masterplans)
- Hash-based change detection
- Daily cron job (2 AM)
- Incremental updates (only modified pages)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│  Next.js Frontend (Port 3000)                       │
│  - GreenFrog chat interface                         │
│  - Real-time avatar video player                    │
│  - Voice input (optional WebRTC)                    │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│  FastAPI Backend (Port 8000)                        │
│  - Request orchestration                            │
│  - WebSocket for real-time updates                  │
│  - Queue management for avatar generation           │
└──┬────────┬──────────────┬──────────────────────────┘
   │        │              │
   │        │              │
┌──▼────┐ ┌─▼──────────┐ ┌▼─────────────────────────┐
│Ollama │ │ AnythingLLM│ │  Avatar Stack            │
│Local  │ │ + ChromaDB │ │  ┌─────────────────────┐ │
│11434  │ │ (Port 3001)│ │  │ Piper TTS (5000)    │ │
│       │ │            │ │  │ CPU: <1s latency    │ │
│Models:│ │ - RAG      │ │  └──────────┬──────────┘ │
│ 8b ✓  │ │ - Embed    │ │             │            │
│ 70b   │ │ - Docs     │ │  ┌──────────▼──────────┐ │
│       │ │            │ │  │ SadTalker (10364)   │ │
└───────┘ └────────────┘ │  │ CPU: 3-6s per video │ │
                         │  └─────────────────────┘ │
                         └──────────────────────────┘
          ┌──────────────────────────────────┐
          │  Website Scraper (Cron: 2 AM)    │
          │  - thematchainitiative.com       │
          │  - Change detection              │
          │  - Incremental updates           │
          └──────────────────────────────────┘
```

---

## Performance Expectations

### Latency Breakdown (Single Request)

| Component | Latency | Notes |
|-----------|---------|-------|
| **RAG Retrieval** | 100-300ms | ChromaDB vector search |
| **LLM Inference** | 1-3s | llama3.1:8b @ 5-10 tok/s |
| **TTS Generation** | 200-800ms | Piper on CPU |
| **Avatar Rendering** | 3-6s | SadTalker CPU bottleneck |
| **Total E2E** | **5-10 seconds** | First-time response |

### Optimization Strategies

1. **Streaming Response**: Stream text immediately, generate avatar in background
2. **Pre-rendering**: Cache common phrases/greetings
3. **Queue System**: Process 1 avatar at a time (CPU limitation)
4. **Progressive Loading**: Show text → audio → avatar sequentially
5. **Smart Caching**: Reuse avatar segments for similar responses

### Concurrent Users

- **Comfortable**: 3-5 simultaneous users
- **Maximum**: 8-10 users (with queueing)
- **Bottleneck**: Avatar generation (CPU-intensive)

---

## Cost Analysis

| Component | Monthly Cost |
|-----------|-------------|
| Hardware (NAS) | $0 (already owned) |
| Ollama LLM | $0 (local) |
| Piper TTS | $0 (open-source) |
| SadTalker | $0 (open-source) |
| AnythingLLM | $0 (open-source) |
| ChromaDB | $0 (open-source) |
| **TOTAL** | **$0/month** |

**Comparison to Cloud Stack**:
- Groq API: ~$10-50/month (depending on usage)
- ElevenLabs TTS: $5-330/month
- HeyGen Avatar: $24-120/month
- **Cloud Total**: $39-500/month
- **Annual Savings**: $468-6,000/year 💰

---

## Memory Allocation (64GB Total)

| Service | RAM Usage | Percentage |
|---------|-----------|------------|
| **System OS** | 2GB | 3% |
| **Ollama (llama3.1:8b)** | 6GB | 9% |
| **AnythingLLM** | 2GB | 3% |
| **ChromaDB** | 1GB | 2% |
| **Piper TTS** | 500MB | 1% |
| **SadTalker** | 6GB | 9% |
| **Backend (FastAPI)** | 500MB | 1% |
| **Frontend (Next.js)** | 500MB | 1% |
| **Scraper** | 500MB | 1% |
| **Buffer/Cache** | 8GB | 13% |
| **Available** | ~37GB | 58% |
| **Total Used** | ~27GB | 42% |

**Conclusion**: Plenty of headroom for growth. Can add monitoring, backup services, or even run llama3.3:70b for special queries.

---

## Scaling Path (Future)

### Phase 1: Current (CPU-Only)
✅ llama3.1:8b (fast)
✅ Piper TTS (CPU)
✅ SadTalker (CPU, slow but functional)

### Phase 2: Add GPU (~$500-1000)
- Upgrade to NVIDIA GPU (RTX 3060 12GB or better)
- Switch to MuseTalk for real-time 30+ FPS
- Enable XTTS-v2 for voice cloning
- 10x faster avatar generation

### Phase 3: Model Upgrade
- Use llama3.3:70b as primary (better quality)
- Add specialized sustainability fine-tuned model
- Multi-model routing (fast vs quality)

---

## Security & Privacy

✅ **100% Local**: No data leaves your NAS
✅ **No API Keys**: No external services
✅ **No Telemetry**: All open-source, no tracking
✅ **Private Data**: User conversations never sent to cloud
✅ **GDPR-Compliant**: Data stays in your infrastructure

Only external connection: Daily scrape of thematchainitiative.com (read-only)

---

## Decision Changelog

| Date | Decision | Reason |
|------|----------|--------|
| 2025-10-31 | Use Ollama (not Groq) | User has 64GB RAM + models installed |
| 2025-10-31 | Use Piper (not XTTS-v2) | No GPU available, CPU-friendly needed |
| 2025-10-31 | Use SadTalker (not MuseTalk) | MuseTalk requires NVIDIA GPU |
| 2025-10-31 | llama3.1:8b primary | Balance speed/quality for real-time |
| 2025-10-31 | Custom scraper (not Firecrawl) | Single website, save $192/year |

---

## References

- Ollama: https://ollama.com
- Piper TTS: https://github.com/rhasspy/piper
- faster-SadTalker-API: https://github.com/kenwaytis/faster-SadTalker-API
- AnythingLLM: https://github.com/Mintplex-Labs/anything-llm
- ChromaDB: https://www.trychroma.com
- The Matcha Initiative: https://www.thematchainitiative.com
