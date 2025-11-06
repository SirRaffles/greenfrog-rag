"""
Avatar Router - Avatar Video Generation Endpoints
Handles avatar video generation from audio/text
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
import structlog
import os
import io

from app.models.schemas import AvatarRequest, AvatarResponse, ErrorResponse
from app.services.avatar_service import get_avatar_service, AvatarService
from app.services.tts_service import get_tts_service, TTSService

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_avatar() -> AvatarService:
    """Dependency injection for avatar service"""
    return get_avatar_service(
        sadtalker_url=os.getenv("SADTALKER_API", "http://sadtalker:7860")
    )


def get_tts() -> TTSService:
    """Dependency injection for TTS service"""
    return get_tts_service(
        piper_url=os.getenv("PIPER_URL", "http://piper:5000"),
        xtts_url=os.getenv("XTTS_URL", "http://xtts:8020")
    )


@router.post("/generate", response_model=AvatarResponse)
async def generate_avatar(
    request: AvatarRequest,
    avatar: AvatarService = Depends(get_avatar),
    tts: TTSService = Depends(get_tts)
):
    """
    Generate talking avatar video

    Args:
        request: Avatar request with audio or text input
        avatar: Avatar service dependency
        tts: TTS service dependency (for text-to-audio conversion)

    Returns:
        AvatarResponse with video URL and metadata
    """
    logger.info("avatar_generate_request",
               has_audio_url=request.audio_url is not None,
               has_audio_base64=request.audio_base64 is not None,
               has_text=request.text is not None,
               avatar_image=request.avatar_image,
               quality=request.quality)

    try:
        audio_data = None
        audio_base64 = request.audio_base64

        # If text is provided, generate audio first using TTS
        if request.text and not audio_base64 and not request.audio_url:
            logger.info("generating_audio_from_text", text_length=len(request.text))

            tts_result = await tts.synthesize(
                text=request.text,
                mode="piper",  # Use Piper for speed
                voice="en_US-lessac-medium",
                speed=1.0,
                return_base64=True
            )

            audio_base64 = tts_result.get("audio_base64")
            logger.info("audio_generated_from_text")

        # Generate avatar video
        result = await avatar.generate_avatar_video(
            audio_data=audio_data,
            audio_url=request.audio_url,
            audio_base64=audio_base64,
            avatar_image=request.avatar_image,
            quality=request.quality,
            return_base64=True
        )

        # Build response
        response = AvatarResponse(
            video_url=result["video_url"],
            video_base64=result.get("video_base64")
        )

        logger.info("avatar_generate_success",
                   video_size=result["video_size"],
                   avatar_image=result["avatar_image"])

        return response

    except Exception as e:
        logger.error("avatar_generate_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Avatar generation failed: {str(e)}"
        )


@router.post("/generate/video")
async def generate_avatar_video_stream(
    request: AvatarRequest,
    avatar: AvatarService = Depends(get_avatar),
    tts: TTSService = Depends(get_tts)
):
    """
    Generate talking avatar video and return video stream directly

    Args:
        request: Avatar request with audio or text input
        avatar: Avatar service dependency
        tts: TTS service dependency

    Returns:
        Video stream (MP4 format)
    """
    logger.info("avatar_video_stream_request",
               has_audio_url=request.audio_url is not None,
               has_audio_base64=request.audio_base64 is not None,
               has_text=request.text is not None)

    try:
        audio_data = None
        audio_base64 = request.audio_base64

        # If text is provided, generate audio first
        if request.text and not audio_base64 and not request.audio_url:
            logger.info("generating_audio_from_text", text_length=len(request.text))

            tts_result = await tts.synthesize(
                text=request.text,
                mode="piper",
                voice="en_US-lessac-medium",
                speed=1.0,
                return_base64=True
            )

            audio_base64 = tts_result.get("audio_base64")

        # Generate avatar video
        result = await avatar.generate_avatar_video(
            audio_data=audio_data,
            audio_url=request.audio_url,
            audio_base64=audio_base64,
            avatar_image=request.avatar_image,
            quality=request.quality,
            return_base64=False
        )

        # Return video stream
        video_data = result["video_data"]

        logger.info("avatar_video_stream_success",
                   video_size=len(video_data))

        return StreamingResponse(
            io.BytesIO(video_data),
            media_type="video/mp4",
            headers={
                "Content-Disposition": "attachment; filename=avatar.mp4"
            }
        )

    except Exception as e:
        logger.error("avatar_video_stream_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Avatar video stream failed: {str(e)}"
        )


@router.get("/avatars")
async def list_avatars(avatar: AvatarService = Depends(get_avatar)):
    """
    List available avatar images

    Args:
        avatar: Avatar service dependency

    Returns:
        List of avatar metadata
    """
    logger.info("list_avatars_request")

    try:
        avatars = await avatar.list_avatars()

        logger.info("list_avatars_success",
                   count=len(avatars.get("avatars", [])))
        return avatars

    except Exception as e:
        logger.error("list_avatars_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list avatars: {str(e)}"
        )


@router.get("/health")
async def health_check(avatar: AvatarService = Depends(get_avatar)):
    """
    Check avatar service health

    Args:
        avatar: Avatar service dependency

    Returns:
        Health status
    """
    logger.info("avatar_health_check_request")

    try:
        is_healthy = await avatar.health_check()

        if is_healthy:
            logger.info("avatar_health_check_success")
            return {
                "status": "healthy",
                "sadtalker": "up"
            }
        else:
            logger.warning("avatar_health_check_unhealthy")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "sadtalker": "down"
                }
            )

    except Exception as e:
        logger.error("avatar_health_check_error", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e)
            }
        )
