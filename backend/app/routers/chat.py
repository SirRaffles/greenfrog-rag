"""
Chat Router - RAG Chat Endpoints
Handles conversational queries with RAG
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import structlog
import os

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services.rag_service import get_rag_service, RAGService

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_rag() -> RAGService:
    """Dependency injection for RAG service"""
    return get_rag_service(
        base_url=os.getenv("ANYTHINGLLM_URL", "http://anythingllm:3001"),
        api_key=os.getenv("ANYTHINGLLM_API_KEY")
    )


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    rag: RAGService = Depends(get_rag)
):
    """
    Send chat message to RAG system

    Args:
        request: Chat request with message and parameters
        rag: RAG service dependency

    Returns:
        ChatResponse with assistant response and sources
    """
    logger.info("chat_message_received",
               message_length=len(request.message),
               workspace=request.workspace_slug,
               mode=request.mode)

    try:
        # Send to RAG service
        result = await rag.chat(
            message=request.message,
            workspace_slug=request.workspace_slug,
            mode=request.mode,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            session_id=request.session_id
        )

        # Build response
        response = ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
            session_id=result["session_id"],
            timestamp=result["timestamp"],
            model=result.get("model")
        )

        logger.info("chat_message_success",
                   response_length=len(response.response),
                   sources_count=len(response.sources))

        return response

    except Exception as e:
        logger.error("chat_message_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/query", response_model=ChatResponse)
async def send_query(
    request: ChatRequest,
    rag: RAGService = Depends(get_rag)
):
    """
    Send single query to RAG system (no chat history)

    Args:
        request: Query request
        rag: RAG service dependency

    Returns:
        ChatResponse with answer and sources
    """
    logger.info("query_received",
               message_length=len(request.message),
               workspace=request.workspace_slug)

    try:
        # Force query mode
        result = await rag.query(
            question=request.message,
            workspace_slug=request.workspace_slug,
            max_tokens=request.max_tokens
        )

        response = ChatResponse(
            response=result["response"],
            sources=result.get("sources", []),
            session_id=result["session_id"],
            timestamp=result["timestamp"],
            model=result.get("model")
        )

        logger.info("query_success",
                   response_length=len(response.response),
                   sources_count=len(response.sources))

        return response

    except Exception as e:
        logger.error("query_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.get("/workspaces")
async def list_workspaces(rag: RAGService = Depends(get_rag)):
    """
    List available workspaces

    Args:
        rag: RAG service dependency

    Returns:
        List of workspace metadata
    """
    logger.info("list_workspaces_request")

    try:
        workspaces = await rag.get_workspaces()

        logger.info("list_workspaces_success", count=len(workspaces))
        return {"workspaces": workspaces}

    except Exception as e:
        logger.error("list_workspaces_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list workspaces: {str(e)}"
        )


@router.get("/workspace/{workspace_slug}/stats")
async def get_workspace_stats(
    workspace_slug: str,
    rag: RAGService = Depends(get_rag)
):
    """
    Get workspace statistics

    Args:
        workspace_slug: Workspace identifier
        rag: RAG service dependency

    Returns:
        Workspace statistics
    """
    logger.info("workspace_stats_request", workspace=workspace_slug)

    try:
        stats = await rag.get_workspace_stats(workspace_slug)

        logger.info("workspace_stats_success", workspace=workspace_slug)
        return {"workspace": stats}

    except Exception as e:
        logger.error("workspace_stats_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get workspace stats: {str(e)}"
        )


@router.get("/health")
async def health_check(rag: RAGService = Depends(get_rag)):
    """
    Check RAG service health

    Args:
        rag: RAG service dependency

    Returns:
        Health status
    """
    logger.info("rag_health_check_request")

    try:
        is_healthy = await rag.health_check()

        if is_healthy:
            logger.info("rag_health_check_success")
            return {
                "status": "healthy",
                "anythingllm": "up"
            }
        else:
            logger.warning("rag_health_check_unhealthy")
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "anythingllm": "down"
                }
            )

    except Exception as e:
        logger.error("rag_health_check_error", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e)
            }
        )
