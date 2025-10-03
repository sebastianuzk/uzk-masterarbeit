"""
Integrated Crawler-Scraper Pipeline
=================================

This module combines the WiSo crawler with the batch scraper to create
a complete pipeline for discovering and scraping WiSo faculty content.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

import hashlib
from src.scraper.wiso_crawler import WisoCrawler, CrawlerConfig
from src.scraper.batch_scraper import BatchScraper, ScrapingConfig
from src.scraper.vector_store import VectorStore, VectorStoreConfig, VectorDocument

logger = logging.getLogger(__name__)

async def run_crawler_scraper_pipeline(
    output_dir: Path,
    max_pages: int = 1000,
    crawl_delay: float = 1.0,
    scrape_delay: float = 1.0,
    concurrent_requests: int = 10
) -> None:
    """
    Run the complete crawler-scraper pipeline.
    
    Args:
        output_dir: Directory to store results
        max_pages: Maximum number of pages to crawl
        crawl_delay: Delay between crawler requests
        scrape_delay: Delay between scraper requests
        concurrent_requests: Number of concurrent requests
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure and run crawler
    crawler_config = CrawlerConfig(
        max_pages=max_pages,
        crawl_delay=crawl_delay,
        concurrent_requests=concurrent_requests
    )
    
    crawler = WisoCrawler(crawler_config)
    discovered_urls = await crawler.crawl()
    
    # Save discovered URLs in the data_analysis directory
    urls_file = Path(__file__).parent / "data_analysis" / "discovered_urls.json"
    with urls_file.open('w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_urls": len(discovered_urls),
            "urls": discovered_urls
        }, f, indent=2, ensure_ascii=False)
        
    logger.info(f"Discovered {len(discovered_urls)} URLs")
    
    # Configure and run scraper
    scraping_config = ScrapingConfig(
        request_delay=scrape_delay,
        max_concurrent_requests=concurrent_requests
    )
    
    scraper = BatchScraper(scraping_config)
    scraped_data = await scraper.scrape_urls(discovered_urls)
    
    # Save scraped content to the standard location
    content_file = Path(__file__).parent / "data_analysis" / "scraped_data.json"
    with content_file.open('w', encoding='utf-8') as f:
        json.dump([content.__dict__ for content in scraped_data], f, indent=2, ensure_ascii=False)
        
    logger.info(f"Scraped {len(scraped_data)} pages saved to {content_file}")
    
    # Initialize vector store
    vector_config = VectorStoreConfig(
        persist_directory=str(output_dir / "vector_db")
    )
    
    vector_store = VectorStore(vector_config)
    
    # Add scraped content to vector store
    vector_store.add_scraped_content(scraped_data)
    
    logger.info("Pipeline completed successfully")

def main():
    """Command line interface for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WiSo Faculty Crawler-Scraper Pipeline")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory to store results"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1000,
        help="Maximum number of pages to crawl"
    )
    parser.add_argument(
        "--crawl-delay",
        type=float,
        default=1.0,
        help="Delay between crawler requests"
    )
    parser.add_argument(
        "--scrape-delay",
        type=float,
        default=1.0,
        help="Delay between scraper requests"
    )
    parser.add_argument(
        "--concurrent-requests",
        type=int,
        default=10,
        help="Number of concurrent requests"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run pipeline
    asyncio.run(run_crawler_scraper_pipeline(
        output_dir=args.output_dir,
        max_pages=args.max_pages,
        crawl_delay=args.crawl_delay,
        scrape_delay=args.scrape_delay,
        concurrent_requests=args.concurrent_requests
    ))

if __name__ == "__main__":
    main()