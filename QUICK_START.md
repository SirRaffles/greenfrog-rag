# GreenFrog RAG System - Quick Start Guide

**Essential commands and quick reference for daily operations**

---

## 🚀 Starting Services

### Start All Services
```bash
cd /volume1/docker/greenfrog-rag
docker compose up -d
```

### Start Specific Services
```bash
# Backend API only
docker compose up -d backend

# TTS only
docker compose up -d piper-tts

# RAG stack only
docker compose up -d chromadb anythingllm
```

### Check Service Status
```bash
docker compose ps
```

Expected output:
```
NAME                    STATUS
greenfrog-anythingllm   Up (healthy)
greenfrog-backend       Up (healthy)
greenfrog-chromadb      Up (healthy)
greenfrog-frontend      Up
greenfrog-piper         Up (healthy)
```

---

## 🔍 Health Checks

### Quick Health Check All Services
```bash
# Backend
curl http://192.168.50.171:8000/health

# ChromaDB
curl http://192.168.50.171:8001/api/v1/heartbeat

# Piper TTS
curl http://192.168.50.171:5000/health

# Ollama
curl http://192.168.50.171:11434/api/tags
```

### One-Line Health Check
```bash
echo "Backend:" && curl -s http://192.168.50.171:8000/health | jq && \
echo "ChromaDB:" && curl -s http://192.168.50.171:8001/api/v1/heartbeat && \
echo "Piper:" && curl -s http://192.168.50.171:5000/health | jq
```

---

## 🎤 Testing TTS

### Generate Speech (Simple)
```bash
curl -X POST http://192.168.50.171:5000/tts \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from GreenFrog","voice":"en_US-lessac-medium","rate":1.0}' \
  -o test_audio.wav
```

### Generate Speech via Backend API
```bash
curl -X POST http://192.168.50.171:8000/api/tts/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, I am GreenFrog, your sustainability assistant.","mode":"piper"}' \
  | jq
```

### List Available Voices
```bash
curl http://192.168.50.171:8000/api/tts/voices/piper | jq
```

---

## 💬 Querying RAG System

### Direct Ollama Query (Fast Test)
```bash
curl -X POST http://192.168.50.171:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","prompt":"What is sustainability?","stream":false}' \
  | jq '.response'
```

### RAG Query via Backend (with document context)
```bash
curl -X POST http://192.168.50.171:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the Matcha Initiative?","mode":"rag"}' \
  | jq
```

### Check Embedded Documents
```bash
curl -X GET http://192.168.50.171:3001/api/v1/workspaces \
  -H "Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA" \
  | jq '.workspaces[0].documents'
```

---

## 📊 Monitoring & Logs

### View Live Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f piper-tts
docker compose logs -f anythingllm

# Last 50 lines
docker logs greenfrog-backend --tail 50
```

### Check Resource Usage
```bash
docker stats --no-stream
```

### Check Disk Usage
```bash
du -sh data/chromadb data/anythingllm
```

---

## 🔧 Troubleshooting

### Restart Services
```bash
# Restart all
docker compose restart

# Restart specific
docker compose restart backend
docker compose restart piper-tts

# Force recreate
docker compose up -d --force-recreate backend
```

### Clear and Rebuild
```bash
# Stop all
docker compose down

# Rebuild specific service
docker compose build piper-tts

# Start fresh
docker compose up -d
```

### Check Container Health
```bash
docker inspect greenfrog-backend --format='{{.State.Health.Status}}'
docker inspect greenfrog-piper --format='{{.State.Health.Status}}'
```

### Debug Piper TTS Issues
```bash
# Test inside container
docker exec greenfrog-piper piper --help

# Check shared libraries
docker exec greenfrog-piper ldconfig -p | grep piper
docker exec greenfrog-piper ls -la /usr/share/espeak-ng-data
```

### Debug Ollama Issues
```bash
# List models
curl http://192.168.50.171:11434/api/tags | jq '.models[].name'

# Test generation
curl -X POST http://192.168.50.171:11434/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"test","stream":false}' \
  --max-time 30
```

---

## 🛠️ Common Fixes

### Issue: "TTS returns 500 error"
```bash
# Check Piper logs
docker logs greenfrog-piper --tail 20

# Rebuild Piper container
docker compose up -d --build piper-tts
```

### Issue: "Ollama timeout"
```bash
# Check Ollama is running
curl http://192.168.50.171:11434/api/tags

# Restart Ollama (if separate service)
sudo systemctl restart ollama

# Check CPU usage
top -bn1 | grep ollama
```

### Issue: "AnythingLLM won't connect to Ollama"
```bash
# Restart AnythingLLM
docker compose restart anythingllm

# Check configuration
docker exec greenfrog-anythingllm cat /app/server/.env | grep OLLAMA

# Test from inside container
docker exec greenfrog-anythingllm curl http://host.docker.internal:11434/api/tags
```

### Issue: "Documents not embedded"
```bash
# Check ChromaDB
curl http://192.168.50.171:8001/api/v1/heartbeat

# Re-run embedding (if script available)
python scripts/load_content.py
```

---

## 📍 Quick Access URLs

| Service | URL | Notes |
|---------|-----|-------|
| Frontend | http://192.168.50.171:3000 | Main UI |
| API Docs | http://192.168.50.171:8000/docs | Interactive API docs |
| API Health | http://192.168.50.171:8000/health | Health check |
| AnythingLLM | http://192.168.50.171:3001 | RAG UI (slow) |
| ChromaDB | http://192.168.50.171:8001 | Vector DB |

---

## 🔑 API Authentication

### AnythingLLM API Key
```bash
ANYTHINGLLM_API_KEY="sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA"

# Example usage
curl -X GET http://192.168.50.171:3001/api/v1/workspaces \
  -H "Authorization: Bearer $ANYTHINGLLM_API_KEY"
```

---

## 📦 Data Backup

### Backup Vector Database
```bash
tar -czf chromadb-backup-$(date +%Y%m%d).tar.gz data/chromadb/
```

### Backup AnythingLLM Data
```bash
tar -czf anythingllm-backup-$(date +%Y%m%d).tar.gz data/anythingllm/
```

### Backup All Data
```bash
tar -czf greenfrog-backup-$(date +%Y%m%d).tar.gz data/
```

---

## 🚨 Emergency Commands

### Stop Everything
```bash
docker compose down
```

### Nuclear Option (Reset Everything)
```bash
docker compose down -v
rm -rf data/chromadb/* data/anythingllm/*
docker compose up -d
# Note: You'll need to re-embed documents
```

### Check Disk Space
```bash
df -h /volume1/docker/greenfrog-rag
```

### Clean Docker
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a --volumes
```

---

## 📚 Performance Benchmarks

### Expected Performance
- **TTS Generation:** 0.4 seconds
- **RAG Query (Ollama):** 10-15 seconds
- **Document Embedding:** Variable (depends on doc size)
- **Health Check:** <1 second

### Test Performance
```bash
# TTS speed test
time curl -X POST http://192.168.50.171:5000/tts \
  -d '{"text":"test","voice":"en_US-lessac-medium","rate":1.0}' \
  -o /dev/null

# Ollama speed test
time curl -X POST http://192.168.50.171:11434/api/generate \
  -d '{"model":"llama3.2:3b","prompt":"hi","stream":false}' \
  | jq '.response'
```

---

## 💡 Pro Tips

1. **Bookmark API Docs:** http://192.168.50.171:8000/docs for interactive testing
2. **Use jq:** Pipe curl output to `jq` for pretty JSON formatting
3. **Monitor Logs:** Keep `docker compose logs -f backend` running during development
4. **Cache Responses:** Consider implementing Redis for frequently asked questions
5. **Ollama Models:** Switch to even smaller model (e.g., `llama3.2:1b`) for faster responses

---

**For detailed system information, see `SYSTEM_STATUS.md`**
**For avatar implementation, see `README_AVATAR_RESEARCH.md`**
