"""
Piper TTS API Server
Fast, CPU-optimized text-to-speech using Piper
"""
import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="GreenFrog Piper TTS API",
    description="Local CPU-optimized text-to-speech using Piper",
    version="1.0.0"
)

# Configuration
MODELS_DIR = Path("/models")
CACHE_DIR = Path("/cache")
OUTPUTS_DIR = Path("/outputs")
PIPER_BIN = "/usr/local/bin/piper"

# Ensure directories exist
CACHE_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# Default voice model
DEFAULT_VOICE = os.getenv("PIPER_VOICE", "en_US-lessac-medium")
DEFAULT_RATE = float(os.getenv("PIPER_RATE", "1.0"))

class TTSRequest(BaseModel):
    """TTS generation request"""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    voice: Optional[str] = Field(DEFAULT_VOICE, description="Voice model to use")
    rate: Optional[float] = Field(DEFAULT_RATE, ge=0.5, le=2.0, description="Speaking rate (0.5-2.0)")
    format: Optional[str] = Field("wav", description="Audio format (wav only currently)")

class TTSResponse(BaseModel):
    """TTS generation response"""
    success: bool
    message: str
    audio_length_seconds: Optional[float] = None
    file_size_bytes: Optional[int] = None

async def generate_speech(text: str, voice: str, rate: float) -> Path:
    """
    Generate speech using Piper TTS

    Args:
        text: Text to synthesize
        voice: Voice model name
        rate: Speaking rate

    Returns:
        Path to generated audio file
    """
    # Verify model exists
    model_path = MODELS_DIR / f"{voice}.onnx"
    if not model_path.exists():
        raise HTTPException(
            status_code=400,
            detail=f"Voice model '{voice}' not found. Available: {DEFAULT_VOICE}"
        )

    # Create temporary output file
    output_file = OUTPUTS_DIR / f"tts_{os.urandom(8).hex()}.wav"

    try:
        # Build Piper command
        cmd = [
            PIPER_BIN,
            "--model", str(model_path),
            "--output_file", str(output_file),
        ]

        # Add rate if not default
        if rate != 1.0:
            cmd.extend(["--length-scale", str(1.0 / rate)])

        logger.info(f"Generating TTS: {len(text)} chars, voice={voice}, rate={rate}")

        # Run Piper process
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Send text to stdin
        stdout, stderr = await process.communicate(input=text.encode('utf-8'))

        if process.returncode != 0:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            logger.error(f"Piper failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"TTS generation failed: {error_msg}")

        if not output_file.exists():
            raise HTTPException(status_code=500, detail="TTS generation produced no output")

        logger.info(f"TTS generated successfully: {output_file.stat().st_size} bytes")
        return output_file

    except Exception as e:
        # Clean up on error
        if output_file.exists():
            output_file.unlink()
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    # Check if Piper binary exists
    if not Path(PIPER_BIN).exists():
        raise HTTPException(status_code=500, detail="Piper binary not found")

    # Check if default voice model exists
    default_model = MODELS_DIR / f"{DEFAULT_VOICE}.onnx"
    if not default_model.exists():
        raise HTTPException(status_code=500, detail=f"Default voice model not found: {DEFAULT_VOICE}")

    return {
        "status": "healthy",
        "service": "piper-tts",
        "version": "1.0.0",
        "default_voice": DEFAULT_VOICE,
        "models_available": [
            f.stem.replace('.onnx', '')
            for f in MODELS_DIR.glob("*.onnx")
        ]
    }

@app.post("/tts", response_model=TTSResponse)
async def text_to_speech(request: TTSRequest):
    """
    Generate speech from text

    Returns audio file as response
    """
    try:
        # Generate speech
        audio_file = await generate_speech(
            text=request.text,
            voice=request.voice,
            rate=request.rate
        )

        # Get file stats
        file_size = audio_file.stat().st_size

        # Estimate audio length (WAV: 44.1kHz, 16-bit, mono ≈ 88KB/sec)
        audio_length = file_size / 88000

        # Return audio file
        return FileResponse(
            path=audio_file,
            media_type="audio/wav",
            filename="speech.wav",
            headers={
                "X-Audio-Length": str(audio_length),
                "X-File-Size": str(file_size),
            },
            background=lambda: audio_file.unlink()  # Clean up after sending
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts/stream")
async def text_to_speech_stream(request: TTSRequest):
    """
    Generate speech and stream it
    (Currently returns full file, streaming TBD)
    """
    # For now, same as /tts
    # TODO: Implement actual streaming with chunked encoding
    return await text_to_speech(request)

@app.get("/voices")
async def list_voices():
    """List available voice models"""
    voices = []
    for model_file in MODELS_DIR.glob("*.onnx"):
        voice_name = model_file.stem.replace('.onnx', '')
        voices.append({
            "name": voice_name,
            "path": str(model_file),
            "size_mb": round(model_file.stat().st_size / 1024 / 1024, 2),
            "is_default": voice_name == DEFAULT_VOICE
        })

    return {
        "voices": voices,
        "default": DEFAULT_VOICE
    }

@app.delete("/cache")
async def clear_cache():
    """Clear temporary audio files"""
    deleted = 0
    for audio_file in OUTPUTS_DIR.glob("*.wav"):
        try:
            audio_file.unlink()
            deleted += 1
        except Exception as e:
            logger.warning(f"Failed to delete {audio_file}: {e}")

    return {
        "deleted_files": deleted,
        "message": f"Cleared {deleted} cached audio files"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, workers=2)
