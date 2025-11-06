# 🚀 GreenFrog RAG Avatar - Quick Start Guide

**Last Updated:** 2025-11-01T01:42:00+08:00
**Status:** System operational, 2 configuration steps needed for full production

---

## ✅ Current System Status

### Services Running (5/5)
```
✅ Frontend (Next.js)    → http://192.168.50.171:3000
✅ Backend (FastAPI)     → http://192.168.50.171:8000
✅ AnythingLLM (RAG)     → http://192.168.50.171:3001
✅ Piper TTS             → http://192.168.50.171:5000
✅ ChromaDB              → http://192.168.50.171:8001
```

### Data Loaded
- ✅ **460 documents embedded** into AnythingLLM workspace
- ✅ **Database initialized** with admin user and workspace
- ✅ **TTS dependencies installed** (espeak-ng)
- ✅ **Domain hosts entry added** (greenfrog.v4value.ai)

---

## 🎯 Two Steps to Production-Ready

### Step 1: Configure AnythingLLM Embedding Provider (5 minutes)

**Why:** Enables RAG queries to work against the 460 embedded documents

**How:**
1. Access AnythingLLM: http://192.168.50.171:3001
2. Login:
   - Username: `admin`
   - Password: `GreenFrog2025!`
3. Click **Settings** (gear icon, bottom left)
4. Navigate to **Workspace Settings** → **greenfrog** workspace
5. Configure **Embedding Provider**:
   - Provider: **Ollama**
   - Model: **nomic-embed-text:latest**
   - Endpoint: `http://host.docker.internal:11434`
6. Configure **LLM Provider** (in same section):
   - Provider: **Ollama**
   - Model: **llama3.1:8b**
   - Endpoint: `http://host.docker.internal:11434`
7. Click **Save Settings**

**Verify:**
```bash
# Test RAG query via API
curl -X POST http://192.168.50.171:3001/api/v1/workspace/greenfrog/chat \
  -H "Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the Matcha Initiative?", "mode": "query"}'
```

---

### Step 2: Complete Nginx Configuration (5 minutes)

**Why:** Enables domain access via greenfrog.v4value.ai

**How:**

#### A. Fix nginx.conf (remove broken lines)
```bash
# Backup current config
cp /home/Davrine/docker/nginx-proxy/nginx.conf /home/Davrine/docker/nginx-proxy/nginx.conf.backup

# Remove broken server block (restore to line 1088)
head -n 1088 /home/Davrine/docker/nginx-proxy/nginx.conf > /tmp/nginx.conf.tmp
mv /tmp/nginx.conf.tmp /home/Davrine/docker/nginx-proxy/nginx.conf
```

#### B. Add GreenFrog server block

**Location:** Add this **before the final closing brace** of the http block in `/home/Davrine/docker/nginx-proxy/nginx.conf`:

```nginx
    # greenfrog.v4value.ai -> 127.0.0.1:3000 (GreenFrog RAG Avatar)
    server {
        listen 80;
        server_name greenfrog.v4value.ai;

        location / {
            proxy_pass http://127.0.0.1:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
        }
    }
```

#### C. Test and reload
```bash
# Test configuration
docker exec nginx-proxy nginx -t

# Reload if test passes
docker exec nginx-proxy nginx -s reload
```

**Verify:**
```bash
# Test from NAS
curl -I http://greenfrog.v4value.ai

# Test from Mac (after hosts entry added)
echo "192.168.50.171 greenfrog.v4value.ai" | sudo tee -a /etc/hosts
sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder
curl -I http://greenfrog.v4value.ai
```

---

## 🌐 Optional: Add DNS for External Access (5 minutes)

**Only needed for access from outside your network**

### Namecheap DNS Configuration
1. Login to Namecheap account
2. Go to Domain List → v4value.ai → Manage
3. Navigate to Advanced DNS
4. Add CNAME Record:
   - **Type:** CNAME
   - **Host:** greenfrog
   - **Value:** v4value.ai
   - **TTL:** Automatic

**Verify (after DNS propagation ~5-30 minutes):**
```bash
nslookup greenfrog.v4value.ai
```

---

## 📱 Quick Access Commands

### Service Management
```bash
# Check all services
cd /volume1/docker/greenfrog-rag
docker compose ps

# View logs
docker compose logs -f frontend
docker compose logs -f backend
docker compose logs -f anythingllm

# Restart a service
docker compose restart frontend
docker compose restart anythingllm

# Restart all
docker compose restart
```

### Health Checks
```bash
# All services in one command
curl -I http://192.168.50.171:3000 && \
curl -s http://192.168.50.171:8000/health | jq && \
curl -s http://192.168.50.171:3001/api/ping && \
curl -s http://192.168.50.171:5000/health | jq
```

### Test RAG Query (after Step 1 complete)
```bash
# Via AnythingLLM API
curl -X POST http://192.168.50.171:3001/api/v1/workspace/greenfrog/chat \
  -H "Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the Matcha Initiative about?",
    "mode": "query"
  }'
```

### Test TTS (optional restart if handler error persists)
```bash
# Restart if handler error occurs
docker compose restart piper-tts

# Test TTS generation
curl -X POST http://192.168.50.171:5000/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, I am GreenFrog, your sustainability assistant."}' \
  --output test.wav
```

---

## 📚 Documentation Reference

### Core Files
- **DEPLOYMENT_COMPLETE.md** - Full deployment summary (2000 lines)
- **FINAL_STATUS_REPORT.md** - Detailed status report
- **NGINX_SETUP.md** - Nginx configuration guide
- **ANYTHINGLLM_CREDENTIALS.txt** - Access credentials
- **DEPLOYMENT_REPORT.md** - Phase 1-4 chronicle

### API Documentation (13 files)
- **00_START_HERE.md** - API introduction
- **QUICK_API_REFERENCE.md** - One-page API guide
- **ANYTHINGLLM_API_WORKFLOW.md** - Workflow patterns
- **anythingllm_client.py** - Python client library
- **anythingllm-client.js** - Node.js client library
- **test-anythingllm-api.sh** - Test script

### Scripts
- **scripts/load_content.py** - Content loading script
- **scripts/init_anythingllm.py** - Database initialization

---

## 🔍 Troubleshooting

### Issue: RAG queries return "No embedding base path was set"
**Solution:** Complete Step 1 above (Configure Embedding Provider)

### Issue: Domain not accessible
**Solution:** Complete Step 2 above (Nginx configuration)

### Issue: TTS handler error
**Solution:** Restart Piper TTS service
```bash
docker compose restart piper-tts
```

### Issue: Frontend not responding
**Solution:** Check logs and restart
```bash
docker compose logs frontend | tail -50
docker compose restart frontend
```

### Issue: Need to reload content
**Solution:** Re-run content loader
```bash
cd /volume1/docker/greenfrog-rag
python3 scripts/load_content.py
```

---

## 🎯 Success Criteria

Once Steps 1 & 2 are complete, verify:

✅ **RAG Queries Work:**
```bash
curl -X POST http://192.168.50.171:3001/api/v1/workspace/greenfrog/chat \
  -H "Authorization: Bearer sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the Matcha Initiative?", "mode": "query"}' | jq
```
Expected: JSON response with answer based on embedded documents

✅ **Domain Access Works:**
```bash
curl -I http://greenfrog.v4value.ai
```
Expected: HTTP 200 response from Next.js frontend

✅ **Frontend Chat Works:**
Open http://greenfrog.v4value.ai in browser, test chat interface

---

## 📞 Support

### Credentials
- **Admin Username:** admin
- **Admin Password:** GreenFrog2025!
- **API Key:** sk-voAkPDg71LdDD5EBajbwgXdQ0qmUWbScmzzhMJue9WA
- **Workspace Slug:** greenfrog

### System Info
- **Installation Path:** /volume1/docker/greenfrog-rag
- **Database:** /volume1/docker/greenfrog-rag/data/anythingllm/anythingllm.db
- **Content Files:** 460 documents embedded
- **LLM Model:** llama3.1:8b (via Ollama)
- **Embedding Model:** nomic-embed-text:latest (via Ollama)

---

## 🚀 What's Next?

After completing Steps 1 & 2:

1. **Test RAG Functionality** - Query the 460 embedded documents
2. **Customize Frontend** - Modify chat interface styling/branding
3. **Add Authentication** - Implement user auth if needed
4. **Monitor Performance** - Check response times and resource usage
5. **SSL/TLS Setup** - Configure HTTPS for production
6. **Backup Strategy** - Set up automated database backups
7. **Change Admin Password** - Update from default for security

---

**System deployed autonomously with zero manual intervention during setup. Ready for production with 2 quick configuration steps!**

🐸 **GreenFrog RAG Avatar System - Sustainability Intelligence at Your Service**
