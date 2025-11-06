"""
Retrieval API Router
Endpoints for hybrid search and document retrieval
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Tuple
import structlog

from app.services.retrieval_service import RetrievalService
from app.services.ollama_service import OllamaService

logger = structlog.get_logger(__name__)

router = APIRouter()


# Request/Response Models
class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., min_length=1, description="Search query")
    k: int = Field(10, ge=1, le=100, description="Number of results to return")
    method: str = Field("hybrid", description="Search method: hybrid, semantic, or bm25")
    rrf_k: int = Field(60, description="RRF constant for hybrid search")
    weights: Tuple[float, float] = Field((0.5, 0.5), description="Weights for (semantic, bm25)")
    min_score: float = Field(0.0, ge=0.0, description="Minimum score threshold")


class DocumentResult(BaseModel):
    """Document search result."""
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float
    method: str
    rrf_score: Optional[float] = None
    semantic_score: Optional[float] = None
    semantic_rank: Optional[int] = None
    bm25_score: Optional[float] = None
    bm25_rank: Optional[int] = None
    distance: Optional[float] = None


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    method: str
    results: List[DocumentResult]
    count: int
    took_ms: Optional[float] = None


class CollectionInfo(BaseModel):
    """ChromaDB collection information."""
    name: str
    metadata: Optional[Dict[str, Any]] = None
    document_count: Optional[int] = None


# Global service instances
_ollama_service: Optional[OllamaService] = None
_retrieval_service: Optional[RetrievalService] = None


def get_services() -> Tuple[OllamaService, RetrievalService]:
    """Get or create service instances."""
    global _ollama_service, _retrieval_service

    if _ollama_service is None:
        _ollama_service = OllamaService()
        logger.info("ollama_service_initialized")

    if _retrieval_service is None:
        _retrieval_service = RetrievalService(
            ollama_service=_ollama_service,
            collection_name="greenfrog"
        )
        logger.info("retrieval_service_initialized")

    return _ollama_service, _retrieval_service


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search documents using hybrid, semantic, or BM25 methods.

    - **hybrid**: Combines semantic and BM25 search with RRF
    - **semantic**: Vector similarity search only
    - **bm25**: Keyword-based search only
    """
    try:
        import time
        start_time = time.time()

        _, retrieval_service = get_services()

        logger.info(
            "search_request",
            query=request.query,
            method=request.method,
            k=request.k
        )

        # Route to appropriate search method
        if request.method == "hybrid":
            results = await retrieval_service.hybrid_search(
                query=request.query,
                k=request.k,
                rrf_k=request.rrf_k,
                weights=request.weights,
                min_score=request.min_score
            )
        elif request.method == "semantic":
            results = await retrieval_service.semantic_search(
                query=request.query,
                k=request.k
            )
        elif request.method == "bm25":
            results = await retrieval_service.keyword_search(
                query=request.query,
                k=request.k
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid search method: {request.method}"
            )

        took_ms = (time.time() - start_time) * 1000

        logger.info(
            "search_complete",
            method=request.method,
            results_count=len(results),
            took_ms=round(took_ms, 2)
        )

        return SearchResponse(
            query=request.query,
            method=request.method,
            results=results,
            count=len(results),
            took_ms=round(took_ms, 2)
        )

    except Exception as e:
        logger.error("search_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse)
async def search_get(
    q: str = Query(..., description="Search query"),
    k: int = Query(10, ge=1, le=100, description="Number of results"),
    method: str = Query("hybrid", description="Search method")
):
    """
    Simple GET endpoint for search (for easy testing).
    """
    request = SearchRequest(query=q, k=k, method=method)
    return await search(request)


@router.post("/reload")
async def reload_documents():
    """
    Reload documents from ChromaDB.
    Useful after adding new documents to the collection.
    """
    try:
        _, retrieval_service = get_services()

        logger.info("reload_documents_request")

        doc_count = await retrieval_service.load_documents(force_reload=True)

        logger.info("reload_documents_complete", count=doc_count)

        return {
            "status": "success",
            "message": f"Reloaded {doc_count} documents",
            "document_count": doc_count
        }

    except Exception as e:
        logger.error("reload_documents_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/collection", response_model=CollectionInfo)
async def get_collection_info():
    """
    Get ChromaDB collection information.
    """
    try:
        _, retrieval_service = get_services()

        info = await retrieval_service.get_collection_info()

        return CollectionInfo(
            name=info.get("name", "greenfrog"),
            metadata=info.get("metadata", {}),
            document_count=info.get("count")
        )

    except Exception as e:
        logger.error("get_collection_info_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """
    Check retrieval service health.
    """
    try:
        ollama_service, retrieval_service = get_services()

        # Check both services
        ollama_healthy = await ollama_service.health_check()
        retrieval_healthy = await retrieval_service.health_check()

        is_healthy = ollama_healthy and retrieval_healthy

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "ollama": "up" if ollama_healthy else "down",
            "retrieval": "up" if retrieval_healthy else "down",
            "document_count": len(retrieval_service._documents) if retrieval_healthy else 0
        }

    except Exception as e:
        logger.error("health_check_error", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/stats")
async def get_stats():
    """
    Get retrieval service statistics.
    """
    try:
        _, retrieval_service = get_services()

        return {
            "collection": retrieval_service.collection_name,
            "chromadb_url": retrieval_service.chromadb_url,
            "embedding_model": retrieval_service.embedding_model,
            "documents_loaded": retrieval_service._documents_loaded,
            "document_count": len(retrieval_service._documents),
            "bm25_index_built": retrieval_service._bm25_index is not None
        }

    except Exception as e:
        logger.error("get_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
