"""
API Key Authentication Middleware
Protects API endpoints with API key authentication
"""

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
import os
import structlog
from typing import Callable

logger = structlog.get_logger(__name__)


# API key from environment variable
API_KEY = os.getenv("API_KEY", "")

# Public endpoints that don't require authentication
PUBLIC_ENDPOINTS = {
    "/",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}


async def api_key_middleware(request: Request, call_next: Callable) -> Response:
    """
    Middleware to validate API key for protected endpoints.

    Public endpoints (health, docs) are allowed without authentication.
    All other endpoints require a valid API key in the X-API-Key header.

    Args:
        request: Incoming FastAPI request
        call_next: Next middleware or route handler

    Returns:
        Response from next handler or 401 Unauthorized
    """

    # Check if this is a public endpoint
    if request.url.path in PUBLIC_ENDPOINTS:
        return await call_next(request)

    # Check for API key
    if not API_KEY:
        # API key not configured - log warning but allow (development mode)
        logger.warning(
            "api_key_not_configured",
            message="API_KEY environment variable not set - authentication disabled",
            path=request.url.path
        )
        return await call_next(request)

    # Get API key from header
    provided_key = request.headers.get("X-API-Key", "")

    if not provided_key:
        logger.warning(
            "api_key_missing",
            path=request.url.path,
            client=request.client.host if request.client else "unknown"
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Unauthorized",
                "message": "Missing API key. Provide X-API-Key header."
            },
            headers={"WWW-Authenticate": "API-Key"}
        )

    if provided_key != API_KEY:
        logger.warning(
            "api_key_invalid",
            path=request.url.path,
            client=request.client.host if request.client else "unknown",
            provided_key_prefix=provided_key[:10] if len(provided_key) > 10 else "short"
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "Unauthorized",
                "message": "Invalid API key"
            },
            headers={"WWW-Authenticate": "API-Key"}
        )

    # API key is valid - proceed
    logger.debug(
        "api_key_validated",
        path=request.url.path,
        method=request.method
    )

    return await call_next(request)


async def optional_api_key_middleware(request: Request, call_next: Callable) -> Response:
    """
    Optional API key middleware - adds user context but doesn't block.

    Useful for rate limiting or analytics without requiring authentication.
    """

    # Extract API key if present
    api_key = request.headers.get("X-API-Key")

    if api_key:
        # Add authenticated flag to request state
        request.state.authenticated = (api_key == API_KEY)
        request.state.api_key = api_key[:10]  # Store prefix for logging
    else:
        request.state.authenticated = False
        request.state.api_key = None

    return await call_next(request)
