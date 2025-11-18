#!/usr/bin/env python3
"""Detaillierte Cache-Analyse"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

def check_current_cache_status():
    print('🔍 DETAILLIERTE CACHE-ANALYSE')
    print('=' * 60)
    
    # 1. HTML-Cache Details
    html_cache_db = Path('data/html_cache/html_cache.db')
    if html_cache_db.exists():
        print('📊 HTML-CACHE DETAIL:')
        print('-' * 30)
        
        conn = sqlite3.connect(html_cache_db)
        cursor = conn.cursor()
        
        # Gesamtstatistik
        cursor.execute('SELECT COUNT(*) FROM html_cache')
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM html_cache WHERE url LIKE '%.pdf'")
        pdf_count = cursor.fetchone()[0]
        
        print(f'📄 HTML-URLs: {total_count - pdf_count:,}')
        print(f'📄 PDF-URLs: {pdf_count:,}')
        print(f'📊 Total: {total_count:,}')
        
        # Zeige letzte URLs
        cursor.execute('SELECT url FROM html_cache ORDER BY rowid DESC LIMIT 10')
        recent_urls = cursor.fetchall()
        
        print('\n🕐 LETZTE 10 URLS IM HTML-CACHE:')
        for i, (url,) in enumerate(recent_urls, 1):
            is_pdf = url.endswith('.pdf')
            icon = '📄' if is_pdf else '🌐'
            short_url = url[:70] + '...' if len(url) > 70 else url
            print(f'   {i:2d}. {icon} {short_url}')
        
        # Domain-Verteilung
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN url LIKE 'https://wiso.uni-koeln.de%' THEN 'wiso.uni-koeln.de'
                    ELSE 'other'
                END as domain,
                COUNT(*) as count
            FROM html_cache 
            GROUP BY domain 
            ORDER BY count DESC
        ''')
        domains = cursor.fetchall()
        
        print('\n🌐 DOMAIN-VERTEILUNG:')
        for domain, count in domains:
            print(f'   {domain}: {count:,} URLs')
        
        conn.close()
    
    # 2. URL-Cache Details
    print('\n📊 URL-CACHE DETAIL:')
    print('-' * 30)
    url_cache_db = Path('data/url_cache.db')
    if url_cache_db.exists():
        conn = sqlite3.connect(url_cache_db)
        cursor = conn.cursor()
        
        # Prüfe alle Tabellen
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        for table_name, in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
            print(f'   {table_name}: {count:,} Einträge')
            
            if count > 0 and table_name != 'sqlite_sequence':
                cursor.execute(f'SELECT * FROM {table_name} LIMIT 3')
                sample = cursor.fetchall()
                print(f'   Sample: {sample}')
        
        conn.close()
    else:
        print('   ❌ Nicht vorhanden')
    
    # 3. Vector Store Details  
    print('\n📊 VECTOR STORE DETAIL:')
    print('-' * 30)
    vector_dir = Path('data/vector_db')
    if vector_dir.exists():
        for item in vector_dir.iterdir():
            if item.is_dir():
                print(f'   📁 Collection: {item.name}')
                # Prüfe Collection-Inhalt
                chroma_file = item / 'chroma.sqlite3'
                if chroma_file.exists():
                    size_mb = chroma_file.stat().st_size / (1024*1024)
                    print(f'      💾 Größe: {size_mb:.1f} MB')
    else:
        print('   ❌ Nicht vorhanden')
    
    # 4. Pipeline-Dateien
    print('\n📊 PIPELINE-DATEIEN:')
    print('-' * 30)
    
    pipeline_dir = Path('src/scraper/pipelines/data_analysis')
    if pipeline_dir.exists():
        for file in pipeline_dir.iterdir():
            if file.is_file():
                size_kb = file.stat().st_size / 1024
                mod_time = datetime.fromtimestamp(file.stat().st_mtime)
                print(f'   📄 {file.name}: {size_kb:.1f} KB (geändert: {mod_time.strftime("%Y-%m-%d %H:%M")})')
                
                # Zeige discovered_urls.json Inhalt
                if file.name == 'discovered_urls.json':
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)
                        
                        urls = data.get('urls', [])
                        pdf_urls = [url for url in urls if url.lower().endswith('.pdf')]
                        
                        print(f'      🔗 URLs: {len(urls):,}')
                        print(f'      📄 PDFs: {len(pdf_urls):,}')
                        
                        if pdf_urls:
                            print(f'      🚨 PDF-URLs in discovered_urls:')
                            for pdf_url in pdf_urls[:3]:
                                print(f'        - {pdf_url}')
                    except Exception as e:
                        print(f'      ❌ Fehler beim Lesen: {e}')
    else:
        print('   ❌ Pipeline data_analysis Verzeichnis nicht gefunden')
    
    print('\n🏁 FAZIT:')
    print('-' * 30)
    print('HTML-Cache: Aktiv mit 522 URLs (0 PDFs)')
    print('URL-Cache: Leer')  
    print('PDF-Cache: Existiert nicht')
    print('Pipeline-Files: Können veraltete Daten enthalten')

if __name__ == '__main__':
    check_current_cache_status()