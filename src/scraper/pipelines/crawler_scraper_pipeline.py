"""
Crawler Pipeline (Stage 1)
==========================

Crawlt die WiSo-Fakultätswebsite und speichert alle gefundenen HTML-Seiten
im html_cache sowie PDF-URLs für die spätere Verarbeitung.

Folgeschritte (separat auszuführen):
  1. src/scraper/tools/import_to_content_db.py  → HTML/PDF → content_database.db
  2. src/scraper/run_production_scraper.py       → content_database.db → vector_db
"""

import asyncio
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any
import json
from datetime import datetime

from src.scraper.core.wiso_crawler import WisoCrawler, CrawlerConfig
from src.scraper.utils.html_cache import HTMLContentCache

logger = logging.getLogger(__name__)

# =============================================================================
# KONFIGURATION – hier zentral anpassen
# =============================================================================
DEFAULT_OUTPUT_DIR        = Path("data")   # Ausgabeverzeichnis
DEFAULT_MAX_PAGES         = 5           # Maximale Seitenanzahl (Testlauf: z.B. 5)
DEFAULT_CRAWL_DELAY       = 1.0           # Sekunden zwischen Requests
DEFAULT_CONCURRENT_REQ    = 10            # Parallele Requests
DEFAULT_ENABLE_CACHING    = True          # HTML-Cache nutzen (empfohlen)
DEFAULT_HTML_CACHE_MAX_AGE = 300          # Cache-Gültigkeit in Tagen
# =============================================================================


async def run_crawler_scraper_pipeline(
    output_dir: Path,
    max_pages: int = DEFAULT_MAX_PAGES,
    crawl_delay: float = DEFAULT_CRAWL_DELAY,
    concurrent_requests: int = DEFAULT_CONCURRENT_REQ,
    enable_caching: bool = DEFAULT_ENABLE_CACHING,
) -> Dict[str, Any]:
    """
    Führt Stage 1 aus: Crawling der WiSo-Fakultätswebsite.

    Gefundene HTML-Seiten werden im html_cache gespeichert.
    Gefundene URLs werden in data_analysis/discovered_urls.json gespeichert.

    Args:
        output_dir: Verzeichnis für Ergebnisse (html_cache wird hier angelegt)
        max_pages: Maximale Anzahl zu crawlender Seiten
        crawl_delay: Verzögerung zwischen Requests in Sekunden
        concurrent_requests: Anzahl paralleler Requests
        enable_caching: HTML-Content-Caching aktivieren (empfohlen)

    Returns:
        Dictionary mit Crawl-Statistiken
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("Starting WiSo Faculty Crawler Pipeline (Stage 1)")
    logger.info("=" * 80)

    # HTML Cache initialisieren
    html_cache = HTMLContentCache(output_dir / "html_cache", max_age_days=DEFAULT_HTML_CACHE_MAX_AGE) if enable_caching else None

    if html_cache:
        logger.info(f"📦 HTML Content Cache: {html_cache.cache_dir} (max_age=300 Tage)")

    # Stage 1: Crawling
    logger.info("\n[Stage 1/1] Crawling WiSo Faculty Website...")
    crawler_config = CrawlerConfig(
        max_pages=max_pages,
        crawl_delay=crawl_delay,
        concurrent_requests=concurrent_requests
    )
    crawler_config.log_url_max_length = 80
    
    crawler = WisoCrawler(crawler_config, html_cache=html_cache)
    discovered_urls = await crawler.crawl()

    # Sicherheits-Check: PDF-URLs aus discovered_urls entfernen
    html_only_urls = [url for url in discovered_urls if not url.lower().endswith('.pdf')]
    pdf_count = len(discovered_urls) - len(html_only_urls)
    if pdf_count > 0:
        logger.warning(f"🚨 GEFILTERT: {pdf_count} PDF-URLs aus discovered_urls entfernt")
        discovered_urls = html_only_urls

    # PDF-URLs aus HTML-Cache extrahieren (für URLs aus vorherigen Crawls)
    cached_pdf_urls = set()
    if html_cache:
        try:
            with sqlite3.connect(html_cache.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT url FROM html_cache WHERE url LIKE '%.pdf'")
                cached_pdfs = cursor.fetchall()
                cached_pdf_urls = {url for (url,) in cached_pdfs}

                if cached_pdf_urls:
                    logger.info(f"🔄 CACHE-RECOVERY: {len(cached_pdf_urls)} PDF-URLs aus HTML-Cache extrahiert")
                    original_pdf_count = len(crawler.pdf_urls)
                    crawler.pdf_urls.update(cached_pdf_urls)
                    new_pdfs = len(crawler.pdf_urls) - original_pdf_count
                    if new_pdfs > 0:
                        logger.info(f"   📄 {new_pdfs} neue PDFs aus Cache hinzugefügt")
        except Exception as e:
            logger.warning(f"Fehler beim Extrahieren von PDF-URLs aus Cache: {e}")

    # Discovered URLs speichern
    data_analysis_dir = Path(__file__).parent / "data_analysis"
    data_analysis_dir.mkdir(parents=True, exist_ok=True)
    urls_file = data_analysis_dir / "discovered_urls.json"
    with urls_file.open('w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_html_urls": len(discovered_urls),
            "total_pdf_urls": len(crawler.pdf_urls),
            "urls": discovered_urls,
            "pdf_urls": list(crawler.pdf_urls),
            "cached_pdf_urls": list(cached_pdf_urls)
        }, f, indent=2, ensure_ascii=False)

    pipeline_stats = {
        "timestamp": datetime.now().isoformat(),
        "configuration": {
            "max_pages": max_pages,
            "crawl_delay": crawl_delay,
            "concurrent_requests": concurrent_requests,
            "enable_caching": enable_caching,
        },
        "results": {
            "urls_discovered": len(discovered_urls),
            "pdfs_found": len(crawler.pdf_urls),
            "cached_pdf_urls_recovered": len(cached_pdf_urls),
        }
    }

    logger.info("\n" + "=" * 80)
    logger.info("Crawling abgeschlossen!")
    logger.info("=" * 80)
    logger.info(f"📊 Ergebnisse:")
    logger.info(f"   • HTML-URLs gefunden: {len(discovered_urls)}")
    logger.info(f"   • PDF-URLs gefunden:  {len(crawler.pdf_urls)}")
    if html_cache:
        html_stats = html_cache.get_statistics()
        logger.info(f"   • HTML Cache Hits:    {html_stats['hits']}")
        logger.info(f"   • HTML Cache Entries: {html_stats['total_entries']}")
        logger.info(f"   • Hit Rate:           {html_stats['hit_rate']}")
    logger.info(f"   • URLs gespeichert:   {urls_file}")
    logger.info("\n📋 Nächste Schritte:")
    logger.info("   1. python -m src.scraper.tools.import_to_content_db")
    logger.info("   2. python -m src.scraper.run_production_scraper")
    logger.info("=" * 80)

    return pipeline_stats
    


def main():
    """Command line interface für den Crawler."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WiSo Faculty Crawler Pipeline (Stage 1)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Standard-Lauf
  python -m src.scraper.pipelines.crawler_scraper_pipeline

  # Mit angepassten Einstellungen
  python -m src.scraper.pipelines.crawler_scraper_pipeline --max-pages 3000 --crawl-delay 2.0

  # Ohne Caching (nicht empfohlen)
  python -m src.scraper.pipelines.crawler_scraper_pipeline --no-caching
        """
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Verzeichnis für Ergebnisse (Standard: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help=f"Maximale Anzahl zu crawlender Seiten (Standard: {DEFAULT_MAX_PAGES})"
    )
    parser.add_argument(
        "--crawl-delay",
        type=float,
        default=DEFAULT_CRAWL_DELAY,
        help=f"Verzögerung zwischen Requests in Sekunden (Standard: {DEFAULT_CRAWL_DELAY})"
    )
    parser.add_argument(
        "--concurrent-requests",
        type=int,
        default=DEFAULT_CONCURRENT_REQ,
        help=f"Anzahl paralleler Requests (Standard: {DEFAULT_CONCURRENT_REQ})"
    )
    parser.add_argument(
        "--no-caching",
        action="store_true",
        help="HTML-Caching deaktivieren (nicht empfohlen)"
    )
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Log-Level (Standard: INFO)"
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    try:
        stats = asyncio.run(run_crawler_scraper_pipeline(
            output_dir=args.output_dir,
            max_pages=args.max_pages,
            crawl_delay=args.crawl_delay,
            concurrent_requests=args.concurrent_requests,
            enable_caching=not args.no_caching,
        ))

        print("\n[SUCCESS] Crawling abgeschlossen!")
        print(f"   HTML-URLs: {stats['results']['urls_discovered']}")
        print(f"   PDF-URLs:  {stats['results']['pdfs_found']}")
        print(f"\nNächste Schritte:")
        print(f"   1. python -m src.scraper.tools.import_to_content_db")
        print(f"   2. python -m src.scraper.run_production_scraper")

    except KeyboardInterrupt:
        print("\n[WARNING] Crawling durch Benutzer unterbrochen")
    except Exception as e:
        logger.error(f"Crawler fehlgeschlagen: {e}", exc_info=True)
        print(f"\n[ERROR] Crawler fehlgeschlagen: {e}")
        return 1

    return 0


if __name__ == "__main__":
    main()