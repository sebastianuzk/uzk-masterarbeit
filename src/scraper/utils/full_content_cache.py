"""
Vollständiges Content-Storage System
===================================

Erweitert URLCache um vollständige Content-Speicherung
"""

import sqlite3
import gzip
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import logging

from src.scraper.utils.url_cache import URLCache

logger = logging.getLogger(__name__)


class FullContentCache(URLCache):
    """
    Erweiterte Version des URLCache mit vollständiger Content-Speicherung.
    
    Zusätzliche Features:
    - Vollständige HTML/Text-Speicherung (komprimiert)
    - Wiederverwendung ohne erneute Requests
    - Content-Retrieval ohne Network-Zugriff
    - Offline-Browsing Möglichkeit
    """
    
    def _create_tables(self):
        """Erstelle Datenbank-Tabellen mit Content-Storage."""
        # Basis-Tabellen erstellen
        super()._create_tables()
        
        # Erweiterte Content-Tabelle
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS full_content (
                url TEXT PRIMARY KEY,
                raw_html TEXT NOT NULL,           -- Vollständiges HTML (komprimiert)
                cleaned_text TEXT,                -- Bereinigter Text
                title TEXT,                       -- Seiten-Titel
                meta_description TEXT,            -- Meta-Description
                links_json TEXT,                  -- Gefundene Links als JSON
                images_json TEXT,                 -- Bilder-URLs als JSON
                file_size INTEGER,                -- Original-Dateigröße
                compressed_size INTEGER,          -- Komprimierte Größe
                extraction_metadata TEXT,         -- Extraktion-Metadaten
                storage_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (url) REFERENCES url_cache(url)
            )
        ''')
        
        # Performance-Indices
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_title 
            ON full_content(title)
        ''')
        
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_content_size 
            ON full_content(file_size)
        ''')
        
        self.conn.commit()

    def store_full_content(
        self,
        url: str,
        raw_html: str,
        cleaned_text: str = None,
        title: str = None,
        meta_description: str = None,
        links: List[str] = None,
        images: List[str] = None,
        extraction_metadata: Dict[str, Any] = None
    ):
        """
        Speichere vollständigen Content für eine URL.
        
        Args:
            url: URL
            raw_html: Vollständiges HTML
            cleaned_text: Bereinigter Text
            title: Seiten-Titel
            meta_description: Meta-Description
            links: Gefundene Links
            images: Gefundene Bilder
            extraction_metadata: Metadaten der Extraktion
        """
        # Komprimiere HTML
        compressed_html = gzip.compress(raw_html.encode('utf-8'))
        
        # Größen berechnen
        original_size = len(raw_html.encode('utf-8'))
        compressed_size = len(compressed_html)
        
        # JSON-Serialisierung
        links_json = json.dumps(links or [])
        images_json = json.dumps(images or [])
        metadata_json = json.dumps(extraction_metadata or {})
        
        # In Datenbank speichern
        self.conn.execute('''
            INSERT OR REPLACE INTO full_content 
            (url, raw_html, cleaned_text, title, meta_description, 
             links_json, images_json, file_size, compressed_size, extraction_metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            url, compressed_html, cleaned_text, title, meta_description,
            links_json, images_json, original_size, compressed_size, metadata_json
        ))
        
        self.conn.commit()
        
        compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
        logger.debug(f"Content gespeichert für {url}: {original_size} bytes → {compressed_size} bytes ({compression_ratio:.1f}% Kompression)")

    def get_full_content(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Lade vollständigen Content für eine URL.
        
        Args:
            url: URL
            
        Returns:
            Dictionary mit vollständigem Content oder None
        """
        cursor = self.conn.execute('''
            SELECT fc.*, uc.last_scraped, uc.category
            FROM full_content fc
            JOIN url_cache uc ON fc.url = uc.url
            WHERE fc.url = ?
        ''', (url,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        # Dekomprimiere HTML
        try:
            raw_html = gzip.decompress(row['raw_html']).decode('utf-8')
        except Exception as e:
            logger.error(f"Fehler beim Dekomprimieren von {url}: {e}")
            return None
        
        # JSON deserialisieren
        links = json.loads(row['links_json']) if row['links_json'] else []
        images = json.loads(row['images_json']) if row['images_json'] else []
        metadata = json.loads(row['extraction_metadata']) if row['extraction_metadata'] else {}
        
        return {
            'url': url,
            'raw_html': raw_html,
            'cleaned_text': row['cleaned_text'],
            'title': row['title'],
            'meta_description': row['meta_description'],
            'links': links,
            'images': images,
            'file_size': row['file_size'],
            'compressed_size': row['compressed_size'],
            'extraction_metadata': metadata,
            'last_scraped': row['last_scraped'],
            'category': row['category']
        }

    def has_full_content(self, url: str) -> bool:
        """Prüfe ob vollständiger Content für URL gespeichert ist."""
        cursor = self.conn.execute(
            'SELECT 1 FROM full_content WHERE url = ?', (url,)
        )
        return cursor.fetchone() is not None

    def get_cached_content_stats(self) -> Dict[str, Any]:
        """Erhalte Statistiken über gespeicherten Content."""
        # Gesamt-Statistiken
        cursor = self.conn.execute('''
            SELECT 
                COUNT(*) as total_pages,
                SUM(file_size) as total_original_size,
                SUM(compressed_size) as total_compressed_size,
                AVG(file_size) as avg_page_size,
                MIN(storage_timestamp) as first_stored,
                MAX(storage_timestamp) as last_stored
            FROM full_content
        ''')
        
        stats = dict(cursor.fetchone())
        
        # Kompressionsrate
        if stats['total_original_size'] and stats['total_compressed_size']:
            compression_ratio = (1 - stats['total_compressed_size'] / stats['total_original_size']) * 100
            stats['compression_ratio'] = f"{compression_ratio:.1f}%"
        else:
            stats['compression_ratio'] = "0%"
        
        # Kategorien-Verteilung
        cursor = self.conn.execute('''
            SELECT uc.category, COUNT(*) as count, SUM(fc.file_size) as total_size
            FROM full_content fc
            JOIN url_cache uc ON fc.url = uc.url
            GROUP BY uc.category
            ORDER BY count DESC
        ''')
        
        stats['by_category'] = {
            row['category']: {
                'count': row['count'],
                'total_size': row['total_size']
            }
            for row in cursor.fetchall()
        }
        
        # Top größte Seiten
        cursor = self.conn.execute('''
            SELECT fc.url, fc.title, fc.file_size
            FROM full_content fc
            ORDER BY fc.file_size DESC
            LIMIT 10
        ''')
        
        stats['largest_pages'] = [
            {
                'url': row['url'],
                'title': row['title'] or 'Untitled',
                'size': row['file_size']
            }
            for row in cursor.fetchall()
        ]
        
        return stats

    def search_content(
        self,
        query: str,
        search_in: List[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Volltext-Suche im gespeicherten Content.
        
        Args:
            query: Suchbegriff
            search_in: Liste der zu durchsuchenden Felder ['title', 'text', 'meta']
            limit: Maximale Anzahl Ergebnisse
            
        Returns:
            Liste von Suchergebnissen
        """
        search_in = search_in or ['title', 'cleaned_text', 'meta_description']
        
        # Build search query
        conditions = []
        params = []
        
        for field in search_in:
            if field in ['title', 'cleaned_text', 'meta_description']:
                conditions.append(f"fc.{field} LIKE ?")
                params.append(f"%{query}%")
        
        if not conditions:
            return []
        
        where_clause = " OR ".join(conditions)
        
        cursor = self.conn.execute(f'''
            SELECT fc.url, fc.title, fc.meta_description, fc.file_size, 
                   uc.category, uc.last_scraped,
                   CASE 
                       WHEN fc.title LIKE ? THEN 100
                       WHEN fc.meta_description LIKE ? THEN 50  
                       ELSE 10
                   END as relevance_score
            FROM full_content fc
            JOIN url_cache uc ON fc.url = uc.url
            WHERE {where_clause}
            ORDER BY relevance_score DESC, fc.file_size DESC
            LIMIT ?
        ''', [f"%{query}%", f"%{query}%"] + params + [limit])
        
        return [dict(row) for row in cursor.fetchall()]

    def export_content(self, url: str, output_path: str) -> bool:
        """
        Exportiere gespeicherten Content als HTML-Datei.
        
        Args:
            url: URL
            output_path: Ausgabe-Pfad
            
        Returns:
            True wenn erfolgreich
        """
        content = self.get_full_content(url)
        if not content:
            return False
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content['raw_html'])
            
            logger.info(f"Content exportiert: {url} → {output_path}")
            return True
        
        except Exception as e:
            logger.error(f"Export-Fehler für {url}: {e}")
            return False

    def bulk_export(self, output_dir: str, category: str = None) -> int:
        """
        Exportiere alle gespeicherten Inhalte.
        
        Args:
            output_dir: Ausgabe-Verzeichnis
            category: Optional: Nur bestimmte Kategorie
            
        Returns:
            Anzahl exportierter Dateien
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Build query
        query = '''
            SELECT fc.url, fc.title
            FROM full_content fc
            JOIN url_cache uc ON fc.url = uc.url
        '''
        params = []
        
        if category:
            query += ' WHERE uc.category = ?'
            params.append(category)
        
        cursor = self.conn.execute(query, params)
        
        exported_count = 0
        for row in cursor.fetchall():
            url = row['url']
            title = row['title'] or 'untitled'
            
            # Erzeuge sicheren Dateinamen
            safe_filename = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_filename = safe_filename[:50] + '.html'
            
            file_path = output_path / safe_filename
            
            if self.export_content(url, str(file_path)):
                exported_count += 1
        
        return exported_count

    def cleanup_old_content(self, days: int = 180):
        """
        Lösche alten Content (aber behalte URL-Cache).
        
        Args:
            days: Alter in Tagen
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor = self.conn.execute('''
            DELETE FROM full_content 
            WHERE url IN (
                SELECT fc.url FROM full_content fc
                JOIN url_cache uc ON fc.url = uc.url
                WHERE uc.last_scraped < ?
            )
        ''', (cutoff,))
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        logger.info(f"{deleted} alte Content-Einträge gelöscht (älter als {days} Tage)")
        return deleted