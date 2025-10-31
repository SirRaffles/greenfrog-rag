#!/usr/bin/env python3
"""
Website Scraper for The Matcha Initiative
Scrapes website content and saves incrementally based on content hashing
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import aiofiles
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel

# Configuration
BASE_URL = os.getenv("TARGET_WEBSITE", "https://www.thematchainitiative.com")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/data/matchainitiative"))
STATE_FILE = Path(os.getenv("STATE_FILE", "/data/state/scraper_state.json"))
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY_SECONDS", "1.0"))
USER_AGENT = os.getenv("USER_AGENT", "GreenFrog-Bot/1.0 (Sustainability Content Aggregator)")

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PageState(BaseModel):
    """State tracking for a single page"""
    url: str
    content_hash: str
    last_scraped: datetime
    status: str  # "success", "failed", "skipped"
    file_path: Optional[str] = None


class ScraperState(BaseModel):
    """Overall scraper state"""
    last_run: Optional[datetime] = None
    pages: Dict[str, PageState] = {}
    total_pages: int = 0
    successful_pages: int = 0
    failed_pages: int = 0
    new_pages: int = 0
    updated_pages: int = 0


class MatchaScraper:
    """Main scraper class for The Matcha Initiative"""

    def __init__(self):
        self.base_url = BASE_URL
        self.output_dir = OUTPUT_DIR
        self.state_file = STATE_FILE
        self.state = self._load_state()
        self.visited_urls: Set[str] = set()
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)

        # Create output directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        )

    def _load_state(self) -> ScraperState:
        """Load scraper state from disk"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                return ScraperState(**data)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
                return ScraperState()
        return ScraperState()

    async def _save_state(self):
        """Save scraper state to disk"""
        try:
            async with aiofiles.open(self.state_file, 'w') as f:
                await f.write(self.state.model_dump_json(indent=2))
            logger.info(f"State saved to {self.state_file}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison"""
        parsed = urlparse(url)
        # Remove fragments and trailing slashes
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
        if parsed.query:
            normalized += f"?{parsed.query}"
        return normalized

    def _is_valid_url(self, url: str) -> bool:
        """Check if URL should be scraped"""
        parsed = urlparse(url)

        # Must be same domain
        if parsed.netloc and parsed.netloc not in self.base_url:
            return False

        # Skip common non-content URLs
        skip_patterns = [
            r'/wp-admin/', r'/wp-content/', r'/wp-json/',
            r'\.(jpg|jpeg|png|gif|svg|ico|css|js|woff|woff2|ttf)$',
            r'/feed/', r'/rss/', r'/xmlrpc\.php',
            r'#', r'mailto:', r'tel:',
        ]

        for pattern in skip_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False

        return True

    def _extract_links(self, soup: BeautifulSoup, current_url: str) -> Set[str]:
        """Extract all valid links from page"""
        links = set()

        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            absolute_url = urljoin(current_url, href)
            normalized_url = self._normalize_url(absolute_url)

            if self._is_valid_url(normalized_url):
                links.add(normalized_url)

        return links

    def _extract_content(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract main content from page"""
        content = {
            "title": "",
            "description": "",
            "text": "",
            "metadata": {}
        }

        # Extract title
        if soup.title:
            content["title"] = soup.title.string.strip()

        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            content["description"] = meta_desc['content'].strip()

        # Extract Open Graph metadata
        og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
        for tag in og_tags:
            key = tag.get('property', '').replace('og:', '')
            value = tag.get('content', '')
            if key and value:
                content["metadata"][key] = value

        # Extract main content (remove scripts, styles, nav, footer)
        for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # Try to find main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main|post'))

        if main_content:
            # Extract text while preserving structure
            paragraphs = main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
            content["text"] = "\n\n".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        else:
            # Fallback: extract all text from body
            body = soup.find('body')
            if body:
                content["text"] = body.get_text(separator='\n', strip=True)

        return content

    def _get_file_path(self, url: str) -> Path:
        """Generate file path for URL"""
        parsed = urlparse(url)
        path = parsed.path.strip('/') or 'index'

        # Remove file extensions and clean path
        path = re.sub(r'\.(html|htm|php)$', '', path)
        path = re.sub(r'[^a-zA-Z0-9/_-]', '_', path)

        # Create subdirectory structure
        parts = path.split('/')
        if len(parts) > 1:
            subdir = self.output_dir / '/'.join(parts[:-1])
            subdir.mkdir(parents=True, exist_ok=True)

        return self.output_dir / f"{path}.json"

    async def _scrape_page(self, url: str) -> Optional[PageState]:
        """Scrape a single page"""
        async with self.semaphore:
            try:
                logger.info(f"Scraping: {url}")

                # Rate limiting
                await asyncio.sleep(REQUEST_DELAY)

                # Fetch page
                response = await self.client.get(url)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'lxml')

                # Extract content
                content = self._extract_content(soup)
                content["url"] = url
                content["scraped_at"] = datetime.now().isoformat()

                # Compute content hash
                content_json = json.dumps(content, sort_keys=True)
                content_hash = self._compute_content_hash(content_json)

                # Check if content has changed
                existing_state = self.state.pages.get(url)
                if existing_state and existing_state.content_hash == content_hash:
                    logger.info(f"  → No changes detected, skipping")
                    return PageState(
                        url=url,
                        content_hash=content_hash,
                        last_scraped=datetime.now(),
                        status="skipped",
                        file_path=existing_state.file_path
                    )

                # Save content to file
                file_path = self._get_file_path(url)
                async with aiofiles.open(file_path, 'w') as f:
                    await f.write(json.dumps(content, indent=2))

                # Extract links for crawling
                links = self._extract_links(soup, url)
                for link in links:
                    if link not in self.visited_urls:
                        self.visited_urls.add(link)

                logger.info(f"  ✓ Saved to {file_path.relative_to(self.output_dir)}")

                return PageState(
                    url=url,
                    content_hash=content_hash,
                    last_scraped=datetime.now(),
                    status="success",
                    file_path=str(file_path.relative_to(self.output_dir))
                )

            except httpx.HTTPStatusError as e:
                logger.error(f"  ✗ HTTP error {e.response.status_code}: {url}")
                return PageState(
                    url=url,
                    content_hash="",
                    last_scraped=datetime.now(),
                    status="failed"
                )
            except Exception as e:
                logger.error(f"  ✗ Error scraping {url}: {e}")
                return PageState(
                    url=url,
                    content_hash="",
                    last_scraped=datetime.now(),
                    status="failed"
                )

    async def run(self):
        """Main scraper execution"""
        logger.info("=" * 80)
        logger.info("GreenFrog Matcha Initiative Scraper")
        logger.info("=" * 80)
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info(f"Max concurrent requests: {MAX_CONCURRENT}")
        logger.info(f"Request delay: {REQUEST_DELAY}s")
        logger.info("")

        start_time = time.time()

        # Start with homepage
        self.visited_urls.add(self.base_url)

        # Process URLs iteratively (breadth-first)
        urls_to_process = list(self.visited_urls)
        processed_urls = set()

        while urls_to_process:
            current_batch = urls_to_process[:MAX_CONCURRENT * 2]  # Process in batches
            urls_to_process = urls_to_process[MAX_CONCURRENT * 2:]

            # Scrape current batch
            tasks = []
            for url in current_batch:
                if url not in processed_urls:
                    tasks.append(self._scrape_page(url))
                    processed_urls.add(url)

            if tasks:
                results = await asyncio.gather(*tasks)

                # Update state
                for result in results:
                    if result:
                        old_state = self.state.pages.get(result.url)
                        self.state.pages[result.url] = result

                        if result.status == "success":
                            self.state.successful_pages += 1
                            if not old_state:
                                self.state.new_pages += 1
                            elif old_state.content_hash != result.content_hash:
                                self.state.updated_pages += 1
                        elif result.status == "failed":
                            self.state.failed_pages += 1

            # Add newly discovered URLs
            new_urls = [url for url in self.visited_urls if url not in processed_urls and url not in urls_to_process]
            urls_to_process.extend(new_urls)

        # Update final state
        self.state.total_pages = len(processed_urls)
        self.state.last_run = datetime.now()
        await self._save_state()

        # Close HTTP client
        await self.client.aclose()

        # Print summary
        elapsed_time = time.time() - start_time
        logger.info("")
        logger.info("=" * 80)
        logger.info("SCRAPING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total pages processed: {self.state.total_pages}")
        logger.info(f"  → Successful: {self.state.successful_pages}")
        logger.info(f"  → Failed: {self.state.failed_pages}")
        logger.info(f"  → New pages: {self.state.new_pages}")
        logger.info(f"  → Updated pages: {self.state.updated_pages}")
        logger.info(f"Elapsed time: {elapsed_time:.2f}s")
        logger.info(f"Output directory: {self.output_dir}")
        logger.info("=" * 80)


async def main():
    """Main entry point"""
    scraper = MatchaScraper()
    await scraper.run()


if __name__ == "__main__":
    asyncio.run(main())
