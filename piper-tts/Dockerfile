# Piper TTS API - CPU-optimized Text-to-Speech
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Download and install Piper binary
RUN wget https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz && \
    tar -xzf piper_linux_x86_64.tar.gz && \
    mv piper/piper /usr/local/bin/ && \
    chmod +x /usr/local/bin/piper && \
    rm -rf piper piper_linux_x86_64.tar.gz

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY download_models.py .

# Create directories
RUN mkdir -p /models /cache /outputs

# Download default voice model on build
RUN python download_models.py

# Expose API port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run the API server
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "5000", "--workers", "2"]
