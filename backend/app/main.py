"""
GreenFrog RAG Avatar - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import os

from app.routers import chat, avatar, tts, scraper, retrieval, chat_v2
from app.utils.logger import setup_logging
from app.services.health_service import get_health_service
from app.services.rag_init import initialize_rag_service_with_timeout

# Setup logging
setup_logging()
logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GreenFrog RAG API",
    description="Sustainability-focused RAG chatbot with avatar and TTS capabilities",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
# Restrict CORS to frontend origin only (security best practice)
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Explicitly list allowed origins (no wildcards)
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(avatar.router, prefix="/api/avatar", tags=["avatar"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])
app.include_router(retrieval.router, prefix="/api/retrieval", tags=["retrieval"])

# Include RAG V2 router (feature flag controlled)
# Set USE_RAG_V2=true in environment to enable V2 endpoints
if os.getenv("USE_RAG_V2", "true").lower() == "true":
    app.include_router(chat_v2.router, prefix="/api/v2/chat", tags=["chat-v2"])
    logger.info("rag_v2_enabled", prefix="/api/v2/chat")
else:
    logger.info("rag_v2_disabled", message="Set USE_RAG_V2=true to enable")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("GreenFrog RAG API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"AnythingLLM: {os.getenv('ANYTHINGLLM_URL', 'http://anythingllm:3001')}")
    logger.info(f"TTS Mode: {os.getenv('TTS_MODE', 'piper')}")
    logger.info(f"RAG V2 Enabled: {os.getenv('USE_RAG_V2', 'true')}")
    logger.info(f"Cache Enabled: {os.getenv('USE_CACHE', 'true')}")
    logger.info(f"Rerank Enabled: {os.getenv('USE_RERANK', 'true')}")

    # Pre-initialize RAG V2 to avoid dependency injection hang
    # This prevents blocking on first request when CacheService/RetrievalService initialize
    if os.getenv("USE_RAG_V2", "true").lower() == "true":
        logger.info("rag_v2_pre_initialization_start")
        await initialize_rag_service_with_timeout(timeout=30.0)
        logger.info("rag_v2_pre_initialization_complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("GreenFrog RAG API shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
    endpoints = {
        "docs": "/docs",
        "health": "/health",
        "chat": "/api/chat",
        "avatar": "/api/avatar",
        "tts": "/api/tts",
        "scraper": "/api/scraper",
        "retrieval": "/api/retrieval"
    }

    # Add V2 endpoints if enabled
    if os.getenv("USE_RAG_V2", "true").lower() == "true":
        endpoints["chat_v2"] = "/api/v2/chat"

    return {
        "service": "GreenFrog RAG API",
        "status": "running",
        "version": "2.0.0",
        "features": {
            "rag_v2": os.getenv("USE_RAG_V2", "true").lower() == "true",
            "cache": os.getenv("USE_CACHE", "true").lower() == "true",
            "rerank": os.getenv("USE_RERANK", "true").lower() == "true",
        },
        "endpoints": endpoints
    }


@app.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint.

    Checks all critical dependencies:
    - Redis (cache)
    - ChromaDB (vector database)
    - Ollama (LLM)
    - AnythingLLM (optional)
    - TTS service (Piper/XTTS)

    Returns:
        - 200: All critical services healthy
        - 503: One or more critical services unhealthy
    """
    try:
        health_service = get_health_service()
        health_status = await health_service.check_all()

        # Return 503 if unhealthy, 200 otherwise
        status_code = 503 if health_status["status"] == "unhealthy" else 200

        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
    except Exception as e:
        logger.error("health_check_failed", error=str(e), error_type=type(e).__name__)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": "Health check failed",
                "message": str(e)
            }
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
