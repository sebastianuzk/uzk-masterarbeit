"""
Integrated Crawler-Scraper Pipeline
=================================

This module combines the WiSo crawler with the batch scraper to create
a complete pipeline for discovering and scraping WiSo faculty content.

Features:
- NAIVE RAG MODE (default): Basic crawling + scraping + simple chunking
- ADVANCED RAG MODE (configurable): All optimizations via scraper.env

Modes:
- Naive: Pure content extraction without optimizations
- Advanced: Intelligent categorization, deduplication, semantic chunking, etc.
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

# Core modules (always needed)
from src.scraper.core.wiso_crawler import WisoCrawler, CrawlerConfig
from src.scraper.core.batch_scraper import BatchScraper, ScrapingConfig, ScrapedContent
from src.scraper.core.vector_store import VectorStore, VectorStoreConfig, VectorDocument
from src.scraper.utils.pdf_extractor import PDFExtractor, PDFContent

# Configuration system
from src.scraper.config import ScraperConfig, load_scraper_config

# Advanced features (only imported if needed)
try:
    from src.scraper.utils.url_cache import URLCache
except ImportError:
    URLCache = None
    
try:
    from src.scraper.utils.content_deduplicator import ContentDeduplicator
except ImportError:
    ContentDeduplicator = None
    
try:
    from src.scraper.utils.content_cleaner import ContentCleaner
except ImportError:
    ContentCleaner = None
    
try:
    from src.scraper.utils.semantic_chunker import SemanticChunker
except ImportError:
    SemanticChunker = None
    
try:
    from src.scraper.analysis.scraper_metrics import ScraperMetrics
except ImportError:
    ScraperMetrics = None
    
try:
    from src.scraper.core.resilient_scraper import ResilientScraper, RetryConfig
except ImportError:
    ResilientScraper = None
    RetryConfig = None
    
try:
    from src.scraper.core.incremental_scraper import IncrementalScraper
except ImportError:
    IncrementalScraper = None

logger = logging.getLogger(__name__)


def simple_categorize_url(url: str) -> str:
    """
    Simple URL categorization for Naive RAG mode.
    
    Args:
        url: The URL to categorize
        
    Returns:
        Category name
    """
    url_lower = url.lower()
    
    # Simple pattern matching
    if 'bewerbung' in url_lower:
        return 'bewerbung'
    elif 'studium' in url_lower or 'bachelor' in url_lower or 'master' in url_lower:
        return 'studium'
    elif 'forschung' in url_lower or 'research' in url_lower:
        return 'forschung'
    elif 'fakultaet' in url_lower or 'dekanat' in url_lower:
        return 'fakultaet'
    elif 'pruefung' in url_lower or 'exam' in url_lower:
        return 'pruefungen'
    else:
        return 'allgemein'


def advanced_categorize_url(url: str) -> str:
    """
    Advanced URL categorization for Advanced RAG mode.
    
    Args:
        url: The URL to categorize
        
    Returns:
        Category name
    """
    url_lower = url.lower()
    
    # Definiere erweiterte Kategorie-Muster
    categories = {
        'studium': ['studium', 'bachelor', 'master', 'study', 'studies', 'programme'],
        'bewerbung': ['bewerbung', 'application', 'admission', 'zulassung'],
        'fakultaet': ['fakultaet', 'faculty', 'dekanat', 'departments', 'department'],
        'forschung': ['forschung', 'research', 'publikationen', 'publications'],
        'services': ['services', 'it-services', 'support', 'beratung'],
        'international': ['international', 'ausland', 'exchange', 'abroad'],
        'pruefungen': ['pruefung', 'exam', 'klausur', 'thesis'],
        'pruefungsordnungen': ['pruefungsordnung', 'po-', 'po_', 'modulhandbuch'],
        'kontakt': ['kontakt', 'contact', 'ansprechpartner'],
    }
    
    for category, keywords in categories.items():
        if any(keyword in url_lower for keyword in keywords):
            return category
    
    return 'allgemein'


def simple_chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[Dict[str, Any]]:
    """
    Simple text chunking for Naive RAG mode.
    
    Args:
        text: Text to chunk
        chunk_size: Size of each chunk
        overlap: Overlap between chunks
        
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [{'text': text, 'chunk_index': 0, 'total_chunks': 1}]
    
    chunks = []
    start = 0
    chunk_index = 0
    
    while start < len(text):
        end = start + chunk_size
        if end > len(text):
            end = len(text)
        
        chunk_text = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk_text.rfind('.')
            if last_period > chunk_size // 2:  # Only if it's not too short
                end = start + last_period + 1
                chunk_text = text[start:end]
        
        chunks.append({
            'text': chunk_text.strip(),
            'chunk_index': chunk_index,
            'total_chunks': 0  # Will be filled later
        })
        
        start = end - overlap if end < len(text) else end
        chunk_index += 1
    
    # Update total chunks
    for chunk in chunks:
        chunk['total_chunks'] = len(chunks)
    
    return chunks


def simple_enrich_metadata(content: ScrapedContent, category: str) -> Dict[str, Any]:
    """
    Simple metadata enrichment for Naive RAG mode.
    
    Args:
        content: ScrapedContent object
        category: URL category
        
    Returns:
        Basic metadata dictionary
    """
    metadata = content.metadata.copy()
    
    # Add basic category
    metadata['category'] = category
    
    # Add basic URL info
    parsed = urlparse(content.url)
    metadata['url_path'] = parsed.path
    
    # Add basic content info
    metadata['has_title'] = bool(content.title)
    metadata['content_length'] = len(content.content)
    
    return metadata


async def run_crawler_scraper_pipeline(
    output_dir: Path,
    max_pages: int = 1000,
    crawl_delay: float = 1.0,
    scrape_delay: float = 1.0,
    concurrent_requests: int = 10,
    config_file: str = "scraper.env"
) -> Dict[str, Any]:
    """
    Run the complete crawler-scraper pipeline in Naive or Advanced RAG mode.
    
    Args:
        output_dir: Directory to store results
        max_pages: Maximum number of pages to crawl
        crawl_delay: Delay between crawler requests
        scrape_delay: Delay between scraper requests
        concurrent_requests: Number of concurrent requests
        config_file: Path to scraper configuration file
        
    Returns:
        Dictionary with pipeline statistics and results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load configuration from scraper.env
    config = load_scraper_config(config_file)
    config.log_configuration()
    
    logger.info("=" * 80)
    if config.is_naive_mode():
        logger.info("Starting WiSo Faculty Crawler-Scraper Pipeline (NAIVE RAG MODE)")
    else:
        logger.info("Starting WiSo Faculty Crawler-Scraper Pipeline (ADVANCED RAG MODE)")
    logger.info("=" * 80)
    
    # Choose functions based on mode
    if config.is_naive_mode():
        categorize_func = simple_categorize_url
        enrich_func = simple_enrich_metadata
        chunk_func = simple_chunk_text
    else:
        categorize_func = advanced_categorize_url
        enrich_func = simple_enrich_metadata  # Keep simple for now, can be enhanced
        chunk_func = simple_chunk_text  # Will be replaced with semantic chunking if enabled
    
    # Initialize enhancement modules (only if enabled)
    url_cache = None
    deduplicator = None
    content_cleaner = None
    semantic_chunker = None
    metrics = None
    resilient_scraper = None
    incremental_scraper = None
    
    if config.enable_caching and URLCache:
        url_cache = URLCache(str(output_dir / "url_cache.db"))
        logger.info("✅ Intelligent caching enabled")
    
    if config.enable_deduplication and ContentDeduplicator:
        deduplicator = ContentDeduplicator()
        logger.info("✅ Content deduplication enabled")
    
    if config.enable_content_cleaning and ContentCleaner:
        content_cleaner = ContentCleaner()
        logger.info("✅ Content cleaning enabled")
    
    if config.enable_semantic_chunking and SemanticChunker:
        semantic_chunker = SemanticChunker()
        chunk_func = semantic_chunker.chunk_document
        logger.info("✅ Semantic chunking enabled")
    
    if config.enable_detailed_metrics and ScraperMetrics:
        metrics = ScraperMetrics()
        logger.info("✅ Detailed metrics enabled")
    
    if config.enable_resilient_scraping and ResilientScraper and RetryConfig:
        retry_config = RetryConfig(
            max_retries=config.max_retries,
            initial_delay=config.initial_retry_delay,
            max_delay=config.max_retry_delay,
            exponential_base=2.0
        )
        resilient_scraper = ResilientScraper(retry_config)
        logger.info(f"✅ Resilient scraping enabled (max {config.max_retries} retries)")
    
    if config.enable_incremental_scraping and IncrementalScraper and url_cache:
        incremental_scraper = IncrementalScraper(url_cache)
        logger.info("✅ Incremental scraping enabled")
    
    # Stage 1: Crawling
    logger.info("\n[Stage 1/4] Crawling WiSo Faculty Website...")
    crawler_config = CrawlerConfig(
        max_pages=max_pages,
        crawl_delay=crawl_delay,
        concurrent_requests=concurrent_requests
    )
    
    crawler = WisoCrawler(crawler_config)
    discovered_urls = await crawler.crawl()
    
    # Debug mode URL limiting
    if config.debug_max_urls > 0:
        discovered_urls = discovered_urls[:config.debug_max_urls]
        logger.info(f"🐛 Debug mode: Limited to {len(discovered_urls)} URLs")
    
    # Save discovered URLs
    urls_file = output_dir / "discovered_urls.json"
    with urls_file.open('w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_urls": len(discovered_urls),
            "urls": discovered_urls
        }, f, indent=2, ensure_ascii=False)
        
    logger.info(f"✓ Discovered {len(discovered_urls)} URLs")
    logger.info(f"✓ Found {len(crawler.pdf_urls)} PDF documents")
    
    # Dry run mode
    if config.dry_run:
        logger.info("🐛 Dry run mode: Stopping after crawling")
        return {"mode": "dry_run", "urls_discovered": len(discovered_urls), "pdfs_found": len(crawler.pdf_urls)}
    
    # Stage 2: URL Filtering (only if incremental scraping enabled)
    urls_to_scrape = discovered_urls
    if incremental_scraper:
        logger.info("\n[Stage 2a/5] Incremental URL Filtering...")
        
        # Categorize URLs for better caching
        url_categories = {url: categorize_func(url) for url in discovered_urls}
        
        filtered = incremental_scraper.filter_urls_for_scraping(
            discovered_urls,
            categories=url_categories
        )
        
        urls_to_scrape = filtered['to_scrape']
        
        logger.info(f"📊 Incremental filtering results:")
        logger.info(f"   • New URLs: {len(filtered['new'])}")
        logger.info(f"   • Expired cache entries: {len(filtered['expired'])}")
        logger.info(f"   • Previously failed: {len(filtered['failed_before'])}")
        logger.info(f"   • Skipped (fresh cache): {len(filtered['skipped'])}")
        logger.info(f"   • To scrape: {len(urls_to_scrape)}/{len(discovered_urls)}")
        
        if not urls_to_scrape:
            logger.info("All URLs are cached and fresh - no scraping needed!")
            urls_to_scrape = discovered_urls  # Fallback for first run
    
    # Stage 3: Scraping HTML Content
    logger.info(f"\n[Stage 2/4] Scraping HTML Content from {len(urls_to_scrape)} URLs...")
    
    scraping_config = ScrapingConfig(
        request_delay=scrape_delay,
        max_concurrent_requests=concurrent_requests
    )
    
    scraper = BatchScraper(scraping_config)
    scraped_data = []
    
    # Choose scraping method based on resilient scraping config
    if resilient_scraper:
        # Advanced scraping with retries
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            for url in urls_to_scrape:
                start_time = datetime.now()
                
                try:
                    content = await resilient_scraper.scrape_with_retry(
                        session=session,
                        url=url,
                        scraper=scraper
                    )
                    
                    if content and content.success:
                        # Content cleaning
                        if content_cleaner and content.content:
                            cleaned_text = content_cleaner._clean_text(content.content)
                            content.content = cleaned_text
                            content.metadata['cleaned'] = True
                        
                        # Change detection
                        if incremental_scraper:
                            change_info = incremental_scraper.detect_changes(url, content.content)
                            content.metadata['change_info'] = change_info
                        
                        # Metrics
                        if metrics:
                            duration = (datetime.now() - start_time).total_seconds()
                            metrics.record_url(
                                url=url,
                                success=True,
                                response_time=duration,
                                content_size=len(content.content),
                                category=categorize_func(url)
                            )
                        
                        # Cache update
                        if url_cache:
                            url_cache.put(
                                url=url,
                                content=content.content,
                                success=True,
                                category=categorize_func(url),
                                metadata=content.metadata
                            )
                        
                        scraped_data.append(content)
                        
                    else:
                        # Handle failure
                        if metrics:
                            duration = (datetime.now() - start_time).total_seconds()
                            metrics.record_url(
                                url=url,
                                success=False,
                                response_time=duration,
                                error=content.error_message if content else 'Unknown error'
                            )
                        
                        if url_cache:
                            url_cache.put(
                                url=url,
                                content="",
                                success=False,
                                category=categorize_func(url),
                                metadata={'error': content.error_message if content else 'Unknown error'}
                            )
                        
                        if content:
                            scraped_data.append(content)
                
                except Exception as e:
                    logger.error(f"Error scraping {url}: {e}")
                    if metrics:
                        duration = (datetime.now() - start_time).total_seconds()
                        metrics.record_url(
                            url=url,
                            success=False,
                            response_time=duration,
                            error=f"{type(e).__name__}: {str(e)}"
                        )
    else:
        # Simple scraping (Naive mode)
        scraped_data = await scraper.scrape_batch(urls_to_scrape)
    
    # Filter successful scrapes
    successful_scrapes = [content for content in scraped_data if content.success]
    
    # Content deduplication (only if enabled)
    if deduplicator and successful_scrapes:
        logger.info(f"\n🔍 Content deduplication...")
        original_count = len(successful_scrapes)
        
        docs = [{'url': c.url, 'content': c.content} for c in successful_scrapes]
        unique_docs, duplicate_docs = deduplicator.deduplicate_batch(docs)
        
        unique_urls = {d['url'] for d in unique_docs}
        successful_scrapes = [c for c in successful_scrapes if c.url in unique_urls]
        
        logger.info(f"   • Original: {original_count} documents")
        logger.info(f"   • Duplicates removed: {len(duplicate_docs)}")
        logger.info(f"   • Unique: {len(successful_scrapes)} documents")
    
    logger.info(f"✓ Successfully scraped {len(successful_scrapes)}/{len(scraped_data)} HTML pages")
    
    
    # Stage 3: Extract PDF Content
    pdf_contents = []
    if crawler.pdf_urls:
        logger.info(f"\n[Stage 3/4] Extracting Content from {len(crawler.pdf_urls)} PDFs...")
        
        pdf_extractor = PDFExtractor(download_dir=str(output_dir / "pdfs"))
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            pdf_tasks = [pdf_extractor.extract_from_url(session, pdf_url) for pdf_url in crawler.pdf_urls]
            pdf_contents = await asyncio.gather(*pdf_tasks)
        
        successful_pdfs = [pdf for pdf in pdf_contents if pdf.success]
        logger.info(f"✓ Successfully extracted {len(successful_pdfs)}/{len(pdf_contents)} PDFs")
        
        # Save PDF metadata
        pdf_metadata_file = output_dir / "pdf_metadata.json"
        with pdf_metadata_file.open('w', encoding='utf-8') as f:
            json.dump([{
                'url': pdf.url,
                'title': pdf.title,
                'num_pages': pdf.num_pages,
                'file_size': pdf.file_size,
                'metadata': pdf.metadata,
                'extraction_method': pdf.extraction_method,
                'success': pdf.success,
                'error': pdf.error
            } for pdf in pdf_contents], f, indent=2, ensure_ascii=False)
    
    # Stage 4: Content Processing and Vector Storage
    logger.info("\n[Stage 4/4] Processing Content and Storing in Vector Database...")
    
    # Prepare all content for processing
    all_content = []
    category_stats = defaultdict(int)
    
    # Process HTML content
    for content in successful_scrapes:
        category = categorize_func(content.url)
        enriched_metadata = enrich_func(content, category)
        content.metadata.update(enriched_metadata)
        all_content.append(content)
        category_stats[category] += 1
    
    # Process PDF content
    for pdf_content in pdf_contents:
        if not pdf_content.success:
            continue
        
        scraped_pdf = ScrapedContent(
            url=pdf_content.url,
            title=pdf_content.title,
            content=pdf_content.text,
            metadata={
                **pdf_content.metadata,
                'content_type': 'pdf',
                'num_pages': pdf_content.num_pages,
                'file_size': pdf_content.file_size,
                'extraction_method': pdf_content.extraction_method
            },
            success=True,
            error_message=None,
            timestamp=datetime.now().isoformat()
        )
        
        category = categorize_func(pdf_content.url)
        if 'pruefungsordnung' in pdf_content.url.lower():
            category = 'pruefungsordnungen'
        
        enriched_metadata = enrich_func(scraped_pdf, category)
        scraped_pdf.metadata.update(enriched_metadata)
        
        all_content.append(scraped_pdf)
        category_stats[category] += 1
    
    logger.info(f"✓ Categorized content into {len(category_stats)} categories:")
    for category, count in sorted(category_stats.items()):
        logger.info(f"  - {category}: {count} documents")
    
    # Text chunking - choose method based on configuration
    logger.info("📝 Chunking documents...")
    chunked_contents = []
    
    if semantic_chunker and config.enable_semantic_chunking:
        # Semantic chunking
        for content in all_content:
            chunks = semantic_chunker.chunk_document(
                text=content.content,
                metadata={
                    'url': content.url,
                    'title': content.title,
                    'category': content.metadata.get('category', 'allgemein'),
                    **content.metadata
                }
            )
            
            for i, chunk in enumerate(chunks):
                chunk_content = ScrapedContent(
                    url=f"{content.url}#chunk_{i}",
                    title=f"{content.title} (Teil {i+1}/{len(chunks)})",
                    content=chunk['text'],
                    metadata={
                        **content.metadata,
                        'chunk_index': chunk.get('chunk_index', i),
                        'total_chunks': chunk.get('total_chunks', len(chunks)),
                        'original_url': content.url,
                        'header': chunk.get('header', '')
                    },
                    success=True,
                    error_message=None,
                    timestamp=content.timestamp
                )
                chunked_contents.append(chunk_content)
    else:
        # Simple chunking
        for content in all_content:
            chunks = chunk_func(content.content)
            
            for i, chunk in enumerate(chunks):
                chunk_content = ScrapedContent(
                    url=f"{content.url}#chunk_{i}",
                    title=f"{content.title} (Teil {i+1}/{len(chunks)})",
                    content=chunk['text'],
                    metadata={
                        **content.metadata,
                        'chunk_index': chunk.get('chunk_index', i),
                        'total_chunks': chunk.get('total_chunks', len(chunks)),
                        'original_url': content.url
                    },
                    success=True,
                    error_message=None,
                    timestamp=content.timestamp
                )
                chunked_contents.append(chunk_content)
    
    logger.info(f"   • {len(chunked_contents)} chunks created from {len(all_content)} documents")
    
    # Store in vector database
    if config.organize_by_category:
        # Separate collections per category
        total_docs = 0
        category_chunks = defaultdict(list)
        
        for chunk in chunked_contents:
            category = chunk.metadata.get('category', 'allgemein')
            category_chunks[category].append(chunk)
        
        for category, chunks in category_chunks.items():
            if not chunks:
                continue
                
            collection_name = f"wiso_{category}"
            vector_config = VectorStoreConfig(
                persist_directory=str(output_dir / "vector_db"),
                collection_name=collection_name
            )
            
            vector_store = VectorStore(vector_config)
            doc_count = vector_store.add_scraped_content(chunks)
            total_docs += doc_count
            
            logger.info(f"  ✓ Stored {doc_count} chunks in collection '{collection_name}'")
    else:
        # Single collection
        vector_config = VectorStoreConfig(
            persist_directory=str(output_dir / "vector_db"),
            collection_name="wiso_scraped_content"
        )
        
        vector_store = VectorStore(vector_config)
        total_docs = vector_store.add_scraped_content(chunked_contents)
        logger.info(f"  ✓ Stored {total_docs} chunks in single collection")
    
    # Save scraped content (for analysis)
    content_file = output_dir / "scraped_data.json"
    with content_file.open('w', encoding='utf-8') as f:
        json.dump([content.__dict__ for content in scraped_data], f, indent=2, ensure_ascii=False)
    
    # Generate pipeline report
    pipeline_stats = {
        "timestamp": datetime.now().isoformat(),
        "mode": "advanced" if not config.is_naive_mode() else "naive",
        "configuration": {
            "max_pages": max_pages,
            "crawl_delay": crawl_delay,
            "scrape_delay": scrape_delay,
            "concurrent_requests": concurrent_requests,
            "organize_by_category": config.organize_by_category,
            "active_features": config.get_active_features()
        },
        "results": {
            "urls_discovered": len(discovered_urls),
            "urls_scraped": len(urls_to_scrape),
            "urls_skipped_cache": len(discovered_urls) - len(urls_to_scrape) if incremental_scraper else 0,
            "pdfs_found": len(crawler.pdf_urls),
            "pages_scraped": len(scraped_data),
            "successful_scrapes": len(successful_scrapes),
            "failed_scrapes": len(scraped_data) - len(successful_scrapes),
            "pdfs_extracted": len([p for p in pdf_contents if p.success]),
            "pdfs_failed": len([p for p in pdf_contents if not p.success]),
            "categories_found": len(category_stats),
            "category_distribution": dict(category_stats),
            "total_chunks_created": len(chunked_contents),
            "total_documents_stored": total_docs
        }
    }
    
    # Add advanced metrics if available
    if metrics:
        metrics_stats = metrics.get_statistics()
        pipeline_stats["metrics"] = {
            "success_rate": metrics_stats.get('success_rate', 0),
            "average_response_time": metrics_stats.get('avg_response_time', 0),
            "total_content_size": metrics_stats.get('total_content_size', 0),
            "error_summary": metrics_stats.get('error_summary', {})
        }
    
    # Save pipeline report
    report_file = output_dir / "pipeline_report.json"
    with report_file.open('w', encoding='utf-8') as f:
        json.dump(pipeline_stats, f, indent=2, ensure_ascii=False)
    
    # Export additional reports if enabled
    if config.enable_report_export:
        # Metrics export
        if metrics:
            metrics_file = output_dir / "scraper_metrics.json"
            metrics.export_report(metrics_file)
            logger.info(f"  ✓ Metrics exported to {metrics_file}")
        
        # Cache statistics
        if url_cache:
            cache_stats = url_cache.get_statistics()
            cache_file = output_dir / "cache_statistics.json"
            with cache_file.open('w', encoding='utf-8') as f:
                json.dump(cache_stats, f, indent=2, ensure_ascii=False)
            logger.info(f"  ✓ Cache statistics exported to {cache_file}")
        
        # Incremental scraping report
        if incremental_scraper:
            changes_file = output_dir / "content_changes.json"
            incremental_scraper.export_changes_report(changes_file)
            logger.info(f"  ✓ Changes report exported to {changes_file}")
        
        # Failed URLs report
        if resilient_scraper:
            failed_urls = resilient_scraper.get_failed_urls()
            if failed_urls:
                failed_file = output_dir / "failed_urls.json"
                resilient_scraper.export_failed_urls(failed_file)
                logger.info(f"  ✓ Failed URLs exported to {failed_file}")
        
        # Deduplication report
        if deduplicator:
            dedup_stats = deduplicator.get_statistics()
            dedup_file = output_dir / "deduplication_report.json"
            with dedup_file.open('w', encoding='utf-8') as f:
                json.dump(dedup_stats, f, indent=2, ensure_ascii=False)
            logger.info(f"  ✓ Deduplication report exported to {dedup_file}")
    
    logger.info("\n" + "=" * 80)
    logger.info("Pipeline Completed Successfully!")
    logger.info("=" * 80)
    logger.info(f"📊 Results Summary:")
    logger.info(f"   • Mode: {pipeline_stats['mode'].upper()}")
    logger.info(f"   • URLs Discovered: {len(discovered_urls)}")
    logger.info(f"   • URLs Scraped: {len(urls_to_scrape)}")
    if incremental_scraper:
        logger.info(f"   • URLs Skipped (Cache): {len(discovered_urls) - len(urls_to_scrape)}")
    logger.info(f"   • PDFs Found: {len(crawler.pdf_urls)}")
    logger.info(f"   • HTML Pages Scraped: {len(successful_scrapes)}/{len(scraped_data)}")
    logger.info(f"   • PDFs Extracted: {len([p for p in pdf_contents if p.success])}/{len(pdf_contents)}")
    logger.info(f"   • Total Chunks Created: {len(chunked_contents)}")
    logger.info(f"   • Total Documents Stored: {total_docs}")
    logger.info(f"   • Categories: {len(category_stats)}")
    if metrics:
        metrics_stats = metrics.get_statistics()
        logger.info(f"   • Success Rate: {metrics_stats.get('success_rate', 0):.1f}%")
        logger.info(f"   • Avg Response Time: {metrics_stats.get('avg_response_time', 0):.2f}s")
    logger.info(f"   • Report saved to: {report_file}")
    logger.info("=" * 80)
    
    return pipeline_stats


def main():
    """Command line interface for the pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="WiSo Faculty Crawler-Scraper Pipeline (Naive & Advanced RAG)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in Naive RAG mode (default - no optimizations)
  python crawler_scraper_pipeline.py
  
  # Run with custom settings
  python crawler_scraper_pipeline.py --max-pages 500 --crawl-delay 2.0
  
  # Use custom scraper configuration file
  python crawler_scraper_pipeline.py --config advanced_scraper.env
  
  # Fast mode for testing
  python crawler_scraper_pipeline.py --concurrent-requests 20 --crawl-delay 0.5

Advanced RAG Mode:
  Enable features by setting them to 'true' in scraper.env:
  - ENABLE_CACHING=true
  - ENABLE_DEDUPLICATION=true
  - ENABLE_SEMANTIC_CHUNKING=true
  - etc.
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
        "--config",
        type=str,
        default="scraper.env",
        help="Path to scraper configuration file (default: scraper.env)"
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
            config_file=args.config
        ))
        
        print(f"\n✅ Pipeline completed successfully!")
        print(f"📊 Mode: {stats['mode'].upper()} RAG")
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