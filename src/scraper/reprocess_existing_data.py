"""
Erneute Verarbeitung vorhandener gescrapeter Daten
==================================================

Dieses Hilfsskript nimmt vorhandene gescrapete Daten und verarbeitet sie erneut mit
verbesserter Kategorisierung, Metadaten-Anreicherung und besserer Organisation.

Verwenden Sie dies, um Daten zu aktualisieren, die mit der alten Pipeline gescraped wurden,
auf das neue erweiterte Format, ohne alles neu scrapen zu müssen.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from collections import defaultdict

# Füge übergeordnetes Verzeichnis zum Pfad für Imports hinzu
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper.batch_scraper import ScrapedContent
from src.scraper.vector_store import VectorStore, VectorStoreConfig
from src.scraper.crawler_scraper_pipeline import categorize_url, enrich_metadata

logger = logging.getLogger(__name__)


def load_scraped_data(filepath: Path) -> List[ScrapedContent]:
    """
    Lade gescrapete Daten aus JSON-Datei.
    
    Args:
        filepath: Pfad zur scraped_data.json-Datei
        
    Returns:
        Liste von ScrapedContent-Objekten
    """
    with filepath.open('r', encoding='utf-8') as f:
        data = json.load(f)
    
    scraped_contents = []
    for item in data:
        # Verarbeite sowohl Dict- als auch Objekt-Formate
        if isinstance(item, dict):
            scraped_contents.append(ScrapedContent(**item))
        else:
            scraped_contents.append(item)
    
    return scraped_contents


def reprocess_data(
    input_file: Path,
    output_dir: Path,
    organize_by_category: bool = True
) -> Dict[str, Any]:
    """
    Verarbeite vorhandene gescrapete Daten erneut mit erweiterten Funktionen.
    
    Args:
        input_file: Pfad zur vorhandenen scraped_data.json
        output_dir: Verzeichnis zum Speichern der neu verarbeiteten Daten
        organize_by_category: Ob nach Kategorie organisiert werden soll
        
    Returns:
        Statistik-Dictionary
    """
    logger.info("=" * 80)
    logger.info("Starting Data Reprocessing")
    logger.info("=" * 80)
    
    # Lade vorhandene Daten
    logger.info(f"\n[Stage 1/3] Loading data from {input_file}...")
    scraped_data = load_scraped_data(input_file)
    successful_scrapes = [content for content in scraped_data if content.success]
    logger.info(f"✓ Loaded {len(successful_scrapes)} successful scrapes")
    
    # Kategorisiere und reichere an
    logger.info("\n[Stage 2/3] Categorizing and Enriching Content...")
    categorized_content = defaultdict(list)
    category_stats = defaultdict(int)
    
    for content in successful_scrapes:
        category = categorize_url(content.url)
        enriched_metadata = enrich_metadata(content, category)
        
        # Aktualisiere Content-Metadaten
        content.metadata.update(enriched_metadata)
        
        # Organisiere nach Kategorie
        categorized_content[category].append(content)
        category_stats[category] += 1
    
    logger.info(f"✓ Categorized content into {len(category_stats)} categories:")
    for category, count in sorted(category_stats.items()):
        logger.info(f"  - {category}: {count} pages")
    
    # Speichere in Vektordatenbank
    logger.info("\n[Stage 3/3] Storing in Vector Database...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    total_docs = 0
    if organize_by_category:
        # Erstelle separate Collection für jede Kategorie
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
        # Einzelne Collection
        vector_config = VectorStoreConfig(
            persist_directory=str(output_dir / "vector_db"),
            collection_name="wiso_scraped_content"
        )
        
        vector_store = VectorStore(vector_config)
        total_docs = vector_store.add_scraped_content(successful_scrapes)
        logger.info(f"  ✓ Stored {total_docs} documents in single collection")
    
    # Erstelle Bericht
    stats = {
        "timestamp": datetime.now().isoformat(),
        "input_file": str(input_file),
        "output_dir": str(output_dir),
        "results": {
            "total_pages": len(scraped_data),
            "successful_pages": len(successful_scrapes),
            "categories_found": len(category_stats),
            "category_distribution": dict(category_stats),
            "total_documents_stored": total_docs
        }
    }
    
    # Speichere Bericht
    report_file = output_dir / "reprocessing_report.json"
    with report_file.open('w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    logger.info("\n" + "=" * 80)
    logger.info("Reprocessing Completed Successfully!")
    logger.info("=" * 80)
    logger.info(f"📊 Results Summary:")
    logger.info(f"   • Pages Processed: {len(successful_scrapes)}")
    logger.info(f"   • Documents Stored: {total_docs}")
    logger.info(f"   • Categories: {len(category_stats)}")
    logger.info(f"   • Report saved to: {report_file}")
    logger.info("=" * 80)
    
    return stats


def main():
    """Command line interface for reprocessing."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Reprocess existing scraped data with enhanced features"
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path(__file__).parent / "data_analysis" / "scraped_data.json",
        help="Path to existing scraped_data.json"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data"),
        help="Directory to store reprocessed data"
    )
    parser.add_argument(
        "--organize-by-category",
        action="store_true",
        default=True,
        help="Organize content into separate collections by category"
    )
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Set logging level"
    )
    
    args = parser.parse_args()
    
    # Konfiguriere Logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    try:
        stats = reprocess_data(
            input_file=args.input_file,
            output_dir=args.output_dir,
            organize_by_category=args.organize_by_category
        )
        
        print("\n✅ Reprocessing completed successfully!")
        print(f"📁 Results saved to: {args.output_dir}")
        
    except Exception as e:
        logger.error(f"Reprocessing failed: {e}", exc_info=True)
        print(f"\n❌ Reprocessing failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
