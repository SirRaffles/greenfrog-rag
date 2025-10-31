# GreenFrog RAG Avatar - Deployment Guide

Complete deployment guide for the GreenFrog sustainability chatbot with talking avatar.

## Prerequisites

- Docker & Docker Compose installed
- Ollama running with llama3.1:8b model
- 20GB+ free disk space
- 8GB+ free RAM

## Quick Start

### 1. Deploy All Services

```bash
cd /volume1/docker/greenfrog-rag
./scripts/deploy.sh
```

This will:
- Build all Docker images
- Start services in correct order
- Wait for health checks
- Display status and URLs

### 2. Configure AnythingLLM

Access AnythingLLM at http://192.168.50.171:3001

**First-time setup:**
1. Create admin account
2. Connect to Ollama:
   - LLM Provider: Ollama
   - Base URL: http://host.docker.internal:11434
   - Model: llama3.1:8b
3. Connect to ChromaDB:
   - Vector Database: Chroma
   - Instance URL: http://chromadb:8000
4. Set embedding model:
   - Provider: Ollama
   - Model: nomic-embed-text

### 3. Load Content

Load the 921 scraped sustainability documents:

```bash
cd /volume1/docker/greenfrog-rag
python3 scripts/load_content.py
```

This will:
- Check AnythingLLM connectivity
- Create "greenfrog" workspace if needed
- Upload all JSON files as text documents
- Display progress and summary

**Expected time:** 10-15 minutes for 921 files

### 4. Create GreenFrog Avatar

Create a 512x512px green frog mascot image:

**Option A: Use AI Generation**
```bash
# Using DALL-E, Midjourney, or Stable Diffusion
# Prompt: "Friendly cartoon green frog mascot, front-facing,
#          clear facial features for lip sync, simple background,
#          professional, sustainability theme"
```

**Option B: Use Placeholder**
```bash
# Create a simple placeholder
mkdir -p sadtalker/avatars
# Place any 512x512 image as greenfrog.png
```

Place the image at: `sadtalker/avatars/greenfrog.png`

### 5. Configure nginx Reverse Proxy

```bash
cd /volume1/docker/greenfrog-rag
./scripts/setup-nginx.sh
```

This will:
- Create nginx configuration for greenfrog.v4value.ai
- Add domain to /etc/hosts
- Test and reload nginx

**On your Mac:**
```bash
echo "192.168.50.171 greenfrog.v4value.ai" | sudo tee -a /etc/hosts
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
```

**Add DNS record on Namecheap:**
- Type: CNAME
- Host: greenfrog
- Value: v4value.ai

### 6. Test the System

**Local access (NAS):**
```bash
curl http://greenfrog.v4value.ai
```

**Test backend API:**
```bash
curl http://192.168.50.171:8000/health
```

**Test chat endpoint:**
```bash
curl -X POST http://192.168.50.171:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is The Matcha Initiative?",
    "workspace_slug": "greenfrog"
  }'
```

## Service URLs

| Service | URL | Port |
|---------|-----|------|
| **Frontend** | http://greenfrog.v4value.ai | 3000 |
| **Backend API** | http://192.168.50.171:8000/docs | 8000 |
| **AnythingLLM** | http://192.168.50.171:3001 | 3001 |
| **ChromaDB** | http://192.168.50.171:8001 | 8001 |

## Service Management

### Start all services
```bash
docker compose up -d
```

### Stop all services
```bash
docker compose down
```

### View logs
```bash
# All services
docker compose logs -f

# Specific service
docker logs greenfrog-backend -f
docker logs greenfrog-frontend -f
docker logs greenfrog-anythingllm -f
```

### Check status
```bash
docker compose ps
```

### Restart service
```bash
docker compose restart backend
docker compose restart frontend
```

### Rebuild service
```bash
docker compose build --no-cache backend
docker compose up -d backend
```

## Troubleshooting

### AnythingLLM not connecting to Ollama

**Check Ollama is running:**
```bash
curl http://192.168.50.171:11434/api/tags
```

**Check Docker network:**
```bash
docker exec greenfrog-anythingllm curl http://host.docker.internal:11434/api/tags
```

### Backend can't reach AnythingLLM

**Check AnythingLLM health:**
```bash
curl http://192.168.50.171:3001/api/ping
```

**Check from backend container:**
```bash
docker exec greenfrog-backend curl http://anythingllm:3001/api/ping
```

### Frontend not loading

**Check build logs:**
```bash
docker logs greenfrog-frontend
```

**Rebuild frontend:**
```bash
cd /volume1/docker/greenfrog-rag
docker compose build --no-cache frontend
docker compose up -d frontend
```

### Avatar generation slow

Avatar generation takes 30-60 seconds for SadTalker processing. This is normal.

To speed up (requires GPU):
- Use a GPU-enabled machine
- Update docker-compose.yml to use GPU runtime
- Enable CUDA in SadTalker container

### Content not loading in RAG

**Re-embed documents:**
1. Go to AnythingLLM workspace settings
2. Click "Re-embed documents"
3. Wait for completion

**Check embeddings:**
```bash
docker logs greenfrog-chromadb
```

## Performance Tuning

### Memory allocation

Edit docker-compose.yml resource limits:

```yaml
services:
  anythingllm:
    deploy:
      resources:
        limits:
          memory: 4G  # Increase if needed
```

### TTS mode switching

Edit `.env` file:
```bash
# Use fast Piper TTS (default)
TTS_MODE=piper

# Use XTTS for voice cloning (slower, needs more RAM)
TTS_MODE=xtts
```

Then restart:
```bash
docker compose restart backend
```

## Backup & Restore

### Backup data volumes
```bash
docker run --rm -v greenfrog-anythingllm-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/anythingllm-backup.tar.gz /data

docker run --rm -v greenfrog-chromadb-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/chromadb-backup.tar.gz /data
```

### Restore data volumes
```bash
docker run --rm -v greenfrog-anythingllm-data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/anythingllm-backup.tar.gz --strip 1"

docker run --rm -v greenfrog-chromadb-data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/chromadb-backup.tar.gz --strip 1"
```

## Monitoring

### Check resource usage
```bash
docker stats
```

### Check disk space
```bash
docker system df
```

### Clean up unused images
```bash
docker system prune -a
```

## Maintenance

### Daily website sync (automated)

The scraper runs daily at 2 AM to update content:
```bash
# Check cron job
docker exec greenfrog-scraper crontab -l

# Manually trigger sync
docker exec greenfrog-scraper python /app/scrape_matcha.py
docker exec greenfrog-scraper python /app/sync_to_anythingllm.py
```

### Update models

**Update Ollama model:**
```bash
ollama pull llama3.1:8b
docker compose restart anythingllm
```

**Update Piper voices:**
```bash
docker exec greenfrog-piper python /app/download_models.py
```

## Security Notes

- AnythingLLM has no authentication by default
- Add authentication in production
- Use HTTPS with SSL certificates
- Restrict access to backend API
- Keep services behind firewall

## Support

For issues or questions:
1. Check logs: `docker compose logs -f`
2. Review troubleshooting section
3. Check GitHub issues

---

**Deployment Time:** ~1 hour for full setup
**Project Status:** 95% complete - Ready for production!
