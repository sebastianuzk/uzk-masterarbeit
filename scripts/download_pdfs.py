#!/usr/bin/env python3
"""
Gezielter PDF-Download von gespeicherten URLs
===========================================

Lädt PDFs basierend auf gespeicherten URL-Listen herunter.

Usage:
    python scripts/download_pdfs.py --from-cache          # Alle PDFs aus URL Cache
    python scripts/download_pdfs.py --from-json file.json # PDFs aus JSON-Liste
    python scripts/download_pdfs.py --urls url1 url2 ...  # Spezifische URLs

Features:
    - Verwendet bestehenden PDFExtractor
    - Rate limiting und retry logic
    - Progress tracking
    - Metadata-Extraktion
"""

import asyncio
import aiohttp
import argparse
import json
import sqlite3
from pathlib import Path
from typing import List, Optional
import logging

from src.scraper.utils.pdf_extractor import PDFExtractor, PDFContent

logger = logging.getLogger(__name__)


async def download_pdfs_from_urls(urls: List[str], output_dir: str = "data/pdfs") -> List[PDFContent]:
    """Download PDFs from URL list."""
    pdf_extractor = PDFExtractor(download_dir=output_dir)
    
    # Rate limiting setup
    connector = aiohttp.TCPConnector(limit=3, limit_per_host=2)
    timeout = aiohttp.ClientTimeout(total=120, connect=30)
    
    results = []
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        # Process in batches of 5
        batch_size = 5
        for i in range(0, len(urls), batch_size):
            batch = urls[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(urls) + batch_size - 1)//batch_size}: {len(batch)} PDFs")
            
            batch_tasks = [pdf_extractor.extract_from_url(session, url) for url in batch]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.warning(f"PDF extraction failed: {result}")
                else:
                    results.append(result)
            
            # Delay between batches
            if i + batch_size < len(urls):
                await asyncio.sleep(2)
    
    return results


def get_pdf_urls_from_cache(db_path: str = "data/url_cache.db") -> List[str]:
    """Extract PDF URLs from URL cache database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Look for PDF URLs (could be in url field or discovered during crawling)
    cursor.execute("SELECT DISTINCT url FROM url_cache WHERE url LIKE '%.pdf'")
    rows = cursor.fetchall()
    
    conn.close()
    return [row[0] for row in rows]


def get_pdf_urls_from_json(json_path: str) -> List[str]:
    """Extract PDF URLs from JSON file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different JSON structures
    if 'urls' in data:
        urls = data['urls']
    elif isinstance(data, list):
        urls = data
    else:
        raise ValueError("Unsupported JSON structure")
    
    # Filter for PDF URLs
    pdf_urls = [url for url in urls if url.lower().endswith('.pdf')]
    return pdf_urls


def get_crawler_pdf_urls() -> List[str]:
    """Get PDF URLs discovered during crawling."""
    try:
        # Check if discovered_urls.json contains PDF URLs
        json_path = "src/scraper/pipelines/data_analysis/discovered_urls.json"
        if Path(json_path).exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [url for url in data.get('urls', []) if url.lower().endswith('.pdf')]
    except:
        pass
    
    return []


async def main():
    parser = argparse.ArgumentParser(description="Gezielter PDF-Download")
    parser.add_argument('--from-cache', action='store_true',
                       help='PDFs aus URL-Cache herunterladen')
    parser.add_argument('--from-json', type=str,
                       help='PDFs aus JSON-Datei herunterladen')
    parser.add_argument('--urls', nargs='+',
                       help='Spezifische URLs herunterladen')
    parser.add_argument('--output-dir', default='data/pdfs',
                       help='Output-Verzeichnis für PDFs')
    parser.add_argument('--save-metadata', default='data/downloaded_pdfs_metadata.json',
                       help='Metadaten-Datei speichern')
    
    args = parser.parse_args()
    
    # Collect URLs
    pdf_urls = []
    
    if args.from_cache:
        cache_urls = get_pdf_urls_from_cache()
        pdf_urls.extend(cache_urls)
        print(f"📁 Found {len(cache_urls)} PDF URLs in cache")
    
    if args.from_json:
        json_urls = get_pdf_urls_from_json(args.from_json)
        pdf_urls.extend(json_urls)
        print(f"📄 Found {len(json_urls)} PDF URLs in JSON")
    
    if args.urls:
        pdf_urls.extend(args.urls)
        print(f"📝 Added {len(args.urls)} manual URLs")
    
    # Also check crawler results
    crawler_urls = get_crawler_pdf_urls()
    if crawler_urls:
        pdf_urls.extend(crawler_urls)
        print(f"🕸️ Found {len(crawler_urls)} PDF URLs from crawler")
    
    # Remove duplicates
    pdf_urls = list(set(pdf_urls))
    
    if not pdf_urls:
        print("❌ No PDF URLs found!")
        return
    
    print(f"\n🎯 Total PDF URLs to download: {len(pdf_urls)}")
    print(f"💾 Output directory: {args.output_dir}")
    
    # Download PDFs
    results = await download_pdfs_from_urls(pdf_urls, args.output_dir)
    
    # Statistics
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]
    
    print(f"\n📊 Download Results:")
    print(f"   ✅ Successful: {len(successful)}")
    print(f"   ❌ Failed: {len(failed)}")
    
    if failed:
        print(f"\n❌ Failed Downloads:")
        for pdf in failed:
            print(f"   • {pdf.url}: {pdf.error}")
    
    # Save metadata
    if args.save_metadata and results:
        metadata = [{
            'url': pdf.url,
            'title': pdf.title,
            'num_pages': pdf.num_pages,
            'file_size': pdf.file_size,
            'metadata': pdf.metadata,
            'success': pdf.success,
            'error': pdf.error
        } for pdf in results]
        
        with open(args.save_metadata, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Metadata saved to: {args.save_metadata}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())