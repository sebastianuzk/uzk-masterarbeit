#!/usr/bin/env python3
"""Cache-Status prüfen"""

import sqlite3
import os
from pathlib import Path

def check_cache_status():
    cache_db = Path('data/html_cache/html_cache.db')
    
    if not cache_db.exists():
        print('❌ Cache-Datei nicht gefunden!')
        return
    
    print('📊 CACHE-STATUS AKTUELL:')
    print('=' * 60)
    
    conn = sqlite3.connect(cache_db)
    cursor = conn.cursor()
    
    # Gesamtstatistik
    cursor.execute('SELECT COUNT(*) FROM html_cache')
    total_urls = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM html_cache WHERE url LIKE '%.pdf'")
    pdf_count = cursor.fetchone()[0]
    
    html_count = total_urls - pdf_count
    
    print(f'📄 URLs GESAMT: {total_urls:,}')
    print(f'🔗 HTML-URLs: {html_count:,}')
    print(f'📄 PDF-URLs: {pdf_count:,}')
    print(f'📊 PDF-Anteil: {100 * pdf_count / max(total_urls, 1):.1f}%')
    print()
    
    # Cache-Größe
    cache_size = cache_db.stat().st_size / (1024 * 1024)
    print(f'💾 Cache-Größe: {cache_size:.1f} MB')
    print()
    
    # Letzte URLs
    print('🔍 LETZTE 10 URLS IM CACHE:')
    print('-' * 60)
    
    cursor.execute('SELECT url FROM html_cache ORDER BY rowid DESC LIMIT 10')
    recent_urls = cursor.fetchall()
    
    for i, (url,) in enumerate(recent_urls, 1):
        is_pdf = url.endswith('.pdf')
        icon = '📄' if is_pdf else '🔗'
        short_url = url if len(url) <= 70 else url[:67] + '...'
        print(f'{i:2d}. {icon} {short_url}')
    
    # PDF-Beispiele
    if pdf_count > 0:
        print()
        print(f'📄 PDF-BEISPIELE ({min(5, pdf_count)} von {pdf_count}):')
        print('-' * 60)
        
        cursor.execute("SELECT url FROM html_cache WHERE url LIKE '%.pdf' ORDER BY rowid DESC LIMIT 5")
        pdf_urls = cursor.fetchall()
        
        for i, (url,) in enumerate(pdf_urls, 1):
            pdf_name = url.split('/')[-1]
            print(f'{i}. {pdf_name}')
            print(f'   -> {url[:70]}{"..." if len(url) > 70 else ""}')
    
    # Domain-Verteilung
    print()
    print('🌐 TOP 5 DOMAINS:')
    print('-' * 60)
    
    cursor.execute('''
        SELECT 
            CASE 
                WHEN url LIKE 'https://%' THEN substr(url, 9, instr(substr(url, 9), '/') - 1)
                WHEN url LIKE 'http://%' THEN substr(url, 8, instr(substr(url, 8), '/') - 1)
                ELSE 'unknown'
            END as domain,
            COUNT(*) as count
        FROM html_cache 
        GROUP BY domain 
        ORDER BY count DESC 
        LIMIT 5
    ''')
    
    domains = cursor.fetchall()
    for i, (domain, count) in enumerate(domains, 1):
        percentage = 100 * count / total_urls
        print(f'{i}. {domain}: {count:,} URLs ({percentage:.1f}%)')
    
    conn.close()
    print()
    print('✅ Cache-Analyse abgeschlossen!')

if __name__ == '__main__':
    check_cache_status()