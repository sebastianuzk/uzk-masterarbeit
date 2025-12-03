#!/usr/bin/env python3
"""
Error Cache für fehlgeschlagene URLs (404, 403, etc.)
"""

import sqlite3
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, Set
import logging

logger = logging.getLogger(__name__)

@dataclass
class ErrorEntry:
    """Eintrag für fehlgeschlagene URL."""
    url: str
    status_code: int
    error_type: str
    error_message: str
    timestamp: float
    attempt_count: int = 1

class ErrorCache:
    """
    Cache für fehlgeschlagene URLs (404, 403, etc.)
    
    Verhindert wiederholte Versuche bei permanenten Fehlern.
    """
    
    def __init__(self, cache_dir: str = "data/error_cache"):
        """Initialisiere Error Cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.cache_dir / "error_cache.db"
        self._init_database()
    
    def _init_database(self):
        """Initialisiere SQLite-Datenbank für Error Cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Error cache table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_cache (
                url TEXT PRIMARY KEY,
                status_code INTEGER NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                timestamp REAL NOT NULL,
                attempt_count INTEGER DEFAULT 1,
                first_seen REAL,
                last_seen REAL
            )
        ''')
        
        # Index für bessere Performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_status ON error_cache(status_code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_timestamp ON error_cache(timestamp)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"Error cache initialized: {self.db_path}")
    
    def contains(self, url: str) -> bool:
        """Prüfe ob URL im Error Cache ist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT 1 FROM error_cache WHERE url = ?', (url,))
        result = cursor.fetchone() is not None
        
        conn.close()
        return result
    
    def get(self, url: str) -> Optional[ErrorEntry]:
        """Lade Error Entry aus Cache."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT url, status_code, error_type, error_message, timestamp, attempt_count
            FROM error_cache WHERE url = ?
        ''', (url,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return ErrorEntry(*row)
        return None
    
    def add(self, url: str, status_code: int, error_type: str, error_message: str, attempt_count: int = 1):
        """Füge Error Entry zum Cache hinzu."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        current_time = time.time()
        
        # Insert or Update
        cursor.execute('''
            INSERT OR REPLACE INTO error_cache 
            (url, status_code, error_type, error_message, timestamp, attempt_count, 
             first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, 
                    COALESCE((SELECT first_seen FROM error_cache WHERE url = ?), ?), ?)
        ''', (url, status_code, error_type, error_message, current_time, attempt_count,
              url, current_time, current_time))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Error cached: {status_code} {url}")
    
    def get_stats(self) -> Dict:
        """Hole Error-Cache-Statistiken."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Gesamtanzahl
        cursor.execute('SELECT COUNT(*) FROM error_cache')
        total_errors = cursor.fetchone()[0]
        
        # Nach Status-Code gruppiert
        cursor.execute('''
            SELECT status_code, COUNT(*) 
            FROM error_cache 
            GROUP BY status_code 
            ORDER BY COUNT(*) DESC
        ''')
        by_status = dict(cursor.fetchall())
        
        # Nach Error-Type gruppiert  
        cursor.execute('''
            SELECT error_type, COUNT(*) 
            FROM error_cache 
            GROUP BY error_type 
            ORDER BY COUNT(*) DESC
        ''')
        by_type = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_errors': total_errors,
            'by_status_code': by_status,
            'by_error_type': by_type
        }
    
    def is_permanent_error(self, status_code: int) -> bool:
        """Prüfe ob Status-Code einen permanenten Fehler darstellt."""
        permanent_errors = {
            400,  # Bad Request
            401,  # Unauthorized  
            403,  # Forbidden
            404,  # Not Found
            405,  # Method Not Allowed
            410,  # Gone
            418,  # I'm a teapot (permanent)
            451   # Unavailable For Legal Reasons
        }
        return status_code in permanent_errors
    
    def cleanup_old_entries(self, max_age_days: int = 30):
        """Entferne alte Error-Einträge."""
        cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM error_cache WHERE timestamp < ?', (cutoff_time,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old error entries")
        
        return deleted_count