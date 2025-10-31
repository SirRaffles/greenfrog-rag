"""
GreenFrog RAG Avatar - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog
import os

from app.routers import chat, avatar, tts, scraper
from app.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = structlog.get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="GreenFrog RAG API",
    description="Sustainability-focused RAG chatbot with avatar and TTS capabilities",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(avatar.router, prefix="/api/avatar", tags=["avatar"])
app.include_router(tts.router, prefix="/api/tts", tags=["tts"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🐸 GreenFrog RAG API starting up...")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"AnythingLLM: {os.getenv('ANYTHINGLLM_URL', 'http://anythingllm:3001')}")
    logger.info(f"TTS Mode: {os.getenv('TTS_MODE', 'piper')}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🐸 GreenFrog RAG API shutting down...")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "GreenFrog RAG API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "chat": "/api/chat",
            "avatar": "/api/avatar",
            "tts": "/api/tts",
            "scraper": "/api/scraper"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # TODO: Add actual health checks for dependencies
        return {
            "status": "healthy",
            "services": {
                "api": "up",
                "anythingllm": "checking",
                "tts": "checking",
                "avatar": "checking"
            }
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unhealthy")


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
