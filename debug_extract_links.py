#!/usr/bin/env python3
"""
🔧 DEBUG: extract_links() Test
=============================

Test ob der extract_links() Fix korrekt funktioniert.
"""

import sys
import asyncio
import aiohttp
from pathlib import Path

# Füge src zum Python-Pfad hinzu
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scraper.core.wiso_crawler import WisoCrawler, CrawlerConfig
from src.scraper.utils.html_cache import HTMLContentCache

async def test_extract_links():
    """Teste extract_links() auf einer Seite mit PDFs."""
    print("🧪 EXTRACT_LINKS() DEBUG TEST")
    print("=" * 50)
    
    # Konfiguration
    config = CrawlerConfig()
    html_cache = HTMLContentCache("data/html_cache")
    crawler = WisoCrawler(config, html_cache=html_cache)
    
    # Test-URL die wahrscheinlich PDFs enthält
    test_url = "https://wiso.uni-koeln.de/de/studium/master/master-information-systems"
    
    print(f"🔍 Teste URL: {test_url}")
    print()
    
    try:
        # Hole HTML-Content
        async with aiohttp.ClientSession() as session:
            async with session.get(test_url) as response:
                if response.status != 200:
                    print(f"❌ HTTP Error {response.status}")
                    return
                
                html_content = await response.text()
                print(f"✅ HTML abgerufen ({len(html_content):,} Zeichen)")
                
                # Reset PDF collection
                crawler.pdf_urls.clear()
                print(f"🔄 PDF collection zurückgesetzt")
                
                # Teste extract_links()
                print(f"🔧 Führe extract_links() aus...")
                links = await crawler.extract_links(test_url, html_content)
                
                # Analysiere Ergebnisse
                print()
                print("📊 ERGEBNISSE:")
                print(f"   • Links zurückgegeben: {len(links)}")
                print(f"   • PDFs in pdf_urls: {len(crawler.pdf_urls)}")
                
                # Check für PDFs in returned links
                pdf_links_in_result = [url for url in links if url.lower().endswith('.pdf')]
                
                if pdf_links_in_result:
                    print()
                    print("🚨 PROBLEM: PDFs in returned links!")
                    for pdf_url in pdf_links_in_result[:3]:  # Erste 3
                        print(f"   ❌ {pdf_url}")
                else:
                    print("   ✅ Keine PDFs in returned links")
                
                # EXTRA DEBUG: Detaillierte Analyse aller URLs
                print()
                print("🔍 DETAILLIERTE ANALYSE:")
                target_pdf_fragment = "brochure-Master-Information_Systems.pdf"
                
                for url in links:
                    if target_pdf_fragment in url:
                        print(f"   🚨 GEFUNDEN IN LINKS: {url}")
                        print(f"      endswith('.pdf'): {url.lower().endswith('.pdf')}")
                        break
                else:
                    print(f"   ✅ '{target_pdf_fragment}' NICHT in returned links gefunden")
                
                if crawler.pdf_urls:
                    print()
                    print("📄 PDFs in pdf_urls collection:")
                    for pdf_url in list(crawler.pdf_urls)[:3]:  # Erste 3
                        print(f"   • {pdf_url}")
                
                # Suche nach spezifischen PDFs aus dem Log
                target_pdfs = [
                    "brochure-Master_Economics.pdf",
                    "brochure-Master-Information_Systems.pdf"
                ]
                
                print()
                print("🎯 SPEZIFISCHE PDF-SUCHE:")
                for target_pdf in target_pdfs:
                    found_in_links = any(target_pdf in url for url in links)
                    found_in_pdfs = any(target_pdf in url for url in crawler.pdf_urls)
                    
                    print(f"   📄 {target_pdf}:")
                    print(f"      In returned links: {'❌ JA' if found_in_links else '✅ NEIN'}")
                    print(f"      In pdf_urls: {'✅ JA' if found_in_pdfs else '❌ NEIN'}")
                
    except Exception as e:
        print(f"❌ Fehler: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_extract_links())