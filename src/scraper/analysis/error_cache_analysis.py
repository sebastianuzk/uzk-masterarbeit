#!/usr/bin/env python3
"""
Error Cache Analyzer
==================

Analysiert den Error-Cache und zeigt Statistiken zu fehlgeschlagenen URLs.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scraper.utils.error_cache import ErrorCache
from pathlib import Path
import json

def analyze_error_cache():
    """Analysiere Error-Cache Status."""
    cache_dir = "data/error_cache"
    
    if not Path(cache_dir).exists():
        print(f"❌ Error-Cache-Verzeichnis nicht gefunden: {cache_dir}")
        return
    
    error_cache = ErrorCache(cache_dir)
    stats = error_cache.get_stats()
    
    print("🔍 ERROR CACHE ANALYSIS")
    print("=" * 50)
    
    print(f"\n📊 GESAMT-STATISTIKEN:")
    print(f"   Fehlerhafte URLs: {stats['total_errors']}")
    
    if stats['total_errors'] > 0:
        print(f"\n🚫 FEHLER NACH STATUS-CODE:")
        for status_code, count in stats['by_status_code'].items():
            print(f"   {status_code}: {count} URLs")
        
        print(f"\n📝 FEHLER NACH TYP:")
        for error_type, count in stats['by_error_type'].items():
            print(f"   {error_type}: {count} URLs")
    
    # Zeige einige Beispiel-URLs
    if stats['total_errors'] > 0:
        print(f"\n📄 BEISPIEL FEHLERHAFTE URLs:")
        import sqlite3
        db_path = Path(cache_dir) / "error_cache.db"
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT url, status_code, error_message, attempt_count 
            FROM error_cache 
            ORDER BY timestamp DESC 
            LIMIT 10
        ''')
        
        for row in cursor.fetchall():
            url, status_code, error_msg, attempts = row
            truncated_url = url[:80] + "..." if len(url) > 80 else url
            print(f"   {status_code}: {truncated_url} (Attempts: {attempts})")
        
        conn.close()
    
    print(f"\n✅ Error-Cache-Analyse abgeschlossen")

if __name__ == "__main__":
    analyze_error_cache()