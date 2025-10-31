"""
TTS Router - Text-to-Speech Endpoints
Handles TTS synthesis requests with hybrid routing
"""

from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import JSONResponse, StreamingResponse
import structlog
import os
import io

from app.models.schemas import TTSRequest, TTSResponse, ErrorResponse
from app.services.tts_service import get_tts_service, TTSService

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_tts() -> TTSService:
    """Dependency injection for TTS service"""
    return get_tts_service(
        piper_url=os.getenv("PIPER_URL", "http://piper:5000"),
        xtts_url=os.getenv("XTTS_URL", "http://xtts:8020")
    )


@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_speech(
    request: TTSRequest,
    tts: TTSService = Depends(get_tts)
):
    """
    Synthesize speech from text

    Args:
        request: TTS request with text and parameters
        tts: TTS service dependency

    Returns:
        TTSResponse with audio URL and metadata
    """
    logger.info("tts_synthesize_request",
               text_length=len(request.text),
               mode=request.mode,
               voice=request.voice)

    try:
        # Synthesize speech
        result = await tts.synthesize(
            text=request.text,
            mode=request.mode,
            voice=request.voice,
            speed=request.speed,
            language=request.language,
            return_base64=True
        )

        # Build response
        response = TTSResponse(
            audio_url=result["audio_url"],
            audio_base64=result.get("audio_base64"),
            mode_used=result["mode_used"],
            text_length=result["text_length"]
        )

        logger.info("tts_synthesize_success",
                   mode=result["mode_used"],
                   audio_size=len(result.get("audio_base64", "")))

        return response

    except Exception as e:
        logger.error("tts_synthesize_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"TTS synthesis failed: {str(e)}"
        )


@router.post("/synthesize/audio")
async def synthesize_audio_stream(
    request: TTSRequest,
    tts: TTSService = Depends(get_tts)
):
    """
    Synthesize speech and return audio stream directly

    Args:
        request: TTS request with text and parameters
        tts: TTS service dependency

    Returns:
        Audio stream (WAV format)
    """
    logger.info("tts_audio_stream_request",
               text_length=len(request.text),
               mode=request.mode)

    try:
        # Synthesize speech
        result = await tts.synthesize(
            text=request.text,
            mode=request.mode,
            voice=request.voice,
            speed=request.speed,
            language=request.language,
            return_base64=False
        )

        # Return audio stream
        audio_data = result["audio_data"]

        logger.info("tts_audio_stream_success",
                   audio_size=len(audio_data),
                   mode=result["mode_used"])

        return StreamingResponse(
            io.BytesIO(audio_data),
            media_type="audio/wav",
            headers={
                "Content-Disposition": "attachment; filename=speech.wav"
            }
        )

    except Exception as e:
        logger.error("tts_audio_stream_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"TTS audio stream failed: {str(e)}"
        )


@router.get("/voices/piper")
async def list_piper_voices(tts: TTSService = Depends(get_tts)):
    """
    List available Piper voices

    Args:
        tts: TTS service dependency

    Returns:
        List of Piper voice metadata
    """
    logger.info("list_piper_voices_request")

    try:
        voices = await tts.list_piper_voices()

        logger.info("list_piper_voices_success",
                   count=len(voices.get("voices", [])))
        return voices

    except Exception as e:
        logger.error("list_piper_voices_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Piper voices: {str(e)}"
        )


@router.get("/voices/xtts")
async def list_xtts_voices(tts: TTSService = Depends(get_tts)):
    """
    List available XTTS voice samples

    Args:
        tts: TTS service dependency

    Returns:
        List of XTTS voice sample metadata
    """
    logger.info("list_xtts_voices_request")

    try:
        voices = await tts.list_xtts_voices()

        logger.info("list_xtts_voices_success",
                   count=len(voices.get("voices", [])))
        return voices

    except Exception as e:
        logger.error("list_xtts_voices_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list XTTS voices: {str(e)}"
        )


@router.get("/health")
async def health_check(tts: TTSService = Depends(get_tts)):
    """
    Check TTS services health

    Args:
        tts: TTS service dependency

    Returns:
        Health status for Piper and XTTS
    """
    logger.info("tts_health_check_request")

    try:
        health = await tts.health_check()

        overall_status = "healthy" if (health["piper"] or health["xtts"]) else "unhealthy"

        logger.info("tts_health_check_complete",
                   status=overall_status,
                   piper=health["piper"],
                   xtts=health["xtts"])

        if overall_status == "healthy":
            return {
                "status": overall_status,
                "services": health
            }
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": overall_status,
                    "services": health
                }
            )

    except Exception as e:
        logger.error("tts_health_check_error", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e)
            }
        )
