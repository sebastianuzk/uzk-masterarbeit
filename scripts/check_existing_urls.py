#!/usr/bin/env python3
"""
Script zum Überprüfen bereits verarbeiteter URLs aus vorherigen Läufen.
"""
import json
import sqlite3
import os
from pathlib import Path

def main():
    print('🔍 ÜBERPRÜFUNG VORHANDENER URL-DATEN:')
    print()

    # 1. Cache-URLs aus der SQLite DB
    cache_db = 'data/url_cache.db'
    if os.path.exists(cache_db):
        try:
            conn = sqlite3.connect(cache_db)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f'📂 URL Cache DB: {cache_db}')
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
                count = cursor.fetchone()[0]
                print(f'   📋 Tabelle {table[0]}: {count} Einträge')
                
                # Zeige ein paar Beispiel-URLs
                if count > 0:
                    cursor.execute(f'SELECT url FROM {table[0]} LIMIT 3')
                    sample_urls = cursor.fetchall()
                    for i, (url,) in enumerate(sample_urls, 1):
                        short = url.replace('https://wiso.uni-koeln.de', '').split('?')[0][:50]
                        print(f'     {i}. {short}...')
            conn.close()
        except Exception as e:
            print(f'   ❌ Fehler beim Lesen der Cache DB: {e}')
    else:
        print('❌ Keine URL Cache DB gefunden')

    print()

    # 2. PDF Metadata
    pdf_meta = Path('data/pdf_metadata.json')
    if pdf_meta.exists():
        try:
            with open(pdf_meta, 'r', encoding='utf-8') as f:
                data = json.load(f)
            pdf_count = len(data.get('pdfs', []))
            print(f'📄 PDF Metadata: {pdf_count} PDFs erfasst')
            if pdf_count > 0:
                latest_pdf = data['pdfs'][-1]
                print(f'   📄 Letztes PDF: {latest_pdf.get("title", "N/A")}')
        except Exception as e:
            print(f'❌ Fehler beim Lesen der PDF Metadata: {e}')
    else:
        print('❌ Keine PDF Metadata gefunden')

    print()

    # 3. HTML Cache
    html_cache_db = 'data/html_cache/html_cache.db'
    if os.path.exists(html_cache_db):
        try:
            conn = sqlite3.connect(html_cache_db)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM html_cache')
            count = cursor.fetchone()[0]
            print(f'🌐 HTML Cache: {count} URLs gecacht')
            
            cursor.execute('SELECT url FROM html_cache ORDER BY rowid DESC LIMIT 5')
            latest = cursor.fetchall()
            print('   🔗 Neueste URLs:')
            for i, (url,) in enumerate(latest, 1):
                short = url.replace('https://wiso.uni-koeln.de', '').split('?')[0][:60]
                print(f'     {i}. {short}')
            conn.close()
        except Exception as e:
            print(f'❌ Fehler beim Lesen des HTML Cache: {e}')
    else:
        print('❌ Kein HTML Cache gefunden')

    print()

    # 4. Suche nach discovered_urls.json (falls vorhanden)
    discovered_urls_file = Path('data/discovered_urls.json')
    if discovered_urls_file.exists():
        try:
            with open(discovered_urls_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f'🔗 Discovered URLs: {data.get("total_urls", 0)} URLs entdeckt')
            if 'urls' in data and len(data['urls']) > 0:
                print(f'   📅 Timestamp: {data.get("timestamp", "N/A")}')
                print('   🔗 Erste URLs:')
                for i, url in enumerate(data['urls'][:3], 1):
                    short = url.replace('https://wiso.uni-koeln.de', '').split('?')[0][:60]
                    print(f'     {i}. {short}')
        except Exception as e:
            print(f'❌ Fehler beim Lesen der discovered URLs: {e}')
    else:
        print('❌ Keine discovered_urls.json gefunden')

    print()

    # 5. Zeige Reports-Verzeichnis
    reports_dir = Path('data/reports')
    if reports_dir.exists():
        report_files = list(reports_dir.glob('*'))
        print(f'📊 Reports-Verzeichnis: {len(report_files)} Dateien')
        for file in sorted(report_files)[-3:]:  # Zeige die neuesten 3
            print(f'   📄 {file.name} ({file.stat().st_size} bytes)')
    else:
        print('❌ Kein Reports-Verzeichnis gefunden')

    print()
    print('💡 EMPFEHLUNG:')
    print('   Die Pipeline kann auf vorhandenen Daten aufbauen!')
    print('   Gecachte URLs werden automatisch übersprungen.')

if __name__ == '__main__':
    main()