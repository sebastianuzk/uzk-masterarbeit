#!/usr/bin/env python3
"""
Analyse der fehlgeschlagenen URLs
"""

import sys
import os
import sqlite3
from pathlib import Path

def analyze_failed_urls():
    """Analysiere fehlgeschlagene URLs im Crawler"""
    print("🔍 ANALYSE FEHLGESCHLAGENER URLS")
    print("=" * 60)
    
    # HTML Cache nach Fehlern durchsuchen
    html_cache_db = 'data/html_cache/html_cache.db'
    if os.path.exists(html_cache_db):
        conn = sqlite3.connect(html_cache_db)
        cursor = conn.cursor()
        
        # Status-Codes analysieren
        cursor.execute("SELECT status_code, COUNT(*) FROM html_cache GROUP BY status_code ORDER BY COUNT(*) DESC")
        status_codes = cursor.fetchall()
        
        print("📊 HTTP Status-Codes im HTML-Cache:")
        for status, count in status_codes:
            if status == 200:
                print(f"   ✅ {status}: {count:,} URLs")
            else:
                print(f"   ❌ {status}: {count:,} URLs")
        
        # Fehlgeschlagene URLs (nicht 200) anzeigen
        cursor.execute("SELECT url, status_code, content_length FROM html_cache WHERE status_code != 200 ORDER BY status_code, url LIMIT 10")
        failed_urls = cursor.fetchall()
        
        if failed_urls:
            print(f"\n❌ Beispiele fehlgeschlagener URLs:")
            for url, status, length in failed_urls:
                print(f"   {status}: {url[:80]}{'...' if len(url) > 80 else ''}")
        
        conn.close()
    
    # Suche nach Crawler-Log-Dateien
    log_files = list(Path(".").glob("*.log"))
    log_files.extend(list(Path("logs").glob("*.log")) if Path("logs").exists() else [])
    
    if log_files:
        print(f"\n📄 Log-Dateien gefunden: {len(log_files)}")
        for log_file in log_files[:3]:  # Nur die ersten 3
            print(f"   📄 {log_file}")
    
    # Schaue nach temporären Error-Dateien
    error_patterns = ["error", "failed", "retry"]
    for pattern in error_patterns:
        files = list(Path(".").glob(f"*{pattern}*"))
        if files:
            print(f"\n🔍 {pattern.upper()}-Dateien:")
            for f in files[:5]:
                print(f"   📄 {f}")

if __name__ == "__main__":
    analyze_failed_urls()