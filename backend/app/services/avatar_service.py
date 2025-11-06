"""
Avatar Service - SadTalker Integration
Handles avatar video generation from audio
"""

import httpx
import structlog
import os
import base64
from typing import Optional, Dict, Any
from pathlib import Path

logger = structlog.get_logger(__name__)


class AvatarService:
    """
    SadTalker Avatar Service
    Generates talking avatar videos from audio input
    """

    def __init__(
        self,
        sadtalker_url: str = "http://sadtalker:7860"
    ):
        """
        Initialize avatar service

        Args:
            sadtalker_url: SadTalker service URL
        """
        self.sadtalker_url = sadtalker_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=300.0)  # 5 min timeout for video generation

        logger.info("avatar_service_initialized", sadtalker_url=sadtalker_url)

    async def generate_avatar_video(
        self,
        audio_data: Optional[bytes] = None,
        audio_url: Optional[str] = None,
        audio_base64: Optional[str] = None,
        avatar_image: str = "greenfrog",
        quality: str = "medium",
        return_base64: bool = False
    ) -> Dict[str, Any]:
        """
        Generate talking avatar video from audio

        Args:
            audio_data: Raw audio bytes
            audio_url: URL to audio file
            audio_base64: Base64 encoded audio
            avatar_image: Avatar image identifier
            quality: Video quality ('low', 'medium', 'high')
            return_base64: Return base64 encoded video

        Returns:
            Dict with video data and metadata
        """
        logger.info("avatar_generate_request",
                   avatar_image=avatar_image,
                   quality=quality,
                   has_audio_data=audio_data is not None,
                   has_audio_url=audio_url is not None,
                   has_audio_base64=audio_base64 is not None)

        try:
            # Prepare audio input
            if audio_base64:
                audio_data = base64.b64decode(audio_base64)
            elif audio_url:
                # Download audio from URL
                audio_response = await self.client.get(audio_url)
                audio_response.raise_for_status()
                audio_data = audio_response.content
            elif not audio_data:
                raise ValueError("No audio input provided")

            # Get avatar image path
            avatar_image_path = self._get_avatar_image_path(avatar_image)

            # Prepare multipart form data
            files = {
                "source_image": open(avatar_image_path, "rb"),
                "driven_audio": ("audio.wav", audio_data, "audio/wav")
            }

            data = {
                "quality": quality,
                "still_mode": "false",
                "preprocess": "crop"
            }

            # Send request to SadTalker
            endpoint = f"{self.sadtalker_url}/generate"
            response = await self.client.post(
                endpoint,
                files=files,
                data=data
            )
            response.raise_for_status()

            # Get video data
            video_data = response.content

            # Build result
            result = {
                "video_data": video_data,
                "video_url": f"/api/avatar/video/{hash(str(audio_data))}",  # Placeholder
                "avatar_image": avatar_image,
                "quality": quality,
                "video_size": len(video_data)
            }

            # Add base64 if requested
            if return_base64:
                result["video_base64"] = base64.b64encode(video_data).decode("utf-8")

            logger.info("avatar_generate_success",
                       video_size=len(video_data),
                       avatar_image=avatar_image)

            return result

        except httpx.HTTPStatusError as e:
            logger.error("sadtalker_http_error",
                        status_code=e.response.status_code,
                        error=str(e))
            raise Exception(f"SadTalker error: {e.response.status_code}")

        except Exception as e:
            logger.error("avatar_generate_error", error=str(e))
            raise Exception(f"Avatar generation failed: {str(e)}")

    def _get_avatar_image_path(self, avatar_image: str) -> str:
        """
        Get path to avatar image file

        Args:
            avatar_image: Avatar identifier

        Returns:
            Path to avatar image file
        """
        # Default avatar images directory
        avatars_dir = Path("/app/avatars")

        # Map avatar identifiers to files
        avatar_map = {
            "greenfrog": "greenfrog.png",
            "default": "greenfrog.png"
        }

        filename = avatar_map.get(avatar_image, "greenfrog.png")
        avatar_path = avatars_dir / filename

        if not avatar_path.exists():
            logger.warning("avatar_image_not_found",
                          avatar_image=avatar_image,
                          path=str(avatar_path))
            # Use default
            avatar_path = avatars_dir / "greenfrog.png"

        return str(avatar_path)

    async def list_avatars(self) -> Dict[str, Any]:
        """
        Get list of available avatar images

        Returns:
            Dict with avatar metadata
        """
        logger.info("list_avatars_request")

        try:
            avatars_dir = Path("/app/avatars")

            if not avatars_dir.exists():
                return {"avatars": []}

            avatars = []
            for avatar_file in avatars_dir.glob("*.png"):
                avatars.append({
                    "id": avatar_file.stem,
                    "name": avatar_file.stem.replace("_", " ").title(),
                    "file": avatar_file.name
                })

            logger.info("list_avatars_success", count=len(avatars))
            return {"avatars": avatars}

        except Exception as e:
            logger.error("list_avatars_error", error=str(e))
            return {"avatars": []}

    async def health_check(self) -> bool:
        """
        Check if SadTalker is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.sadtalker_url}/health",
                timeout=5.0
            )
            return response.status_code == 200

        except Exception as e:
            logger.warning("sadtalker_health_check_failed", error=str(e))
            return False

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("avatar_service_closed")


# Global avatar service instance
_avatar_instance: Optional[AvatarService] = None


def get_avatar_service(
    sadtalker_url: str = "http://sadtalker:8000"
) -> AvatarService:
    """
    Get or create avatar service instance

    Args:
        sadtalker_url: SadTalker service URL

    Returns:
        AvatarService instance
    """
    global _avatar_instance
    if _avatar_instance is None:
        _avatar_instance = AvatarService(sadtalker_url=sadtalker_url)
    return _avatar_instance
