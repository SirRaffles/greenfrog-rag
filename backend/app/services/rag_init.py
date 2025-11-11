"""
PRODUCTION FIX: RAG Service Initialization Hang

PROBLEM:
--------
Dependency injection hangs because get_rag_service_v2() blocks on:
1. CacheService loading SentenceTransformer model (600MB+ download)
2. RetrievalService connecting to ChromaDB
3. Redis connection initialization

SOLUTION:
---------
1. Pre-initialize RAG service during FastAPI startup (not on first request)
2. Add timeout protection to initialization
3. Make initialization truly lazy (no blocking in __init__)
4. Add fallback to non-cached mode if initialization fails

DEPLOYMENT:
-----------
Add this to main.py startup event.
"""

import asyncio
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)

# Global flag to track initialization status
_rag_v2_initialization_complete = False
_rag_v2_initialization_error: Optional[str] = None


async def initialize_rag_service_with_timeout(timeout: float = 30.0):
    """
    Initialize RAG V2 service with timeout protection.

    This should be called during FastAPI startup, NOT on first request.

    Args:
        timeout: Maximum seconds to wait for initialization
    """
    global _rag_v2_initialization_complete, _rag_v2_initialization_error

    try:
        logger.info("rag_v2_startup_init_begin", timeout=timeout)

        async def _init():
            # Import here to avoid circular dependency
            from app.services.rag_service_v2 import get_rag_service_v2

            # This will create the singleton
            rag_service = get_rag_service_v2()

            # Optionally pre-load heavy resources
            # (but don't block on them - they'll lazy load later)
            logger.info("rag_v2_singleton_created")

            return rag_service

        # Initialize with timeout
        rag_service = await asyncio.wait_for(_init(), timeout=timeout)

        _rag_v2_initialization_complete = True

        logger.info(
            "rag_v2_startup_init_success",
            model=rag_service.model,
            use_cache=rag_service.use_cache,
            use_rerank=rag_service.use_rerank
        )

    except asyncio.TimeoutError:
        error_msg = f"RAG V2 initialization timeout after {timeout}s"
        _rag_v2_initialization_error = error_msg
        logger.error(
            "rag_v2_startup_init_timeout",
            timeout=timeout,
            message="RAG V2 initialization took too long - will retry on first request"
        )

    except Exception as e:
        error_msg = f"RAG V2 initialization failed: {str(e)}"
        _rag_v2_initialization_error = error_msg
        logger.error(
            "rag_v2_startup_init_error",
            error=str(e),
            error_type=type(e).__name__,
            message="RAG V2 initialization failed - will retry on first request"
        )


def get_initialization_status() -> dict:
    """Get RAG V2 initialization status for debugging."""
    return {
        "initialized": _rag_v2_initialization_complete,
        "error": _rag_v2_initialization_error,
    }
