"""
Intelligentes URL-Caching System
=================================

Verhindert doppeltes Scraping durch Caching von URLs und Inhalten.
Unterstützt verschiedene Cache-Strategien basierend auf Content-Typ.
"""

import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CachedURL:
    """Repräsentiert eine gecachte URL."""
    url: str
    content_hash: str
    last_scraped: datetime
    success: bool
    status_code: int
    category: str
    metadata: Dict[str, Any]


class URLCache:
    """
    Intelligentes Caching-System für gescrapte URLs.
    
    Features:
    - Persistente Speicherung in SQLite
    - Flexible Verfallszeiten basierend auf Content-Typ
    - Content-Hash für Change Detection
    - Statistiken und Reporting
    """
    
    def __init__(self, db_path: str = "data/url_cache.db"):
        """
        Initialisiere URL-Cache.
        
        Args:
            db_path: Pfad zur SQLite-Datenbank
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        
        self._create_tables()
        
        # Cache-Strategien (in Tagen)
        self.cache_strategies = {
            'news': 1,              # News/Aktuelles: Täglich
            'events': 1,            # Veranstaltungen: Täglich
            'pruefungsordnungen': 90,  # Prüfungsordnungen: Semesterly
            'modulhandbuch': 90,    # Modulhandbücher: Semesterly
            'faculty': 30,          # Fakultäts-Info: Monatlich
            'research': 30,         # Forschung: Monatlich
            'contact': 90,          # Kontakte: Alle 3 Monate
            'static': 30,           # Statische Seiten: Monatlich
            'default': 7            # Standard: Wöchentlich
        }
    
    def _create_tables(self):
        """Erstelle Datenbank-Tabellen."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS url_cache (
                url TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                last_scraped TIMESTAMP NOT NULL,
                success BOOLEAN NOT NULL,
                status_code INTEGER,
                category TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS scrape_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                content_hash TEXT,
                scraped_at TIMESTAMP NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                FOREIGN KEY (url) REFERENCES url_cache(url)
            )
        ''')
        
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_url_last_scraped 
            ON url_cache(last_scraped)
        ''')
        
        self.conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_category 
            ON url_cache(category)
        ''')
        
        self.conn.commit()
    
    def compute_content_hash(self, content: str) -> str:
        """
        Berechne Hash für Content.
        
        Args:
            content: Inhalt als String
            
        Returns:
            SHA256-Hash als Hex-String
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def get_cache_max_age(self, url: str, category: str = None) -> int:
        """
        Bestimme maximales Cache-Alter für URL.
        
        Args:
            url: URL
            category: Content-Kategorie
            
        Returns:
            Maximales Alter in Tagen
        """
        url_lower = url.lower()
        
        # Prüfe URL-spezifische Patterns
        if '/news/' in url_lower or '/aktuelles/' in url_lower:
            return self.cache_strategies['news']
        
        if '/event/' in url_lower or '/veranstaltung' in url_lower:
            return self.cache_strategies['events']
        
        if 'pruefungsordnung' in url_lower or '/po-' in url_lower or '/po_' in url_lower:
            return self.cache_strategies['pruefungsordnungen']
        
        if 'modulhandbuch' in url_lower:
            return self.cache_strategies['modulhandbuch']
        
        # Prüfe Kategorie
        if category:
            category_lower = category.lower()
            if category_lower in self.cache_strategies:
                return self.cache_strategies[category_lower]
        
        # Default
        return self.cache_strategies['default']
    
    def is_fresh(
        self,
        url: str,
        category: str = None,
        max_age_days: int = None
    ) -> bool:
        """
        Prüfe ob gecachte URL noch frisch ist.
        
        Args:
            url: Zu prüfende URL
            category: Content-Kategorie
            max_age_days: Optional: Überschreibe maximales Alter
            
        Returns:
            True wenn Cache frisch ist
        """
        cursor = self.conn.execute(
            'SELECT last_scraped, category FROM url_cache WHERE url = ?',
            (url,)
        )
        
        row = cursor.fetchone()
        if not row:
            return False
        
        last_scraped = datetime.fromisoformat(row['last_scraped'])
        cached_category = row['category']
        
        # Bestimme maximales Alter
        if max_age_days is None:
            max_age_days = self.get_cache_max_age(url, category or cached_category)
        
        age = datetime.now() - last_scraped
        is_fresh = age < timedelta(days=max_age_days)
        
        if not is_fresh:
            logger.debug(
                f"Cache abgelaufen für {url}: "
                f"Alter {age.days} Tage, Max {max_age_days} Tage"
            )
        
        return is_fresh
    
    def get(self, url: str) -> Optional[CachedURL]:
        """
        Hole gecachte URL-Daten.
        
        Args:
            url: URL
            
        Returns:
            CachedURL-Objekt oder None
        """
        cursor = self.conn.execute(
            'SELECT * FROM url_cache WHERE url = ?',
            (url,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        metadata = json.loads(row['metadata']) if row['metadata'] else {}
        
        return CachedURL(
            url=row['url'],
            content_hash=row['content_hash'],
            last_scraped=datetime.fromisoformat(row['last_scraped']),
            success=bool(row['success']),
            status_code=row['status_code'],
            category=row['category'],
            metadata=metadata
        )
    
    def put(
        self,
        url: str,
        content: str,
        success: bool,
        category: str = None,
        status_code: int = None,
        metadata: Dict[str, Any] = None
    ):
        """
        Speichere URL im Cache.
        
        Args:
            url: URL
            content: Inhalt
            success: Ob erfolgreich gescraped
            category: Content-Kategorie
            status_code: HTTP-Status-Code
            metadata: Zusätzliche Metadaten
        """
        content_hash = self.compute_content_hash(content)
        now = datetime.now()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        # Upsert in url_cache
        self.conn.execute('''
            INSERT OR REPLACE INTO url_cache 
            (url, content_hash, last_scraped, success, status_code, category, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (url, content_hash, now, success, status_code, category, metadata_json))
        
        # Füge zu History hinzu
        self.conn.execute('''
            INSERT INTO scrape_history 
            (url, content_hash, scraped_at, success)
            VALUES (?, ?, ?, ?)
        ''', (url, content_hash, now, success))
        
        self.conn.commit()
        
        logger.debug(f"URL im Cache gespeichert: {url}")
    
    def has_content_changed(self, url: str, new_content: str) -> bool:
        """
        Prüfe ob sich Inhalt seit letztem Scrape geändert hat.
        
        Args:
            url: URL
            new_content: Neuer Inhalt
            
        Returns:
            True wenn Inhalt sich geändert hat
        """
        cached = self.get(url)
        if not cached:
            return True  # Neu, also "geändert"
        
        new_hash = self.compute_content_hash(new_content)
        changed = new_hash != cached.content_hash
        
        if changed:
            logger.info(f"Inhalt geändert für {url}")
        
        return changed
    
    def should_scrape(
        self,
        url: str,
        category: str = None,
        force: bool = False
    ) -> bool:
        """
        Entscheide ob URL gescraped werden soll.
        
        Args:
            url: URL
            category: Content-Kategorie
            force: Erzwinge Scraping
            
        Returns:
            True wenn scrapen
        """
        if force:
            return True
        
        # Nicht im Cache -> scrapen
        if not self.get(url):
            return True
        
        # Cache abgelaufen -> scrapen
        if not self.is_fresh(url, category):
            return True
        
        # Cache frisch -> nicht scrapen
        logger.debug(f"Überspringe {url} (Cache frisch)")
        return False
    
    def invalidate(self, url: str):
        """
        Invalidiere Cache für URL.
        
        Args:
            url: URL
        """
        self.conn.execute('DELETE FROM url_cache WHERE url = ?', (url,))
        self.conn.commit()
        logger.info(f"Cache invalidiert für {url}")
    
    def invalidate_category(self, category: str):
        """
        Invalidiere alle URLs einer Kategorie.
        
        Args:
            category: Kategorie
        """
        self.conn.execute('DELETE FROM url_cache WHERE category = ?', (category,))
        self.conn.commit()
        logger.info(f"Cache invalidiert für Kategorie {category}")
    
    def invalidate_old(self, days: int = 90):
        """
        Invalidiere alle Cache-Einträge älter als X Tage.
        
        Args:
            days: Maximales Alter in Tagen
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        cursor = self.conn.execute(
            'DELETE FROM url_cache WHERE last_scraped < ?',
            (cutoff,)
        )
        
        deleted = cursor.rowcount
        self.conn.commit()
        
        logger.info(f"{deleted} alte Cache-Einträge gelöscht (älter als {days} Tage)")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Erhalte Cache-Statistiken.
        
        Returns:
            Dictionary mit Statistiken
        """
        cursor = self.conn.execute('SELECT COUNT(*) as total FROM url_cache')
        total = cursor.fetchone()['total']
        
        cursor = self.conn.execute('SELECT COUNT(*) as successful FROM url_cache WHERE success = 1')
        successful = cursor.fetchone()['successful']
        
        cursor = self.conn.execute(
            'SELECT category, COUNT(*) as count FROM url_cache GROUP BY category'
        )
        categories = {row['category']: row['count'] for row in cursor.fetchall()}
        
        # Zähle frische vs. abgelaufene Einträge
        fresh_count = 0
        expired_count = 0
        
        cursor = self.conn.execute('SELECT url, category FROM url_cache')
        for row in cursor.fetchall():
            if self.is_fresh(row['url'], row['category']):
                fresh_count += 1
            else:
                expired_count += 1
        
        return {
            'total_cached': total,
            'successful': successful,
            'failed': total - successful,
            'fresh': fresh_count,
            'expired': expired_count,
            'categories': categories
        }
    
    def export_report(self) -> str:
        """
        Generiere Cache-Report.
        
        Returns:
            Formatierter Report
        """
        stats = self.get_statistics()
        
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                  URL CACHE BERICHT                           ║
╚══════════════════════════════════════════════════════════════╝

📊 Cache-Statistiken
  Gesamt gecacht: {stats['total_cached']}
  Erfolgreich: {stats['successful']}
  Fehlgeschlagen: {stats['failed']}
  Frisch: {stats['fresh']}
  Abgelaufen: {stats['expired']}

📁 Nach Kategorie
"""
        
        for category, count in sorted(
            stats['categories'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            if category:
                report += f"  - {category}: {count}\n"
        
        report += "\n⚙️  Cache-Strategien (Tage)\n"
        for category, days in sorted(self.cache_strategies.items()):
            report += f"  - {category}: {days}\n"
        
        report += "\n" + "="*64 + "\n"
        
        return report
    
    def close(self):
        """Schließe Datenbank-Verbindung."""
        self.conn.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
