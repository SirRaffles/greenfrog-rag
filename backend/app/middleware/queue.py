"""
Request Queue Middleware for NAS Resource Management

Limits concurrent LLM requests to prevent CPU/memory saturation on NAS hardware.
"""

import asyncio
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog
import os
import time
from typing import Callable

logger = structlog.get_logger(__name__)


# Maximum concurrent LLM requests (configurable via environment)
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "3"))

# Semaphore to limit concurrency
llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

# Track queue metrics
queue_metrics = {
    "total_queued": 0,
    "total_processed": 0,
    "current_queue_depth": 0,
    "max_queue_depth_seen": 0,
    "avg_wait_time_ms": 0.0,
    "total_wait_time_ms": 0.0,
}


# Protected paths that should be queued
QUEUED_PATHS = [
    "/api/chat/message",
    "/api/chat/query",
    "/api/v2/chat/query",
    "/api/v2/chat/stream",
]


async def queue_middleware(request: Request, call_next: Callable) -> Response:
    """
    Queue middleware to limit concurrent LLM requests.

    Prevents resource exhaustion on NAS by queuing excess requests.
    Only applies to LLM-heavy endpoints (chat, query).

    Args:
        request: Incoming request
        call_next: Next middleware/handler

    Returns:
        Response from handler or 429 if queue is full
    """

    # Check if this path should be queued
    should_queue = any(request.url.path.startswith(path) for path in QUEUED_PATHS)

    if not should_queue:
        # Non-queued endpoint - pass through immediately
        return await call_next(request)

    # Calculate current queue depth
    queue_depth = MAX_CONCURRENT_REQUESTS - llm_semaphore._value
    queue_metrics["current_queue_depth"] = queue_depth
    queue_metrics["max_queue_depth_seen"] = max(
        queue_metrics["max_queue_depth_seen"],
        queue_depth
    )

    # Optional: Reject if queue is too deep (prevents unbounded queuing)
    max_queue_depth = int(os.getenv("MAX_QUEUE_DEPTH", "10"))
    if queue_depth >= max_queue_depth:
        logger.warning(
            "queue_full",
            queue_depth=queue_depth,
            max_queue_depth=max_queue_depth,
            path=request.url.path
        )
        return JSONResponse(
            status_code=429,  # Too Many Requests
            content={
                "error": "Queue full",
                "message": f"Server is processing {queue_depth} requests. Please try again in a few seconds.",
                "queue_depth": queue_depth,
                "max_concurrent": MAX_CONCURRENT_REQUESTS,
                "retry_after": 5
            },
            headers={"Retry-After": "5"}
        )

    # Acquire semaphore (wait in queue if necessary)
    start_wait = time.time()

    logger.info(
        "request_queued",
        path=request.url.path,
        queue_depth=queue_depth,
        concurrent_limit=MAX_CONCURRENT_REQUESTS
    )

    queue_metrics["total_queued"] += 1

    async with llm_semaphore:
        wait_time_ms = (time.time() - start_wait) * 1000

        # Update wait time metrics
        queue_metrics["total_wait_time_ms"] += wait_time_ms
        queue_metrics["avg_wait_time_ms"] = (
            queue_metrics["total_wait_time_ms"] / queue_metrics["total_queued"]
        )

        if wait_time_ms > 100:  # Log if waited > 100ms
            logger.info(
                "request_dequeued",
                path=request.url.path,
                wait_time_ms=round(wait_time_ms, 2)
            )

        # Process request
        try:
            response = await call_next(request)
            queue_metrics["total_processed"] += 1
            return response

        finally:
            # Log queue state after processing
            logger.debug(
                "request_completed",
                path=request.url.path,
                queue_depth=MAX_CONCURRENT_REQUESTS - llm_semaphore._value
            )


def get_queue_metrics() -> dict:
    """
    Get current queue metrics for monitoring.

    Returns:
        Dictionary with queue statistics
    """
    return {
        **queue_metrics,
        "current_concurrent": MAX_CONCURRENT_REQUESTS - llm_semaphore._value,
        "max_concurrent": MAX_CONCURRENT_REQUESTS,
        "available_slots": llm_semaphore._value,
    }


def reset_queue_metrics():
    """Reset queue metrics (useful for testing or periodic resets)."""
    queue_metrics.update({
        "total_queued": 0,
        "total_processed": 0,
        "current_queue_depth": 0,
        "max_queue_depth_seen": 0,
        "avg_wait_time_ms": 0.0,
        "total_wait_time_ms": 0.0,
    })
    logger.info("queue_metrics_reset")
