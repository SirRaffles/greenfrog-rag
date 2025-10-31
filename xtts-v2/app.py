"""
XTTS-v2 API Server
Voice cloning and multilingual text-to-speech using Coqui TTS
"""
import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, List
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import torch
from TTS.api import TTS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="GreenFrog XTTS-v2 API",
    description="Voice cloning and multilingual TTS using Coqui XTTS-v2",
    version="1.0.0"
)

# Configuration
MODELS_DIR = Path("/models")
VOICES_DIR = Path("/voices")
OUTPUTS_DIR = Path("/outputs")
CACHE_DIR = Path("/cache")

# Ensure directories exist
VOICES_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# Set TTS cache
os.environ['TTS_HOME'] = str(MODELS_DIR)

# Device configuration
DEVICE = os.getenv("XTTS_DEVICE", "cpu")
DEFAULT_LANGUAGE = os.getenv("XTTS_LANGUAGE", "en")

# Global TTS model (loaded on startup)
tts_model = None

class TTSRequest(BaseModel):
    """TTS generation request"""
    text: str = Field(..., min_length=1, max_length=5000, description="Text to synthesize")
    language: Optional[str] = Field(DEFAULT_LANGUAGE, description="Language code (en, es, fr, de, it, pt, pl, tr, ru, nl, cs, ar, zh-cn, ja, hu, ko)")
    speaker_wav: Optional[str] = Field(None, description="Path to speaker reference audio for voice cloning")
    speed: Optional[float] = Field(1.0, ge=0.5, le=2.0, description="Speaking speed (0.5-2.0)")

class TTSResponse(BaseModel):
    """TTS generation response"""
    success: bool
    message: str
    audio_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None

@app.on_event("startup")
async def startup_event():
    """Load TTS model on startup"""
    global tts_model
    try:
        logger.info("Loading XTTS-v2 model...")
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(DEVICE)
        logger.info(f"✅ XTTS-v2 model loaded successfully on {DEVICE}")
        logger.info(f"📋 Supported languages: {', '.join(tts_model.languages)}")
    except Exception as e:
        logger.error(f"❌ Failed to load XTTS-v2 model: {e}")
        raise

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")

    return {
        "status": "healthy",
        "service": "xtts-v2",
        "version": "1.0.0",
        "device": DEVICE,
        "model": "tts_models/multilingual/multi-dataset/xtts_v2",
        "languages": tts_model.languages if tts_model else [],
        "voice_cloning": "enabled"
    }

@app.post("/tts")
async def text_to_speech(request: TTSRequest):
    """
    Generate speech from text with optional voice cloning

    Args:
        request: TTS request with text, language, and optional speaker reference

    Returns:
        Audio file
    """
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")

    try:
        # Validate language
        if request.language not in tts_model.languages:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}. Supported: {', '.join(tts_model.languages)}"
            )

        # Create output file
        output_file = OUTPUTS_DIR / f"tts_{os.urandom(8).hex()}.wav"

        logger.info(f"Generating TTS: {len(request.text)} chars, lang={request.language}, voice_cloning={request.speaker_wav is not None}")

        # Generate speech
        if request.speaker_wav:
            # Voice cloning mode
            speaker_path = VOICES_DIR / request.speaker_wav
            if not speaker_path.exists():
                raise HTTPException(status_code=404, detail=f"Speaker reference not found: {request.speaker_wav}")

            tts_model.tts_to_file(
                text=request.text,
                file_path=str(output_file),
                speaker_wav=str(speaker_path),
                language=request.language,
                speed=request.speed
            )
        else:
            # Standard TTS mode (no voice cloning)
            tts_model.tts_to_file(
                text=request.text,
                file_path=str(output_file),
                language=request.language,
                speed=request.speed
            )

        if not output_file.exists():
            raise HTTPException(status_code=500, detail="TTS generation failed")

        # Get file stats
        file_size = output_file.stat().st_size

        logger.info(f"✅ TTS generated: {file_size} bytes")

        # Return audio file
        return FileResponse(
            path=output_file,
            media_type="audio/wav",
            filename="speech.wav",
            headers={
                "X-File-Size": str(file_size),
                "X-Language": request.language,
            },
            background=lambda: output_file.unlink()  # Clean up after sending
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts/clone")
async def text_to_speech_with_upload(
    text: str = Form(..., min_length=1, max_length=5000),
    language: str = Form(DEFAULT_LANGUAGE),
    speed: float = Form(1.0),
    speaker_audio: UploadFile = File(...)
):
    """
    Generate speech with voice cloning using uploaded audio

    Args:
        text: Text to synthesize
        language: Language code
        speed: Speaking speed
        speaker_audio: Audio file for voice cloning (6-30 seconds recommended)

    Returns:
        Audio file with cloned voice
    """
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")

    # Save uploaded audio temporarily
    temp_speaker = CACHE_DIR / f"speaker_{os.urandom(8).hex()}.wav"

    try:
        # Save speaker audio
        with temp_speaker.open("wb") as f:
            content = await speaker_audio.read()
            f.write(content)

        logger.info(f"Voice cloning: {len(text)} chars, speaker audio: {temp_speaker.stat().st_size} bytes")

        # Create output file
        output_file = OUTPUTS_DIR / f"tts_cloned_{os.urandom(8).hex()}.wav"

        # Generate speech with cloned voice
        tts_model.tts_to_file(
            text=text,
            file_path=str(output_file),
            speaker_wav=str(temp_speaker),
            language=language,
            speed=speed
        )

        if not output_file.exists():
            raise HTTPException(status_code=500, detail="Voice cloning failed")

        # Get file stats
        file_size = output_file.stat().st_size

        logger.info(f"✅ Voice cloned: {file_size} bytes")

        # Return cloned audio
        return FileResponse(
            path=output_file,
            media_type="audio/wav",
            filename="cloned_speech.wav",
            headers={
                "X-File-Size": str(file_size),
                "X-Language": language,
                "X-Voice-Cloning": "true",
            },
            background=lambda: [output_file.unlink(), temp_speaker.unlink()]
        )

    except HTTPException:
        if temp_speaker.exists():
            temp_speaker.unlink()
        raise
    except Exception as e:
        if temp_speaker.exists():
            temp_speaker.unlink()
        logger.error(f"Voice cloning error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/voices/upload")
async def upload_voice_reference(
    name: str = Form(..., min_length=1, max_length=50),
    audio: UploadFile = File(...)
):
    """
    Upload a voice reference audio for reuse

    Args:
        name: Voice reference name (alphanumeric + underscore)
        audio: Audio file (6-30 seconds recommended, WAV/MP3)

    Returns:
        Success message with voice reference ID
    """
    # Sanitize filename
    safe_name = "".join(c for c in name if c.isalnum() or c in "_-")
    voice_file = VOICES_DIR / f"{safe_name}.wav"

    if voice_file.exists():
        raise HTTPException(status_code=400, detail=f"Voice reference '{safe_name}' already exists")

    try:
        # Save audio file
        with voice_file.open("wb") as f:
            content = await audio.read()
            f.write(content)

        file_size = voice_file.stat().st_size

        logger.info(f"✅ Voice reference uploaded: {safe_name} ({file_size} bytes)")

        return {
            "success": True,
            "message": f"Voice reference uploaded successfully",
            "voice_id": safe_name,
            "file_size": file_size,
            "path": f"/voices/{safe_name}.wav"
        }

    except Exception as e:
        if voice_file.exists():
            voice_file.unlink()
        logger.error(f"Upload error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/voices")
async def list_voices():
    """List all available voice references"""
    voices = []
    for voice_file in VOICES_DIR.glob("*.wav"):
        voices.append({
            "name": voice_file.stem,
            "path": f"/voices/{voice_file.name}",
            "size_mb": round(voice_file.stat().st_size / 1024 / 1024, 2)
        })

    return {
        "voices": voices,
        "total": len(voices)
    }

@app.delete("/voices/{voice_name}")
async def delete_voice(voice_name: str):
    """Delete a voice reference"""
    voice_file = VOICES_DIR / f"{voice_name}.wav"

    if not voice_file.exists():
        raise HTTPException(status_code=404, detail=f"Voice reference '{voice_name}' not found")

    try:
        voice_file.unlink()
        logger.info(f"🗑️ Deleted voice reference: {voice_name}")

        return {
            "success": True,
            "message": f"Voice reference '{voice_name}' deleted"
        }

    except Exception as e:
        logger.error(f"Delete error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/languages")
async def list_languages():
    """List supported languages"""
    if tts_model is None:
        raise HTTPException(status_code=503, detail="TTS model not loaded")

    return {
        "languages": tts_model.languages,
        "total": len(tts_model.languages),
        "default": DEFAULT_LANGUAGE
    }

@app.delete("/cache")
async def clear_cache():
    """Clear temporary audio files"""
    deleted = 0

    # Clear outputs
    for audio_file in OUTPUTS_DIR.glob("*.wav"):
        try:
            audio_file.unlink()
            deleted += 1
        except Exception as e:
            logger.warning(f"Failed to delete {audio_file}: {e}")

    # Clear cache
    for cache_file in CACHE_DIR.glob("*"):
        try:
            cache_file.unlink()
            deleted += 1
        except Exception as e:
            logger.warning(f"Failed to delete {cache_file}: {e}")

    return {
        "deleted_files": deleted,
        "message": f"Cleared {deleted} cached files"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, workers=1)
