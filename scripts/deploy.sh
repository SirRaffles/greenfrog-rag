#!/bin/bash
#
# GreenFrog RAG Avatar - Deployment Script
# Deploys all services and configures the full stack
#

set -e  # Exit on error

PROJECT_ROOT="/volume1/docker/greenfrog-rag"
cd "$PROJECT_ROOT"

echo "🐸 GreenFrog RAG Avatar - Deployment Script"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Step 1: Check prerequisites
log_info "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    log_error "Docker not found. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    log_error "Docker Compose not found. Please install Docker Compose first."
    exit 1
fi

log_info "✓ Docker and Docker Compose found"

# Step 2: Check Ollama
log_info "Checking Ollama..."

if ! curl -s http://192.168.50.171:11434/api/tags &> /dev/null; then
    log_warn "Ollama not accessible at http://192.168.50.171:11434"
    log_warn "Make sure Ollama is running on the host"
else
    log_info "✓ Ollama is running"

    # Check for llama3.1:8b model
    if curl -s http://192.168.50.171:11434/api/tags | grep -q "llama3.1:8b"; then
        log_info "✓ llama3.1:8b model found"
    else
        log_warn "llama3.1:8b model not found. Pull it with: ollama pull llama3.1:8b"
    fi
fi

# Step 3: Stop existing containers
log_info "Stopping existing containers..."
docker compose down || true

# Step 4: Build services
log_info "Building Docker images..."
docker compose build --no-cache

# Step 5: Start core services first (ChromaDB, AnythingLLM)
log_info "Starting core services (ChromaDB, AnythingLLM)..."
docker compose up -d chromadb anythingllm

log_info "Waiting for services to be healthy (60 seconds)..."
sleep 60

# Check AnythingLLM health
if curl -sf http://192.168.50.171:3001/api/ping &> /dev/null; then
    log_info "✓ AnythingLLM is healthy"
else
    log_error "AnythingLLM health check failed"
    docker logs greenfrog-anythingllm --tail 50
    exit 1
fi

# Step 6: Start Piper TTS
log_info "Starting Piper TTS service..."
docker compose up -d piper

log_info "Waiting for Piper to download models (30 seconds)..."
sleep 30

# Step 7: Start backend
log_info "Starting FastAPI backend..."
docker compose up -d backend

log_info "Waiting for backend to start (10 seconds)..."
sleep 10

# Check backend health
if curl -sf http://192.168.50.171:8000/health &> /dev/null; then
    log_info "✓ Backend is healthy"
else
    log_warn "Backend health check failed, checking logs..."
    docker logs greenfrog-backend --tail 50
fi

# Step 8: Start frontend
log_info "Starting Next.js frontend..."
docker compose up -d frontend

log_info "Waiting for frontend to start (20 seconds)..."
sleep 20

# Check frontend
if curl -sf http://192.168.50.171:3000 &> /dev/null; then
    log_info "✓ Frontend is accessible"
else
    log_warn "Frontend not yet accessible, may still be building..."
fi

# Step 9: Display service status
echo ""
log_info "Service Status:"
docker compose ps

# Step 10: Display URLs
echo ""
log_info "Access URLs:"
echo "  Frontend:    http://192.168.50.171:3000"
echo "  Backend API: http://192.168.50.171:8000/docs"
echo "  AnythingLLM: http://192.168.50.171:3001"
echo ""

# Step 11: Next steps
log_info "Next Steps:"
echo "  1. Configure AnythingLLM workspace at http://192.168.50.171:3001"
echo "  2. Load scraped content from data/scraped/Matchainitiative/"
echo "  3. Create GreenFrog avatar image (sadtalker/avatars/greenfrog.png)"
echo "  4. Configure nginx reverse proxy for greenfrog.v4value.ai"
echo ""

log_info "Deployment complete! 🎉"
