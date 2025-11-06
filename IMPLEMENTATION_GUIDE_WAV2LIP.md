# Wav2Lip CPU Implementation Guide
## Quick Start for FastAPI Integration

**Target:** Replace SadTalker with CPU-compatible Wav2Lip solution
**Platform:** Docker + FastAPI on CPU-only system
**Expected Performance:** 10-60 seconds per video generation

---

## Option 1: Intel OPEA Docker (Recommended)

### Advantages
- Production-ready Docker image
- Pre-configured for CPU
- FastAPI reference implementation
- Maintained by Intel

### Quick Deployment

```bash
# Pull the image
docker pull opea/wav2lip:latest

# Run the container
docker run -d \
  --name wav2lip \
  -p 8080:8080 \
  -v $(pwd)/models:/models \
  -v $(pwd)/cache:/cache \
  -v $(pwd)/output:/output \
  -e DEVICE=cpu \
  -e CACHE_ENABLED=true \
  opea/wav2lip:latest

# Test the endpoint
curl -X POST http://localhost:8080/v1/animation \
  -F "audio=@test_audio.wav" \
  -F "avatar=@test_image.jpg"
```

### Integration with Existing FastAPI

```python
from fastapi import FastAPI, UploadFile
import httpx
import asyncio

app = FastAPI()

@app.post("/generate-avatar")
async def generate_avatar(audio: UploadFile, avatar: UploadFile):
    """Proxy to Wav2Lip service"""

    async with httpx.AsyncClient() as client:
        files = {
            'audio': (audio.filename, await audio.read(), audio.content_type),
            'avatar': (avatar.filename, await avatar.read(), avatar.content_type)
        }

        response = await client.post(
            'http://localhost:8080/v1/animation',
            files=files,
            timeout=120.0  # 2 minute timeout
        )

        return response.json()
```

---

## Option 2: Custom Wav2Lip Docker (More Control)

### Step 1: Create Dockerfile

```dockerfile
FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone Wav2Lip
WORKDIR /app
RUN git clone https://github.com/Rudrabha/Wav2Lip.git .

# Install Python dependencies
RUN pip install --no-cache-dir \
    torch==1.8.1+cpu \
    torchvision==0.9.1+cpu \
    torchaudio==0.8.1 \
    -f https://download.pytorch.org/whl/torch_stable.html

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn python-multipart

# Download models
RUN mkdir -p checkpoints && \
    cd checkpoints && \
    wget https://github.com/Rudrabha/Wav2Lip/releases/download/models/wav2lip.pth && \
    wget https://github.com/Rudrabha/Wav2Lip/releases/download/models/wav2lip_gan.pth

# Copy FastAPI server
COPY api_server.py /app/

# Force CPU mode
ENV CUDA_VISIBLE_DEVICES=""

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Step 2: Create FastAPI Server

```python
# api_server.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import subprocess
import os
import uuid
import shutil
from pathlib import Path
import json
from typing import Optional
import asyncio

app = FastAPI(title="Wav2Lip CPU Service")

# Configuration
CHECKPOINT_PATH = "checkpoints/wav2lip_gan.pth"  # or wav2lip.pth
UPLOAD_DIR = Path("/tmp/wav2lip/uploads")
OUTPUT_DIR = Path("/tmp/wav2lip/outputs")
CACHE_DIR = Path("/tmp/wav2lip/cache")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/v1/animation")
async def generate_animation(
    audio: UploadFile = File(...),
    avatar: UploadFile = File(...),
    fps: Optional[int] = 10,
    use_cache: Optional[bool] = True
):
    """
    Generate talking avatar animation from audio and image/video

    Args:
        audio: Audio file (.wav, .mp3)
        avatar: Image (.jpg, .png) or video (.mp4)
        fps: Frame rate (lower = faster processing)
        use_cache: Enable face detection caching

    Returns:
        Video file with lip-synced avatar
    """

    # Generate unique ID for this request
    request_id = str(uuid.uuid4())

    try:
        # Save uploaded files
        audio_path = UPLOAD_DIR / f"{request_id}_{audio.filename}"
        avatar_path = UPLOAD_DIR / f"{request_id}_{avatar.filename}"
        output_path = OUTPUT_DIR / f"{request_id}_output.mp4"

        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        with open(avatar_path, "wb") as f:
            f.write(await avatar.read())

        # Build Wav2Lip command
        cmd = [
            "python", "inference.py",
            "--checkpoint_path", CHECKPOINT_PATH,
            "--face", str(avatar_path),
            "--audio", str(audio_path),
            "--outfile", str(output_path),
            "--fps", str(fps),
            "--pads", "0", "10", "0", "0",  # Adjust padding as needed
            "--resize_factor", "1"
        ]

        if not use_cache:
            cmd.append("--nosmooth")

        # Run Wav2Lip inference
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Wav2Lip processing failed: {stderr.decode()}"
            )

        # Check if output was generated
        if not output_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Output video was not generated"
            )

        # Return the video file
        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=f"avatar_{request_id}.mp4"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup uploaded files (keep output for now)
        if audio_path.exists():
            audio_path.unlink()
        if avatar_path.exists():
            avatar_path.unlink()


@app.post("/v1/animation-with-cache")
async def generate_animation_cached(
    audio: UploadFile = File(...),
    avatar_id: str = "default",
    fps: Optional[int] = 10
):
    """
    Generate animation using cached face detection for known avatars

    This endpoint is significantly faster for repeated use of the same avatar
    """

    request_id = str(uuid.uuid4())

    try:
        # Check if avatar is in cache
        cached_avatar = CACHE_DIR / f"avatar_{avatar_id}.jpg"

        if not cached_avatar.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Avatar '{avatar_id}' not found in cache. Upload via /cache-avatar first."
            )

        # Save audio
        audio_path = UPLOAD_DIR / f"{request_id}_{audio.filename}"
        output_path = OUTPUT_DIR / f"{request_id}_output.mp4"

        with open(audio_path, "wb") as f:
            f.write(await audio.read())

        # Run with cached avatar
        cmd = [
            "python", "inference.py",
            "--checkpoint_path", CHECKPOINT_PATH,
            "--face", str(cached_avatar),
            "--audio", str(audio_path),
            "--outfile", str(output_path),
            "--fps", str(fps)
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        if not output_path.exists():
            raise HTTPException(status_code=500, detail="Generation failed")

        return FileResponse(
            output_path,
            media_type="video/mp4",
            filename=f"avatar_{request_id}.mp4"
        )

    finally:
        if audio_path.exists():
            audio_path.unlink()


@app.post("/cache-avatar")
async def cache_avatar(
    avatar: UploadFile = File(...),
    avatar_id: str = "default"
):
    """
    Cache an avatar for faster repeated processing

    Face detection will be performed once and cached
    """

    cached_path = CACHE_DIR / f"avatar_{avatar_id}.jpg"

    with open(cached_path, "wb") as f:
        f.write(await avatar.read())

    return {
        "status": "cached",
        "avatar_id": avatar_id,
        "path": str(cached_path)
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "wav2lip-cpu",
        "checkpoint": CHECKPOINT_PATH
    }


@app.delete("/cleanup")
async def cleanup_old_files(older_than_hours: int = 24):
    """Clean up old output files"""

    import time
    current_time = time.time()
    cutoff_time = current_time - (older_than_hours * 3600)

    deleted_count = 0

    for file_path in OUTPUT_DIR.glob("*.mp4"):
        if file_path.stat().st_mtime < cutoff_time:
            file_path.unlink()
            deleted_count += 1

    return {
        "status": "cleaned",
        "deleted_files": deleted_count
    }
```

### Step 3: Build and Run

```bash
# Build the Docker image
docker build -t wav2lip-cpu:latest .

# Run the container
docker run -d \
  --name wav2lip-service \
  -p 8000:8000 \
  -v $(pwd)/cache:/tmp/wav2lip/cache \
  -v $(pwd)/output:/tmp/wav2lip/outputs \
  --restart unless-stopped \
  wav2lip-cpu:latest

# Check logs
docker logs -f wav2lip-service
```

---

## Option 3: OpenVINO Optimized Version

For best CPU performance, convert to OpenVINO:

```bash
# Install OpenVINO toolkit
pip install openvino-dev

# Convert Wav2Lip model
mo --input_model wav2lip.pth \
   --output_dir openvino_models/ \
   --model_name wav2lip_optimized

# Use OpenVINO inference (modify inference.py)
```

See: https://docs.openvino.ai/2025/notebooks/wav2lip-with-output.html

---

## Performance Optimization Tips

### 1. Face Detection Caching

```python
# Pre-process avatars once
@app.on_event("startup")
async def preload_avatars():
    """Pre-detect faces for common avatars"""
    common_avatars = [
        "default_male.jpg",
        "default_female.jpg",
        "business_avatar.jpg"
    ]

    for avatar_file in common_avatars:
        if Path(f"avatars/{avatar_file}").exists():
            # Run face detection once
            subprocess.run([
                "python", "preprocess_faces.py",
                "--input", f"avatars/{avatar_file}",
                "--output", f"cache/{avatar_file}.cache"
            ])
```

### 2. Reduce FPS

```python
# Use fps=10 instead of fps=25
# Reduces processing by ~60% with minimal quality loss
await generate_animation(audio, avatar, fps=10)
```

### 3. Use Smaller Models

```python
# wav2lip.pth (smaller) vs wav2lip_gan.pth (better quality)
CHECKPOINT_PATH = "checkpoints/wav2lip.pth"  # Faster
```

### 4. Parallel Processing

```python
# Process multiple requests in parallel (if CPU has enough cores)
import concurrent.futures

executor = concurrent.futures.ProcessPoolExecutor(max_workers=2)

@app.post("/batch-generate")
async def batch_generate(requests: list):
    futures = [
        executor.submit(process_single, req)
        for req in requests
    ]
    results = [f.result() for f in futures]
    return results
```

---

## Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  wav2lip:
    build: .
    container_name: wav2lip-service
    ports:
      - "8000:8000"
    volumes:
      - ./cache:/tmp/wav2lip/cache
      - ./output:/tmp/wav2lip/outputs
      - ./models:/app/checkpoints
    environment:
      - CUDA_VISIBLE_DEVICES=
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Your existing FastAPI backend
  backend:
    image: your-backend:latest
    ports:
      - "8080:8080"
    environment:
      - WAV2LIP_URL=http://wav2lip:8000
    depends_on:
      - wav2lip
```

---

## Integration Examples

### Python Client

```python
import httpx
import asyncio

async def generate_talking_avatar(audio_file: str, avatar_file: str):
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(audio_file, 'rb') as audio, open(avatar_file, 'rb') as avatar:
            files = {
                'audio': ('audio.wav', audio, 'audio/wav'),
                'avatar': ('avatar.jpg', avatar, 'image/jpeg')
            }

            response = await client.post(
                'http://localhost:8000/v1/animation',
                files=files,
                params={'fps': 10, 'use_cache': True}
            )

            # Save the result
            with open('output.mp4', 'wb') as f:
                f.write(response.content)

# Usage
asyncio.run(generate_talking_avatar('speech.wav', 'avatar.jpg'))
```

### JavaScript/TypeScript Client

```typescript
async function generateAvatar(audioBlob: Blob, avatarBlob: Blob) {
  const formData = new FormData();
  formData.append('audio', audioBlob, 'audio.wav');
  formData.append('avatar', avatarBlob, 'avatar.jpg');

  const response = await fetch('http://localhost:8000/v1/animation', {
    method: 'POST',
    body: formData
  });

  const videoBlob = await response.blob();
  return URL.createObjectURL(videoBlob);
}
```

### cURL Examples

```bash
# Basic generation
curl -X POST http://localhost:8000/v1/animation \
  -F "audio=@speech.wav" \
  -F "avatar=@portrait.jpg" \
  -F "fps=10" \
  -o output.mp4

# Using cached avatar
curl -X POST http://localhost:8000/v1/animation-with-cache \
  -F "audio=@speech.wav" \
  -F "avatar_id=john_doe" \
  -F "fps=10" \
  -o output.mp4

# Cache a new avatar
curl -X POST http://localhost:8000/cache-avatar \
  -F "avatar=@new_person.jpg" \
  -F "avatar_id=jane_doe"

# Health check
curl http://localhost:8000/health
```

---

## Monitoring and Logging

### Add Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, generate_latest
import time

# Metrics
generation_counter = Counter('avatar_generations_total', 'Total avatar generations')
generation_duration = Histogram('avatar_generation_duration_seconds', 'Generation duration')
generation_errors = Counter('avatar_generation_errors_total', 'Generation errors')

@app.post("/v1/animation")
async def generate_animation(...):
    start_time = time.time()

    try:
        # ... existing code ...
        generation_counter.inc()
        return result
    except Exception as e:
        generation_errors.inc()
        raise
    finally:
        duration = time.time() - start_time
        generation_duration.observe(duration)

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Add Structured Logging

```python
import logging
import json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.post("/v1/animation")
async def generate_animation(...):
    logger.info(json.dumps({
        "event": "generation_started",
        "request_id": request_id,
        "audio_size": audio.size,
        "avatar_size": avatar.size
    }))

    # ... processing ...

    logger.info(json.dumps({
        "event": "generation_completed",
        "request_id": request_id,
        "duration": duration,
        "output_size": output_path.stat().st_size
    }))
```

---

## Troubleshooting

### Issue: "CUDA not available" warnings

```bash
# Ensure CPU-only mode is enforced
export CUDA_VISIBLE_DEVICES=""
# Or in Dockerfile: ENV CUDA_VISIBLE_DEVICES=""
```

### Issue: Slow processing (>2 minutes)

```yaml
# Reduce FPS
fps: 10  # instead of 25

# Use smaller model
checkpoint: wav2lip.pth  # instead of wav2lip_gan.pth

# Enable caching
use_cache: true
```

### Issue: Out of memory

```python
# Process in smaller batches
# Reduce video resolution
--resize_factor 2  # Half resolution

# Limit concurrent requests
semaphore = asyncio.Semaphore(2)  # Max 2 concurrent
```

### Issue: Poor lip sync quality

```python
# Adjust padding
--pads 0 10 0 0  # top, bottom, left, right

# Try GAN model for better quality
CHECKPOINT_PATH = "checkpoints/wav2lip_gan.pth"

# Increase FPS (slower but better)
fps: 25
```

---

## Production Checklist

- [ ] Docker image built and tested
- [ ] Health check endpoint working
- [ ] Monitoring/logging configured
- [ ] Face detection caching implemented
- [ ] File cleanup task scheduled
- [ ] Error handling robust
- [ ] Timeout values appropriate
- [ ] Resource limits set (CPU/memory)
- [ ] Backup/failover strategy defined
- [ ] Performance benchmarks completed

---

## Expected Performance Benchmarks

| Audio Length | FPS | Cache | Expected Time | Notes |
|--------------|-----|-------|---------------|-------|
| 5 seconds | 10 | Yes | 5-10s | Fast |
| 5 seconds | 10 | No | 20-30s | First time |
| 30 seconds | 10 | Yes | 30-45s | Acceptable |
| 30 seconds | 10 | No | 90-120s | Initial |
| 2 minutes | 10 | Yes | 2-3 min | Good |
| 2 minutes | 25 | Yes | 4-6 min | High quality |

---

## Next Steps

1. **Choose deployment option** (OPEA vs Custom)
2. **Build and test locally**
3. **Run performance benchmarks**
4. **Optimize based on results**
5. **Deploy to production**
6. **Monitor and iterate**

---

## Additional Resources

- **Official Repo:** https://github.com/Rudrabha/Wav2Lip
- **OpenVINO Tutorial:** https://docs.openvino.ai/2025/notebooks/wav2lip-with-output.html
- **OPEA Documentation:** Search Intel Developer Zone for "AI Avatar Chatbot"
- **Community Docker:** https://gist.github.com/xenogenesi/e62d3d13dadbc164124c830e9c453668

---

**Document Version:** 1.0
**Last Updated:** 2025-11-03
**Status:** Ready for Implementation
