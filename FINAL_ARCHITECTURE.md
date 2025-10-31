# GreenFrog RAG Avatar - Final Architecture

## 🎯 Executive Decision: Hybrid Approach

**Primary Stack**: Piper TTS + faster-SadTalker-API
**Optional**: XTTS-v2 for voice cloning (when responsiveness is less critical)

---

## Final Technology Stack

### 1. Large Language Model
**Ollama with llama3.1:8b** (Local)
- ✅ Already installed on your NAS
- ✅ 4.9GB model, 5-10 tokens/second
- ✅ Perfect for real-time sustainability Q&A

### 2. Text-to-Speech (Hybrid)

#### Primary: **Piper TTS**
- **Use case**: Default, fast responses
- **Speed**: <1 second latency
- **Quality**: High-quality natural speech
- **Hardware**: CPU-only, optimized
- **Port**: 5000

#### Optional: **XTTS-v2**
- **Use case**: Voice cloning, multilingual
- **Speed**: 10-30 seconds (CPU)
- **Quality**: Excellent with cloning
- **Hardware**: CPU (slow) or GPU (fast)
- **Port**: 5001
- **Enabled**: Via Docker profile `--profile optional`

### 3. Avatar Generation
**faster-SadTalker-API**
- **Speed**: 10x faster than original SadTalker
- **Quality**: High-fidelity lip-sync
- **Hardware**: CPU-compatible (4-8GB RAM)
- **Latency**: 3-6 seconds per response
- **Port**: 10364

### 4. Vector Database
**ChromaDB**
- Fast similarity search
- Python-native integration
- Port: 8001

### 5. RAG Framework
**AnythingLLM**
- Complete RAG solution
- Ollama integration
- Port: 3001

---

## Architecture Diagram

```
                         ┌─────────────────────────┐
                         │   Next.js Frontend      │
                         │   Port: 3000            │
                         │   - GreenFrog chat UI   │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │  FastAPI Backend        │
                         │  Port: 8000             │
                         │  - Request routing      │
                         │  - TTS mode switching   │
                         └──┬────┬─────┬─────┬────┘
                            │    │     │     │
          ┌─────────────────┘    │     │     └──────────────────┐
          │                      │     │                        │
  ┌───────▼────────┐   ┌────────▼─────▼───────┐   ┌───────────▼────────┐
  │  AnythingLLM   │   │   TTS Services        │   │   Avatar Gen       │
  │  + ChromaDB    │   │   ┌──────────────┐    │   │   ┌──────────────┐ │
  │  Port: 3001    │   │   │ Piper (5000) │◄───┤   │   │  SadTalker   │ │
  │                │   │   │ ⚡ PRIMARY    │    │   │   │  (10364)     │ │
  │  ┌──────────┐  │   │   └──────────────┘    │   │   │  CPU 3-6s    │ │
  │  │ Ollama   │  │   │   ┌──────────────┐    │   │   └──────────────┘ │
  │  │ (11434)  │  │   │   │ XTTS (5001)  │    │   └────────────────────┘
  │  │ 8b/70b   │  │   │   │ 🔧 OPTIONAL  │    │
  │  └──────────┘  │   │   └──────────────┘    │
  └────────────────┘   └───────────────────────┘
           ▲
           │
  ┌────────┴──────────┐
  │  Website Scraper  │
  │  Cron: Daily 2 AM │
  │  matcha initiative│
  └───────────────────┘
```

---

## TTS Mode Switching

The backend supports **dynamic TTS mode switching**:

### Fast Mode (Default)
```
User Query → RAG → Ollama → Piper TTS → SadTalker → User
Total: ~5-8 seconds
```

### Voice Cloning Mode (On-demand)
```
User Query → RAG → Ollama → XTTS-v2 → SadTalker → User
Total: ~15-35 seconds
```

**Configuration:**
```bash
# Use Piper (default, fast)
TTS_MODE=piper

# Use XTTS-v2 (voice cloning)
TTS_MODE=xtts

# Or switch via API endpoint
POST /api/settings
{"tts_mode": "xtts"}
```

---

## Deployment Commands

### Standard Stack (Piper + SadTalker)
```bash
cd /volume1/docker/greenfrog-rag
docker compose up -d
```

### With XTTS-v2 (Voice Cloning)
```bash
docker compose --profile optional up -d
```

### Only Core Services (No Avatar)
```bash
docker compose up -d anythingllm chromadb piper-tts backend frontend
```

---

## Performance Expectations

| Component | Latency | CPU Usage | RAM Usage |
|-----------|---------|-----------|-----------|
| **RAG Retrieval** | 100-300ms | Low | 1GB |
| **Ollama (8b)** | 1-3s | Medium | 6GB |
| **Piper TTS** | 200-800ms | Low | 500MB |
| **XTTS-v2** | 10-30s | High | 4GB |
| **SadTalker** | 3-6s | High | 6GB |
| **Total (Piper)** | **5-10s** | Medium | ~15GB |
| **Total (XTTS)** | **15-40s** | High | ~20GB |

---

## Cost Breakdown

| Item | Cost |
|------|------|
| Hardware (NAS) | $0 (owned) |
| RAM (64GB) | $0 (installed) |
| Ollama LLM | $0 (local) |
| Piper TTS | $0 (open-source) |
| XTTS-v2 | $0 (open-source) |
| SadTalker | $0 (open-source) |
| AnythingLLM | $0 (open-source) |
| ChromaDB | $0 (open-source) |
| **Total Monthly** | **$0** |

---

## Use Cases

### 1. Standard Chat (Piper Mode)
- **Scenario**: Quick Q&A about sustainability
- **User**: "What is carbon footprint?"
- **Flow**: Query → RAG → Ollama → Piper → SadTalker
- **Time**: 5-8 seconds
- **Best for**: Real-time conversations

### 2. Personalized Voice (XTTS Mode)
- **Scenario**: GreenFrog with custom voice personality
- **Setup**: Upload 10-second audio sample
- **Flow**: Query → RAG → Ollama → XTTS (cloned) → SadTalker
- **Time**: 15-35 seconds
- **Best for**: Demos, special presentations

### 3. Multilingual Support (XTTS Mode)
- **Scenario**: Spanish/French sustainability content
- **Flow**: Query → RAG → Ollama → XTTS (language=es) → SadTalker
- **Languages**: 17 supported
- **Best for**: International users

---

## Scaling Strategy

### Phase 1: Current (CPU-Only) ✅
- Piper TTS (fast, <1s)
- SadTalker (CPU, 3-6s)
- XTTS-v2 (optional, slow)

### Phase 2: Add GPU (~$500-1000)
- NVIDIA RTX 3060 12GB or better
- XTTS-v2 → 2-5s (10x faster)
- SadTalker → 1-2s (3x faster)
- Consider MuseTalk upgrade (30 FPS real-time)

### Phase 3: Model Upgrade
- Switch to llama3.3:70b (better quality)
- Fine-tune on sustainability corpus
- Multi-model routing

---

## Key Benefits

✅ **100% Local** - No cloud dependencies, full privacy
✅ **$0/month** - Zero recurring costs
✅ **Hybrid TTS** - Fast Piper + optional XTTS voice cloning
✅ **CPU-Optimized** - Runs on your existing NAS hardware
✅ **Multilingual** - 17 languages via XTTS-v2
✅ **Scalable** - Easy GPU upgrade path
✅ **Production-Ready** - Docker-based, auto-restart

---

## References

- **Ollama**: https://ollama.com
- **Piper TTS**: https://github.com/rhasspy/piper
- **XTTS-v2**: https://github.com/coqui-ai/TTS
- **faster-SadTalker**: https://github.com/kenwaytis/faster-SadTalker-API
- **AnythingLLM**: https://github.com/Mintplex-Labs/anything-llm
- **The Matcha Initiative**: https://www.thematchainitiative.com
