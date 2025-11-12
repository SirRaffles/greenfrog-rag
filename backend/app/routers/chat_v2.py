"""
Chat Router V2 - Production-Ready RAG Endpoints

This router provides next-generation RAG capabilities with:
- Semantic caching (Redis + embeddings)
- Hybrid retrieval (BM25 + semantic search)
- Optional reranking for quality improvement
- Streaming and non-streaming responses
- Comprehensive health checks and statistics
- Feature flag support for gradual rollout

Architecture:
    Client → FastAPI → RAGServiceV2 → [Cache, Retrieval, Rerank, Ollama, Stream]

Key Features:
- 100% type-safe with Pydantic validation
- SSE streaming with real-time metrics
- Singleton service management
- Environment-based configuration
- Rich error handling with proper status codes
- Structured logging for observability
- Cache invalidation endpoints for admin
"""

import os
import time
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
import structlog

from app.services.cache_service import CacheService
from app.services.ollama_service import OllamaService
from app.services.retrieval_service import RetrievalService
from app.services.rerank_service import RerankService
from app.services.stream_service import StreamService
from app.services.rag_service_v2 import RAGServiceV2

logger = structlog.get_logger(__name__)
router = APIRouter()

# ============================================================================
# Pydantic Models - Request/Response Schemas
# ============================================================================


class ChatRequestV2(BaseModel):
    """
    Chat request schema for RAG V2 API.

    Example:
        ```json
        {
            "message": "What is the capital of France?",
            "workspace": "greenfrog",
            "k": 5,
            "stream": false,
            "temperature": 0.7,
            "max_tokens": 1024,
            "use_cache": true,
            "use_rerank": true
        }
        ```
    """
    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="User query or question"
    )
    workspace: str = Field(
        default="greenfrog",
        description="Workspace/collection identifier for document retrieval"
    )
    k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of documents to retrieve for context"
    )
    stream: bool = Field(
        default=False,
        description="Enable Server-Sent Events (SSE) streaming"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature (0=deterministic, 2=creative)"
    )
    max_tokens: int = Field(
        default=1024,
        ge=1,
        le=4096,
        description="Maximum tokens to generate in response"
    )
    use_cache: Optional[bool] = Field(
        default=None,
        description="Override service-level cache setting (None=use default)"
    )
    use_rerank: Optional[bool] = Field(
        default=None,
        description="Override service-level rerank setting (None=use default)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Override default LLM model (e.g., 'phi3:mini', 'llama3.2:3b')"
    )


class SourceMetadata(BaseModel):
    """Metadata for a single source document."""
    id: str = Field(..., description="Document unique identifier")
    text: str = Field(..., description="Document text snippet (truncated)")
    score: float = Field(..., description="Relevance score (0-1)")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional document metadata (source, chunk_id, etc.)"
    )
    method: str = Field(
        default="unknown",
        description="Retrieval method used (bm25, semantic, hybrid)"
    )


class ResponseMetadata(BaseModel):
    """Detailed metadata about the RAG pipeline execution."""
    cached: bool = Field(..., description="Whether response was served from cache")
    retrieval_method: str = Field(default="hybrid", description="Retrieval strategy used")
    retrieval_time_ms: float = Field(..., description="Document retrieval time in milliseconds")
    rerank_time_ms: float = Field(default=0.0, description="Reranking time in milliseconds")
    generation_time_ms: float = Field(default=0.0, description="LLM generation time in milliseconds")
    total_time_ms: float = Field(..., description="Total end-to-end pipeline time")
    model: str = Field(..., description="LLM model used for generation")
    context_length: int = Field(..., description="Length of context provided to LLM")
    source_count: int = Field(..., description="Number of source documents retrieved")
    use_cache: bool = Field(..., description="Cache feature flag status")
    use_rerank: bool = Field(..., description="Rerank feature flag status")
    cache_time_ms: Optional[float] = Field(default=None, description="Cache lookup time (if applicable)")
    no_context_found: Optional[bool] = Field(default=False, description="Flag if no relevant documents found")


class ChatResponseV2(BaseModel):
    """
    Chat response schema for RAG V2 API.

    Example:
        ```json
        {
            "response": "The capital of France is Paris.",
            "sources": [
                {
                    "id": "doc_123",
                    "text": "Paris is the capital and largest city of France...",
                    "score": 0.92,
                    "metadata": {"source": "geography.pdf", "page": 42},
                    "method": "hybrid"
                }
            ],
            "metadata": {
                "cached": false,
                "retrieval_method": "hybrid",
                "retrieval_time_ms": 45.2,
                "rerank_time_ms": 12.5,
                "generation_time_ms": 238.7,
                "total_time_ms": 296.4,
                "model": "phi3:mini",
                "context_length": 1523,
                "source_count": 5,
                "use_cache": true,
                "use_rerank": true
            },
            "timestamp": "2025-01-15T10:30:45.123456"
        }
        ```
    """
    response: str = Field(..., description="Generated answer from RAG system")
    sources: List[SourceMetadata] = Field(
        default_factory=list,
        description="Source documents used to generate the answer"
    )
    metadata: ResponseMetadata = Field(..., description="Pipeline execution metadata")
    timestamp: str = Field(..., description="Response timestamp (ISO 8601)")


class HealthCheckResponse(BaseModel):
    """Health check response for all RAG V2 services."""
    status: str = Field(..., description="Overall health status: 'healthy', 'degraded', 'unhealthy'")
    services: Dict[str, Union[bool, str]] = Field(
        ...,
        description="Individual service health statuses"
    )
    timestamp: str = Field(..., description="Health check timestamp (ISO 8601)")


class StatsResponse(BaseModel):
    """Aggregate statistics for RAG V2 services."""
    cache: Dict[str, Any] = Field(
        default_factory=dict,
        description="Cache statistics (hit rate, entry count, etc.)"
    )
    retrieval: Dict[str, Any] = Field(
        default_factory=dict,
        description="Retrieval service statistics (document count, collections, etc.)"
    )
    model: str = Field(..., description="Current LLM model in use")
    use_cache: bool = Field(..., description="Cache feature flag status")
    use_rerank: bool = Field(..., description="Rerank feature flag status")
    timestamp: str = Field(..., description="Statistics timestamp (ISO 8601)")


class CacheInvalidateRequest(BaseModel):
    """Request to invalidate cache entries."""
    workspace: str = Field(
        default="greenfrog",
        description="Workspace to clear cache for"
    )
    query: Optional[str] = Field(
        default=None,
        description="Specific query to invalidate (None=clear all workspace entries)"
    )


class CacheInvalidateResponse(BaseModel):
    """Response from cache invalidation."""
    keys_deleted: int = Field(..., description="Number of cache keys deleted")
    workspace: str = Field(..., description="Workspace affected")
    timestamp: str = Field(..., description="Invalidation timestamp (ISO 8601)")


# ============================================================================
# Dependency Injection - Singleton RAG Service
# ============================================================================

async def get_rag_service() -> RAGServiceV2:
    """
    Dependency injection for RAGServiceV2 singleton.

    Returns the global RAGServiceV2 instance that was initialized during
    FastAPI startup (see main.py startup event). This prevents blocking
    initialization on first request.

    The global singleton is managed by get_rag_service_v2() in
    app.services.rag_service_v2, which is pre-initialized during startup
    via initialize_rag_service_with_timeout() in app.services.rag_init.

    Returns:
        Pre-initialized RAGServiceV2 instance

    Raises:
        HTTPException: If service initialization failed during startup
    """
    from app.services.rag_service_v2 import get_rag_service_v2

    try:
        # Return the pre-initialized global singleton
        # This was created during FastAPI startup, so it should be ready
        return get_rag_service_v2()
    except Exception as e:
        logger.error("rag_service_v2_dependency_injection_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG service unavailable: {str(e)}"
        )


# ============================================================================
# API Endpoints
# ============================================================================


@router.post(
    "/query",
    response_model=ChatResponseV2,
    status_code=status.HTTP_200_OK,
    summary="Query RAG system (non-streaming)",
    description="""
    Send a query to the RAG V2 system and receive a complete JSON response.

    This endpoint orchestrates the full RAG pipeline:
    1. Check semantic cache for similar queries
    2. If cache miss: retrieve relevant documents (hybrid search)
    3. Optionally rerank documents by relevance
    4. Build context from top-k documents
    5. Generate response using LLM
    6. Cache response for future similar queries

    Returns a complete response with sources and detailed metadata.
    """,
    responses={
        200: {
            "description": "Successful query with generated response",
            "model": ChatResponseV2,
        },
        422: {
            "description": "Validation error (invalid parameters)",
        },
        500: {
            "description": "Internal server error (pipeline failure)",
        },
        503: {
            "description": "Service unavailable (dependency failure)",
        },
    },
)
async def query_rag(
    request: ChatRequestV2,
    rag: RAGServiceV2 = Depends(get_rag_service),
) -> ChatResponseV2:
    """
    Execute a non-streaming RAG query.

    Args:
        request: Query request with message and parameters
        rag: RAG service dependency (injected)

    Returns:
        Complete response with answer, sources, and metadata

    Raises:
        HTTPException: On validation or pipeline errors
    """
    start_time = time.time()

    logger.info(
        "rag_v2_query_request",
        message_length=len(request.message),
        workspace=request.workspace,
        k=request.k,
        stream=request.stream,
        use_cache_override=request.use_cache,
        use_rerank_override=request.use_rerank,
    )

    try:
        # Apply per-request overrides if provided
        original_use_cache = rag.use_cache
        original_use_rerank = rag.use_rerank

        if request.use_cache is not None:
            rag.use_cache = request.use_cache
        if request.use_rerank is not None:
            rag.use_rerank = request.use_rerank

        try:
            # Execute RAG pipeline (non-streaming)
            result = await rag.query(
                question=request.message,
                workspace=request.workspace,
                k=request.k,
                stream=False,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                model=request.model,
            )

        finally:
            # Restore original settings
            rag.use_cache = original_use_cache
            rag.use_rerank = original_use_rerank

        # Convert raw result to Pydantic model
        response = ChatResponseV2(
            response=result["response"],
            sources=[SourceMetadata(**src) for src in result.get("sources", [])],
            metadata=ResponseMetadata(**result["metadata"]),
            timestamp=result["timestamp"],
        )

        request_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "rag_v2_query_success",
            response_length=len(response.response),
            source_count=len(response.sources),
            cached=response.metadata.cached,
            total_time_ms=round(request_time_ms, 2),
        )

        return response

    except ValueError as e:
        # Validation errors (400 Bad Request)
        logger.error("rag_v2_query_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )

    except TimeoutError as e:
        # Timeout errors (504 Gateway Timeout)
        logger.error("rag_v2_query_timeout", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request timeout: The RAG pipeline took too long to respond"
        )

    except Exception as e:
        # All other errors (500 Internal Server Error)
        logger.error(
            "rag_v2_query_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {str(e)}"
        )


@router.post(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Query RAG system (streaming)",
    description="""
    Send a query to the RAG V2 system and receive a streaming response via Server-Sent Events (SSE).

    The endpoint returns SSE events containing:
    - Token-by-token generation (real-time)
    - Streaming metrics (tokens/sec, elapsed time)
    - Final completion event with sources and metadata

    SSE Event Format:
    ```
    data: {"token": "Hello", "done": false, "metrics": {...}}
    data: {"token": " world", "done": false, "metrics": {...}}
    data: {"done": true, "stats": {...}}
    ```

    Perfect for real-time chat interfaces and low-latency applications.
    """,
    responses={
        200: {
            "description": "Streaming response (text/event-stream)",
            "content": {
                "text/event-stream": {
                    "example": 'data: {"token": "Paris", "done": false}\n\ndata: {"done": true}\n\n'
                }
            },
        },
        422: {
            "description": "Validation error (invalid parameters)",
        },
        500: {
            "description": "Internal server error (pipeline failure)",
        },
    },
)
async def stream_rag_query(
    request: ChatRequestV2,
    rag: RAGServiceV2 = Depends(get_rag_service),
):
    """
    Execute a streaming RAG query with SSE.

    Args:
        request: Query request with message and parameters
        rag: RAG service dependency (injected)

    Returns:
        StreamingResponse with text/event-stream content

    Raises:
        HTTPException: On validation or pipeline errors
    """
    logger.info(
        "rag_v2_stream_request",
        message_length=len(request.message),
        workspace=request.workspace,
        k=request.k,
    )

    try:
        # Apply per-request overrides if provided
        original_use_cache = rag.use_cache
        original_use_rerank = rag.use_rerank

        if request.use_cache is not None:
            rag.use_cache = request.use_cache
        if request.use_rerank is not None:
            rag.use_rerank = request.use_rerank

        async def event_generator():
            """Generate SSE events from RAG streaming response."""
            try:
                # Execute RAG pipeline (streaming mode)
                async for sse_event in await rag.query(
                    question=request.message,
                    workspace=request.workspace,
                    k=request.k,
                    stream=True,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                    model=request.model,
                ):
                    yield sse_event

            except Exception as e:
                # Yield error event to client
                import json
                error_event = f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
                logger.error(
                    "rag_v2_stream_generation_error",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                yield error_event

            finally:
                # Restore original settings
                rag.use_cache = original_use_cache
                rag.use_rerank = original_use_rerank

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
            },
        )

    except ValueError as e:
        logger.error("rag_v2_stream_validation_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )

    except Exception as e:
        logger.error(
            "rag_v2_stream_error",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming query failed: {str(e)}"
        )


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check RAG V2 health status",
    description="""
    Perform a comprehensive health check on all RAG V2 services.

    Checks:
    - Cache service (Redis connectivity)
    - Ollama service (LLM availability)
    - Retrieval service (Qdrant vector DB)
    - Rerank service (if enabled)

    Returns HTTP 200 if all critical services are healthy.
    Returns HTTP 503 if any critical service is down.
    """,
    responses={
        200: {
            "description": "All services healthy",
            "model": HealthCheckResponse,
        },
        503: {
            "description": "One or more services unhealthy",
            "model": HealthCheckResponse,
        },
    },
)
async def health_check(rag: RAGServiceV2 = Depends(get_rag_service)):
    """
    Execute health check on all RAG V2 services.

    Args:
        rag: RAG service dependency (injected)

    Returns:
        Health status for all services
    """
    logger.info("rag_v2_health_check_request")

    try:
        health_status = await rag.health_check()

        # Determine overall status
        overall_healthy = health_status.get("overall", False)

        response = HealthCheckResponse(
            status="healthy" if overall_healthy else "unhealthy",
            services=health_status,
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info(
            "rag_v2_health_check_complete",
            status=response.status,
            services=health_status,
        )

        # Return 503 if unhealthy
        if not overall_healthy:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=response.model_dump(),
            )

        return response

    except Exception as e:
        logger.error("rag_v2_health_check_error", error=str(e))

        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "error",
                "services": {"error": str(e)},
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


@router.get(
    "/stats",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get RAG V2 aggregate statistics",
    description="""
    Retrieve aggregate statistics from all RAG V2 services.

    Includes:
    - Cache statistics (hit rate, entry count, workspace stats)
    - Retrieval statistics (document count, collection info)
    - Model configuration (current LLM, feature flags)

    Useful for monitoring, analytics, and performance tuning.
    """,
)
async def get_stats(rag: RAGServiceV2 = Depends(get_rag_service)) -> StatsResponse:
    """
    Retrieve aggregate statistics from RAG services.

    Args:
        rag: RAG service dependency (injected)

    Returns:
        Comprehensive statistics from all services

    Raises:
        HTTPException: If statistics retrieval fails
    """
    logger.info("rag_v2_stats_request")

    try:
        stats = await rag.get_stats()

        response = StatsResponse(
            cache=stats.get("cache", {}),
            retrieval=stats.get("retrieval", {}),
            model=stats.get("model", "unknown"),
            use_cache=stats.get("use_cache", False),
            use_rerank=stats.get("use_rerank", False),
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info("rag_v2_stats_success", stats=stats)

        return response

    except Exception as e:
        logger.error("rag_v2_stats_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve statistics: {str(e)}"
        )


@router.post(
    "/cache/invalidate",
    response_model=CacheInvalidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Invalidate cache entries (Admin)",
    description="""
    Clear cache entries for a workspace or specific query.

    Use cases:
    - Clear stale cache after document updates
    - Force re-generation of responses
    - Workspace-level cache purge

    If `query` is provided, only that specific query is invalidated.
    If `query` is null, all cache entries for the workspace are cleared.

    **Note:** This is an admin endpoint and should be protected in production.
    """,
)
async def invalidate_cache(
    request: CacheInvalidateRequest,
    rag: RAGServiceV2 = Depends(get_rag_service),
) -> CacheInvalidateResponse:
    """
    Invalidate cache entries.

    Args:
        request: Invalidation request with workspace and optional query
        rag: RAG service dependency (injected)

    Returns:
        Number of cache entries deleted

    Raises:
        HTTPException: If invalidation fails
    """
    logger.info(
        "rag_v2_cache_invalidate_request",
        workspace=request.workspace,
        query_provided=bool(request.query),
    )

    try:
        # Invalidate cache
        keys_deleted = await rag.cache_service.invalidate(
            query=request.query,
            workspace=request.workspace,
        )

        response = CacheInvalidateResponse(
            keys_deleted=keys_deleted,
            workspace=request.workspace,
            timestamp=datetime.utcnow().isoformat(),
        )

        logger.info(
            "rag_v2_cache_invalidate_success",
            keys_deleted=keys_deleted,
            workspace=request.workspace,
        )

        return response

    except Exception as e:
        logger.error(
            "rag_v2_cache_invalidate_error",
            error=str(e),
            workspace=request.workspace,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache invalidation failed: {str(e)}"
        )
