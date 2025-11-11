"""
Enhanced Ollama Service with Aggressive Timeouts and Fallback Models

FIXES:
1. Reduced default timeout from 120s → 45s
2. Per-endpoint timeout configuration
3. Automatic fallback to smaller model on timeout
4. Better error messages
5. Health check that actually tests generation
"""

import asyncio
from typing import Optional, Dict, Any, AsyncIterator, List
import httpx
import structlog
import os
import json

logger = structlog.get_logger(__name__)


class OllamaService:
    """
    Direct Ollama API client with aggressive timeouts and model fallback.

    IMPROVEMENTS:
    - Reduced default timeout: 120s → 45s
    - Configurable timeouts per endpoint
    - Automatic fallback to smaller/faster models
    - Health check with actual generation test
    - Better timeout error messages
    """

    # Model fallback chain (fastest to slowest)
    MODEL_FALLBACK_CHAIN = [
        "tinyllama:latest",      # ~600MB, very fast
        "phi3:mini",             # ~2.3GB, medium speed (current default)
        "llama3.2:3b",          # ~2GB, medium speed
        "llama3.1:8b",          # ~4.7GB, slow on CPU
    ]

    def __init__(
        self,
        base_url: str = None,
        model: str = "phi3:mini",
        timeout: float = 45.0,  # REDUCED from 120s
        max_retries: int = 2,   # REDUCED from 3
        enable_fallback: bool = True,
    ):
        """
        Initialize Ollama service with aggressive timeout settings.

        Args:
            base_url: Ollama API base URL (default from env)
            model: Default model to use
            timeout: Request timeout in seconds (default: 45s, was 120s)
            max_retries: Maximum retry attempts on failure (default: 2, was 3)
            enable_fallback: Enable automatic model fallback on timeout
        """
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL",
            "http://host.docker.internal:11434"
        )
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.enable_fallback = enable_fallback

        # HTTP client with connection pooling (lazy initialized)
        self._client: Optional[httpx.AsyncClient] = None

        # Track which models are available
        self._available_models: Optional[List[str]] = None

        logger.info(
            "ollama_service_init",
            base_url=self.base_url,
            model=model,
            timeout=timeout,
            enable_fallback=enable_fallback
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client with connection pooling."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5
                )
            )
            logger.info("ollama_client_created", timeout=self.timeout)
        return self._client

    async def _get_available_models(self) -> List[str]:
        """Get list of available models (cached)."""
        if self._available_models is None:
            try:
                client = await self._get_client()
                response = await client.get("/api/tags", timeout=5.0)
                response.raise_for_status()
                data = response.json()
                self._available_models = [m["name"] for m in data.get("models", [])]
                logger.info("available_models", models=self._available_models)
            except Exception as e:
                logger.error("failed_to_get_models", error=str(e))
                self._available_models = [self.model]  # Fallback to default

        return self._available_models

    async def _try_generate_with_timeout(
        self,
        payload: Dict[str, Any],
        timeout_override: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Try to generate with a specific timeout.

        Uses asyncio.wait_for for additional timeout enforcement beyond httpx.
        """
        timeout = timeout_override or self.timeout

        try:
            client = await self._get_client()

            # Double timeout protection: httpx.Timeout + asyncio.wait_for
            async def _make_request():
                response = await client.post("/api/generate", json=payload)
                response.raise_for_status()
                return response.json()

            # asyncio.wait_for provides additional timeout layer
            result = await asyncio.wait_for(_make_request(), timeout=timeout)

            return result

        except asyncio.TimeoutError:
            model = payload.get("model", "unknown")
            prompt_len = len(payload.get("prompt", ""))
            logger.error(
                "ollama_asyncio_timeout",
                model=model,
                timeout=timeout,
                prompt_length=prompt_len,
                message=f"Ollama did not respond within {timeout}s"
            )
            raise TimeoutError(f"Ollama generation timeout after {timeout}s")

        except httpx.TimeoutException as e:
            model = payload.get("model", "unknown")
            logger.error(
                "ollama_httpx_timeout",
                model=model,
                timeout=timeout,
                error=str(e)
            )
            raise TimeoutError(f"Ollama HTTP timeout after {timeout}s")

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        context: Optional[List[int]] = None,
        timeout_override: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Generate completion with automatic fallback on timeout.

        IMPROVEMENTS:
        - Tries primary model with timeout
        - Falls back to smaller/faster model if timeout
        - Better error messages with suggestions

        Args:
            prompt: Input prompt
            model: Model to use (default: self.model)
            system: System prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            context: Context array from previous generation
            timeout_override: Override default timeout for this request

        Returns:
            Response dict with 'response', 'model', 'context', etc.

        Raises:
            TimeoutError: If all models timeout
            ValueError: If invalid parameters
        """
        if stream:
            raise ValueError("Use generate_stream() for streaming responses")

        model = model or self.model
        timeout = timeout_override or self.timeout

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        if context:
            payload["context"] = context

        logger.info(
            "ollama_generate_start",
            model=model,
            prompt_length=len(prompt),
            timeout=timeout,
            has_system=bool(system),
            has_context=bool(context)
        )

        # Try primary model
        try:
            start_time = asyncio.get_event_loop().time()
            result = await self._try_generate_with_timeout(payload, timeout)
            duration = asyncio.get_event_loop().time() - start_time

            logger.info(
                "ollama_generate_complete",
                model=model,
                response_length=len(result.get("response", "")),
                duration_seconds=round(duration, 2)
            )

            return result

        except (TimeoutError, httpx.TimeoutException) as e:
            logger.warning(
                "ollama_timeout_attempting_fallback",
                model=model,
                timeout=timeout,
                enable_fallback=self.enable_fallback
            )

            # Try fallback to smaller model if enabled
            if self.enable_fallback:
                available_models = await self._get_available_models()

                # Find a smaller model to try
                fallback_model = None
                for candidate in self.MODEL_FALLBACK_CHAIN:
                    if candidate != model and candidate in available_models:
                        fallback_model = candidate
                        break

                if fallback_model:
                    logger.info(
                        "ollama_fallback_attempt",
                        original_model=model,
                        fallback_model=fallback_model,
                        timeout=timeout * 0.75  # Shorter timeout for fallback
                    )

                    try:
                        payload["model"] = fallback_model
                        result = await self._try_generate_with_timeout(
                            payload,
                            timeout * 0.75  # 75% of original timeout
                        )

                        # Add metadata about fallback
                        result["_fallback_used"] = True
                        result["_original_model"] = model
                        result["model"] = fallback_model

                        logger.info(
                            "ollama_fallback_success",
                            original_model=model,
                            fallback_model=fallback_model
                        )

                        return result

                    except Exception as fallback_error:
                        logger.error(
                            "ollama_fallback_failed",
                            fallback_model=fallback_model,
                            error=str(fallback_error)
                        )
                        # Fall through to raise original error

            # No fallback available or fallback failed
            raise TimeoutError(
                f"Ollama timeout after {timeout}s with model '{model}'. "
                f"Prompt length: {len(prompt)} chars. "
                f"Suggestion: Use smaller model or reduce prompt size."
            )

        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_generate_http_error",
                status=e.response.status_code,
                model=model,
                error=str(e)
            )
            raise

        except Exception as e:
            logger.error("ollama_generate_error", model=model, error=str(e))
            raise

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[List[int]] = None,
    ) -> AsyncIterator[str]:
        """
        Generate completion with streaming (existing implementation).

        Note: Streaming has different timeout behavior - tokens arrive continuously.
        """
        # Keep existing streaming implementation
        # (I won't modify this since it's working)
        model = model or self.model

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": True,
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        if context:
            payload["context"] = context

        try:
            client = await self._get_client()

            logger.info(
                "ollama_stream_start",
                model=model,
                prompt_length=len(prompt)
            )

            async with client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            yield data.get("response", "")

                            if data.get("done", False):
                                logger.info("ollama_stream_complete", model=model)
                                break
                        except json.JSONDecodeError:
                            logger.warning("ollama_stream_invalid_json", line=line[:100])
                            continue

        except Exception as e:
            logger.error("ollama_stream_error", model=model, error=str(e))
            raise

    async def embeddings(
        self,
        text: str,
        model: str = "nomic-embed-text:latest"
    ) -> List[float]:
        """Generate embeddings for text (existing implementation)."""
        try:
            client = await self._get_client()

            response = await client.post(
                "/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=30.0  # Shorter timeout for embeddings
            )
            response.raise_for_status()

            result = response.json()
            return result.get("embedding", [])

        except Exception as e:
            logger.error("ollama_embeddings_error", error=str(e))
            raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models (existing implementation)."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)
            response.raise_for_status()

            data = response.json()
            return data.get("models", [])

        except Exception as e:
            logger.error("ollama_list_models_error", error=str(e))
            raise

    async def health_check(self) -> bool:
        """
        IMPROVED: Health check that actually tests generation.

        Previous implementation only checked model list.
        Now tests actual generation capability with timeout.
        """
        try:
            # Quick generation test with tiny prompt
            result = await self.generate(
                prompt="Hi",
                max_tokens=5,
                timeout_override=10.0  # 10 second timeout for health check
            )

            # Check if we got a response
            response_text = result.get("response", "")
            if len(response_text) > 0:
                logger.info("ollama_health_check_passed", model=self.model)
                return True
            else:
                logger.warning("ollama_health_check_empty_response")
                return False

        except Exception as e:
            logger.error("ollama_health_check_failed", error=str(e))
            return False

    async def close(self):
        """Close HTTP client connection."""
        if self._client:
            await self._client.aclose()
            logger.info("ollama_client_closed")


# Singleton instance (existing pattern)
_ollama_instance: Optional[OllamaService] = None


def get_ollama_service() -> OllamaService:
    """Get or create Ollama service singleton."""
    global _ollama_instance
    if _ollama_instance is None:
        _ollama_instance = OllamaService(
            timeout=float(os.getenv("OLLAMA_TIMEOUT", "45")),  # Configurable via env
            enable_fallback=os.getenv("OLLAMA_ENABLE_FALLBACK", "true").lower() == "true"
        )
    return _ollama_instance
