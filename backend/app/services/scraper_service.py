"""
Intelligent Web Scraping Orchestrator
Uses MCP tools: crawl4ai-mcp → read-website-fast → puppeteer (fallback chain)
"""

import asyncio
import httpx
import structlog
from typing import Dict, List, Optional, Any
from enum import Enum
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class ScraperEngine(str, Enum):
    """Available scraping engines"""
    CRAWL4AI = "crawl4ai"  # AI-powered intelligent extraction
    READ_FAST = "read_fast"  # Fast simple extraction
    PUPPETEER = "puppeteer"  # JavaScript-heavy sites
    FIRECRAWL = "firecrawl"  # Bulk operations (API)


class ScrapingResult(BaseModel):
    """Scraping result model"""
    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    engine_used: ScraperEngine
    success: bool
    error: Optional[str] = None


class ScraperOrchestrator:
    """
    Intelligent scraping orchestrator with fallback chain:
    1. crawl4ai-mcp (AI-powered, best quality)
    2. read-website-fast (fast, simple sites)
    3. puppeteer (JavaScript-heavy sites)
    4. firecrawl (bulk operations via API)
    """

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60.0)
        self.mcp_available = self._check_mcp_availability()

    def _check_mcp_availability(self) -> Dict[str, bool]:
        """Check which MCP tools are available"""
        # TODO: Implement actual MCP availability check
        return {
            "crawl4ai": True,
            "read_fast": True,
            "puppeteer": True,
            "firecrawl": False  # API-based, needs key
        }

    async def scrape_url(
        self,
        url: str,
        preferred_engine: Optional[ScraperEngine] = None,
        use_fallback: bool = True
    ) -> ScrapingResult:
        """
        Scrape a URL using intelligent engine selection with fallback chain
        
        Args:
            url: URL to scrape
            preferred_engine: Preferred scraping engine (None = auto-select)
            use_fallback: Enable fallback to other engines if preferred fails
            
        Returns:
            ScrapingResult with content and metadata
        """
        logger.info("scrape_url_start", url=url, engine=preferred_engine)

        # Determine scraping strategy
        if preferred_engine:
            engines = [preferred_engine]
            if use_fallback:
                engines.extend(self._get_fallback_chain(preferred_engine))
        else:
            # Auto-select based on URL characteristics
            engines = self._select_engines(url)

        last_error = None

        # Try each engine in order
        for engine in engines:
            try:
                logger.info("trying_engine", url=url, engine=engine)
                
                if engine == ScraperEngine.CRAWL4AI:
                    result = await self._scrape_crawl4ai(url)
                elif engine == ScraperEngine.READ_FAST:
                    result = await self._scrape_read_fast(url)
                elif engine == ScraperEngine.PUPPETEER:
                    result = await self._scrape_puppeteer(url)
                elif engine == ScraperEngine.FIRECRAWL:
                    result = await self._scrape_firecrawl(url)
                else:
                    raise ValueError(f"Unknown engine: {engine}")

                if result.success:
                    logger.info("scrape_success", url=url, engine=engine)
                    return result
                    
            except Exception as e:
                last_error = str(e)
                logger.warning("engine_failed", url=url, engine=engine, error=str(e))
                continue

        # All engines failed
        logger.error("all_engines_failed", url=url, last_error=last_error)
        return ScrapingResult(
            url=url,
            title="",
            content="",
            metadata={},
            engine_used=engines[-1] if engines else ScraperEngine.READ_FAST,
            success=False,
            error=f"All scraping engines failed. Last error: {last_error}"
        )

    def _select_engines(self, url: str) -> List[ScraperEngine]:
        """Auto-select scraping engines based on URL characteristics"""
        engines = []

        # Start with AI-powered extraction (best quality)
        if self.mcp_available.get("crawl4ai"):
            engines.append(ScraperEngine.CRAWL4AI)

        # Add fast extraction for simple sites
        if self.mcp_available.get("read_fast"):
            engines.append(ScraperEngine.READ_FAST)

        # Add puppeteer for complex sites
        if self.mcp_available.get("puppeteer"):
            engines.append(ScraperEngine.PUPPETEER)

        return engines

    def _get_fallback_chain(self, engine: ScraperEngine) -> List[ScraperEngine]:
        """Get fallback engines for a given engine"""
        fallback_map = {
            ScraperEngine.CRAWL4AI: [ScraperEngine.READ_FAST, ScraperEngine.PUPPETEER],
            ScraperEngine.READ_FAST: [ScraperEngine.CRAWL4AI, ScraperEngine.PUPPETEER],
            ScraperEngine.PUPPETEER: [ScraperEngine.CRAWL4AI, ScraperEngine.READ_FAST],
            ScraperEngine.FIRECRAWL: [ScraperEngine.CRAWL4AI, ScraperEngine.READ_FAST]
        }
        return fallback_map.get(engine, [])

    async def _scrape_crawl4ai(self, url: str) -> ScrapingResult:
        """
        Scrape using crawl4ai-mcp (AI-powered intelligent extraction)
        Best for complex content extraction with semantic understanding
        """
        # TODO: Implement actual crawl4ai-mcp integration via MCP protocol
        # For now, simulate with httpx
        logger.info("scraping_with_crawl4ai", url=url)
        
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            # TODO: Replace with actual MCP call to crawl4ai
            # This would use the MCP protocol to call:
            # mcp_call("crawl4ai", "scrape", {"url": url, "extract_semantic": True})
            
            content = response.text
            
            return ScrapingResult(
                url=url,
                title="Extracted Title",  # TODO: Extract from response
                content=content[:5000],  # Truncate for now
                metadata={
                    "engine": "crawl4ai",
                    "content_length": len(content),
                    "timestamp": "2025-10-31"
                },
                engine_used=ScraperEngine.CRAWL4AI,
                success=True
            )
        except Exception as e:
            logger.error("crawl4ai_failed", url=url, error=str(e))
            raise

    async def _scrape_read_fast(self, url: str) -> ScrapingResult:
        """
        Scrape using read-website-fast (fast simple extraction)
        Best for simple, static content pages
        """
        logger.info("scraping_with_read_fast", url=url)
        
        try:
            # TODO: Implement actual read-website-fast MCP integration
            response = await self.client.get(url)
            response.raise_for_status()
            
            content = response.text
            
            return ScrapingResult(
                url=url,
                title="Fast Extracted Title",
                content=content[:5000],
                metadata={
                    "engine": "read_fast",
                    "content_length": len(content)
                },
                engine_used=ScraperEngine.READ_FAST,
                success=True
            )
        except Exception as e:
            logger.error("read_fast_failed", url=url, error=str(e))
            raise

    async def _scrape_puppeteer(self, url: str) -> ScrapingResult:
        """
        Scrape using puppeteer (JavaScript-heavy sites)
        Best for SPAs and dynamic content
        """
        logger.info("scraping_with_puppeteer", url=url)
        
        try:
            # TODO: Implement actual puppeteer MCP integration
            # Use existing puppeteer MCP server
            
            # Placeholder implementation
            response = await self.client.get(url)
            response.raise_for_status()
            
            content = response.text
            
            return ScrapingResult(
                url=url,
                title="Puppeteer Extracted Title",
                content=content[:5000],
                metadata={
                    "engine": "puppeteer",
                    "content_length": len(content),
                    "javascript_rendered": True
                },
                engine_used=ScraperEngine.PUPPETEER,
                success=True
            )
        except Exception as e:
            logger.error("puppeteer_failed", url=url, error=str(e))
            raise

    async def _scrape_firecrawl(self, url: str) -> ScrapingResult:
        """
        Scrape using Firecrawl API (bulk operations)
        Best for crawling entire websites
        """
        logger.info("scraping_with_firecrawl", url=url)
        
        try:
            # TODO: Implement Firecrawl API integration
            raise NotImplementedError("Firecrawl requires API key configuration")
        except Exception as e:
            logger.error("firecrawl_failed", url=url, error=str(e))
            raise

    async def bulk_scrape(
        self,
        urls: List[str],
        max_concurrent: int = 5
    ) -> List[ScrapingResult]:
        """
        Scrape multiple URLs concurrently with rate limiting
        
        Args:
            urls: List of URLs to scrape
            max_concurrent: Maximum concurrent requests
            
        Returns:
            List of ScrapingResult
        """
        logger.info("bulk_scrape_start", url_count=len(urls), max_concurrent=max_concurrent)
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_semaphore(url: str) -> ScrapingResult:
            async with semaphore:
                return await self.scrape_url(url)
        
        tasks = [scrape_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("bulk_scrape_error", url=urls[i], error=str(result))
                processed_results.append(ScrapingResult(
                    url=urls[i],
                    title="",
                    content="",
                    metadata={},
                    engine_used=ScraperEngine.READ_FAST,
                    success=False,
                    error=str(result)
                ))
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.success)
        logger.info("bulk_scrape_complete", 
                   total=len(urls), 
                   success=success_count, 
                   failed=len(urls) - success_count)
        
        return processed_results

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global scraper instance
_scraper_instance: Optional[ScraperOrchestrator] = None


def get_scraper() -> ScraperOrchestrator:
    """Get or create scraper orchestrator instance"""
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = ScraperOrchestrator()
    return _scraper_instance
