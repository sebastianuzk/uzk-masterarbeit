#!/usr/bin/env python3
"""
Cache-Status-Check
"""

import sqlite3
import os
from pathlib import Path

def check_cache_status():
    """Prüft den aktuellen Status beider Cache-Systeme"""
    print("📊 CACHE STATUS OVERVIEW")
    print("=" * 40)
    
    # HTML Cache prüfen
    html_cache_db = 'data/html_cache/html_cache.db'
    if os.path.exists(html_cache_db):
        conn = sqlite3.connect(html_cache_db)
        cursor = conn.cursor()
        
        # Gesamtanzahl URLs
        cursor.execute("SELECT COUNT(*) FROM html_cache")
        total_urls = cursor.fetchone()[0]
        
        # PDF-URLs im HTML-Cache
        cursor.execute("SELECT COUNT(*) FROM html_cache WHERE url LIKE '%.pdf'")
        pdf_in_html_cache = cursor.fetchone()[0]
        
        # Cache-Dateigröße
        cache_size = os.path.getsize(html_cache_db) / 1024 / 1024
        
        print(f"🌐 HTML CACHE:")
        print(f"   📊 Gesamt URLs: {total_urls:,}")
        print(f"   📄 PDF-URLs: {pdf_in_html_cache:,}")
        print(f"   💾 Cache-Größe: {cache_size:.2f} MB")
        
        conn.close()
    else:
        print("🌐 HTML CACHE:")
        print("   ❌ Cache-Datei nicht gefunden")
    
    print()
    
    # PDF Cache prüfen
    pdf_cache_dir = Path('data/pdf_cache')
    if pdf_cache_dir.exists():
        pdf_files = list(pdf_cache_dir.glob('*.pdf'))
        total_pdf_size = sum(f.stat().st_size for f in pdf_files if f.is_file())
        
        print(f"📄 PDF CACHE:")
        print(f"   📊 PDF-Dateien: {len(pdf_files):,}")
        print(f"   💾 Gesamt-Größe: {total_pdf_size / 1024 / 1024:.2f} MB")
        
        if pdf_files:
            print(f"   📋 Dateien:")
            for f in sorted(pdf_files)[:5]:  # Nur erste 5 anzeigen
                size = f.stat().st_size
                print(f"     • {f.name[:60]}{'...' if len(f.name) > 60 else ''} ({size:,} bytes)")
            
            if len(pdf_files) > 5:
                print(f"     ... und {len(pdf_files) - 5} weitere")
    else:
        print(f"📄 PDF CACHE:")
        print("   📁 Kein PDF-Cache-Verzeichnis gefunden")

if __name__ == "__main__":
    check_cache_status()