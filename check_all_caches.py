#!/usr/bin/env python3
"""Cache-Übersicht prüfen"""

import sqlite3
from pathlib import Path

def check_all_caches():
    print('📊 CACHE-ÜBERSICHT:')
    print('=' * 60)
    
    # Prüfe alle möglichen Cache-Dateien
    cache_files = [
        'data/html_cache/html_cache.db',
        'data/url_cache.db', 
        'data/pdf_cache.db'
    ]
    
    for cache_file in cache_files:
        cache_path = Path(cache_file)
        
        if cache_path.exists():
            print(f'✅ {cache_file} EXISTIERT')
            
            try:
                conn = sqlite3.connect(cache_file)
                cursor = conn.cursor()
                
                # Hole Tabellenstruktur
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                print(f'   📋 Tabellen: {[t[0] for t in tables]}')
                
                for table_name, in tables:
                    cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
                    count = cursor.fetchone()[0]
                    print(f'   📊 {table_name}: {count:,} Einträge')
                    
                    # Bei html_cache: PDF-URLs zählen
                    if table_name == 'html_cache':
                        cursor.execute("SELECT COUNT(*) FROM html_cache WHERE url LIKE '%.pdf'")
                        pdf_count = cursor.fetchone()[0]
                        print(f'   📄 PDFs in html_cache: {pdf_count:,}')
                        
                        # Zeige ein paar PDF-URLs als Beispiel
                        if pdf_count > 0:
                            cursor.execute("SELECT url FROM html_cache WHERE url LIKE '%.pdf' LIMIT 3")
                            pdf_urls = cursor.fetchall()
                            print(f'   🔍 PDF-Beispiele:')
                            for i, (url,) in enumerate(pdf_urls, 1):
                                pdf_name = url.split('/')[-1][:50]
                                print(f'     {i}. {pdf_name}')
                
                conn.close()
                
            except Exception as e:
                print(f'   ❌ Fehler beim Lesen: {e}')
        else:
            print(f'❌ {cache_file} NICHT GEFUNDEN')
    
    print()
    
    # Prüfe data-Verzeichnis Struktur
    data_dir = Path('data')
    if data_dir.exists():
        print('📁 DATA-VERZEICHNIS STRUKTUR:')
        print('-' * 40)
        
        for item in sorted(data_dir.rglob('*')):
            if item.is_file() and item.suffix in ['.db', '.json', '.txt']:
                size_mb = item.stat().st_size / (1024*1024)
                rel_path = item.relative_to(data_dir)
                print(f'   📄 {rel_path}: {size_mb:.2f} MB')
    
    print()
    print('🔍 PDF-CACHE STATUS:')
    print('-' * 40)
    
    # Spezifisch PDF-Cache prüfen
    pdf_cache_path = Path('data/pdf_cache.db')
    if pdf_cache_path.exists():
        print('✅ PDF-Cache gefunden!')
        
        conn = sqlite3.connect(pdf_cache_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table_name, in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'   📊 {table_name}: {count:,} PDF-Einträge')
        
        conn.close()
    else:
        print('❌ Separater PDF-Cache nicht gefunden')
        print('💡 PDFs werden vermutlich im HTML-Cache gespeichert')

if __name__ == '__main__':
    check_all_caches()