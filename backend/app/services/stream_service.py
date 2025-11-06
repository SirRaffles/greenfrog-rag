"""
Server-Sent Events (SSE) Streaming Service
Wraps Ollama streaming responses and formats them as SSE events
"""

import json
import time
from typing import Optional, AsyncIterator, Dict, Any
from datetime import datetime
import structlog

from app.services.ollama_service import OllamaService

logger = structlog.get_logger(__name__)


class StreamMetrics:
    """Track streaming metrics for monitoring and analytics."""

    def __init__(self):
        """Initialize metrics tracker."""
        self.start_time: float = time.time()
        self.token_count: int = 0
        self.chunk_count: int = 0
        self.total_characters: int = 0
        self.error_occurred: bool = False
        self.error_message: Optional[str] = None

    def add_chunk(self, content: str) -> None:
        """
        Record a new chunk.

        Args:
            content: Chunk content
        """
        self.chunk_count += 1
        self.token_count += 1
        self.total_characters += len(content)

    def get_elapsed_ms(self) -> float:
        """
        Get elapsed time in milliseconds.

        Returns:
            Elapsed time
        """
        return (time.time() - self.start_time) * 1000

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to dictionary.

        Returns:
            Metrics dict
        """
        return {
            "token_count": self.token_count,
            "chunk_count": self.chunk_count,
            "total_characters": self.total_characters,
            "elapsed_ms": round(self.get_elapsed_ms(), 2),
            "tokens_per_second": round(
                self.token_count / max(self.get_elapsed_ms() / 1000, 0.001), 2
            ),
        }


class StreamService:
    """
    Server-Sent Events (SSE) streaming service.

    Wraps Ollama streaming responses and formats them as SSE events for
    client consumption. Handles errors gracefully and tracks streaming metrics.

    Features:
    - Format responses as SSE events (data: {json}\n\n)
    - Metric tracking (tokens, chunks, elapsed time)
    - Error handling and reporting
    - Proper stream completion signaling
    """

    def __init__(self):
        """Initialize streaming service."""
        logger.info("stream_service_init")

    @staticmethod
    def _format_sse_event(data: Dict[str, Any]) -> str:
        """
        Format data as Server-Sent Event.

        SSE format: data: {json}\n\n

        Args:
            data: Event data dictionary

        Returns:
            Formatted SSE event string
        """
        return f"data: {json.dumps(data)}\n\n"

    async def stream_response(
        self,
        ollama_service: OllamaService,
        prompt: str,
        system: Optional[str] = None,
        model: str = "phi3:mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream response from Ollama as SSE events.

        Yields formatted SSE events with tokens, completion status, and metrics.

        Args:
            ollama_service: OllamaService instance for LLM generation
            prompt: Input prompt for generation
            system: Optional system prompt
            model: Model to use (default: phi3:mini)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Yields:
            Formatted SSE event strings

        Raises:
            ValueError: If prompt is empty
            Exception: If Ollama service fails
        """
        if not prompt or not prompt.strip():
            error_event = self._format_sse_event({
                "error": "Prompt cannot be empty",
                "done": True,
            })
            logger.error("stream_response_empty_prompt")
            yield error_event
            return

        metrics = StreamMetrics()

        try:
            logger.info(
                "stream_response_start",
                model=model,
                prompt_length=len(prompt),
                has_system=bool(system),
                temperature=temperature,
            )

            full_response = ""

            # Stream from Ollama
            async for chunk in ollama_service.generate_stream(
                prompt=prompt,
                model=model,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                if not chunk:
                    continue

                # Update metrics
                metrics.add_chunk(chunk)
                full_response += chunk

                # Format as SSE event
                event = self._format_sse_event({
                    "token": chunk,
                    "done": False,
                    "metrics": metrics.to_dict(),
                })

                logger.debug(
                    "stream_response_chunk",
                    chunk_length=len(chunk),
                    total_tokens=metrics.token_count,
                )

                yield event

            # Send completion event with final metrics
            completion_event = self._format_sse_event({
                "done": True,
                "stats": {
                    **metrics.to_dict(),
                    "total_response_length": len(full_response),
                },
            })

            logger.info(
                "stream_response_complete",
                model=model,
                total_tokens=metrics.token_count,
                total_characters=metrics.total_characters,
                elapsed_ms=metrics.get_elapsed_ms(),
            )

            yield completion_event

        except ValueError as e:
            # Handle validation errors
            metrics.error_occurred = True
            metrics.error_message = str(e)

            error_event = self._format_sse_event({
                "error": f"Validation error: {str(e)}",
                "done": True,
            })

            logger.error(
                "stream_response_validation_error",
                error=str(e),
                model=model,
            )

            yield error_event

        except TimeoutError as e:
            # Handle timeout errors
            metrics.error_occurred = True
            metrics.error_message = "Stream timeout"

            error_event = self._format_sse_event({
                "error": "Request timeout: Ollama service did not respond in time",
                "done": True,
            })

            logger.error(
                "stream_response_timeout",
                model=model,
                elapsed_ms=metrics.get_elapsed_ms(),
            )

            yield error_event

        except Exception as e:
            # Handle all other errors
            metrics.error_occurred = True
            metrics.error_message = str(e)

            error_event = self._format_sse_event({
                "error": f"Streaming error: {str(e)}",
                "done": True,
            })

            logger.error(
                "stream_response_error",
                error=str(e),
                model=model,
                error_type=type(e).__name__,
            )

            yield error_event

    async def stream_chat(
        self,
        ollama_service: OllamaService,
        messages: list,
        model: str = "phi3:mini",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat response from Ollama as SSE events.

        Yields formatted SSE events with message content, completion status,
        and metrics.

        Args:
            ollama_service: OllamaService instance for LLM generation
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: phi3:mini)
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Yields:
            Formatted SSE event strings

        Raises:
            ValueError: If messages list is empty or invalid
            Exception: If Ollama service fails
        """
        if not messages or not isinstance(messages, list):
            error_event = self._format_sse_event({
                "error": "Messages must be a non-empty list",
                "done": True,
            })
            logger.error("stream_chat_invalid_messages")
            yield error_event
            return

        metrics = StreamMetrics()

        try:
            logger.info(
                "stream_chat_start",
                model=model,
                message_count=len(messages),
                temperature=temperature,
            )

            full_response = ""

            # Stream from Ollama
            async for chunk in ollama_service.chat_stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                if not chunk:
                    continue

                # Update metrics
                metrics.add_chunk(chunk)
                full_response += chunk

                # Format as SSE event
                event = self._format_sse_event({
                    "content": chunk,
                    "done": False,
                    "metrics": metrics.to_dict(),
                })

                logger.debug(
                    "stream_chat_chunk",
                    chunk_length=len(chunk),
                    total_tokens=metrics.token_count,
                )

                yield event

            # Send completion event with final metrics
            completion_event = self._format_sse_event({
                "done": True,
                "stats": {
                    **metrics.to_dict(),
                    "total_response_length": len(full_response),
                },
            })

            logger.info(
                "stream_chat_complete",
                model=model,
                total_tokens=metrics.token_count,
                total_characters=metrics.total_characters,
                elapsed_ms=metrics.get_elapsed_ms(),
            )

            yield completion_event

        except ValueError as e:
            # Handle validation errors
            metrics.error_occurred = True
            metrics.error_message = str(e)

            error_event = self._format_sse_event({
                "error": f"Validation error: {str(e)}",
                "done": True,
            })

            logger.error(
                "stream_chat_validation_error",
                error=str(e),
                model=model,
            )

            yield error_event

        except TimeoutError as e:
            # Handle timeout errors
            metrics.error_occurred = True
            metrics.error_message = "Stream timeout"

            error_event = self._format_sse_event({
                "error": "Request timeout: Ollama service did not respond in time",
                "done": True,
            })

            logger.error(
                "stream_chat_timeout",
                model=model,
                elapsed_ms=metrics.get_elapsed_ms(),
            )

            yield error_event

        except Exception as e:
            # Handle all other errors
            metrics.error_occurred = True
            metrics.error_message = str(e)

            error_event = self._format_sse_event({
                "error": f"Streaming error: {str(e)}",
                "done": True,
            })

            logger.error(
                "stream_chat_error",
                error=str(e),
                model=model,
                error_type=type(e).__name__,
            )

            yield error_event
