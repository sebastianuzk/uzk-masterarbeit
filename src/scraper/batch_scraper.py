"""
Batch Web Scraper for RAG Data Collection
=========================================

This module provides comprehensive web scraping capabilities for collecting
data to feed into a RAG system. It supports multiple URL processing,
content extraction, and data structuring for vector database storage.

Features:
- Batch processing of multiple URLs
- Configurable content extraction
- Error handling and retry logic
- Progress tracking
- Structured data output for vector storage
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Any, Callable
import json
import time
from datetime import datetime
import logging
from pathlib import Path


@dataclass
class ScrapedContent:
    """Data structure for scraped web content."""
    url: str
    title: str
    content: str
    metadata: Dict[str, Any]
    timestamp: str
    success: bool
    error_message: Optional[str] = None


@dataclass
class ScrapingConfig:
    """Configuration for web scraping operations."""
    max_concurrent_requests: int = 10
    request_delay: float = 1.0
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 2.0
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    headers: Dict[str, str] = None
    content_selectors: Dict[str, str] = None
    exclude_selectors: List[str] = None


class BatchScraper:
    """
    Batch web scraper for collecting data for RAG systems.
    
    This scraper processes multiple URLs asynchronously, extracts content,
    and structures it for vector database storage.
    """
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Initialize the batch scraper.
        
        Args:
            config: Scraping configuration. Uses defaults if None.
        """
        self.config = config or ScrapingConfig()
        self.logger = self._setup_logger()
        self.results: List[ScrapedContent] = []
        
        # Default content selectors
        if not self.config.content_selectors:
            self.config.content_selectors = {
                'title': 'title, h1',
                'content': 'article, main, .content, .post, p',
                'description': 'meta[name="description"]',
                'keywords': 'meta[name="keywords"]'
            }
        
        # Default exclude selectors
        if not self.config.exclude_selectors:
            self.config.exclude_selectors = [
                'script', 'style', 'nav', 'footer', 'header',
                '.advertisement', '.ads', '.sidebar'
            ]
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the scraper."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def scrape_urls(self, urls: List[str], 
                         progress_callback: Optional[Callable] = None) -> List[ScrapedContent]:
        """
        Scrape multiple URLs asynchronously.
        
        Args:
            urls: List of URLs to scrape
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List of ScrapedContent objects
        """
        self.logger.info(f"Starting batch scraping of {len(urls)} URLs")
        
        semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers={'User-Agent': self.config.user_agent}
        ) as session:
            
            tasks = [
                self._scrape_single_url(session, url, semaphore, progress_callback)
                for url in urls
            ]
            
            self.results = await asyncio.gather(*tasks, return_exceptions=False)
        
        successful = sum(1 for result in self.results if result.success)
        self.logger.info(f"Scraping completed: {successful}/{len(urls)} successful")
        
        return self.results
    
    async def _scrape_single_url(self, session: aiohttp.ClientSession, url: str,
                                semaphore: asyncio.Semaphore,
                                progress_callback: Optional[Callable] = None) -> ScrapedContent:
        """
        Scrape a single URL with retry logic.
        
        Args:
            session: aiohttp session
            url: URL to scrape
            semaphore: Concurrency control
            progress_callback: Optional progress callback
            
        Returns:
            ScrapedContent object
        """
        async with semaphore:
            for attempt in range(self.config.retry_attempts):
                try:
                    await asyncio.sleep(self.config.request_delay)
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            html = await response.text()
                            content = self._extract_content(html, url)
                            
                            if progress_callback:
                                progress_callback(url, True, None)
                            
                            return content
                        else:
                            raise aiohttp.ClientError(f"HTTP {response.status}")
                
                except Exception as e:
                    self.logger.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}")
                    
                    if attempt < self.config.retry_attempts - 1:
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                    else:
                        if progress_callback:
                            progress_callback(url, False, str(e))
                        
                        return ScrapedContent(
                            url=url,
                            title="",
                            content="",
                            metadata={},
                            timestamp=datetime.now().isoformat(),
                            success=False,
                            error_message=str(e)
                        )
    
    def _extract_content(self, html: str, url: str) -> ScrapedContent:
        """
        Extract structured content from HTML.
        
        Args:
            html: Raw HTML content
            url: Source URL
            
        Returns:
            ScrapedContent object
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove unwanted elements
        for selector in self.config.exclude_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Extract title
        title_element = soup.select_one(self.config.content_selectors['title'])
        title = title_element.get_text(strip=True) if title_element else ""
        
        # Extract main content
        content_elements = soup.select(self.config.content_selectors['content'])
        content_texts = [elem.get_text(strip=True) for elem in content_elements]
        content = '\n\n'.join(text for text in content_texts if text)
        
        # Extract metadata
        metadata = self._extract_metadata(soup, url)
        
        return ScrapedContent(
            url=url,
            title=title,
            content=content,
            metadata=metadata,
            timestamp=datetime.now().isoformat(),
            success=True
        )
    
    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract metadata from the HTML document.
        
        Args:
            soup: BeautifulSoup object
            url: Source URL
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {
            'domain': urlparse(url).netloc,
            'word_count': 0,
            'links': [],
            'images': [],
        }
        
        # Extract description
        desc_element = soup.select_one(self.config.content_selectors['description'])
        if desc_element:
            metadata['description'] = desc_element.get('content', '')
        
        # Extract keywords
        keywords_element = soup.select_one(self.config.content_selectors['keywords'])
        if keywords_element:
            metadata['keywords'] = keywords_element.get('content', '').split(',')
        
        # Count words in main content
        content_text = soup.get_text()
        metadata['word_count'] = len(content_text.split()) if content_text else 0
        
        # Extract links
        for link in soup.find_all('a', href=True):
            full_url = urljoin(url, link['href'])
            metadata['links'].append({
                'url': full_url,
                'text': link.get_text(strip=True)
            })
        
        # Extract images
        for img in soup.find_all('img', src=True):
            full_url = urljoin(url, img['src'])
            metadata['images'].append({
                'url': full_url,
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            })
        
        return metadata
    
    def save_results(self, filepath: str, format: str = 'json') -> None:
        """
        Save scraping results to file.
        
        Args:
            filepath: Output file path
            format: Output format ('json' or 'jsonl')
        """
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump([asdict(result) for result in self.results], f, 
                         ensure_ascii=False, indent=2)
        
        elif format == 'jsonl':
            with open(filepath, 'w', encoding='utf-8') as f:
                for result in self.results:
                    json.dump(asdict(result), f, ensure_ascii=False)
                    f.write('\n')
        
        self.logger.info(f"Results saved to {filepath}")
    
    def get_successful_results(self) -> List[ScrapedContent]:
        """Get only successful scraping results."""
        return [result for result in self.results if result.success]
    
    def get_failed_results(self) -> List[ScrapedContent]:
        """Get only failed scraping results."""
        return [result for result in self.results if not result.success]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get scraping statistics."""
        total = len(self.results)
        successful = len(self.get_successful_results())
        failed = len(self.get_failed_results())
        
        if successful > 0:
            avg_content_length = sum(
                len(result.content) for result in self.get_successful_results()
            ) / successful
            
            total_words = sum(
                result.metadata.get('word_count', 0) 
                for result in self.get_successful_results()
            )
        else:
            avg_content_length = 0
            total_words = 0
        
        return {
            'total_urls': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'avg_content_length': avg_content_length,
            'total_words': total_words,
            'unique_domains': len(set(
                result.metadata.get('domain', '') 
                for result in self.get_successful_results()
            ))
        }


# Example usage and CLI interface
if __name__ == "__main__":
    import argparse
    
    def progress_callback(url: str, success: bool, error: Optional[str]):
        status = "✓" if success else "✗"
        print(f"{status} {url}")
        if error:
            print(f"  Error: {error}")
    
    async def main():
        parser = argparse.ArgumentParser(description="Batch Web Scraper for RAG")
        parser.add_argument('urls', nargs='+', help='URLs to scrape')
        parser.add_argument('--output', '-o', default='scraped_data.json', 
                          help='Output file path')
        parser.add_argument('--format', choices=['json', 'jsonl'], default='json',
                          help='Output format')
        parser.add_argument('--concurrent', '-c', type=int, default=10,
                          help='Max concurrent requests')
        parser.add_argument('--delay', '-d', type=float, default=1.0,
                          help='Delay between requests')
        
        args = parser.parse_args()
        
        config = ScrapingConfig(
            max_concurrent_requests=args.concurrent,
            request_delay=args.delay
        )
        
        scraper = BatchScraper(config)
        
        # Run scraping
        results = await scraper.scrape_urls(args.urls, progress_callback)
        
        # Save results
        scraper.save_results(args.output, args.format)
        
        # Print statistics
        stats = scraper.get_statistics()
        print(f"\nScraping Statistics:")
        print(f"Total URLs: {stats['total_urls']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        print(f"Success Rate: {stats['success_rate']:.2%}")
        print(f"Average Content Length: {stats['avg_content_length']:.0f} chars")
        print(f"Total Words: {stats['total_words']}")
        print(f"Unique Domains: {stats['unique_domains']}")
    
    asyncio.run(main())