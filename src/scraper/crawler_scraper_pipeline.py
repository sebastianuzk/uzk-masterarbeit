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
from typing import List, Optional, Dict, Any, TYPE_CHECKING
import json
from datetime import datetime
from collections import defaultdict
from urllib.parse import urlparse

import hashlib
from src.scraper.wiso_crawler import WisoCrawler, CrawlerConfig
from src.scraper.batch_scraper import BatchScraper, ScrapingConfig, ScrapedContent
from src.scraper.vector_store import VectorStore, VectorStoreConfig, VectorDocument
from src.scraper.pdf_extractor import PDFExtractor, PDFContent

# Enhancement-Module
from src.scraper.url_cache import URLCache
from src.scraper.content_deduplicator import ContentDeduplicator
from src.scraper.content_cleaner import ContentCleaner
from src.scraper.semantic_chunker import SemanticChunker
from src.scraper.scraper_metrics import ScraperMetrics
from src.scraper.resilient_scraper import ResilientScraper, RetryConfig
from src.scraper.incremental_scraper import IncrementalScraper

logger = logging.getLogger(__name__)

def categorize_url(url: str) -> str:
    """
    Kategorisiere URL basierend auf ihrem Pfad für bessere Inhaltsorganisation.
    
    Args:
        url: Die zu kategorisierende URL
        
    Returns:
        Kategoriename
    """
    url_lower = url.lower()
    
    # Definiere Kategorie-Muster
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


def enrich_metadata(content: ScrapedContent, category: str) -> Dict[str, Any]:
    """
    Reichere Metadaten von gescrapeten Inhalten für besseres Retrieval an.
    
    Args:
        content: ScrapedContent-Objekt
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
    organize_by_category: bool = True,
    enable_caching: bool = True,
    enable_deduplication: bool = True,
    enable_content_cleaning: bool = True
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
        enable_caching: Aktiviere intelligentes Caching
        enable_deduplication: Aktiviere Content-Deduplizierung
        enable_content_cleaning: Aktiviere Content-Bereinigung
        
    Returns:
        Dictionary with pipeline statistics and results
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("=" * 80)
    logger.info("Starting WiSo Faculty Crawler-Scraper Pipeline (Enhanced)")
    logger.info("=" * 80)
    
    # Initialisiere Enhancement-Module
    url_cache = URLCache(str(output_dir / "url_cache.db")) if enable_caching else None
    deduplicator = ContentDeduplicator() if enable_deduplication else None
    content_cleaner = ContentCleaner() if enable_content_cleaning else None
    semantic_chunker = SemanticChunker()
    metrics = ScraperMetrics()
    
    # Resilient Scraper mit angepasster Konfiguration
    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=2.0,
        max_delay=60.0,
        exponential_base=2.0
    )
    resilient_scraper = ResilientScraper(retry_config)
    
    # Incremental Scraper
    incremental_scraper = IncrementalScraper(url_cache) if enable_caching else None
    
    logger.info(f"📦 Enhancement-Module aktiv:")
    logger.info(f"   • Intelligentes Caching: {enable_caching}")
    logger.info(f"   • Content-Deduplizierung: {enable_deduplication}")
    logger.info(f"   • Content-Bereinigung: {enable_content_cleaning}")
    logger.info(f"   • Semantisches Chunking: Aktiviert")
    logger.info(f"   • Resilient Scraping: Aktiviert (max {retry_config.max_retries} Retries)")
    logger.info(f"   • Metriken: Aktiviert")
    
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
    logger.info(f"✓ Found {len(crawler.pdf_urls)} PDF documents")
    
    # Stage 2: Scraping HTML Content
    logger.info(f"\n[Stage 2/5] Scraping HTML Content from {len(discovered_urls)} URLs...")
    
    # Inkrementelles Scraping: Filtere URLs
    urls_to_scrape = discovered_urls
    if incremental_scraper:
        # Kategorisiere URLs für besseres Caching
        url_categories = {url: categorize_url(url) for url in discovered_urls}
        
        filtered = incremental_scraper.filter_urls_for_scraping(
            discovered_urls,
            categories=url_categories
        )
        
        urls_to_scrape = filtered['to_scrape']
        
        logger.info(f"📊 Inkrementelles Scraping:")
        logger.info(f"   • Neue URLs: {len(filtered['new'])}")
        logger.info(f"   • Abgelaufene Cache-Einträge: {len(filtered['expired'])}")
        logger.info(f"   • Zuvor fehlgeschlagen: {len(filtered['failed_before'])}")
        logger.info(f"   • Übersprungen (frischer Cache): {len(filtered['skipped'])}")
        logger.info(f"   • Zu scrapen: {len(urls_to_scrape)}/{len(discovered_urls)}")
    
    if not urls_to_scrape:
        logger.info("Alle URLs sind im Cache und aktuell - kein Scraping erforderlich!")
        urls_to_scrape = discovered_urls  # Fallback für erste Ausführung
    
    scraping_config = ScrapingConfig(
        request_delay=scrape_delay,
        max_concurrent_requests=concurrent_requests
    )
    
    scraper = BatchScraper(scraping_config)
    
    # Verwende Resilient Scraper für robustes Scraping
    import aiohttp
    scraped_data = []
    
    async with aiohttp.ClientSession() as session:
        for url in urls_to_scrape:
            start_time = datetime.now()
            
            try:
                # Resilient Scraping mit Retries
                content = await resilient_scraper.scrape_with_retry(
                    session=session,
                    url=url,
                    scraper=scraper
                )
                
                if content and content.success:
                    # Content-Bereinigung (Text wird nochmal bereinigt)
                    if content_cleaner and content.content:
                        cleaned_text = content_cleaner._clean_text(content.content)
                        content.content = cleaned_text
                        content.metadata['cleaned'] = True
                    
                    # Change Detection
                    if incremental_scraper:
                        change_info = incremental_scraper.detect_changes(url, content.content)
                        content.metadata['change_info'] = change_info
                    
                    # Metrics erfassen
                    duration = (datetime.now() - start_time).total_seconds()
                    metrics.record_url(
                        url=url,
                        success=True,
                        response_time=duration,
                        content_size=len(content.content),
                        category=categorize_url(url)
                    )
                    
                    # Cache aktualisieren
                    if url_cache:
                        url_cache.put(
                            url=url,
                            content=content.content,
                            success=True,
                            category=categorize_url(url),
                            metadata=content.metadata
                        )
                    
                    scraped_data.append(content)
                else:
                    # Fehlschlag
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
                            category=categorize_url(url),
                            metadata={'error': content.error_message if content else 'Unknown error'}
                        )
                    
                    if content:
                        scraped_data.append(content)
            
            except Exception as e:
                logger.error(f"Fehler beim Scrapen von {url}: {e}")
                duration = (datetime.now() - start_time).total_seconds()
                metrics.record_url(
                    url=url,
                    success=False,
                    response_time=duration,
                    error=f"{type(e).__name__}: {str(e)}"
                )
    
    # Filter successful scrapes
    successful_scrapes = [content for content in scraped_data if content.success]
    
    # Content-Deduplizierung
    if deduplicator and successful_scrapes:
        logger.info(f"\n🔍 Content-Deduplizierung...")
        original_count = len(successful_scrapes)
        
        # Konvertiere zu dict format für deduplicator
        docs = [{'url': c.url, 'content': c.content} for c in successful_scrapes]
        unique_docs, duplicate_docs = deduplicator.deduplicate_batch(docs)
        
        # Erstelle Mapping zurück zu ScrapedContent
        unique_urls = {d['url'] for d in unique_docs}
        successful_scrapes = [c for c in successful_scrapes if c.url in unique_urls]
        
        duplicate_count = len(duplicate_docs)
        
        logger.info(f"   • Original: {original_count} Dokumente")
        logger.info(f"   • Duplikate entfernt: {duplicate_count}")
        logger.info(f"   • Unique: {len(successful_scrapes)} Dokumente")
    
    # Save scraped content
    content_file = Path(__file__).parent / "data_analysis" / "scraped_data.json"
    with content_file.open('w', encoding='utf-8') as f:
        json.dump([content.__dict__ for content in scraped_data], f, indent=2, ensure_ascii=False)
        
    logger.info(f"✓ Successfully scraped {len(successful_scrapes)}/{len(scraped_data)} HTML pages")
    
    # Stage 2.5: Extract PDF Content
    pdf_contents = []
    if crawler.pdf_urls:
        logger.info(f"\n[Stage 2.5/5] Extracting Content from {len(crawler.pdf_urls)} PDFs...")
        
        pdf_extractor = PDFExtractor(download_dir=str(output_dir / "pdfs"))
        
        # Process PDFs with progress tracking
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
    
    # Stage 3: Content Categorization and Enrichment
    logger.info("\n[Stage 3/5] Categorizing and Enriching Content...")
    
    categorized_content = defaultdict(list)
    category_stats = defaultdict(int)
    
    # Categorize HTML content
    for content in successful_scrapes:
        category = categorize_url(content.url)
        enriched_metadata = enrich_metadata(content, category)
        
        # Update content metadata
        content.metadata.update(enriched_metadata)
        
        # Organize by category
        categorized_content[category].append(content)
        category_stats[category] += 1
    
    # Categorize PDF content
    for pdf_content in pdf_contents:
        if not pdf_content.success:
            continue
        
        # Convert PDFContent to ScrapedContent format
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
        
        category = categorize_url(pdf_content.url)
        # PDFs with Prüfungsordnung should always go to pruefungsordnungen category
        if 'pruefungsordnung' in pdf_content.url.lower() or 'document_type' in pdf_content.metadata:
            category = 'pruefungsordnungen'
        
        enriched_metadata = enrich_metadata(scraped_pdf, category)
        scraped_pdf.metadata.update(enriched_metadata)
        
        categorized_content[category].append(scraped_pdf)
        category_stats[category] += 1
    
    logger.info(f"✓ Categorized content into {len(category_stats)} categories:")
    for category, count in sorted(category_stats.items()):
        logger.info(f"  - {category}: {count} documents")
    
    # Stage 4: Vector Store Integration with Semantic Chunking
    logger.info("\n[Stage 4/5] Storing Content in Vector Database...")
    
    # Semantisches Chunking für alle Inhalte
    logger.info("📝 Wende semantisches Chunking an...")
    chunked_contents = []
    
    for category, contents in categorized_content.items():
        for content in contents:
            # Chunks erstellen
            chunks = semantic_chunker.chunk_document(
                text=content.content,
                metadata={
                    'url': content.url,
                    'title': content.title,
                    'category': category,
                    **content.metadata
                }
            )
            
            # Konvertiere Chunks in ScrapedContent-Objekte
            for i, chunk in enumerate(chunks):
                chunked_content = ScrapedContent(
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
                chunked_contents.append((category, chunked_content))
    
    logger.info(f"   • {len(chunked_contents)} Chunks erstellt aus {sum(len(c) for c in categorized_content.values())} Dokumenten")
    
    if organize_by_category:
        # Create separate collection for each category
        total_docs = 0
        category_chunk_counts = defaultdict(int)
        
        for category, chunked_content in chunked_contents:
            category_chunk_counts[category] += 1
        
        for category, count in category_chunk_counts.items():
            # Sammle alle Chunks für diese Kategorie
            category_chunks = [content for cat, content in chunked_contents if cat == category]
            
            if not category_chunks:
                continue
                
            collection_name = f"wiso_{category}"
            vector_config = VectorStoreConfig(
                persist_directory=str(output_dir / "vector_db"),
                collection_name=collection_name
            )
            
            vector_store = VectorStore(vector_config)
            doc_count = vector_store.add_scraped_content(category_chunks)
            total_docs += doc_count
            
            logger.info(f"  ✓ Stored {doc_count} chunks in collection '{collection_name}'")
    else:
        # Single collection for all content
        vector_config = VectorStoreConfig(
            persist_directory=str(output_dir / "vector_db"),
            collection_name="wiso_scraped_content"
        )
        
        vector_store = VectorStore(vector_config)
        all_chunks = [content for _, content in chunked_contents]
        total_docs = vector_store.add_scraped_content(all_chunks)
        logger.info(f"  ✓ Stored {total_docs} chunks in single collection")
    
    # Stage 5: Generate Reports and Export Metrics
    logger.info("\n[Stage 5/5] Generiere Reports und Metriken...")
    
    # Metrics-Export
    metrics_file = output_dir / "scraper_metrics.json"
    metrics.export_report(metrics_file)
    logger.info(f"  ✓ Metriken exportiert nach {metrics_file}")
    
    # Cache-Statistiken
    if url_cache:
        cache_stats = url_cache.get_statistics()
        cache_file = output_dir / "cache_statistics.json"
        with cache_file.open('w', encoding='utf-8') as f:
            json.dump(cache_stats, f, indent=2, ensure_ascii=False)
        logger.info(f"  ✓ Cache-Statistiken exportiert nach {cache_file}")
    
    # Incremental Scraping Report
    if incremental_scraper:
        changes_file = output_dir / "content_changes.json"
        incremental_scraper.export_changes_report(changes_file)
        logger.info(f"  ✓ Änderungs-Report exportiert nach {changes_file}")
    
    # Resilient Scraper Report
    failed_urls = resilient_scraper.get_failed_urls()
    if failed_urls:
        failed_file = output_dir / "failed_urls.json"
        resilient_scraper.export_failed_urls(failed_file)
        logger.info(f"  ✓ Fehlgeschlagene URLs exportiert nach {failed_file}")
    
    # Deduplication Report
    if deduplicator:
        dedup_stats = deduplicator.get_statistics()
        dedup_file = output_dir / "deduplication_report.json"
        with dedup_file.open('w', encoding='utf-8') as f:
            json.dump(dedup_stats, f, indent=2, ensure_ascii=False)
        logger.info(f"  ✓ Deduplizierungs-Report exportiert nach {dedup_file}")
    
    # Generate comprehensive pipeline report
    metrics_stats = metrics.get_statistics()
    
    pipeline_stats = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "max_pages": max_pages,
            "crawl_delay": crawl_delay,
            "scrape_delay": scrape_delay,
            "concurrent_requests": concurrent_requests,
            "organize_by_category": organize_by_category,
            "enhancements": {
                "caching": enable_caching,
                "deduplication": enable_deduplication,
                "content_cleaning": enable_content_cleaning,
                "semantic_chunking": True,
                "resilient_scraping": True
            }
        },
        "results": {
            "urls_discovered": len(discovered_urls),
            "urls_scraped": len(urls_to_scrape) if 'urls_to_scrape' in locals() else len(discovered_urls),
            "urls_skipped_cache": len(discovered_urls) - len(urls_to_scrape) if 'urls_to_scrape' in locals() else 0,
            "pdfs_found": len(crawler.pdf_urls),
            "pages_scraped": len(scraped_data),
            "successful_scrapes": len(successful_scrapes),
            "failed_scrapes": len(scraped_data) - len(successful_scrapes),
            "duplicates_removed": metrics_stats.get('duplicates_removed', 0) if deduplicator else 0,
            "pdfs_extracted": len([p for p in pdf_contents if p.success]),
            "pdfs_failed": len([p for p in pdf_contents if not p.success]),
            "categories_found": len(category_stats),
            "category_distribution": dict(category_stats),
            "total_chunks_created": len(chunked_contents),
            "total_documents_stored": total_docs
        },
        "metrics": {
            "success_rate": metrics_stats.get('success_rate', 0),
            "average_response_time": metrics_stats.get('avg_response_time', 0),
            "total_content_size": metrics_stats.get('total_content_size', 0),
            "error_summary": metrics_stats.get('error_summary', {})
        },
        "cache_stats": url_cache.get_statistics() if url_cache else {},
        "changes_detected": incremental_scraper.get_statistics() if incremental_scraper else {}
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
    logger.info(f"   • URLs Scraped: {len(urls_to_scrape) if 'urls_to_scrape' in locals() else len(discovered_urls)}")
    if enable_caching and 'urls_to_scrape' in locals():
        logger.info(f"   • URLs Skipped (Cache): {len(discovered_urls) - len(urls_to_scrape)}")
    logger.info(f"   • PDFs Found: {len(crawler.pdf_urls)}")
    logger.info(f"   • HTML Pages Scraped: {len(successful_scrapes)}/{len(scraped_data)}")
    if deduplicator:
        logger.info(f"   • Duplicates Removed: {pipeline_stats['results']['duplicates_removed']}")
    logger.info(f"   • PDFs Extracted: {len([p for p in pdf_contents if p.success])}/{len(pdf_contents)}")
    logger.info(f"   • Total Chunks Created: {len(chunked_contents)}")
    logger.info(f"   • Total Documents Stored: {total_docs}")
    logger.info(f"   • Categories: {len(category_stats)}")
    logger.info(f"   • Success Rate: {metrics_stats.get('success_rate', 0):.1f}%")
    logger.info(f"   • Avg Response Time: {metrics_stats.get('avg_response_time', 0):.2f}s")
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
        "--no-caching",
        action="store_true",
        help="Disable intelligent caching"
    )
    parser.add_argument(
        "--no-deduplication",
        action="store_true",
        help="Disable content deduplication"
    )
    parser.add_argument(
        "--no-cleaning",
        action="store_true",
        help="Disable content cleaning"
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
            organize_by_category=args.organize_by_category,
            enable_caching=not args.no_caching,
            enable_deduplication=not args.no_deduplication,
            enable_content_cleaning=not args.no_cleaning
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