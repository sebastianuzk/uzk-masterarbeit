"""
Import Script für Content Database
=================================

Importiert alle HTML- und PDF-Inhalte aus Cache in die permanente
Content Database.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any
import sys
from tqdm import tqdm

# Füge Parent-Directory zum Path hinzu
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.scraper.utils.content_database import ContentDatabase
from src.scraper.utils.html_cache import HTMLContentCache
from src.scraper.utils.pdf_extractor import PDFExtractor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def categorize_url(url: str) -> str:
    """Kategorisiere URL basierend auf Pfad."""
    url_lower = url.lower()
    
    if '/studium/' in url_lower or '/studiengaenge/' in url_lower:
        return 'studium'
    elif '/forschung/' in url_lower or '/research/' in url_lower:
        return 'forschung'
    elif '/fakultaet/' in url_lower or '/ueber-uns/' in url_lower:
        return 'allgemein'
    elif '/service/' in url_lower or '/beratung/' in url_lower:
        return 'services'
    else:
        return 'sonstiges'


def extract_title_from_html(html_content: str) -> str:
    """Extrahiere Titel aus HTML (einfache Methode)."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Versuche verschiedene Titel-Quellen
        title = None
        
        # 1. <title> Tag
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        
        # 2. <h1> Tag
        if not title:
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text().strip()
        
        # 3. og:title Meta-Tag
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = og_title['content'].strip()
        
        return title or "Unbekannter Titel"
        
    except Exception as e:
        logger.warning(f"Fehler beim Titel-Extrahieren: {e}")
        return "Unbekannter Titel"


def extract_text_from_html(html_content: str) -> str:
    """Extrahiere Text aus HTML."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Entferne Script- und Style-Elemente
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        
        # Hole Text
        text = soup.get_text(separator=' ', strip=True)
        
        # Bereinige Whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
        
    except Exception as e:
        logger.error(f"Fehler beim Text-Extrahieren: {e}")
        return ""


def sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Konvertiert alle Metadaten-Werte zu JSON-serialisierbaren Typen.
    
    Behebt Probleme mit PyPDF2 IndirectObject und anderen nicht-serialisierbaren Objekten.
    
    Args:
        metadata: Dictionary mit potentiell nicht-serialisierbaren Werten
        
    Returns:
        Dictionary mit nur JSON-sicheren Werten (str, int, float, bool, None, list)
    """
    clean = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool, type(None))):
            # Bereits JSON-sicher
            clean[key] = value
        elif isinstance(value, (list, tuple)):
            # Listen/Tupel: Jedes Element zu String konvertieren
            clean[key] = [str(v) for v in value]
        elif isinstance(value, dict):
            # Nested Dictionary: Rekursiv bereinigen
            clean[key] = sanitize_metadata(value)
        else:
            # Alles andere (z.B. PyPDF2.IndirectObject): Zu String
            clean[key] = str(value)
    return clean


def import_html_cache(content_db: ContentDatabase, html_cache_path: Path) -> Dict[str, int]:
    """
    Importiere alle HTML-Seiten aus Cache.
    
    Returns:
        Statistiken über Import
    """
    logger.info("Starte HTML-Import aus Cache...")
    stats = {'success': 0, 'skipped': 0, 'errors': 0}
    
    try:
        # Öffne HTML-Cache Datenbank direkt
        with sqlite3.connect(html_cache_path / "html_cache.db") as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM html_cache")
            total = cursor.fetchone()[0]
            
            logger.info(f"Gefunden: {total} HTML-Seiten im Cache")
            
            cursor = conn.execute("""
                SELECT url, file_path, content_type, status_code
                FROM html_cache
                WHERE status_code = 200
            """)
            
            for url, file_path, content_type, status_code in tqdm(
                cursor.fetchall(), 
                desc="HTML importieren",
                total=total
            ):
                try:
                    # Lade komprimierten Content
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        logger.warning(f"Datei nicht gefunden: {file_path}")
                        stats['skipped'] += 1
                        continue
                    
                    import gzip
                    with open(file_path_obj, 'rb') as f:
                        compressed_data = f.read()
                    html_content = gzip.decompress(compressed_data).decode('utf-8')
                    
                    # Extrahiere Titel und Text
                    title = extract_title_from_html(html_content)
                    text_content = extract_text_from_html(html_content)
                    
                    if not text_content.strip():
                        logger.warning(f"Leerer Text-Content: {url}")
                        stats['skipped'] += 1
                        continue
                    
                    # Kategorisiere
                    category = categorize_url(url)
                    
                    # Speichere in Content DB
                    metadata = {
                        'content_type': content_type,
                        'status_code': status_code,
                        'source': 'html_cache'
                    }
                    
                    doc_id = content_db.add_document(
                        url=url,
                        title=title,
                        content=text_content,
                        content_type='html',
                        category=category,
                        metadata=metadata
                    )
                    
                    if doc_id:
                        stats['success'] += 1
                    else:
                        stats['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Fehler bei {url}: {e}")
                    stats['errors'] += 1
        
        logger.info(f"HTML-Import abgeschlossen: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Fehler beim HTML-Import: {e}")
        return stats


def import_pdf_cache(content_db: ContentDatabase, pdf_cache_path: Path) -> Dict[str, int]:
    """
    Importiere alle PDFs aus Cache.
    
    Returns:
        Statistiken über Import
    """
    logger.info("Starte PDF-Import aus Cache...")
    stats = {'success': 0, 'skipped': 0, 'errors': 0}
    
    try:
        pdf_extractor = PDFExtractor()
        
        # Finde alle PDFs
        pdf_files = list(pdf_cache_path.glob("**/*.pdf"))
        logger.info(f"Gefunden: {len(pdf_files)} PDFs im Cache")
        
        for pdf_path in tqdm(pdf_files, desc="PDFs importieren"):
            try:
                # Extrahiere Text direkt mit pypdf2/pdfplumber
                text, pdf_metadata = pdf_extractor.extract_text_pypdf2(pdf_path)
                
                if not text or not text.strip():
                    # Versuche pdfplumber als Fallback
                    text, pdf_metadata = pdf_extractor.extract_text_pdfplumber(pdf_path)
                
                if not text or not text.strip():
                    logger.warning(f"Leerer PDF-Content: {pdf_path}")
                    stats['skipped'] += 1
                    continue
                
                # Verwende Dateipfad als "URL" für PDFs
                url = f"file://{pdf_path.as_posix()}"
                title = pdf_metadata.get('title') or pdf_path.stem
                
                # Kategorisiere basierend auf Pfad
                category = categorize_url(str(pdf_path))
                
                # Bereinige PDF-Metadaten für JSON-Serialisierung
                clean_pdf_metadata = sanitize_metadata(pdf_metadata)
                
                # Speichere in Content DB
                metadata = {
                    'file_path': str(pdf_path),
                    'source': 'pdf_cache',
                    'pdf_metadata': clean_pdf_metadata
                }
                
                doc_id = content_db.add_document(
                    url=url,
                    title=title,
                    content=text,
                    content_type='pdf',
                    category=category,
                    metadata=metadata
                )
                
                if doc_id:
                    stats['success'] += 1
                else:
                    stats['errors'] += 1
                    
            except Exception as e:
                logger.error(f"Fehler bei {pdf_path}: {e}")
                stats['errors'] += 1
        
        logger.info(f"PDF-Import abgeschlossen: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Fehler beim PDF-Import: {e}")
        return stats


def main():
    """Hauptfunktion für Import."""
    logger.info("=" * 80)
    logger.info("Content Database Import")
    logger.info("=" * 80)
    
    # Pfade
    base_dir = Path(__file__).parent.parent.parent.parent
    data_dir = base_dir / "data"
    html_cache_path = data_dir / "html_cache"
    pdf_cache_path = data_dir / "pdf_cache"
    content_db_path = data_dir / "content_database.db"
    
    logger.info(f"Basis-Verzeichnis: {base_dir}")
    logger.info(f"HTML-Cache: {html_cache_path}")
    logger.info(f"PDF-Cache: {pdf_cache_path}")
    logger.info(f"Content-DB: {content_db_path}")
    
    # Prüfe Pfade
    if not html_cache_path.exists():
        logger.error(f"HTML-Cache nicht gefunden: {html_cache_path}")
        return
    
    if not pdf_cache_path.exists():
        logger.warning(f"PDF-Cache nicht gefunden: {pdf_cache_path}")
    
    # Initialisiere Content Database
    logger.info("\nInitialisiere Content Database...")
    content_db = ContentDatabase(content_db_path)
    
    # Import HTML
    logger.info("\n" + "=" * 80)
    html_stats = import_html_cache(content_db, html_cache_path)
    
    # Import PDFs
    logger.info("\n" + "=" * 80)
    pdf_stats = import_pdf_cache(content_db, pdf_cache_path)
    
    # Gesamtstatistik
    logger.info("\n" + "=" * 80)
    logger.info("Import abgeschlossen!")
    logger.info("=" * 80)
    logger.info(f"HTML: {html_stats['success']} erfolgreich, "
                f"{html_stats['skipped']} übersprungen, "
                f"{html_stats['errors']} Fehler")
    logger.info(f"PDF:  {pdf_stats['success']} erfolgreich, "
                f"{pdf_stats['skipped']} übersprungen, "
                f"{pdf_stats['errors']} Fehler")
    
    # Datenbank-Statistiken
    logger.info("\n" + "=" * 80)
    logger.info("Datenbank-Statistiken:")
    logger.info("=" * 80)
    db_stats = content_db.get_statistics()
    
    logger.info(f"Gesamt: {db_stats.get('total_documents', 0)} Dokumente")
    logger.info(f"\nNach Typ:")
    for content_type, count in db_stats.get('by_type', {}).items():
        logger.info(f"  - {content_type}: {count}")
    
    logger.info(f"\nNach Kategorie:")
    for category, count in sorted(
        db_stats.get('by_category', {}).items(), 
        key=lambda x: x[1], 
        reverse=True
    ):
        logger.info(f"  - {category}: {count}")
    
    storage = db_stats.get('storage', {})
    logger.info(f"\nSpeicher:")
    logger.info(f"  - Original: {storage.get('original_mb', 0)} MB")
    logger.info(f"  - Komprimiert: {storage.get('compressed_mb', 0)} MB")
    logger.info(f"  - Kompressionsrate: {storage.get('compression_ratio', 0)}%")
    
    content_db.close()
    logger.info("\nFertig!")


if __name__ == "__main__":
    main()
