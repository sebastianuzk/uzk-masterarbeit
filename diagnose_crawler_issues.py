#!/usr/bin/env python3
"""
Detaillierte Crawler-Fehler-Diagnose
"""

import sys
import os
import asyncio
from pathlib import Path

# Pfad für Imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def diagnose_crawler_issues():
    """Führe Diagnose durch um URL-Probleme zu identifizieren"""
    print("🔍 CRAWLER-FEHLER-DIAGNOSE")
    print("=" * 60)
    
    try:
        from scraper.core.wiso_crawler import WisoCrawler, CrawlerConfig
        
        # Erstelle Crawler-Instanz
        config = CrawlerConfig()
        crawler = WisoCrawler(config)
        
        print("📊 Crawler-Status:")
        print(f"   🔍 Found URLs: {len(crawler.found_urls)}")
        print(f"   📄 PDF URLs: {len(crawler.pdf_urls)}")
        print(f"   🔄 Retry Queue: {len(crawler.retry_queue)}")
        print(f"   ❌ Failed URLs: {len(crawler.failed_urls)}")
        
        if crawler.retry_queue:
            print(f"\n🔄 RETRY QUEUE ({len(crawler.retry_queue)} URLs):")
            for i, entry in enumerate(crawler.retry_queue[:5], 1):
                url = entry.get('url', 'Unknown')
                error = entry.get('last_error', 'Unknown error')
                attempts = entry.get('attempt_count', 0)
                print(f"   {i}. [{attempts} attempts] {url[:60]}{'...' if len(url) > 60 else ''}")
                print(f"      Error: {error}")
        
        if crawler.failed_urls:
            print(f"\n❌ FAILED URLs ({len(crawler.failed_urls)}):")
            for i, (url, error_type, error_msg) in enumerate(crawler.failed_urls[:5], 1):
                print(f"   {i}. [{error_type}] {url[:60]}{'...' if len(url) > 60 else ''}")
                print(f"      {error_msg}")
        
        await crawler.close()
        
    except Exception as e:
        print(f"❌ Fehler beim Laden des Crawlers: {e}")
    
    # Teste ein paar URLs direkt
    print(f"\n🧪 DIREKTE URL-TESTS:")
    test_urls = [
        "https://wiso.uni-koeln.de/de/",
        "https://wiso.uni-koeln.de/de/studium/",
        "https://wiso.uni-koeln.de/de/forschung/"
    ]
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        for url in test_urls:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"   ✅ {response.status}: {url}")
            except Exception as e:
                print(f"   ❌ FEHLER: {url} - {e}")

if __name__ == "__main__":
    asyncio.run(diagnose_crawler_issues())