"""
HTML Content Cache System
========================

Separates Caching-System für rohen HTML-Content während des Crawlings.
Vermeidet unnötige Requests und speichert HTML für spätere Verarbeitung.
"""

import json
import gzip
import hashlib
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import sqlite3
import threading

logger = logging.getLogger(__name__)

@dataclass
class CachedHTMLEntry:
    """Gespeicherter HTML-Content mit Metadaten."""
    url: str
    content: str
    content_type: str
    status_code: int
    headers: Dict[str, str]
    timestamp: float
    content_length: int
    encoding: str
    etag: Optional[str] = None
    last_modified: Optional[str] = None
    cache_hash: Optional[str] = None

class HTMLContentCache:
    """
    High-Performance HTML Content Cache.
    
    Features:
    - Komprimierte Speicherung (gzip)
    - Content-basierte Deduplizierung  
    - Flexible Retention-Policies
    - Thread-safe Operations
    - Bulk Import/Export
    """
    
    def __init__(self, cache_dir: Path, max_age_days: int = 30):
        """
        Initialisiere HTML Cache.
        
        Args:
            cache_dir: Verzeichnis für Cache-Dateien
            max_age_days: Maximales Alter in Tagen
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age_days = max_age_days
        
        # Cache-Struktur
        self.html_dir = self.cache_dir / "html"
        self.html_dir.mkdir(exist_ok=True)
        
        # Metadata-Database
        self.db_path = self.cache_dir / "html_cache.db"
        self.lock = threading.RLock()
        
        self._init_database()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0,
            'total_size': 0,
            'deduplicated': 0
        }

    def _init_database(self):
        """Initialisiere SQLite-Datenbank für Metadaten."""
        with sqlite3.connect(self.db_path, timeout=30.0) as conn:
            # Optimierungen für Concurrency und Performance
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA cache_size=10000")
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS html_cache (
                    url TEXT PRIMARY KEY,
                    file_path TEXT NOT NULL,
                    content_type TEXT,
                    status_code INTEGER,
                    headers TEXT,
                    timestamp REAL,
                    content_length INTEGER,
                    encoding TEXT,
                    etag TEXT,
                    last_modified TEXT,
                    cache_hash TEXT,
                    created_at REAL DEFAULT (julianday('now'))
                )
            """)
            
            # Index für Performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON html_cache(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_hash ON html_cache(cache_hash)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON html_cache(created_at)")
            
            conn.commit()

    def _generate_content_hash(self, content: str) -> str:
        """Generiere Hash für Content-Deduplizierung."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

    def _generate_file_path(self, url: str) -> Path:
        """Generiere Dateipfad basierend auf URL."""
        url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()
        # Hierarchische Struktur: html/ab/cd/abcdef123456.html.gz
        return self.html_dir / url_hash[:2] / url_hash[2:4] / f"{url_hash}.html.gz"

    def _compress_content(self, content: str) -> bytes:
        """Komprimiere HTML-Content."""
        return gzip.compress(content.encode('utf-8'))

    def _decompress_content(self, compressed_data: bytes) -> str:
        """Dekomprimiere HTML-Content."""
        return gzip.decompress(compressed_data).decode('utf-8')

    def contains(self, url: str) -> bool:
        """Prüfe ob URL im Cache ist und noch gültig."""
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    conn.execute("PRAGMA busy_timeout=10000")
                    cursor = conn.execute(
                        "SELECT timestamp FROM html_cache WHERE url = ?", 
                        (url,)
                    )
                    result = cursor.fetchone()
                    
                    if result:
                        timestamp = result[0]
                        age_days = (time.time() - timestamp) / (24 * 3600)
                        return age_days <= self.max_age_days
                    
                    return False
            except Exception as e:
                logger.warning(f"Fehler bei Cache-Check für {url}: {e}")
                return False

    def get(self, url: str) -> Optional[CachedHTMLEntry]:
        """
        Hole HTML-Content aus Cache.
        
        Args:
            url: URL des gesuchten Contents
            
        Returns:
            CachedHTMLEntry oder None
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=10.0) as conn:
                    conn.execute("PRAGMA busy_timeout=10000")
                    cursor = conn.execute("""
                        SELECT file_path, content_type, status_code, headers, timestamp,
                               content_length, encoding, etag, last_modified, cache_hash
                        FROM html_cache WHERE url = ?
                    """, (url,))
                    
                    result = cursor.fetchone()
                    if not result:
                        self.stats['misses'] += 1
                        return None
                    
                    file_path, content_type, status_code, headers_json, timestamp, \
                    content_length, encoding, etag, last_modified, cache_hash = result
                    
                    # Prüfe Alter
                    age_days = (time.time() - timestamp) / (24 * 3600)
                    if age_days > self.max_age_days:
                        self.stats['misses'] += 1
                        return None
                    
                    # Lade Content
                    try:
                        file_path_obj = Path(file_path)
                        if not file_path_obj.exists():
                            self.stats['misses'] += 1
                            return None
                        
                        with open(file_path_obj, 'rb') as f:
                            compressed_data = f.read()
                        
                        content = self._decompress_content(compressed_data)
                        headers = json.loads(headers_json) if headers_json else {}
                        
                        self.stats['hits'] += 1
                        
                        return CachedHTMLEntry(
                            url=url,
                            content=content,
                            content_type=content_type or 'text/html',
                            status_code=status_code or 200,
                            headers=headers,
                            timestamp=timestamp,
                            content_length=content_length or len(content),
                            encoding=encoding or 'utf-8',
                            etag=etag,
                            last_modified=last_modified,
                            cache_hash=cache_hash
                        )
                        
                    except Exception as e:
                        logger.error(f"Fehler beim Laden von Cache-Content für {url}: {e}")
                        self.stats['misses'] += 1
                        return None
                        
            except Exception as e:
                logger.error(f"Fehler bei DB-Zugriff für {url}: {e}")
                self.stats['misses'] += 1
                return None

    def put(self, url: str, content: str, content_type: str = 'text/html', 
            status_code: int = 200, headers: Optional[Dict[str, str]] = None,
            encoding: str = 'utf-8') -> bool:
        """
        Speichere HTML-Content im Cache.
        
        Args:
            url: URL des Contents
            content: HTML-Content
            content_type: Content-Type Header
            status_code: HTTP Status Code
            headers: HTTP Headers
            encoding: Content-Encoding
            
        Returns:
            True bei Erfolg
        """
        if not content or not content.strip():
            return False
            
        with self.lock:
            try:
                # Generiere Metadaten
                timestamp = time.time()
                cache_hash = self._generate_content_hash(content)
                file_path = self._generate_file_path(url)
                headers = headers or {}
                
                # Erstelle Verzeichnisstruktur
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Komprimiere und speichere Content
                compressed_data = self._compress_content(content)
                with open(file_path, 'wb') as f:
                    f.write(compressed_data)
                
                # Alle DB-Operationen in einer einzigen Transaktion
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    # Setze WAL-Mode für bessere Concurrency
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=30000")
                    
                    # Prüfe auf Deduplizierung
                    cursor = conn.execute(
                        "SELECT url FROM html_cache WHERE cache_hash = ? AND url != ?",
                        (cache_hash, url)
                    )
                    duplicate = cursor.fetchone()
                    if duplicate:
                        logger.debug(f"Content bereits vorhanden (Hash-Duplikat): {duplicate[0]}")
                        self.stats['deduplicated'] += 1
                    
                    # Speichere Metadaten in DB
                    conn.execute("""
                        INSERT OR REPLACE INTO html_cache 
                        (url, file_path, content_type, status_code, headers, timestamp,
                         content_length, encoding, etag, last_modified, cache_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        url, str(file_path), content_type, status_code,
                        json.dumps(headers), timestamp, len(content), encoding,
                        headers.get('etag'), headers.get('last-modified'), cache_hash
                    ))
                    conn.commit()
                
                self.stats['saves'] += 1
                self.stats['total_size'] += len(compressed_data)
                
                logger.debug(f"HTML cached: {url} ({len(content)} chars -> {len(compressed_data)} bytes)")
                return True
                
            except Exception as e:
                logger.error(f"Fehler beim Speichern von HTML-Cache für {url}: {e}")
                return False

    def cleanup_old_entries(self) -> int:
        """
        Entferne veraltete Cache-Einträge.
        
        Returns:
            Anzahl gelöschter Einträge
        """
        cutoff_time = time.time() - (self.max_age_days * 24 * 3600)
        deleted_count = 0
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Finde veraltete Einträge
                cursor = conn.execute(
                    "SELECT url, file_path FROM html_cache WHERE timestamp < ?",
                    (cutoff_time,)
                )
                old_entries = cursor.fetchall()
                
                for url, file_path in old_entries:
                    try:
                        # Lösche Datei
                        Path(file_path).unlink(missing_ok=True)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Fehler beim Löschen von {file_path}: {e}")
                
                # Lösche DB-Einträge
                conn.execute("DELETE FROM html_cache WHERE timestamp < ?", (cutoff_time,))
                conn.commit()
        
        if deleted_count > 0:
            logger.info(f"HTML Cache cleanup: {deleted_count} veraltete Einträge gelöscht")
        
        return deleted_count

    def get_statistics(self) -> Dict[str, Any]:
        """Erhalte Cache-Statistiken."""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*), SUM(content_length) FROM html_cache")
                total_entries, total_content_size = cursor.fetchone()
                
                cursor = conn.execute("SELECT COUNT(DISTINCT cache_hash) FROM html_cache")
                unique_content_count = cursor.fetchone()[0]
        
        hit_rate = self.stats['hits'] / max(self.stats['hits'] + self.stats['misses'], 1) * 100
        compression_ratio = self.stats['total_size'] / max(total_content_size or 1, 1) * 100
        
        return {
            'total_entries': total_entries or 0,
            'unique_content': unique_content_count or 0,
            'total_content_size': total_content_size or 0,
            'compressed_size': self.stats['total_size'],
            'compression_ratio': f"{compression_ratio:.1f}%",
            'hit_rate': f"{hit_rate:.1f}%",
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'saves': self.stats['saves'],
            'deduplicated': self.stats['deduplicated'],
            'cache_dir': str(self.cache_dir)
        }

    def export_all(self, output_file: Path) -> int:
        """
        Exportiere kompletten Cache in JSON-Datei.
        
        Args:
            output_file: Ziel-JSON-Datei
            
        Returns:
            Anzahl exportierter Einträge
        """
        exported_count = 0
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT url, file_path, content_type, status_code, headers,
                           timestamp, content_length, encoding, etag, last_modified
                    FROM html_cache ORDER BY url
                """)
                
                export_data = []
                
                for row in cursor:
                    url, file_path, content_type, status_code, headers_json, \
                    timestamp, content_length, encoding, etag, last_modified = row
                    
                    try:
                        # Lade Content
                        with open(file_path, 'rb') as f:
                            compressed_data = f.read()
                        content = self._decompress_content(compressed_data)
                        headers = json.loads(headers_json) if headers_json else {}
                        
                        export_data.append({
                            'url': url,
                            'content': content,
                            'content_type': content_type,
                            'status_code': status_code,
                            'headers': headers,
                            'timestamp': timestamp,
                            'content_length': content_length,
                            'encoding': encoding,
                            'etag': etag,
                            'last_modified': last_modified
                        })
                        exported_count += 1
                        
                    except Exception as e:
                        logger.error(f"Fehler beim Exportieren von {url}: {e}")
        
        # Schreibe JSON-Datei
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'export_timestamp': datetime.now().isoformat(),
                'total_entries': exported_count,
                'cache_statistics': self.get_statistics(),
                'html_cache': export_data
            }, f, indent=2, ensure_ascii=False)
        
        logger.info(f"HTML Cache exportiert: {exported_count} Einträge -> {output_file}")
        return exported_count

    def clear_all(self) -> int:
        """
        Lösche kompletten Cache.
        
        Returns:
            Anzahl gelöschter Einträge
        """
        deleted_count = 0
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT file_path FROM html_cache")
                file_paths = [row[0] for row in cursor.fetchall()]
                
                # Lösche alle Dateien
                for file_path in file_paths:
                    try:
                        Path(file_path).unlink(missing_ok=True)
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Fehler beim Löschen von {file_path}: {e}")
                
                # Lösche DB-Einträge
                conn.execute("DELETE FROM html_cache")
                conn.commit()
        
        # Reset Statistics
        self.stats = {
            'hits': 0,
            'misses': 0, 
            'saves': 0,
            'total_size': 0,
            'deduplicated': 0
        }
        
        logger.info(f"HTML Cache geleert: {deleted_count} Einträge gelöscht")
        return deleted_count