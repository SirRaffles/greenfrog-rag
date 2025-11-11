# GreenFrog RAG - Claude Code Project Context

## Project Overview
GreenFrog RAG is a sustainability-focused conversational AI assistant with avatar generation capabilities. It combines:
- RAG (Retrieval-Augmented Generation) for knowledge-based responses
- TTS (Text-to-Speech) with Piper for voice synthesis
- Avatar animation with SadTalker
- Next.js frontend with FastAPI backend
- Multi-service Docker architecture

**Public URL:** http://greenfrog.v4value.ai
**Local Backend:** http://192.168.50.171:8000
**Local Frontend:** http://192.168.50.171:3000

## Git Repository
- **Repository:** https://github.com/SirRaffles/greenfrog-rag
- **GitHub Username:** SirRaffles
- **Authentication:** GitHub PAT (stored in user's ~/.claude/CLAUDE.md)
- **Branch:** master (default)

### Git Commands
```bash
cd /volume1/docker/greenfrog-rag

# Pull latest changes
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" git pull

# Push changes
GIT_SSH_COMMAND="ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" git push origin main
```

## Architecture

### Docker Services (9 total)
```
1. chromadb:8001      - Vector database (ChromaDB 0.5.20)
2. redis:6400         - Semantic cache
3. anythingllm:3001   - RAG orchestration (currently unused)
4. piper-tts:5000     - Primary TTS (CPU-optimized)
5. xtts:5001          - Voice cloning TTS (optional)
6. sadtalker:7860     - Avatar generation
7. scraper:N/A        - Website scraper
8. backend:8000       - FastAPI orchestration
9. frontend:3000      - Next.js UI
```

### Technology Stack
- **Backend:** Python 3.11+, FastAPI, Pydantic
- **Frontend:** Next.js 14, React 18, TypeScript
- **LLM:** Ollama (llama3.2:3b, phi3:mini)
- **Vector DB:** ChromaDB (768-dim embeddings)
- **Cache:** Redis 7
- **TTS:** Piper (primary), XTTS-v2 (optional)
- **Avatar:** SadTalker

### RAG V2 Architecture
```
User Query → FastAPI Backend
    ↓
Dependency Injection (get_rag_service_v2)
    ↓
RAG Service V2 Initialization:
    - CacheService (Redis)
    - OllamaService (LLM)
    - RetrievalService (ChromaDB + BM25)
    - RerankService (score-based)
    - StreamService (SSE)
    ↓
Pipeline:
    1. Semantic cache check
    2. Hybrid retrieval (if miss)
    3. Document reranking
    4. Context construction
    5. LLM generation
    6. Response caching
```

## Key Files & Locations

### Backend
- `backend/app/routers/chat.py` - Chat endpoint handlers
- `backend/app/services/rag_service_v2.py` - RAG orchestration (line 917: get_rag_service_v2)
- `backend/app/services/cache_service.py` - Redis semantic cache
- `backend/app/services/ollama_service.py` - Ollama LLM integration
- `backend/app/services/retrieval_service.py` - ChromaDB + BM25 hybrid search
- `backend/load_chroma_with_embeddings.py` - Document loader script

### Frontend
- `frontend/src/app/page.tsx` - Main chat interface
- `frontend/src/components/` - React components

### Configuration
- `docker-compose.yml` - Service definitions
- `.gitignore` - Excludes data/, logs/, .env files
- `backend/Dockerfile` - Python 3.11 slim
- `frontend/Dockerfile` - Node.js 18

### Data Directories (git-ignored)
- `data/chromadb/` - Vector embeddings
- `data/redis/` - Cache data
- `data/anythingllm/` - AnythingLLM storage
- `data/scraped/Matchainitiative/` - Scraped content
- `logs/` - Application logs

## Environment Variables

### Backend (docker-compose.yml lines 195-218)
```bash
ANYTHINGLLM_URL=http://anythingllm:3001
ANYTHINGLLM_API_KEY=sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA
OLLAMA_API=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:3b
PIPER_TTS_API=http://piper-tts:5000
SADTALKER_API=http://sadtalker:7860
TTS_MODE=piper

# RAG V2 Configuration
USE_RAG_V2=true
USE_CACHE=true
USE_RERANK=true
REDIS_URL=redis://greenfrog-redis:6379
CHROMADB_URL=http://chromadb:8000
CHROMADB_COLLECTION=greenfrog
EMBEDDING_MODEL=nomic-embed-text:latest
```

### Frontend (docker-compose.yml lines 247-250)
```bash
NEXT_PUBLIC_API_URL=http://192.168.50.171:8000
NEXT_PUBLIC_WS_URL=ws://192.168.50.171:8000/ws
NODE_ENV=production
```

## Common Commands

### Docker Management
```bash
cd /volume1/docker/greenfrog-rag

# View status
docker compose ps

# Restart services
docker compose restart backend frontend

# Rebuild and restart
docker compose up -d --build backend

# View logs
docker compose logs -f backend
docker logs greenfrog-backend --tail 100

# Stop all
docker compose down

# Start all
docker compose up -d
```

### Testing Endpoints
```bash
# Health check
curl http://192.168.50.171:8000/health

# Test Ollama directly
curl -X POST http://192.168.50.171:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","prompt":"test","stream":false}'

# Test RAG query
curl -X POST http://192.168.50.171:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{"message":"What is the Matcha Initiative?","mode":"chat"}'

# Test TTS
curl -X POST http://192.168.50.171:8000/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello","mode":"piper"}'
```

### Document Loading
```bash
# Load documents into ChromaDB
docker exec greenfrog-backend bash -c "cd /app && python3 load_chroma_with_embeddings.py"
```

## Known Issues

### CRITICAL: RAG Service Initialization Hang (as of 2025-11-11)
**Status:** UNRESOLVED

**Symptoms:**
- Chat queries timeout after 120 seconds
- No RAG-related logs appear in backend
- Request never reaches chat endpoint handler
- No "initializing_rag_v2_singleton" log message

**Root Cause:**
FastAPI dependency injection hangs when calling `get_rag_service_v2()` in `chat.py:41`.
The singleton initialization (rag_service_v2.py:917-953) never completes.

**Evidence:**
- Ollama works fine (7.7s response time for simple queries)
- Backend health endpoint responds normally
- TTS and avatar endpoints work
- Test script successfully initializes RAG services outside FastAPI
- No log entry at chat.py:53 ("chat_message_received")

**Likely Culprit:**
One of these services is making a blocking synchronous call during initialization:
- CacheService (Redis connection)
- OllamaService (initial model check?)
- RetrievalService (ChromaDB connection)
- RerankService
- StreamService

**Temporary Workarounds Attempted:**
- Restarting backend - No change
- Verifying environment variables - Correct
- Testing dependencies individually - All healthy
- Git pull - Already up to date

**Next Steps to Fix:**
1. Add timeout and async handling to RAG initialization
2. Make initialization lazy (defer to first use)
3. Add health checks for each sub-service
4. Add logging at each initialization step
5. Consider switching to tinyllama model (faster inference)

### Minor Issues
1. **Avatar Generation Fails**
   - Missing `/app/avatars/greenfrog.png` file
   - Returns 500 error
   - Does not block RAG functionality

2. **Frontend Health Check Fails**
   - Container reports unhealthy
   - Site loads successfully anyway
   - Can be ignored

## Network Configuration

### Nginx Reverse Proxy
- **Config:** `/home/Davrine/docker/nginx-proxy/nginx.conf`
- **Domain:** greenfrog.v4value.ai → 127.0.0.1:3000
- **Fixed:** 2025-11-11 - Changed from port 9107 to 3000

### Ollama (Host System)
- **Service:** systemd (ollama.service)
- **Port:** 11434
- **Models:**
  - llama3.2:3b (2.0GB, Q4_K_M)
  - phi3:mini (2.2GB, Q4_0)
  - nomic-embed-text:latest (274MB, F16)
  - mixtral:8x7b (26GB, Q4_0)
  - llama3.3:70b-instruct-q4_K_M (42GB)

## Troubleshooting Guide

### Issue: Chat queries timeout
**Check:**
1. Backend logs: `docker logs greenfrog-backend --tail 100`
2. Ollama status: `curl http://192.168.50.171:11434/api/tags`
3. ChromaDB health: `curl http://192.168.50.171:8001/api/v1/heartbeat`
4. Redis health: `docker exec greenfrog-redis redis-cli ping`
5. System load: `uptime` (should be < 4.0)

**Common Causes:**
- RAG service initialization hang (current issue)
- Ollama overloaded (CPU > 95%)
- ChromaDB unavailable
- Redis connection failure

### Issue: 502 Bad Gateway
**Check:**
1. Container status: `docker compose ps`
2. Nginx config: `/home/Davrine/docker/nginx-proxy/nginx.conf`
3. Port mappings in docker-compose.yml

**Fix:**
- Verify proxy_pass matches container port
- Restart nginx-proxy: `docker restart nginx-proxy`

### Issue: Frontend won't load
**Check:**
1. Next.js build: `docker logs greenfrog-frontend`
2. API URL: Should be http://192.168.50.171:8000
3. CORS settings in backend

### Issue: No documents retrieved
**Check:**
1. ChromaDB collection:
   ```bash
   curl http://192.168.50.171:8001/api/v1/collections/greenfrog
   ```
2. Document count should be > 0
3. Reload if needed: Run load_chroma_with_embeddings.py

## Performance Benchmarks

### Ollama Inference
- llama3.2:3b: ~7-8 seconds for short responses
- phi3:mini: Similar performance
- System load should be < 4.0 for responsive queries

### RAG Pipeline (when working)
- Cache hit: < 1 second
- Cache miss: 10-15 seconds (retrieval + generation)
- Document retrieval: 1-2 seconds
- Reranking: 0.5 seconds
- LLM generation: 5-10 seconds

## Development Notes

### Adding New Documents
1. Place JSON files in `data/scraped/Matchainitiative/`
2. Run: `docker exec greenfrog-backend python3 /app/load_chroma_with_embeddings.py`
3. Verify: Check document count in ChromaDB

### Modifying RAG Behavior
- Caching: `USE_CACHE` env var
- Reranking: `USE_RERANK` env var
- Model: `OLLAMA_MODEL` env var
- Context limit: `rag_service_v2.py:58-62`

### Frontend Changes
1. Edit files in `frontend/src/`
2. Rebuild: `docker compose up -d --build frontend`
3. Check logs: `docker logs greenfrog-frontend`

### Backend Changes
1. Edit files in `backend/app/`
2. Rebuild: `docker compose up -d --build backend`
3. Test: `curl http://192.168.50.171:8000/health`

## Production Deployment Checklist

- [ ] All services running (`docker compose ps`)
- [ ] Ollama models downloaded
- [ ] ChromaDB populated with documents
- [ ] Redis cache initialized
- [ ] Nginx reverse proxy configured
- [ ] Domain resolves to http://greenfrog.v4value.ai
- [ ] Backend health check passes
- [ ] Frontend loads successfully
- [ ] RAG queries respond (currently failing)
- [ ] TTS works
- [ ] Avatar generation works (currently failing)

## Maintenance

### Daily
- Monitor system load (should be < 4.0)
- Check disk space in data/ directories
- Review error logs

### Weekly
- Update Docker images
- Clean old logs
- Verify document count in ChromaDB

### Monthly
- Update Ollama models
- Review and optimize cache hit rate
- Performance benchmarking

## Contact & Resources

- **Repository:** https://github.com/SirRaffles/greenfrog-rag
- **Deployment:** UGREEN NAS (192.168.50.171)
- **Domain:** v4value.ai (managed via Namecheap)

## Session History

### 2025-11-11: Initial Setup & Troubleshooting
- Fixed nginx proxy port (9107 → 3000)
- Diagnosed RAG initialization hang
- Confirmed Ollama working (7.7s response)
- Identified blocking dependency injection issue
- **Status:** Website loads, RAG queries timeout
- **Action Required:** Fix RAG service initialization

---

Last Updated: 2025-11-11
