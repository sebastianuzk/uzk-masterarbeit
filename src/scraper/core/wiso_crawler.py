"""
WISO Faculty Web Crawler
=======================

This module implements a focused web crawler for the WiSo faculty website.
It discovers and extracts all relevant URLs while respecting common crawling
etiquette and robots.txt rules.

Features:
- Focused crawling of WiSo faculty domain
- Respects robots.txt and crawl delays
- Filters for relevant content pages
- Integrates with batch scraper
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict, Optional
import re
import logging
from pathlib import Path
import json
import time
import robotexclusionrulesparser
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class CrawlerConfig:
    """Configuration for the WiSo crawler."""
    seed_url: str = "https://wiso.uni-koeln.de/"
    allowed_domains: Set[str] = None
    max_pages: int = 6000
    crawl_delay: float = 2.0  # Erhöht von 1.0 auf 2.0 - verhindert Blockierung
    max_depth: int = 5
    concurrent_requests: int = 5  # Reduziert von 10 auf 5 - weniger aggressiv
    
    def __post_init__(self):
        if self.allowed_domains is None:
            self.allowed_domains = {
                "wiso.uni-koeln.de",
                "verwaltung.uni-koeln.de"
            }

class WisoCrawler:
    """Crawler implementation for WiSo faculty website."""
    
    def __init__(self, config: CrawlerConfig):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.queue: Set[str] = {config.seed_url}
        self.found_urls: Set[str] = set()
        self.pdf_urls: Set[str] = set()  # Separate collection for PDFs
        self.robots_parser = robotexclusionrulesparser.RobotFileParserLookalike()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def init_session(self):
        """Initialize aiohttp session and robots.txt parser."""
        if self.session is None:
            # Add realistic headers to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            # Add timeout and connector settings for better stability
            # Disable SSL verification to avoid handshake issues
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            connector = aiohttp.TCPConnector(
                limit=5, 
                limit_per_host=3, 
                ssl=False,  # Disable SSL verification
                force_close=True  # Close connections after each request
            )
            self.session = aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout,
                connector=connector
            )
            
        # Fetch and parse robots.txt
        try:
            robots_url = urljoin(self.config.seed_url, "/robots.txt")
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    self.robots_parser.parse(robots_content.splitlines())
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt: {e}")

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

    def is_allowed_url(self, url: str) -> bool:
        """Check if URL should be crawled based on domain and robots.txt."""
        parsed = urlparse(url)
        
        # Check domain
        if parsed.netloc not in self.config.allowed_domains:
            return False
            
        # Check robots.txt
        if not self.robots_parser.is_allowed("*", url):
            return False
            
        # Filter out non-HTML resources and certain patterns (but keep PDFs!)
        excluded_patterns = [
            r'\.(jpg|jpeg|png|gif|css|js|ico|xml)$',  # Removed pdf from here
            r'(calendar|print|rss|feed)',
            r'/(de|en)/api/',
        ]
        
        url_lower = url.lower()
        return not any(re.search(pattern, url_lower) for pattern in excluded_patterns)

    async def extract_links(self, url: str, html: str) -> Set[str]:
        """Extract and normalize links from HTML content."""
        links = set()
        soup = BeautifulSoup(html, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(url, href)
            
            # Normalize URL
            parsed = urlparse(absolute_url)
            normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized_url += f"?{parsed.query}"
            
            # Check if it's a PDF
            if normalized_url.lower().endswith('.pdf'):
                # Add to PDF collection
                if parsed.netloc in self.config.allowed_domains:
                    self.pdf_urls.add(normalized_url)
                    logger.debug(f"Found PDF: {normalized_url}")
            elif self.is_allowed_url(normalized_url):
                links.add(normalized_url)
                
        return links

    async def crawl_page(self, url: str) -> Set[str]:
        """Crawl a single page and extract links."""
        if not self.session:
            await self.init_session()
        
        # Add delay to respect server
        await asyncio.sleep(self.config.crawl_delay)
            
        try:
            async with self.session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    html = await response.text()
                    links = await self.extract_links(url, html)
                    self.found_urls.add(url)
                    return links
                else:
                    logger.warning(f"Failed to fetch {url}: Status {response.status}")
        except asyncio.TimeoutError:
            logger.error(f"Timeout crawling {url}")
        except aiohttp.ClientError as e:
            logger.error(f"Client error crawling {url}: {e}")
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
        
        return set()

    async def crawl(self) -> List[str]:
        """Main crawling loop."""
        try:
            await self.init_session()
            tasks = set()
            
            while self.queue and len(self.found_urls) < self.config.max_pages:
                # Respect crawl delay
                await asyncio.sleep(self.config.crawl_delay)
                
                # Get next URL to crawl
                url = self.queue.pop()
                if url in self.visited_urls:
                    continue
                    
                self.visited_urls.add(url)
                
                # Crawl page and extract links
                new_links = await self.crawl_page(url)
                
                # Add new links to queue
                for link in new_links:
                    if link not in self.visited_urls:
                        self.queue.add(link)
                        
                logger.info(f"Crawled: {url} | Queue: {len(self.queue)} | Found: {len(self.found_urls)}")
                
            return list(self.found_urls)
            
        finally:
            await self.close()

async def crawl_wiso_faculty() -> List[str]:
    """Helper function to run the crawler with default configuration."""
    config = CrawlerConfig()
    crawler = WisoCrawler(config)
    return await crawler.crawl()

def save_urls_to_file(urls: List[str], output_file: str):
    """Save discovered URLs to a JSON file."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "total_urls": len(urls),
        "urls": urls
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Run crawler
    urls = asyncio.run(crawl_wiso_faculty())
    
    # Save results
    output_file = Path(__file__).parent / "discovered_urls.json"
    save_urls_to_file(urls, str(output_file))
    print(f"Discovered {len(urls)} URLs. Results saved to {output_file}")