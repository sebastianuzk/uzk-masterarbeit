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
from src.scraper.utils.pdf_extractor import PDFExtractor, sanitize_metadata

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
    """
    DEPRECATED: Diese Funktion wird nicht mehr verwendet.
    Für Naive-RAG speichern wir RAW-HTML direkt in die Datenbank.
    
    Diese Funktion bleibt nur für Kompatibilität erhalten.
    """
    # Für RAW-HTML Speicherung geben wir einfach den Original-Content zurück
    return html_content


def reimport_html_only(content_db: ContentDatabase, html_cache_path: Path) -> Dict[str, int]:
    """
    Lösche alte HTML-Einträge und importiere sie mit RAW-HTML neu.
    PDFs bleiben unverändert.
    
    Returns:
        Statistiken über Import
    """
    stats = {'deleted': 0, 'success': 0, 'skipped': 0, 'errors': 0}
    
    try:
        # Lösche zuerst alle HTML-Einträge
        logger.info("Lösche alte HTML-Einträge...")
        with sqlite3.connect(content_db.db_path, timeout=30.0) as conn:
            cursor = conn.execute("DELETE FROM documents WHERE content_type='html'")
            stats['deleted'] = cursor.rowcount
            conn.commit()
        
        logger.info(f"Gelöscht: {stats['deleted']} alte HTML-Einträge")
        
        # Importiere HTMLs neu mit RAW-HTML
        import gzip
        
        # Öffne HTML-Cache Datenbank
        with sqlite3.connect(html_cache_path / "html_cache.db") as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM html_cache WHERE status_code = 200")
            total = cursor.fetchone()[0]
            
            logger.info(f"Gefunden: {total} HTML-Seiten im Cache")
            
            cursor = conn.execute("""
                SELECT url, file_path, content_type, status_code
                FROM html_cache
                WHERE status_code = 200
            """)
            
            for url, file_path, content_type, status_code in tqdm(
                cursor.fetchall(), 
                desc="HTMLs neu importieren (RAW-HTML)",
                total=total
            ):
                try:
                    # Lade RAW-HTML
                    file_path_obj = Path(file_path)
                    if not file_path_obj.exists():
                        logger.warning(f"Datei nicht gefunden: {file_path}")
                        stats['skipped'] += 1
                        continue
                    
                    with open(file_path_obj, 'rb') as f:
                        compressed_data = f.read()
                    html_content = gzip.decompress(compressed_data).decode('utf-8')
                    
                    # Extrahiere nur Titel
                    title = extract_title_from_html(html_content)
                    
                    if not html_content.strip():
                        logger.warning(f"Leerer HTML-Content: {url}")
                        stats['skipped'] += 1
                        continue
                    
                    # Kategorisiere
                    category = categorize_url(url)
                    
                    # Speichere RAW-HTML in Content DB
                    metadata = {
                        'content_type': content_type,
                        'status_code': status_code,
                        'source': 'html_cache',
                        'raw_html': True
                    }
                    
                    doc_id = content_db.add_document(
                        url=url,
                        title=title,
                        content=html_content,  # RAW-HTML!
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
        
        logger.info(f"HTML-Reimport abgeschlossen: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Fehler beim HTML-Reimport: {e}")
        return stats


def reimport_pdfs_only(content_db: ContentDatabase, pdf_cache_path: Path) -> Dict[str, int]:
    """
    Lösche alte PDF-Einträge und importiere sie mit korrekten Metadaten neu.
    HTMLs bleiben unverändert.
    
    Returns:
        Statistiken über Import
    """
    stats = {'deleted': 0, 'success': 0, 'skipped': 0, 'errors': 0}
    
    try:
        # Lösche zuerst alle PDF-Einträge
        logger.info("Lösche alte PDF-Einträge...")
        with sqlite3.connect(content_db.db_path, timeout=30.0) as conn:
            cursor = conn.execute("DELETE FROM documents WHERE content_type='pdf'")
            stats['deleted'] = cursor.rowcount
            conn.commit()
        
        logger.info(f"Gelöscht: {stats['deleted']} alte PDF-Einträge")
        
        # Importiere PDFs neu mit korrekten Metadaten
        pdf_extractor = PDFExtractor()
        
        # Finde alle PDFs
        pdf_files = list(pdf_cache_path.glob("**/*.pdf"))
        logger.info(f"Gefunden: {len(pdf_files)} PDFs im Cache")
        
        for pdf_path in tqdm(pdf_files, desc="PDFs neu importieren"):
            try:
                # Extrahiere Text mit PyPDF2 (enthält bereits sanitize_metadata)
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
                
                # Hole Titel aus Metadaten (bereits durch sanitize_metadata bereinigt in pdf_extractor)
                title = pdf_metadata.get('title', '') or pdf_path.stem
                
                # Wenn Titel leer oder nur Whitespace, nutze Dateinamen
                if not title or not title.strip():
                    title = pdf_path.stem
                
                # Kategorisiere basierend auf Pfad
                category = categorize_url(str(pdf_path))
                
                # Metadaten sind bereits durch sanitize_metadata() in extract_text_pypdf2() bereinigt!
                metadata = {
                    'file_path': str(pdf_path),
                    'source': 'pdf_cache',
                    'pdf_metadata': pdf_metadata,  # Bereits sanitized!
                    'extraction_method': 'pypdf2'
                }
                
                # Speichere in Content DB
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
        
        logger.info(f"PDF-Reimport abgeschlossen: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Fehler beim PDF-Reimport: {e}")
        return stats


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
                    
                    # 🔥 WICHTIG: Speichere RAW-HTML für Naive-RAG!
                    # Extrahiere nur Titel, aber behalte HTML für Content
                    title = extract_title_from_html(html_content)
                    
                    # Speichere RAW-HTML statt extrahiertem Text
                    raw_content = html_content
                    
                    if not raw_content.strip():
                        logger.warning(f"Leerer HTML-Content: {url}")
                        stats['skipped'] += 1
                        continue
                    
                    # Kategorisiere
                    category = categorize_url(url)
                    
                    # Speichere in Content DB mit RAW-HTML
                    metadata = {
                        'content_type': content_type,
                        'status_code': status_code,
                        'source': 'html_cache',
                        'raw_html': True  # Markierung dass dies RAW-HTML ist
                    }
                    
                    doc_id = content_db.add_document(
                        url=url,
                        title=title,
                        content=raw_content,  # RAW-HTML speichern!
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
                
                # Metadaten sind bereits durch sanitize_metadata() in extract_text_pypdf2() bereinigt
                # Speichere in Content DB
                metadata = {
                    'file_path': str(pdf_path),
                    'source': 'pdf_cache',
                    'pdf_metadata': pdf_metadata  # Bereits sanitized in pdf_extractor!
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
    import sys
    
    # Prüfe Kommandozeilen-Argumente
    reimport_pdfs = '--reimport-pdfs' in sys.argv
    reimport_html = '--reimport-html' in sys.argv
    
    logger.info("=" * 80)
    if reimport_pdfs:
        logger.info("Content Database - PDF Reimport")
    elif reimport_html:
        logger.info("Content Database - HTML Reimport (RAW-HTML)")
    else:
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
    
    if reimport_html:
        # Nur HTMLs reimportieren mit RAW-HTML
        logger.info("\n" + "=" * 80)
        logger.info("ACHTUNG: Nur HTMLs werden reimportiert mit RAW-HTML, PDFs bleiben unverändert!")
        logger.info("=" * 80)
        
        # Zeige aktuelle Statistik
        db_stats = content_db.get_statistics()
        logger.info(f"\nAktuell in Datenbank:")
        logger.info(f"  Gesamt: {db_stats.get('total_documents', 0)} Dokumente")
        for content_type, count in db_stats.get('by_type', {}).items():
            logger.info(f"  - {content_type}: {count}")
        
        html_stats = reimport_html_only(content_db, html_cache_path)
        pdf_stats = {'success': 0, 'skipped': 0, 'errors': 0}  # Dummy für Report
        
    elif reimport_pdfs:
        # Nur PDFs reimportieren
        logger.info("\n" + "=" * 80)
        logger.info("ACHTUNG: Nur PDFs werden reimportiert, HTMLs bleiben unverändert!")
        logger.info("=" * 80)
        
        # Zeige aktuelle Statistik
        db_stats = content_db.get_statistics()
        logger.info(f"\nAktuell in Datenbank:")
        logger.info(f"  Gesamt: {db_stats.get('total_documents', 0)} Dokumente")
        for content_type, count in db_stats.get('by_type', {}).items():
            logger.info(f"  - {content_type}: {count}")
        
        pdf_stats = reimport_pdfs_only(content_db, pdf_cache_path)
        html_stats = {'success': 0, 'skipped': 0, 'errors': 0}  # Dummy für Report
        
    else:
        # Vollständiger Import (HTML + PDF)
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
