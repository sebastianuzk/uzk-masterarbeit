#!/usr/bin/env python3
"""Check für PDF-URLs in discovered_urls"""

print('🚨 ÜBERPRÜFUNG: Wo landen PDF-URLs wirklich?')
print('=' * 50)

from pathlib import Path
import json
import sqlite3

# 1. Prüfe discovered_urls.json
urls_file = Path('src/scraper/pipelines/data_analysis/discovered_urls.json')
if urls_file.exists():
    print('📊 DISCOVERED_URLs.JSON:')
    with open(urls_file, 'r') as f:
        data = json.load(f)
    
    urls = data.get('urls', [])
    pdf_urls_in_discovered = [url for url in urls if url.lower().endswith('.pdf')]
    
    print(f'   Total URLs: {len(urls):,}')
    print(f'   PDF-URLs: {len(pdf_urls_in_discovered):,}')
    
    if pdf_urls_in_discovered:
        print('🚨 PROBLEM GEFUNDEN: PDFs sind in discovered_urls!')
        print('   → Diese werden als HTML-Seiten gescrapt!')
        print('   → Daher die 404-Fehler!')
        
        print('\n📄 Beispiel PDF-URLs in discovered_urls:')
        for i, url in enumerate(pdf_urls_in_discovered[:5], 1):
            print(f'   {i}. {url}')
    else:
        print('✅ Gut: Keine PDFs in discovered_urls')
else:
    print('❌ discovered_urls.json nicht gefunden')

print('\n' + '-' * 50)

# 2. Prüfe HTML-Cache
cache_db = Path('data/html_cache/html_cache.db')
if cache_db.exists():
    print('📊 HTML-CACHE ANALYSE:')
    
    conn = sqlite3.connect(cache_db)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM html_cache WHERE url LIKE '%.pdf'")
    pdf_count = cursor.fetchone()[0]
    
    print(f'   PDF-URLs im HTML-Cache: {pdf_count:,}')
    
    if pdf_count > 0:
        print('🚨 PROBLEM: PDFs sind im HTML-Cache!')
        print('   → PDFs wurden als HTML verarbeitet!')
        
        cursor.execute("SELECT url FROM html_cache WHERE url LIKE '%.pdf' LIMIT 10")
        pdf_urls = cursor.fetchall()
        
        print('\n📄 PDF-URLs im HTML-Cache:')
        for i, (url,) in enumerate(pdf_urls, 1):
            print(f'   {i}. {url}')
    else:
        print('✅ Gut: Keine PDFs im HTML-Cache')
    
    conn.close()
else:
    print('❌ HTML-Cache nicht gefunden')

print('\n' + '=' * 50)
print('🔍 DIAGNOSE:')

if urls_file.exists():
    with open(urls_file, 'r') as f:
        data = json.load(f)
    urls = data.get('urls', [])
    pdf_in_discovered = len([url for url in urls if url.lower().endswith('.pdf')])
    
    if pdf_in_discovered > 0:
        print('❌ CRAWLER-FILTER FUNKTIONIERT NICHT!')
        print('   PDFs landen noch in discovered_urls')
        print('   → Scraper versucht PDFs als HTML zu laden')
        print('   → 404-Fehler bei PDF-URLs')
        print('\n💡 LÖSUNG ERFORDERLICH:')
        print('   1. Crawler-Filter reparieren')
        print('   2. PDFs aus discovered_urls entfernen')
    else:
        print('✅ Crawler-Filter funktioniert')
        print('   Aber warum dann 404-Fehler?')
        print('   → Prüfe andere Quellen für PDF-URLs')

print('\nWENN SIE 404-FEHLER SEHEN:')
print('→ PDFs werden definitiv noch als HTML verarbeitet!')
print('→ Die "Fixes" haben NICHT funktioniert!')