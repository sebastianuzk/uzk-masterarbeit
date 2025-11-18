#!/usr/bin/env python3
"""
Check für PDFs im HTML-Cache
"""

import sqlite3
import os

def check_pdfs_in_html_cache():
    """Prüft ob PDFs im HTML-Cache vorhanden sind"""
    html_cache_db = 'data/html_cache/html_cache.db'
    
    if not os.path.exists(html_cache_db):
        print("❌ HTML-Cache nicht gefunden")
        return
    
    conn = sqlite3.connect(html_cache_db)
    cursor = conn.cursor()
    
    # PDFs im HTML-Cache zählen
    cursor.execute("SELECT COUNT(*) FROM html_cache WHERE url LIKE '%.pdf'")
    pdf_count = cursor.fetchone()[0]
    
    print(f"🔍 PDFs im HTML-Cache: {pdf_count}")
    
    if pdf_count > 0:
        print("\n📄 Gefundene PDF-URLs:")
        cursor.execute("SELECT url, status_code, timestamp FROM html_cache WHERE url LIKE '%.pdf' ORDER BY timestamp DESC")
        for i, (url, status, timestamp) in enumerate(cursor.fetchall(), 1):
            print(f"  {i}. {url}")
            print(f"     Status: {status}, Zeit: {timestamp}")
        
        print("\n❗ PROBLEM: Diese PDFs sind noch im HTML-Cache gespeichert!")
        print("   Sie sollten in den PDF-Cache migriert werden.")
    else:
        print("✅ Keine PDFs im HTML-Cache gefunden")
    
    conn.close()

if __name__ == "__main__":
    check_pdfs_in_html_cache()