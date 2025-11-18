#!/usr/bin/env python3
"""
Zeigt aktuelle URLs im Crawling-Prozess
"""

import sqlite3
import os
from pathlib import Path

def show_current_crawling_status():
    """Zeigt welche URLs noch gecrawlt werden"""
    print("🕷️ AKTUELLER CRAWLING-STATUS")
    print("=" * 60)
    
    # HTML Cache analysieren
    html_cache_db = 'data/html_cache/html_cache.db'
    if os.path.exists(html_cache_db):
        conn = sqlite3.connect(html_cache_db)
        cursor = conn.cursor()
        
        # Neuste URLs im Cache
        cursor.execute("SELECT url, timestamp, status_code FROM html_cache ORDER BY rowid DESC LIMIT 10")
        recent_urls = cursor.fetchall()
        
        print("📊 LETZTE 10 GECACHTE URLs:")
        for i, (url, timestamp, status) in enumerate(recent_urls, 1):
            status_icon = "✅" if status == 200 else "❌"
            print(f"   {i:2d}. {status_icon} {status} | {timestamp} | {url[:70]}{'...' if len(url) > 70 else ''}")
        
        # URL-Muster analysieren
        cursor.execute("SELECT COUNT(*) as count, SUBSTR(url, 1, 50) as pattern FROM html_cache GROUP BY pattern ORDER BY count DESC LIMIT 10")
        patterns = cursor.fetchall()
        
        print(f"\n📋 HÄUFIGSTE URL-MUSTER:")
        for count, pattern in patterns:
            print(f"   {count:3d}x | {pattern}...")
        
        # Domains analysieren
        cursor.execute("SELECT COUNT(*) as count FROM html_cache WHERE url LIKE '%wiso.uni-koeln.de%'")
        wiso_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM html_cache")
        total_count = cursor.fetchone()[0]
        
        print(f"\n🌐 DOMAIN-ANALYSE:")
        print(f"   📊 Gesamt URLs: {total_count:,}")
        print(f"   🏛️  WiSo-URLs: {wiso_count:,} ({100*wiso_count/max(total_count,1):.1f}%)")
        print(f"   🌍 Andere: {total_count-wiso_count:,}")
        
        conn.close()
    
    # PDF Cache analysieren
    pdf_cache_dir = Path('data/pdf_cache')
    if pdf_cache_dir.exists():
        pdf_files = list(pdf_cache_dir.glob('*.pdf'))
        recent_pdfs = sorted(pdf_files, key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        
        print(f"\n📄 LETZTE 5 HERUNTERGELADENE PDFs:")
        for i, pdf_file in enumerate(recent_pdfs, 1):
            size = pdf_file.stat().st_size
            name = pdf_file.name
            if len(name) > 60:
                name = name[:57] + "..."
            print(f"   {i}. {name} ({size:,} bytes)")
    
    # Schaue nach aktuellen Discovery-Dateien
    discovery_files = [
        "discovered_urls.json",
        "src/scraper/pipelines/data_analysis/discovered_urls.json"
    ]
    
    for file_path in discovery_files:
        if os.path.exists(file_path):
            import json
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    total_urls = data.get('total_urls', 0)
                    timestamp = data.get('timestamp', 'Unknown')
                    print(f"\n📋 DISCOVERED URLS ({file_path}):")
                    print(f"   📊 Total URLs: {total_urls:,}")
                    print(f"   🕐 Timestamp: {timestamp}")
                    
                    # Zeige einige URLs
                    urls = data.get('urls', [])
                    if urls:
                        print(f"   📋 Beispiel URLs:")
                        for i, url in enumerate(urls[:5], 1):
                            print(f"     {i}. {url[:70]}{'...' if len(url) > 70 else ''}")
                    break
            except Exception as e:
                print(f"   ❌ Fehler beim Lesen von {file_path}: {e}")

if __name__ == "__main__":
    show_current_crawling_status()