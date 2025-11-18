#!/usr/bin/env python3
"""
Analysiert was bei Pipeline-Neustart verarbeitet wird
"""

import sqlite3
import os
import json
from pathlib import Path

def analyze_restart_behavior():
    """Analysiert welche URLs bei Neustart verarbeitet werden"""
    print("🔄 PIPELINE RESTART ANALYSE")
    print("=" * 60)
    
    # 1. Was ist im Cache?
    html_cache_db = 'data/html_cache/html_cache.db'
    cached_urls = set()
    
    if os.path.exists(html_cache_db):
        conn = sqlite3.connect(html_cache_db)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM html_cache")
        total_cached = cursor.fetchone()[0]
        
        cursor.execute("SELECT url FROM html_cache")
        cached_urls = {row[0] for row in cursor.fetchall()}
        
        print(f"🗄️  HTML CACHE:")
        print(f"   📊 Gecachte URLs: {total_cached:,}")
        
        conn.close()
    
    # 2. Was ist im PDF Cache?
    pdf_cache_dir = Path('data/pdf_cache')
    cached_pdfs = set()
    
    if pdf_cache_dir.exists():
        pdf_files = list(pdf_cache_dir.glob('*.pdf'))
        print(f"📄 PDF CACHE:")
        print(f"   📊 Gecachte PDFs: {len(pdf_files):,}")
        
        # Konvertiere PDF-Dateinamen zurück zu URLs
        for pdf_file in pdf_files:
            if pdf_file.name.startswith('__'):
                # URL aus Dateiname rekonstruieren
                url_part = pdf_file.name[2:]  # Remove __
                if url_part.endswith('.pdf'):
                    url_part = url_part[:-4]  # Remove .pdf
                
                # Rückkonvertierung der URL
                reconstructed_url = url_part.replace('_', '/')
                reconstructed_url = f"https://{reconstructed_url}"
                if not reconstructed_url.endswith('.pdf'):
                    reconstructed_url += '.pdf'
                cached_pdfs.add(reconstructed_url)
    
    # 3. Was sind alle bekannten URLs?
    all_discovered_urls = set()
    
    # Aus discovered_urls.json
    discovery_files = [
        "discovered_urls.json",
        "src/scraper/pipelines/data_analysis/discovered_urls.json"
    ]
    
    for file_path in discovery_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    urls = data.get('urls', [])
                    all_discovered_urls.update(urls)
                    print(f"📋 DISCOVERED ({file_path}):")
                    print(f"   📊 URLs: {len(urls):,}")
            except Exception as e:
                print(f"   ❌ Fehler: {e}")
    
    # Aus Cache extrahieren
    all_discovered_urls.update(cached_urls)
    
    print(f"\n📊 RESTART-ANALYSE:")
    total_known = len(all_discovered_urls)
    total_cached_combined = len(cached_urls) + len(cached_pdfs)
    
    print(f"   🌐 Bekannte URLs gesamt: {total_known:,}")
    print(f"   💾 Gecacht (HTML+PDF): {total_cached_combined:,}")
    
    if total_known > 0:
        cached_percentage = (total_cached_combined / total_known) * 100
        remaining = total_known - total_cached_combined
        
        print(f"   ✅ Cache-Rate: {cached_percentage:.1f}%")
        print(f"   🔄 Verbleibend: {remaining:,} URLs")
        
        if remaining > 0:
            print(f"\n🔄 BEI NEUSTART:")
            print(f"   📊 {remaining:,} URLs würden neu verarbeitet")
            print(f"   💾 {total_cached_combined:,} URLs aus Cache geladen (sofort)")
            print(f"   ⚡ Speedup: ~{cached_percentage:.0f}% weniger HTTP-Requests")
        else:
            print(f"\n✅ VOLLSTÄNDIG GECACHT:")
            print(f"   🚀 Alle URLs sind gecacht - Neustart wäre sehr schnell!")
    
    # 4. Startup-Verhalten analysieren
    print(f"\n🚀 PIPELINE STARTUP-VERHALTEN:")
    print(f"   1. 🎯 Start mit: https://wiso.uni-koeln.de/de/")
    
    start_url = "https://wiso.uni-koeln.de/de/"
    if start_url in cached_urls:
        print(f"   ✅ Start-URL ist gecacht → Sofortiger Cache HIT")
    else:
        print(f"   🌐 Start-URL nicht gecacht → HTTP Request nötig")
    
    print(f"   2. 🕷️  Crawler würde systematisch durch Queue arbeiten")
    print(f"   3. 💾 Cache HITs für alle gecachten URLs")
    print(f"   4. 🌐 HTTP Requests nur für neue URLs")
    print(f"   5. 🔄 Retry-Queue für fehlgeschlagene URLs")

if __name__ == "__main__":
    analyze_restart_behavior()