# GreenFrog RAG Avatar - Project Location & Structure

## 📍 **EXACT LOCATION**

**Full Path:** `/volume1/docker/greenfrog-rag/`

**On UGREEN NAS:**
- Volume: `volume1` (main storage volume)
- Subdirectory: `docker` (all Docker projects)
- Project: `greenfrog-rag` (this project)

---

## 📂 **COMPLETE DIRECTORY STRUCTURE**

```
/volume1/docker/greenfrog-rag/
│
├── 📄 docker-compose.yml          ← Main Docker orchestration file
├── 📄 .env                        ← Environment variables (ports, settings)
├── 📄 .env.example                ← Example environment file
│
├── 📖 README.md                   ← Main documentation
├── 📖 ARCHITECTURE_DECISIONS.md   ← Technology decisions
├── 📖 FINAL_ARCHITECTURE.md       ← Final architecture summary
├── 📖 PROJECT_STATUS.md           ← Current progress (60% complete)
├── 📖 TRANSFER_GUIDE.md           ← File transfer instructions
├── 📖 PROJECT_LOCATION.md         ← This file
│
├── 🔧 anythingllm/               ← AnythingLLM RAG service
│   └── (empty - will store config)
│
├── 🔧 chromadb/                  ← Vector database service
│   └── (empty - will store vectors)
│
├── 🔧 piper-tts/                 ← Primary TTS (fast, CPU-optimized)
│   ├── Dockerfile                ← Build instructions
│   ├── requirements.txt          ← Python dependencies
│   ├── app.py                    ← FastAPI TTS server ✅
│   └── download_models.py        ← Auto-download voice models ✅
│
├── 🔧 xtts-v2/                   ← Optional TTS (voice cloning)
│   ├── Dockerfile                ← Build instructions
│   ├── requirements.txt          ← Python dependencies
│   ├── app.py                    ← FastAPI TTS server ✅
│   ├── download_models.py        ← Auto-download XTTS model ✅
│   ├── models/                   ← XTTS-v2 model files (1.8GB)
│   ├── voices/                   ← Voice reference samples
│   ├── outputs/                  ← Generated audio files
│   ├── avatars/                  ← (unused)
│   └── results/                  ← (unused)
│
├── 🔧 sadtalker/                 ← Avatar generation (talking head)
│   └── (empty - will download checkpoints)
│
├── 🔧 musetalk/                  ← (Alternative avatar, not used)
│   ├── models/
│   ├── avatars/
│   ├── outputs/
│   ├── results/
│   └── voices/
│
├── 🔧 scraper/                   ← Website content scraper
│   ├── Dockerfile                ← Build instructions
│   ├── requirements.txt          ← Python dependencies
│   └── (scripts to be added)
│
├── 🔧 backend/                   ← FastAPI orchestration layer
│   └── (to be created)
│
├── 🔧 frontend/                  ← Next.js chat interface
│   └── (to be created)
│
├── 🔧 nginx/                     ← Reverse proxy config
│   └── (to be configured)
│
├── 📁 data/                      ← Persistent data storage
│   └── scraped/                  ← Scraped website content
│       └── matchainitiative/     ← The Matcha Initiative content
│           └── (YOUR FILES GO HERE) ⬅️
│
└── 📁 logs/                      ← Application logs
    └── (will be created on startup)
```

---

## 🎯 **WHERE TO PUT YOUR matchainitiative CONTENT**

**Destination Path:**
```
/volume1/docker/greenfrog-rag/data/scraped/matchainitiative/
```

**On MacBook via SMB:**
```
smb://192.168.50.171/docker/greenfrog-rag/data/scraped/matchainitiative/
```

**What to copy:**
- Your `~/Documents/matchainitiative` folder
- All HTML files, PDFs, images from The Matcha Initiative website
- Directory structure will be preserved

---

## 🚢 **DOCKER SERVICES (8 Total)**

| Service | Directory | Port | Status |
|---------|-----------|------|--------|
| **AnythingLLM** | `anythingllm/` | 3001 | Configured ⚙️ |
| **ChromaDB** | `chromadb/` | 8001 | Configured ⚙️ |
| **Piper TTS** | `piper-tts/` | 5000 | Complete ✅ |
| **XTTS-v2** | `xtts-v2/` | 5001 | Complete ✅ |
| **SadTalker** | `sadtalker/` | 10364 | Configured ⚙️ |
| **Scraper** | `scraper/` | - | Partial 🚧 |
| **Backend** | `backend/` | 8000 | Pending ⏳ |
| **Frontend** | `frontend/` | 3000 | Pending ⏳ |

---

## 💾 **DATA STORAGE LOCATIONS**

### On Host (NAS):
```
/volume1/docker/greenfrog-rag/data/
├── anythingllm/          ← RAG documents & embeddings
├── chromadb/             ← Vector database storage
└── scraped/              ← Website scrape cache
    └── matchainitiative/ ← Your content here ⬅️
```

### Inside Docker Containers:
```
anythingllm container:
  /app/server/storage → /volume1/docker/greenfrog-rag/data/anythingllm

chromadb container:
  /chroma/chroma → /volume1/docker/greenfrog-rag/data/chromadb

piper-tts container:
  /models → /volume1/docker/greenfrog-rag/piper-tts/models
  /cache → /volume1/docker/greenfrog-rag/piper-tts/cache

scraper container:
  /data → /volume1/docker/greenfrog-rag/data/scraped
```

---

## 🔗 **RELATED LOCATIONS**

### Ollama (Host System):
```
Location: Running on NAS host (not in Docker)
Port: 11434
Models: /usr/share/ollama/.ollama/models/
Config: /etc/ollama/
Service: systemctl status ollama

Models installed:
- llama3.1:8b (4.9GB) ← Primary
- llama3.2:3b (2GB)
- llama3.3:70b (42GB)
- mixtral:8x7b (26GB)
```

### nginx Reverse Proxy:
```
Location: /home/Davrine/docker/nginx-proxy/ (different project)
Config: /home/Davrine/docker/nginx-proxy/conf.d/
Domain: greenfrog.v4value.ai (to be configured)
```

---

## 🌐 **ACCESS URLS (After Deployment)**

| Service | Internal URL | External URL |
|---------|-------------|--------------|
| Frontend | http://192.168.50.171:3000 | http://greenfrog.v4value.ai |
| Backend | http://192.168.50.171:8000 | http://greenfrog.v4value.ai/api |
| AnythingLLM | http://192.168.50.171:3001 | (internal only) |
| ChromaDB | http://192.168.50.171:8001 | (internal only) |
| Piper TTS | http://192.168.50.171:5000 | (internal only) |
| XTTS-v2 | http://192.168.50.171:5001 | (internal only) |
| SadTalker | http://192.168.50.171:10364 | (internal only) |

---

## 📊 **CURRENT STATUS**

```
✅ Project structure created
✅ Docker Compose configured
✅ Piper TTS service complete
✅ XTTS-v2 service complete
✅ Documentation written
⚙️ Scraper partially complete
⏳ Backend not started
⏳ Frontend not started
⏳ GreenFrog avatar image needed
📂 matchainitiative content: WAITING FOR TRANSFER ⬅️
```

**Progress:** 60% complete
**Next Step:** Transfer matchainitiative content to `/volume1/docker/greenfrog-rag/data/scraped/matchainitiative/`

---

## 🚀 **QUICK COMMANDS**

### Navigate to project:
```bash
cd /volume1/docker/greenfrog-rag
```

### View structure:
```bash
tree -L 2 /volume1/docker/greenfrog-rag/
```

### Check data directory:
```bash
ls -la /volume1/docker/greenfrog-rag/data/scraped/matchainitiative/
```

### Start services (when ready):
```bash
cd /volume1/docker/greenfrog-rag
docker compose up -d
```

### Check logs:
```bash
docker compose logs -f
```

### Stop services:
```bash
docker compose down
```

---

## 💡 **IMPORTANT NOTES**

1. **All project files** are in `/volume1/docker/greenfrog-rag/`
2. **matchainitiative content** should go to `data/scraped/matchainitiative/`
3. **Ollama runs on host**, not in Docker (already configured)
4. **nginx reverse proxy** is in a different directory (`/home/Davrine/docker/nginx-proxy/`)
5. **Total disk space used**: ~500MB (will grow to ~25GB after deployment)

---

## 🆘 **GETTING HELP**

All documentation is in `/volume1/docker/greenfrog-rag/`:
- `README.md` - Main guide
- `ARCHITECTURE_DECISIONS.md` - Why we chose each technology
- `FINAL_ARCHITECTURE.md` - System design
- `PROJECT_STATUS.md` - What's complete, what's pending
- `TRANSFER_GUIDE.md` - How to transfer files from MacBook

**Current Task:** Transfer matchainitiative content from MacBook to NAS
**Method:** SMB via Finder (⌘K → smb://192.168.50.171)
