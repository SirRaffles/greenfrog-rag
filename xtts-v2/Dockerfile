# XTTS-v2 API - Coqui TTS with Voice Cloning
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install PyTorch CPU version (no GPU)
RUN pip install --no-cache-dir \
    torch==2.0.1 \
    torchaudio==2.0.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install TTS (Coqui)
RUN pip install --no-cache-dir TTS==0.22.0

# Copy application code
COPY app.py .
COPY download_models.py .

# Create directories
RUN mkdir -p /models /voices /outputs /cache

# Download XTTS-v2 model on build (this may take a while)
RUN python download_models.py

# Expose API port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the API server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "1"]
