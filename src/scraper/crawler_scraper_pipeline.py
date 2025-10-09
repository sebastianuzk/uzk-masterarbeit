"""
Integrated Crawler-Scraper Pipeline
=================================

This module combines the WiSo crawler with the batch scraper to create
a complete pipeline for discovering and scraping WiSo faculty content.

Features:
- Comprehensive content discovery and extraction
- Intelligent content categorization
- Enhanced metadata enrichment
- Optimized chunking for RAG systems
- Progress tracking and reporting
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

from src.scraper.wiso_crawler import WisoCrawler, CrawlerConfig
from src.scraper.batch_scraper import BatchScraper, ScrapingConfig, ScrapedContent
from src.scraper.vector_store import VectorStore, VectorStoreConfig, VectorDocument

logger = logging.getLogger(__name__)

def categorize_url(url: str) -> str:
    """
    Categorize URL based on its path to organize content better.
    
    Args:
        url: The URL to categorize
        
    Returns:
        Category name
    """
    url_lower = url.lower()
    
    # Define category patterns
    categories = {
        'studium': ['studium', 'bachelor', 'master', 'study', 'studies', 'programme'],
        'bewerbung': ['bewerbung', 'application', 'admission', 'zulassung'],
        'fakultaet': ['fakultaet', 'faculty', 'dekanat', 'departments', 'department'],
        'forschung': ['forschung', 'research', 'publikationen', 'publications'],
        'services': ['services', 'it-services', 'support', 'beratung'],
        'international': ['international', 'ausland', 'exchange', 'abroad'],
        'pruefungen': ['pruefung', 'exam', 'klausur', 'thesis'],
        'kontakt': ['kontakt', 'contact', 'ansprechpartner'],
    }
    
    for category, keywords in categories.items():
        if any(keyword in url_lower for keyword in keywords):
            return category
    
    return 'allgemein'


def enrich_metadata(content: ScrapedContent, category: str) -> Dict[str, Any]:
    """
    Enrich scraped content metadata for better retrieval.
    
    Args:
        content: ScrapedContent object
        category: URL category
        
    Returns:
        Enhanced metadata dictionary
    """
    metadata = content.metadata.copy()
    
    # Add category
    metadata['category'] = category
    
    # Add URL path components for filtering
    parsed = urlparse(content.url)
    path_parts = [p for p in parsed.path.split('/') if p]
    metadata['url_path'] = '/'.join(path_parts)
    metadata['url_depth'] = len(path_parts)
    
    # Add language detection
    if '/de/' in content.url or '/de' in content.url:
        metadata['language'] = 'de'
    elif '/en/' in content.url or '/en' in content.url:
        metadata['language'] = 'en'
    else:
        metadata['language'] = 'unknown'
    
    # Analyze content for additional context
    content_lower = content.content.lower()
    
    # Detect specific topics
    topics = []
    topic_keywords = {
        'bewerbung': ['bewerbung', 'application', 'fristen', 'deadline'],
        'pruefung': ['prüfung', 'klausur', 'exam', 'thesis'],
        'praktikum': ['praktikum', 'internship'],
        'ausland': ['ausland', 'international', 'exchange', 'abroad'],
        'bachelor': ['bachelor'],
        'master': ['master'],
        'promotion': ['promotion', 'phd', 'doktor'],
    }
    
    for topic, keywords in topic_keywords.items():
        if any(keyword in content_lower for keyword in keywords):
            topics.append(topic)
    
    if topics:
        metadata['topics'] = topics
    
    # Add content quality indicators
    metadata['has_title'] = bool(content.title)
    metadata['content_length'] = len(content.content)
    metadata['is_substantial'] = len(content.content) > 500
    
    return metadata


async def run_crawler_scraper_pipeline(
    output_dir: Path,
    max_pages: int = 1000,
    crawl_delay: float = 1.0,
    scrape_delay: float = 1.0,
    concurrent_requests: int = 10,
    organize_by_category: bool = True
) -> Dict[str, Any]:
    """
    Run the complete crawler-scraper pipeline with enhanced features.
    
    Args:
        output_dir: Directory to store results
        max_pages: Maximum number of pages to crawl
        crawl_delay: Delay between crawler requests
        scrape_delay: Delay between scraper requests
        concurrent_requests: Number of concurrent requests
        organize_by_category: Whether to organize content by category in separate collections
        
    Returns:
        Dictionary with pipeline statistics and results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("Starting WiSo Faculty Crawler-Scraper Pipeline")
    logger.info("=" * 80)
    
    # Stage 1: Crawling
    logger.info("\n[Stage 1/4] Crawling WiSo Faculty Website...")
    crawler_config = CrawlerConfig(
        max_pages=max_pages,
        crawl_delay=crawl_delay,
        concurrent_requests=concurrent_requests
    )
    
    crawler = WisoCrawler(crawler_config)
    discovered_urls = await crawler.crawl()
    
    # Save discovered URLs
    urls_file = Path(__file__).parent / "data_analysis" / "discovered_urls.json"
    with urls_file.open('w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_urls": len(discovered_urls),
            "urls": discovered_urls
        }, f, indent=2, ensure_ascii=False)
        
    logger.info(f"✓ Discovered {len(discovered_urls)} URLs")
    
    # Stage 2: Scraping
    logger.info(f"\n[Stage 2/4] Scraping Content from {len(discovered_urls)} URLs...")
    scraping_config = ScrapingConfig(
        request_delay=scrape_delay,
        max_concurrent_requests=concurrent_requests
    )
    
    scraper = BatchScraper(scraping_config)
    scraped_data = await scraper.scrape_urls(discovered_urls)
    
    # Filter successful scrapes
    successful_scrapes = [content for content in scraped_data if content.success]
    
    # Save scraped content
    content_file = Path(__file__).parent / "data_analysis" / "scraped_data.json"
    with content_file.open('w', encoding='utf-8') as f:
        json.dump([content.__dict__ for content in scraped_data], f, indent=2, ensure_ascii=False)
        
    logger.info(f"✓ Successfully scraped {len(successful_scrapes)}/{len(scraped_data)} pages")
    
    # Stage 3: Content Categorization and Enrichment
    logger.info("\n[Stage 3/4] Categorizing and Enriching Content...")
    
    categorized_content = defaultdict(list)
    category_stats = defaultdict(int)
    
    for content in successful_scrapes:
        category = categorize_url(content.url)
        enriched_metadata = enrich_metadata(content, category)
        
        # Update content metadata
        content.metadata.update(enriched_metadata)
        
        # Organize by category
        categorized_content[category].append(content)
        category_stats[category] += 1
    
    logger.info(f"✓ Categorized content into {len(category_stats)} categories:")
    for category, count in sorted(category_stats.items()):
        logger.info(f"  - {category}: {count} pages")
    
    # Stage 4: Vector Store Integration
    logger.info("\n[Stage 4/4] Storing Content in Vector Database...")
    
    if organize_by_category:
        # Create separate collection for each category
        total_docs = 0
        for category, contents in categorized_content.items():
            if not contents:
                continue
                
            collection_name = f"wiso_{category}"
            vector_config = VectorStoreConfig(
                persist_directory=str(output_dir / "vector_db"),
                collection_name=collection_name
            )
            
            vector_store = VectorStore(vector_config)
            doc_count = vector_store.add_scraped_content(contents)
            total_docs += doc_count
            
            logger.info(f"  ✓ Stored {doc_count} documents in collection '{collection_name}'")
    else:
        # Single collection for all content
        vector_config = VectorStoreConfig(
            persist_directory=str(output_dir / "vector_db"),
            collection_name="wiso_scraped_content"
        )
        
        vector_store = VectorStore(vector_config)
        total_docs = vector_store.add_scraped_content(successful_scrapes)
        logger.info(f"  ✓ Stored {total_docs} documents in single collection")
    
    # Generate pipeline report
    pipeline_stats = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "max_pages": max_pages,
            "crawl_delay": crawl_delay,
            "scrape_delay": scrape_delay,
            "concurrent_requests": concurrent_requests,
            "organize_by_category": organize_by_category
        },
        "results": {
            "urls_discovered": len(discovered_urls),
            "pages_scraped": len(scraped_data),
            "successful_scrapes": len(successful_scrapes),
            "failed_scrapes": len(scraped_data) - len(successful_scrapes),
            "categories_found": len(category_stats),
            "category_distribution": dict(category_stats),
            "total_documents_stored": total_docs
        }
    }
    
    # Save pipeline report
    report_file = Path(__file__).parent / "data_analysis" / "pipeline_report.json"
    with report_file.open('w', encoding='utf-8') as f:
        json.dump(pipeline_stats, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "=" * 80)
    logger.info("Pipeline Completed Successfully!")
    logger.info("=" * 80)
    logger.info(f"📊 Results Summary:")
    logger.info(f"   • URLs Discovered: {len(discovered_urls)}")
    logger.info(f"   • Pages Scraped: {len(successful_scrapes)}/{len(scraped_data)}")
    logger.info(f"   • Documents Stored: {total_docs}")
    logger.info(f"   • Categories: {len(category_stats)}")
    logger.info(f"   • Report saved to: {report_file}")
    logger.info("=" * 80)
    
    return pipeline_stats


def main():
    """Command line interface for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="WiSo Faculty Crawler-Scraper Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings
  python crawler_scraper_pipeline.py
  
  # Run with custom settings
  python crawler_scraper_pipeline.py --max-pages 500 --crawl-delay 2.0
  
  # Organize content by category
  python crawler_scraper_pipeline.py --organize-by-category
  
  # Fast mode (more concurrent requests, less delay)
  python crawler_scraper_pipeline.py --concurrent-requests 20 --crawl-delay 0.5
        """
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory to store results (default: data)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=1000,
        help="Maximum number of pages to crawl (default: 1000)"
    )
    parser.add_argument(
        "--crawl-delay",
        type=float,
        default=1.0,
        help="Delay between crawler requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--scrape-delay",
        type=float,
        default=1.0,
        help="Delay between scraper requests in seconds (default: 1.0)"
    )
    parser.add_argument(
        "--concurrent-requests",
        type=int,
        default=10,
        help="Number of concurrent requests (default: 10)"
    )
    parser.add_argument(
        "--organize-by-category",
        action="store_true",
        help="Organize content into separate collections by category"
    )
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Set logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Run pipeline
    try:
        stats = asyncio.run(run_crawler_scraper_pipeline(
            output_dir=args.output_dir,
            max_pages=args.max_pages,
            crawl_delay=args.crawl_delay,
            scrape_delay=args.scrape_delay,
            concurrent_requests=args.concurrent_requests,
            organize_by_category=args.organize_by_category
        ))
        
        print("\n✅ Pipeline completed successfully!")
        print(f"📁 Results saved to: {args.output_dir}")
        
    except KeyboardInterrupt:
        print("\n⚠️  Pipeline interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n❌ Pipeline failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    main()