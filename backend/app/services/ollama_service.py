"""
Ollama Service
Direct integration with Ollama API for LLM inference
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
    Direct Ollama API client with connection pooling and streaming support.

    Features:
    - Support for multiple models (phi3:mini, llama3.2:3b)
    - Streaming and non-streaming generation
    - Connection pooling for efficiency
    - Proper timeout and error handling
    - Context management
    """

    def __init__(
        self,
        base_url: str = None,
        model: str = "phi3:mini",
        timeout: float = 120.0,
        max_retries: int = 3,
    ):
        """
        Initialize Ollama service.

        Args:
            base_url: Ollama API base URL (default from env)
            model: Default model to use
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts on failure
        """
        self.base_url = base_url or os.getenv(
            "OLLAMA_API",
            "http://host.docker.internal:11434"
        )
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries

        # HTTP client with connection pooling (lazy initialized)
        self._client: Optional[httpx.AsyncClient] = None

        logger.info(
            "ollama_service_init",
            base_url=self.base_url,
            model=model,
            timeout=timeout
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
            logger.info("ollama_client_created")
        return self._client

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        context: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Generate completion from prompt.

        Args:
            prompt: Input prompt
            model: Model to use (default: self.model)
            system: System prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response
            context: Context array from previous generation

        Returns:
            Response dict with 'response', 'model', 'context', etc.
        """
        model = model or self.model

        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": stream,
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        if context:
            payload["context"] = context

        try:
            client = await self._get_client()

            if stream:
                # Streaming not implemented in this method, use generate_stream()
                raise ValueError("Use generate_stream() for streaming responses")

            logger.info(
                "ollama_generate_start",
                model=model,
                prompt_length=len(prompt),
                has_system=bool(system),
                has_context=bool(context)
            )

            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()

            result = response.json()

            logger.info(
                "ollama_generate_complete",
                model=model,
                response_length=len(result.get("response", "")),
                total_duration_ms=result.get("total_duration", 0) // 1_000_000
            )

            return result

        except httpx.TimeoutException as e:
            logger.error(
                "ollama_generate_timeout",
                model=model,
                timeout=self.timeout,
                error=str(e)
            )
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_generate_http_error",
                status=e.response.status_code,
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
        Generate completion with streaming.

        Args:
            prompt: Input prompt
            model: Model to use (default: self.model)
            system: System prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            context: Context array from previous generation

        Yields:
            Response chunks as strings
        """
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
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if "response" in chunk:
                                yield chunk["response"]

                            # Check if done
                            if chunk.get("done", False):
                                logger.info(
                                    "ollama_stream_complete",
                                    model=model,
                                    total_duration_ms=chunk.get("total_duration", 0) // 1_000_000
                                )
                                break

                        except json.JSONDecodeError:
                            logger.warning("ollama_stream_invalid_json", line=line[:100])
                            continue

        except httpx.TimeoutException as e:
            logger.error("ollama_stream_timeout", model=model, error=str(e))
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_stream_http_error",
                status=e.response.status_code,
                error=str(e)
            )
            raise

        except Exception as e:
            logger.error("ollama_stream_error", model=model, error=str(e))
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Chat completion with message history.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: self.model)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream response

        Returns:
            Response dict with 'message', 'model', etc.
        """
        model = model or self.model

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        try:
            client = await self._get_client()

            if stream:
                # Streaming not implemented in this method, use chat_stream()
                raise ValueError("Use chat_stream() for streaming responses")

            logger.info(
                "ollama_chat_start",
                model=model,
                message_count=len(messages)
            )

            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()

            result = response.json()

            logger.info(
                "ollama_chat_complete",
                model=model,
                response_length=len(result.get("message", {}).get("content", "")),
                total_duration_ms=result.get("total_duration", 0) // 1_000_000
            )

            return result

        except httpx.TimeoutException as e:
            logger.error("ollama_chat_timeout", model=model, error=str(e))
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_chat_http_error",
                status=e.response.status_code,
                error=str(e)
            )
            raise

        except Exception as e:
            logger.error("ollama_chat_error", model=model, error=str(e))
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Chat completion with streaming.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: self.model)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Yields:
            Response chunks as strings
        """
        model = model or self.model

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        try:
            client = await self._get_client()

            logger.info(
                "ollama_chat_stream_start",
                model=model,
                message_count=len(messages)
            )

            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                yield chunk["message"]["content"]

                            # Check if done
                            if chunk.get("done", False):
                                logger.info(
                                    "ollama_chat_stream_complete",
                                    model=model,
                                    total_duration_ms=chunk.get("total_duration", 0) // 1_000_000
                                )
                                break

                        except json.JSONDecodeError:
                            logger.warning("ollama_chat_stream_invalid_json", line=line[:100])
                            continue

        except httpx.TimeoutException as e:
            logger.error("ollama_chat_stream_timeout", model=model, error=str(e))
            raise

        except httpx.HTTPStatusError as e:
            logger.error(
                "ollama_chat_stream_http_error",
                status=e.response.status_code,
                error=str(e)
            )
            raise

        except Exception as e:
            logger.error("ollama_chat_stream_error", model=model, error=str(e))
            raise

    async def embeddings(
        self,
        text: str,
        model: str = "nomic-embed-text:latest"
    ) -> List[float]:
        """
        Generate embeddings for text.

        Args:
            text: Input text
            model: Embedding model to use

        Returns:
            Embedding vector
        """
        payload = {
            "model": model,
            "prompt": text
        }

        try:
            client = await self._get_client()

            logger.debug("ollama_embeddings_start", model=model, text_length=len(text))

            response = await client.post("/api/embeddings", json=payload)
            response.raise_for_status()

            result = response.json()
            embedding = result.get("embedding", [])

            logger.debug(
                "ollama_embeddings_complete",
                model=model,
                embedding_dim=len(embedding)
            )

            return embedding

        except Exception as e:
            logger.error("ollama_embeddings_error", model=model, error=str(e))
            raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.

        Returns:
            List of model dicts
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()

            result = response.json()
            models = result.get("models", [])

            logger.info("ollama_list_models", count=len(models))
            return models

        except Exception as e:
            logger.error("ollama_list_models_error", error=str(e))
            raise

    async def health_check(self) -> bool:
        """
        Check if Ollama service is healthy.

        Returns:
            True if Ollama is reachable
        """
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=5.0)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error("ollama_health_check_failed", error=str(e))
            return False

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            logger.info("ollama_client_closed")
