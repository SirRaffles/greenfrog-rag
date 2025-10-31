# GreenFrog RAG Avatar Chatbot

AI-powered sustainability assistant with animated avatar and voice, using content from The Matcha Initiative.

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│  Next.js Frontend                        │
│  - GreenFrog chat interface              │
│  - Real-time avatar display              │
│  Port: 3000                              │
└─────────────┬───────────────────────────┘
              │
┌─────────────▼───────────────────────────┐
│  FastAPI Backend                         │
│  - RAG orchestration                     │
│  - Avatar/TTS coordination               │
│  Port: 8000                              │
└─────────────┬───────────────────────────┘
              │
       ┌──────┴──────┐
       │             │
┌──────▼──────┐  ┌──▼──────────────────────┐
│ AnythingLLM │  │  Avatar Stack            │
│ + ChromaDB  │  │  - Piper TTS             │
│ + Groq API  │  │  - SadTalker Generation  │
│ Port: 3001  │  │  Port: 10364             │
└─────────────┘  └──────────────────────────┘
```

## 🚀 Components

### 1. **AnythingLLM** (RAG Core)
- Document management and embedding
- ChromaDB vector database
- Groq API integration (Llama 3.3 70B)
- Port: 3001

### 2. **ChromaDB** (Vector Store)
- Persistent vector storage
- Fast similarity search
- Port: 8001

### 3. **Piper TTS** (Text-to-Speech)
- High-quality open-source TTS
- Low latency, CPU-efficient
- Multiple voice models
- Port: 5000

### 4. **SadTalker** (Avatar Generation)
- Real-time talking head generation
- Lip-sync with audio
- GreenFrog custom avatar
- Port: 10364

### 5. **Web Scraper** (Content Sync)
- Daily sync from thematchainitiative.com
- Change detection with hashing
- Incremental updates
- Cron: Daily at 2 AM

### 6. **FastAPI Backend** (Orchestration)
- API gateway for all services
- Request routing and coordination
- WebSocket support for real-time
- Port: 8000

### 7. **Next.js Frontend** (UI)
- Chat interface with GreenFrog
- Video avatar display
- Voice input (optional)
- Port: 3000

## 📋 Prerequisites

- UGREEN DXP 4800 Plus NAS
- Docker & Docker Compose
- 32GB RAM (minimum 16GB for basic functionality)
- Groq API key (free tier)

## 🔧 Setup

### 1. Environment Configuration

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your settings
nano .env
```

Required variables:
```env
# Groq API
GROQ_API_KEY=your_groq_api_key_here

# Ports
FRONTEND_PORT=3000
BACKEND_PORT=8000
ANYTHINGLLM_PORT=3001
CHROMADB_PORT=8001
PIPER_TTS_PORT=5000
SADTALKER_PORT=10364

# Paths
DATA_PATH=/volume1/docker/greenfrog-rag/data
LOGS_PATH=/volume1/docker/greenfrog-rag/logs
```

### 2. Get Groq API Key

1. Visit https://console.groq.com
2. Sign up for free account
3. Generate API key
4. Add to `.env` file

### 3. Deploy Stack

```bash
cd /volume1/docker/greenfrog-rag
docker compose up -d
```

### 4. Initial Data Load

```bash
# Run initial website scrape
docker exec greenfrog-scraper python scrape_matcha.py --initial

# Wait for embedding (may take 10-30 minutes)
docker logs -f greenfrog-anythingllm
```

### 5. Access Application

- Frontend: http://greenfrog.v4value.ai or http://192.168.50.171:3000
- Backend API: http://192.168.50.171:8000/docs
- AnythingLLM: http://192.168.50.171:3001

## 🧪 Testing

```bash
# Test RAG endpoint
curl http://192.168.50.171:8000/api/chat -X POST \
  -H "Content-Type: application/json" \
  -d '{"message": "What is The Matcha Initiative?"}'

# Test TTS
curl http://192.168.50.171:5000/tts -X POST \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, I am GreenFrog"}' \
  --output test.wav

# Test avatar generation
curl http://192.168.50.171:10364/generate -X POST \
  -F "audio=@test.wav" \
  -F "image=@greenfrog.png" \
  --output avatar.mp4
```

## 📊 Monitoring

```bash
# View all logs
docker compose logs -f

# Individual service logs
docker logs -f greenfrog-backend
docker logs -f greenfrog-anythingllm
docker logs -f greenfrog-scraper

# Resource usage
docker stats
```

## 🔄 Website Sync

The scraper runs automatically daily at 2 AM:
- Scrapes thematchainitiative.com
- Detects changes using content hashing
- Updates only modified pages
- Re-embeds changed content

Manual sync:
```bash
docker exec greenfrog-scraper python scrape_matcha.py
```

## 🎨 Customization

### Change GreenFrog Avatar
1. Replace `sadtalker/greenfrog.png` with your custom image
2. Restart SadTalker: `docker compose restart sadtalker`

### Change Voice
1. Download new Piper voice model from https://github.com/rhasspy/piper
2. Place in `piper-tts/models/`
3. Update `piper-tts/config.yaml`
4. Restart: `docker compose restart piper-tts`

### Adjust RAG Parameters
Edit `anythingllm/config.json`:
- `top_k`: Number of documents to retrieve (default: 5)
- `similarity_threshold`: Minimum relevance score (default: 0.7)
- `chunk_size`: Document chunk size (default: 1000)

## 🐛 Troubleshooting

### AnythingLLM won't start
```bash
# Check logs
docker logs greenfrog-anythingllm

# Reset data (CAUTION: loses embeddings)
rm -rf data/anythingllm/*
docker compose restart anythingllm
```

### SadTalker slow/crashes
- Requires 8GB+ RAM
- Check available memory: `free -h`
- Reduce concurrent requests in backend

### Scraper fails
```bash
# Check website accessibility
curl -I https://www.thematchainitiative.com

# Test manually
docker exec -it greenfrog-scraper bash
python scrape_matcha.py --debug
```

## 💰 Cost Breakdown

| Component | Cost |
|-----------|------|
| RAM Upgrade (32GB) | $80 (one-time) |
| Groq API (free tier) | $0 (14,400 req/day) |
| All software | $0 (open-source) |
| **Total Monthly** | **$0** |

## 📈 Performance Expectations

- **RAG Retrieval**: 200-500ms
- **Groq LLM**: 50-200ms (very fast)
- **TTS Generation**: 100-300ms
- **Avatar Rendering**: 2-5 seconds
- **Total E2E Latency**: 3-6 seconds

## 🔐 Security

- No external API keys stored in code
- All credentials in `.env` (gitignored)
- Local TTS/avatar (no data leaves NAS)
- Only Groq API receives user queries

## 📚 Documentation

- `/docs/ARCHITECTURE.md` - Detailed architecture
- `/docs/API.md` - Backend API documentation
- `/docs/DEPLOYMENT.md` - Deployment guide
- `/docs/SCRAPER.md` - Scraper configuration

## 🆘 Support

Issues? Check:
1. Docker logs: `docker compose logs -f`
2. System resources: `docker stats`
3. Network: `docker network inspect greenfrog-network`
4. Port conflicts: `ss -tulpn | grep -E '(3000|3001|8000|8001|5000|10364)'`

## 📝 License

MIT License - See LICENSE file

## 🙏 Credits

- AnythingLLM - https://github.com/Mintplex-Labs/anything-llm
- Piper TTS - https://github.com/rhasspy/piper
- SadTalker - https://github.com/OpenTalker/SadTalker
- ChromaDB - https://www.trychroma.com
- Groq - https://groq.com
- The Matcha Initiative - https://www.thematchainitiative.com
