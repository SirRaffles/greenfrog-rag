"""
TTS Service - Hybrid Text-to-Speech Router
Routes between Piper (fast) and XTTS-v2 (voice cloning)
"""

import httpx
import structlog
import os
import base64
from typing import Optional, Dict, Any
from pathlib import Path

logger = structlog.get_logger(__name__)


class TTSService:
    """
    Hybrid TTS Service
    Routes between Piper (CPU-optimized, fast) and XTTS-v2 (GPU, voice cloning)
    """

    def __init__(
        self,
        piper_url: str = "http://piper:5000",
        xtts_url: str = "http://xtts:8020"
    ):
        """
        Initialize TTS service

        Args:
            piper_url: Piper TTS service URL
            xtts_url: XTTS-v2 service URL
        """
        self.piper_url = piper_url.rstrip("/")
        self.xtts_url = xtts_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=120.0)

        logger.info("tts_service_initialized",
                   piper_url=piper_url,
                   xtts_url=xtts_url)

    async def synthesize(
        self,
        text: str,
        mode: str = "piper",
        voice: str = "en_US-lessac-medium",
        speed: float = 1.0,
        language: str = "en",
        return_base64: bool = False
    ) -> Dict[str, Any]:
        """
        Synthesize speech from text

        Args:
            text: Text to convert to speech
            mode: TTS mode ('piper' or 'xtts')
            voice: Voice model identifier
            speed: Speech speed (0.5-2.0)
            language: Language code
            return_base64: Return base64 encoded audio

        Returns:
            Dict with audio data and metadata
        """
        logger.info("tts_request",
                   mode=mode,
                   text_length=len(text),
                   voice=voice,
                   speed=speed)

        # Route to appropriate service
        if mode == "piper":
            return await self._synthesize_piper(
                text=text,
                voice=voice,
                speed=speed,
                return_base64=return_base64
            )
        elif mode == "xtts":
            return await self._synthesize_xtts(
                text=text,
                voice=voice,
                language=language,
                return_base64=return_base64
            )
        else:
            raise ValueError(f"Unknown TTS mode: {mode}")

    async def _synthesize_piper(
        self,
        text: str,
        voice: str,
        speed: float,
        return_base64: bool
    ) -> Dict[str, Any]:
        """
        Synthesize using Piper (fast, CPU-optimized)

        Args:
            text: Text to synthesize
            voice: Piper voice model
            speed: Speech speed
            return_base64: Return base64 audio

        Returns:
            Dict with audio data
        """
        logger.info("piper_tts_request", voice=voice, speed=speed)

        try:
            # Piper API endpoint
            endpoint = f"{self.piper_url}/tts"

            # Build request payload
            payload = {
                "text": text,
                "voice": voice,
                "rate": speed
            }

            # Send request
            response = await self.client.post(
                endpoint,
                json=payload
            )
            response.raise_for_status()

            # Get audio data
            audio_data = response.content

            # Build result
            result = {
                "audio_data": audio_data,
                "audio_url": f"/api/tts/audio/{hash(text)}",  # Placeholder
                "mode_used": "piper",
                "text_length": len(text),
                "voice": voice
            }

            # Add base64 if requested
            if return_base64:
                result["audio_base64"] = base64.b64encode(audio_data).decode("utf-8")

            logger.info("piper_tts_success",
                       audio_size=len(audio_data),
                       voice=voice)

            return result

        except httpx.HTTPStatusError as e:
            logger.error("piper_http_error",
                        status_code=e.response.status_code,
                        error=str(e))
            raise Exception(f"Piper TTS error: {e.response.status_code}")

        except Exception as e:
            logger.error("piper_tts_error", error=str(e))
            raise Exception(f"Piper TTS failed: {str(e)}")

    async def _synthesize_xtts(
        self,
        text: str,
        voice: str,
        language: str,
        return_base64: bool
    ) -> Dict[str, Any]:
        """
        Synthesize using XTTS-v2 (GPU, voice cloning)

        Args:
            text: Text to synthesize
            voice: Voice sample identifier
            language: Language code
            return_base64: Return base64 audio

        Returns:
            Dict with audio data
        """
        logger.info("xtts_tts_request", voice=voice, language=language)

        try:
            # XTTS API endpoint
            endpoint = f"{self.xtts_url}/tts_to_audio"

            # Build request payload
            payload = {
                "text": text,
                "speaker_wav": voice,  # Voice sample file
                "language": language
            }

            # Send request
            response = await self.client.post(
                endpoint,
                json=payload
            )
            response.raise_for_status()

            # Get audio data
            audio_data = response.content

            # Build result
            result = {
                "audio_data": audio_data,
                "audio_url": f"/api/tts/audio/{hash(text)}",  # Placeholder
                "mode_used": "xtts",
                "text_length": len(text),
                "voice": voice
            }

            # Add base64 if requested
            if return_base64:
                result["audio_base64"] = base64.b64encode(audio_data).decode("utf-8")

            logger.info("xtts_tts_success",
                       audio_size=len(audio_data),
                       voice=voice)

            return result

        except httpx.HTTPStatusError as e:
            logger.error("xtts_http_error",
                        status_code=e.response.status_code,
                        error=str(e))

            # Fallback to Piper if XTTS fails
            logger.info("falling_back_to_piper")
            return await self._synthesize_piper(
                text=text,
                voice="en_US-lessac-medium",
                speed=1.0,
                return_base64=return_base64
            )

        except Exception as e:
            logger.error("xtts_tts_error", error=str(e))

            # Fallback to Piper
            logger.info("falling_back_to_piper")
            return await self._synthesize_piper(
                text=text,
                voice="en_US-lessac-medium",
                speed=1.0,
                return_base64=return_base64
            )

    async def list_piper_voices(self) -> Dict[str, Any]:
        """
        Get list of available Piper voices

        Returns:
            Dict with voice metadata
        """
        logger.info("list_piper_voices_request")

        try:
            response = await self.client.get(f"{self.piper_url}/api/voices")
            response.raise_for_status()

            voices = response.json()
            logger.info("list_piper_voices_success", count=len(voices))
            return {"voices": voices}

        except Exception as e:
            logger.error("list_piper_voices_error", error=str(e))
            return {"voices": []}

    async def list_xtts_voices(self) -> Dict[str, Any]:
        """
        Get list of available XTTS voice samples

        Returns:
            Dict with voice sample metadata
        """
        logger.info("list_xtts_voices_request")

        try:
            response = await self.client.get(f"{self.xtts_url}/speakers")
            response.raise_for_status()

            voices = response.json()
            logger.info("list_xtts_voices_success", count=len(voices))
            return {"voices": voices}

        except Exception as e:
            logger.error("list_xtts_voices_error", error=str(e))
            return {"voices": []}

    async def health_check(self) -> Dict[str, bool]:
        """
        Check TTS services health

        Returns:
            Dict with service health status
        """
        logger.info("tts_health_check")

        piper_healthy = False
        xtts_healthy = False

        # Check Piper
        try:
            response = await self.client.get(
                f"{self.piper_url}/health",
                timeout=5.0
            )
            piper_healthy = response.status_code == 200
        except Exception as e:
            logger.warning("piper_health_check_failed", error=str(e))

        # Check XTTS
        try:
            response = await self.client.get(
                f"{self.xtts_url}/health",
                timeout=5.0
            )
            xtts_healthy = response.status_code == 200
        except Exception as e:
            logger.warning("xtts_health_check_failed", error=str(e))

        logger.info("tts_health_check_complete",
                   piper=piper_healthy,
                   xtts=xtts_healthy)

        return {
            "piper": piper_healthy,
            "xtts": xtts_healthy
        }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        logger.info("tts_service_closed")


# Global TTS service instance
_tts_instance: Optional[TTSService] = None


def get_tts_service(
    piper_url: str = "http://piper:5000",
    xtts_url: str = "http://xtts:8020"
) -> TTSService:
    """
    Get or create TTS service instance

    Args:
        piper_url: Piper service URL
        xtts_url: XTTS service URL

    Returns:
        TTSService instance
    """
    global _tts_instance
    if _tts_instance is None:
        _tts_instance = TTSService(piper_url=piper_url, xtts_url=xtts_url)
    return _tts_instance
