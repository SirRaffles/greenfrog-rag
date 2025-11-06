# GreenFrog RAG Avatar System - Status Report

**Last Updated:** November 3, 2025
**System Version:** 1.0
**Status:** Partially Operational

---

## System Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend    │────▶│   Ollama    │
│  (Next.js)  │     │  (FastAPI)   │     │ (llama3.2)  │
└─────────────┘     └──────────────┘     └─────────────┘
                            │
                            │
                    ┌───────┴────────┐
                    ▼                ▼
            ┌─────────────┐   ┌─────────────┐
            │  Piper TTS  │   │  ChromaDB   │
            │   (0.4s)    │   │ (538 docs)  │
            └─────────────┘   └─────────────┘
                                      │
                                      ▼
                              ┌──────────────┐
                              │ AnythingLLM  │
                              │  (Frontend)  │
                              └──────────────┘
```

---

## ✅ Working Components

### 1. **Piper TTS - FULLY OPERATIONAL**
- **Endpoint:** `http://192.168.50.171:5000/tts`
- **Performance:** 0.4 seconds per audio generation
- **Model:** `en_US-lessac-medium`
- **Status:** Production ready

**Test Command:**
```bash
curl -X POST http://192.168.50.171:5000/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from GreenFrog","voice":"en_US-lessac-medium","rate":1.0}'
```

### 2. **Document Embedding - COMPLETE**
- **Vector Database:** ChromaDB
- **Documents Embedded:** 538 documents
- **Embedding Model:** nomic-embed-text:latest (Ollama)
- **Endpoint:** `http://192.168.50.171:8001`
- **Status:** Fully embedded and queryable

### 3. **Backend API - OPERATIONAL**
- **Endpoint:** `http://192.168.50.171:8000`
- **Framework:** FastAPI
- **Features:**
  - TTS synthesis routing
  - RAG query handling
  - Avatar generation integration (pending)
- **Health Check:** `http://192.168.50.171:8000/health`

### 4. **Frontend - DEPLOYED**
- **Endpoint:** `http://192.168.50.171:3000`
- **Framework:** Next.js
- **Status:** Running and accessible

---

## ⚠️ Partially Working Components

### 5. **RAG Query System - PERFORMANCE LIMITED**

**Status:** Technically functional but too slow for AnythingLLM UI

**Root Cause:**
- Ollama with llama3.2:3b takes 10-15 seconds per query
- AnythingLLM's internal timeout is shorter than Ollama response time
- Model is CPU-bound on current hardware

**What Works:**
- ✅ Direct Ollama API calls (10-15s response time)
- ✅ Document retrieval from ChromaDB
- ✅ Embedding generation
- ✅ Backend API queries

**What Doesn't Work:**
- ❌ AnythingLLM UI chat (times out)

**Workaround - Use Backend API Directly:**
```bash
curl -X POST http://192.168.50.171:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the Matcha Initiative?","mode":"rag"}'
```

**Configuration Applied:**
- Switched from `llama3.1:8b` → `llama3.2:3b` (2.4x faster)
- Updated environment variables in docker-compose.yml
- Optimized Ollama keep-alive timeout

---

## ❌ Blocked Components

### 6. **Avatar Generation (SadTalker) - GPU REQUIRED**

**Status:** Cannot run on CPU-only system

**Error:**
```
RuntimeError: Found no NVIDIA driver on your system
```

**Solution:** See `README_AVATAR_RESEARCH.md` for CPU-compatible alternatives
- **Recommended:** Wav2Lip with OpenVINO (10-60s per video on CPU)
- See implementation guide: `IMPLEMENTATION_GUIDE_WAV2LIP.md`

---

## Configuration Changes Made

### 1. **Piper TTS Dockerfile** (`piper-tts/Dockerfile`)
**Issue:** Missing shared libraries and espeak-ng data
**Fix:**
- Line 19: Changed `mv piper/lib/*.so*` → `mv piper/*.so*`
- Line 21: Added `cp -r piper/espeak-ng-data /usr/share/espeak-ng-data`
- Line 22: Added `ldconfig`

### 2. **TTS Service** (`backend/app/services/tts_service.py`)
**Issue:** Incorrect API endpoint and parameter names
**Fix:**
- Line 112: Changed `/api/tts` → `/tts`
- Line 118: Changed `"speed"` → `"rate"`

### 3. **TTS Router** (`backend/app/routers/tts.py`)
**Issue:** Environment variable naming mismatch
**Fix:**
- Line 22: `PIPER_URL` → `PIPER_TTS_API`
- Line 23: `XTTS_URL` → `XTTS_API`

### 4. **Avatar Service** (`backend/app/services/avatar_service.py`)
**Issue:** Incorrect SadTalker port
**Fix:**
- Line 24: Changed `8000` → `7860`

### 5. **Docker Compose** (`docker-compose.yml`)
**Issue:** Slow LLM model
**Fix:**
- Line 41, 180: `llama3.1:8b` → `llama3.2:3b`
- Line 117: Updated SadTalker image to `wawa9000/sadtalker:latest`

### 6. **AnythingLLM Config** (`anythingllm/env.txt`)
**Issue:** Model preference not updated
**Fix:**
- Line 5: `llama3.1:8b` → `llama3.2:3b`

---

## Known Limitations

### Performance Constraints
1. **Ollama Query Speed:** 10-15 seconds per query (CPU-bound)
2. **AnythingLLM Timeout:** Internal timeout shorter than Ollama response time
3. **No GPU Available:** Cannot run GPU-accelerated avatar generation

### Workarounds Implemented
1. **RAG Queries:** Use backend API instead of AnythingLLM UI
2. **Model Size:** Switched to smaller llama3.2:3b model
3. **Avatar Generation:** Research completed for CPU alternative (Wav2Lip)

---

## Service Endpoints

| Service | URL | Status | Purpose |
|---------|-----|--------|---------|
| Frontend | http://192.168.50.171:3000 | ✅ Running | User interface |
| Backend API | http://192.168.50.171:8000 | ✅ Running | API orchestration |
| Backend Health | http://192.168.50.171:8000/health | ✅ Running | Health check |
| Backend Docs | http://192.168.50.171:8000/docs | ✅ Running | API documentation |
| AnythingLLM | http://192.168.50.171:3001 | ⚠️ Slow | RAG UI (limited) |
| ChromaDB | http://192.168.50.171:8001 | ✅ Running | Vector database |
| Piper TTS | http://192.168.50.171:5000 | ✅ Running | Text-to-speech |
| Ollama | http://192.168.50.171:11434 | ✅ Running | LLM inference |
| SadTalker | http://192.168.50.171:10364 | ❌ GPU Required | Avatar (blocked) |

---

## Next Steps

### Immediate Actions
1. ✅ **Avatar Research Complete** - See `README_AVATAR_RESEARCH.md`
2. 🔄 **Deploy Wav2Lip** - Follow `IMPLEMENTATION_GUIDE_WAV2LIP.md`
3. 📝 **Test End-to-End** - TTS + RAG integration

### Future Optimizations
1. **Faster LLM Model:** Consider using Mistral-7B or smaller quantized models
2. **GPU Addition:** If GPU becomes available, revert to SadTalker
3. **Caching:** Implement response caching for common queries
4. **Load Balancing:** Add multiple Ollama instances if needed

---

## Performance Metrics

| Component | Metric | Target | Actual | Status |
|-----------|--------|--------|--------|--------|
| TTS Generation | Time per request | <2s | 0.4s | ✅ Excellent |
| Document Embedding | Total docs | 900+ | 538 | ⚠️ Partial |
| RAG Query | Response time | <5s | 10-15s | ⚠️ Slow |
| Avatar Generation | Time per video | <30s | N/A | ❌ Blocked |

---

## Support & Troubleshooting

### Common Issues

**Q: AnythingLLM chat times out**
A: Use the backend API directly for RAG queries (see workaround above)

**Q: Ollama responses are slow**
A: Expected on CPU. Consider smaller model or add GPU acceleration.

**Q: SadTalker won't start**
A: Requires NVIDIA GPU. Use Wav2Lip alternative (CPU-compatible).

**Q: Documents not embedding**
A: Mac resource fork files (_* files) are excluded. Only 538/904 files embedded.

### Service Restart Commands
```bash
# Restart all services
docker compose restart

# Restart specific service
docker compose restart backend
docker compose restart piper-tts
docker compose restart anythingllm

# View logs
docker compose logs -f backend
docker compose logs -f piper-tts

# Check service health
docker compose ps
```

---

## Documentation Index

- `SYSTEM_STATUS.md` - This file (system overview)
- `QUICK_START.md` - Essential commands and quick reference
- `README_AVATAR_RESEARCH.md` - Avatar solution research summary
- `CPU_TALKING_AVATAR_RESEARCH.md` - Detailed avatar research
- `IMPLEMENTATION_GUIDE_WAV2LIP.md` - Wav2Lip deployment guide
- `QUICK_DECISION_MATRIX.md` - Avatar solution decision matrix

---

**For questions or issues, refer to the troubleshooting section above or check service logs.**
