"""
Import Script für Content Database
=================================

Importiert alle HTML- und PDF-Inhalte aus Cache in die permanente
Content Database.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict
import sys
from tqdm import tqdm

# Füge Parent-Directory zum Path hinzu
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.scraper.utils.content_database import ContentDatabase
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


def extract_clean_text_from_html(html: str, url: str = None) -> dict:
    """
    Konvertiert HTML in strukturierten Markdown-ähnlichen Text.
    
    Entfernt Navigation, Footer, Scripts und behält die inhaltliche Struktur
    mit Überschriften, Listen, Tabellen und Absätzen.
    
    Args:
        html: RAW-HTML Content
        url: Optionale URL für Metadaten
        
    Returns:
        dict mit:
            - url: URL oder None
            - title: Seitentitel
            - clean_text: Strukturierter Markdown-ähnlicher Text
    """
    from bs4 import BeautifulSoup, NavigableString, Comment
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # === 1. GLOBAL ENTFERNEN ===
    # Entferne Scripts, Styles, etc.
    for tag_name in ['script', 'style', 'noscript', 'iframe']:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    
    # Entferne Kommentare
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    # Entferne Layout-Container
    for tag_name in ['header', 'nav', 'footer']:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    
    # Entferne Elemente mit typischen Layout-Klassen
    layout_classes = [
        'cookie', 'cookies', 'banner', 'navbar', 'breadcrumb', 'breadcrumbs',
        'social', 'footer', 'menu', 'navigation', 'sidebar', 'side-bar'
    ]
    for tag in soup.find_all(class_=True):
        if not hasattr(tag, 'attrs') or tag.attrs is None:
            continue
        classes = tag.get('class', [])
        if isinstance(classes, str):
            classes = [classes]
        if any(layout_class in ' '.join(classes).lower() for layout_class in layout_classes):
            tag.decompose()
    
    # === 2. TITEL EXTRAHIEREN ===
    title = None
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    
    if not title:
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
    
    if not title:
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            title = og_title['content'].strip()
    
    title = title or "Unbekannter Titel"
    
    # === 3. HAUPTINHALT FINDEN ===
    main_content = (
        soup.find('main') or
        soup.find('article') or
        soup.find('div', id='content') or
        soup.find('div', class_=lambda c: c and 'content' in str(c).lower()) or
        soup.body or
        soup
    )
    
    # === 4. MARKDOWN-KONVERTIERUNG ===
    def process_element(element, depth=0) -> str:
        """Rekursive Verarbeitung eines Elements."""
        if isinstance(element, NavigableString):
            text = str(element).strip()
            return text if text else ''
        
        if element.name is None:
            return ''
        
        tag_name = element.name.lower()
        result = []
        
        # Überschriften
        if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level = int(tag_name[1])
            text = element.get_text(strip=True)
            if text:
                result.append(f"\n{'#' * level} {text}\n")
        
        # Absätze
        elif tag_name == 'p':
            text = element.get_text(strip=True)
            if text:
                result.append(f"\n{text}\n")
        
        # Ungeordnete Listen
        elif tag_name == 'ul':
            for li in element.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                if text:
                    result.append(f"- {text}\n")
            result.append('\n')
        
        # Geordnete Listen
        elif tag_name == 'ol':
            for idx, li in enumerate(element.find_all('li', recursive=False), 1):
                text = li.get_text(strip=True)
                if text:
                    result.append(f"{idx}. {text}\n")
            result.append('\n')
        
        # Tabellen
        elif tag_name == 'table':
            rows = []
            
            # Header-Zeile
            thead = element.find('thead')
            if thead:
                headers = [th.get_text(strip=True) for th in thead.find_all(['th', 'td'])]
                if headers:
                    rows.append('| ' + ' | '.join(headers) + ' |')
                    rows.append('|' + '|'.join(['---' for _ in headers]) + '|')
            
            # Body-Zeilen
            tbody = element.find('tbody') or element
            for tr in tbody.find_all('tr'):
                cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
                if cells:
                    rows.append('| ' + ' | '.join(cells) + ' |')
            
            if rows:
                result.append('\n' + '\n'.join(rows) + '\n\n')
        
        # Listen-Items (falls einzeln verarbeitet)
        elif tag_name == 'li':
            text = element.get_text(strip=True)
            if text:
                result.append(f"- {text}\n")
        
        # Zeilenumbrüche
        elif tag_name == 'br':
            result.append('\n')
        
        # Horizontale Linien
        elif tag_name == 'hr':
            result.append('\n---\n\n')
        
        # Inline-Elemente mit Formatierung: Text extrahieren, aber Kinder rekursiv verarbeiten
        # (damit verschachtelte Strukturen wie <a><h2>Titel</h2></a> funktionieren)
        elif tag_name in ['span', 'strong', 'b', 'em', 'i', 'code']:
            # Prüfe ob Kinder Block-Elemente enthalten
            has_block_children = any(
                child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'section', 'ul', 'ol', 'table']
                for child in element.children
                if hasattr(child, 'name') and child.name
            )
            
            if has_block_children:
                # Rekursiv verarbeiten
                for child in element.children:
                    result.append(process_element(child, depth + 1))
            else:
                # Nur Text extrahieren
                text = element.get_text(strip=True)
                if text:
                    result.append(text + ' ')
        
        # Alle anderen Elemente: Rekursiv verarbeiten
        # (div, section, article, main, a, und alles Unbekannte)
        else:
            for child in element.children:
                result.append(process_element(child, depth + 1))
        
        return ''.join(result)
    
    # Verarbeite Hauptinhalt
    clean_text = process_element(main_content)
    
    # === 5. TEXT-BEREINIGUNG ===
    # Entferne mehrfache Leerzeilen
    lines = clean_text.split('\n')
    cleaned_lines = []
    prev_empty = False
    
    for line in lines:
        line_stripped = line.strip()
        if line_stripped:
            cleaned_lines.append(line_stripped)
            prev_empty = False
        elif not prev_empty:
            cleaned_lines.append('')
            prev_empty = True
    
    clean_text = '\n'.join(cleaned_lines).strip()
    
    # Entferne mehrfache Leerzeichen
    import re
    clean_text = re.sub(r' +', ' ', clean_text)
    
    return {
        'url': url,
        'title': title,
        'clean_text': clean_text
    }


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
                    
                    # Extrahiere strukturierten Text (Markdown-ähnlich)
                    result = extract_clean_text_from_html(html_content, url)
                    
                    if not result['clean_text'].strip():
                        logger.warning(f"Leerer Clean-Text: {url}")
                        stats['skipped'] += 1
                        continue
                    
                    # Kategorisiere
                    category = categorize_url(url)
                    
                    # Speichere strukturierten Text in Content DB
                    metadata = {
                        'content_type': content_type,
                        'status_code': status_code,
                        'source': 'html_cache',
                        'structured_text': True,  # Marker für Markdown-ähnliche Struktur
                        'extraction_method': 'markdown_conversion'
                    }
                    
                    doc_id = content_db.add_document(
                        url=url,
                        title=result['title'],
                        content=result['clean_text'],  # Strukturierter Markdown-Text!
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
                    
                    # Extrahiere strukturierten Text (Markdown-ähnlich)
                    result = extract_clean_text_from_html(html_content, url)
                    
                    if not result['clean_text'].strip():
                        logger.warning(f"Leerer Clean-Text: {url}")
                        stats['skipped'] += 1
                        continue
                    
                    # Kategorisiere
                    category = categorize_url(url)
                    
                    # Speichere strukturierten Text in Content DB
                    metadata = {
                        'content_type': content_type,
                        'status_code': status_code,
                        'source': 'html_cache',
                        'structured_text': True,  # Marker für Markdown-ähnliche Struktur
                        'extraction_method': 'markdown_conversion'
                    }
                    
                    doc_id = content_db.add_document(
                        url=url,
                        title=result['title'],
                        content=result['clean_text'],  # Strukturierter Markdown-Text!
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
    test_mode = '--test' in sys.argv
    reimport_pdfs = '--reimport-pdfs' in sys.argv
    reimport_html = '--reimport-html' in sys.argv
    
    # Test-Modus: Zeige Extraktion eines einzelnen HTML-Dokuments
    if test_mode:
        logger.info("=" * 80)
        logger.info("TEST-MODUS: HTML-Markdown-Extraktion")
        logger.info("=" * 80)
        
        # Pfade
        base_dir = Path(__file__).parent.parent.parent.parent
        data_dir = base_dir / "data"
        html_cache_path = data_dir / "html_cache"
        
        # Lade erste HTML-Datei aus Cache
        import gzip
        with sqlite3.connect(html_cache_path / "html_cache.db") as conn:
            cursor = conn.execute("""
                SELECT url, file_path
                FROM html_cache
                WHERE status_code = 200
                LIMIT 1
            """)
            url, file_path = cursor.fetchone()
        
        logger.info(f"\nVerarbeite Test-Dokument:")
        logger.info(f"URL: {url}")
        logger.info(f"Datei: {file_path}")
        
        # Lade HTML
        file_path_obj = Path(file_path)
        with open(file_path_obj, 'rb') as f:
            compressed_data = f.read()
        html_content = gzip.decompress(compressed_data).decode('utf-8')
        
        logger.info(f"HTML Größe: {len(html_content):,} Zeichen")
        
        # Extrahiere strukturierten Text
        result = extract_clean_text_from_html(html_content, url)
        
        logger.info(f"\nErgebnis:")
        logger.info(f"Titel: {result['title']}")
        logger.info(f"Clean Text Größe: {len(result['clean_text']):,} Zeichen")
        logger.info(f"Kompressionsrate: {len(result['clean_text']) / len(html_content) * 100:.1f}%")
        logger.info(f"\nVollständiger strukturierter Text:")
        logger.info("-" * 80)
        logger.info(result['clean_text'])
        logger.info("-" * 80)
        
        return
    
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
