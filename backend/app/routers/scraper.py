"""
Scraper Router - Web Scraping Endpoints
Handles web scraping requests with intelligent engine routing
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import structlog
from typing import List

from app.models.schemas import (
    ScraperRequest,
    ScraperBulkRequest,
    ScraperResponse,
    ErrorResponse
)
from app.services.scraper_service import (
    get_scraper,
    ScraperOrchestrator,
    ScraperEngine
)

logger = structlog.get_logger(__name__)
router = APIRouter()


def get_scraper_service() -> ScraperOrchestrator:
    """Dependency injection for scraper service"""
    return get_scraper()


@router.post("/scrape", response_model=ScraperResponse)
async def scrape_url(
    request: ScraperRequest,
    scraper: ScraperOrchestrator = Depends(get_scraper_service)
):
    """
    Scrape a single URL

    Args:
        request: Scraper request with URL and parameters
        scraper: Scraper service dependency

    Returns:
        ScraperResponse with extracted content
    """
    logger.info("scrape_url_request",
               url=request.url,
               engine=request.engine,
               use_fallback=request.use_fallback)

    try:
        # Convert engine string to enum
        preferred_engine = None
        if request.engine:
            preferred_engine = ScraperEngine(request.engine)

        # Scrape URL
        result = await scraper.scrape_url(
            url=request.url,
            preferred_engine=preferred_engine,
            use_fallback=request.use_fallback
        )

        # Build response
        response = ScraperResponse(
            url=result.url,
            title=result.title,
            content=result.content,
            metadata=result.metadata,
            engine_used=result.engine_used.value,
            success=result.success,
            error=result.error
        )

        logger.info("scrape_url_success",
                   url=request.url,
                   engine_used=result.engine_used.value,
                   content_length=len(result.content))

        return response

    except Exception as e:
        logger.error("scrape_url_error", url=request.url, error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Scraping failed: {str(e)}"
        )


@router.post("/scrape/bulk", response_model=List[ScraperResponse])
async def scrape_bulk(
    request: ScraperBulkRequest,
    scraper: ScraperOrchestrator = Depends(get_scraper_service)
):
    """
    Scrape multiple URLs in bulk

    Args:
        request: Bulk scraper request with URLs and parameters
        scraper: Scraper service dependency

    Returns:
        List of ScraperResponse for each URL
    """
    logger.info("scrape_bulk_request",
               url_count=len(request.urls),
               max_concurrent=request.max_concurrent,
               engine=request.engine)

    try:
        # Scrape URLs in bulk
        results = await scraper.bulk_scrape(
            urls=request.urls,
            max_concurrent=request.max_concurrent
        )

        # Build responses
        responses = []
        for result in results:
            responses.append(ScraperResponse(
                url=result.url,
                title=result.title,
                content=result.content,
                metadata=result.metadata,
                engine_used=result.engine_used.value,
                success=result.success,
                error=result.error
            ))

        success_count = sum(1 for r in responses if r.success)
        logger.info("scrape_bulk_success",
                   total=len(responses),
                   success=success_count,
                   failed=len(responses) - success_count)

        return responses

    except Exception as e:
        logger.error("scrape_bulk_error", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Bulk scraping failed: {str(e)}"
        )


@router.get("/engines")
async def list_engines():
    """
    List available scraping engines

    Returns:
        List of available engines with descriptions
    """
    logger.info("list_engines_request")

    engines = [
        {
            "id": "crawl4ai",
            "name": "Crawl4AI",
            "description": "AI-powered intelligent extraction with semantic understanding",
            "best_for": "Complex content extraction, semantic analysis"
        },
        {
            "id": "read_fast",
            "name": "Read Website Fast",
            "description": "Fast simple extraction for static pages",
            "best_for": "Simple, static content pages"
        },
        {
            "id": "puppeteer",
            "name": "Puppeteer",
            "description": "JavaScript rendering for dynamic sites",
            "best_for": "SPAs, JavaScript-heavy sites"
        },
        {
            "id": "firecrawl",
            "name": "Firecrawl",
            "description": "Bulk operations via API",
            "best_for": "Crawling entire websites"
        }
    ]

    logger.info("list_engines_success", count=len(engines))
    return {"engines": engines}


@router.get("/health")
async def health_check(scraper: ScraperOrchestrator = Depends(get_scraper_service)):
    """
    Check scraper service health

    Args:
        scraper: Scraper service dependency

    Returns:
        Health status
    """
    logger.info("scraper_health_check_request")

    try:
        # Check MCP availability
        mcp_status = scraper.mcp_available

        overall_status = "healthy" if any(mcp_status.values()) else "degraded"

        logger.info("scraper_health_check_complete",
                   status=overall_status,
                   mcp_status=mcp_status)

        return {
            "status": overall_status,
            "engines": mcp_status
        }

    except Exception as e:
        logger.error("scraper_health_check_error", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "error",
                "error": str(e)
            }
        )
