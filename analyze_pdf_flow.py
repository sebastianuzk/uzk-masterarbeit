#!/usr/bin/env python3
"""Analyse: Was passiert mit PDF-URLs in der Pipeline?"""

print('🔍 PDF-URL FLOW ANALYSE')
print('=' * 60)

print('📊 SCHRITT 1: CRAWLER')
print('-' * 30)
print('✅ Crawler findet URLs auf Webseiten')
print('✅ PDF-URLs werden erkannt (Endung .pdf)')
print('✅ PDFs werden NICHT in found_urls eingefügt')  
print('✅ PDFs werden in separater crawler.pdf_urls Sammlung gespeichert')
print('✅ Nur HTML-URLs kommen in discovered_urls')
print()

print('📊 SCHRITT 2: SCRAPER (HTML)')
print('-' * 30)
print('✅ Nur discovered_urls (HTML) werden gescrapt')
print('✅ PDFs werden NICHT gescrapt (gut)')
print('✅ HTML-Content wird im html_cache.db gespeichert')
print('❌ PDF-URLs kommen NICHT in den HTML-Cache')
print()

print('📊 SCHRITT 3: PDF-VERARBEITUNG')
print('-' * 30)
print('✅ Pipeline verwendet crawler.pdf_urls')
print('✅ PDF-Extractor lädt PDFs herunter')
print('✅ PDF-Content wird extrahiert')
print('✅ PDFs werden als ScrapedContent konvertiert')
print('✅ PDF-Content geht in Vector Store')
print('❌ ABER: PDF-URLs werden NIRGENDS gecacht!')
print()

print('📊 SCHRITT 4: BEIM NÄCHSTEN PIPELINE-RUN')
print('-' * 30)
print('❌ Crawler muss ALLE PDF-URLs wieder neu finden')
print('❌ Kein Cache-Check für PDFs')
print('❌ PDF-Extraktion wird wiederholt')
print('❌ Ineffizient!')
print()

print('🎯 DAS PROBLEM:')
print('-' * 30)
print('1. PDFs werden korrekt vom HTML-Scraping getrennt')
print('2. PDF-Content wird extrahiert und gespeichert')  
print('3. ABER: Es gibt kein PDF-URL-Caching')
print('4. Nächster Run findet PDFs wieder neu')
print('5. PDF-Extraktion wird unnötig wiederholt')
print()

print('💡 LÖSUNG:')
print('-' * 30)
print('1. PDF-Cache implementieren')
print('2. PDF-URLs aus vorherigen Runs wiederverwenden')
print('3. Nur neue/veränderte PDFs neu verarbeiten')

# Prüfe was derzeit im System ist
import sqlite3
from pathlib import Path

cache_db = Path('data/html_cache/html_cache.db')
if cache_db.exists():
    print()
    print('🔍 AKTUELLER STATUS:')
    print('-' * 30)
    
    conn = sqlite3.connect(cache_db)
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM html_cache')
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM html_cache WHERE url LIKE '%.pdf'")
    pdfs = cursor.fetchone()[0]
    
    print(f'📄 URLs im HTML-Cache: {total}')
    print(f'📄 PDFs im HTML-Cache: {pdfs}')
    
    if pdfs == 0:
        print('✅ Korrekt: Keine PDFs im HTML-Cache!')
    else:
        print('❌ Problem: PDFs sind im HTML-Cache!')
        
    conn.close()
    
# Prüfe Vector Store
vector_db_dir = Path('data/vector_db')
if vector_db_dir.exists():
    print(f'📊 Vector Store existiert: {vector_db_dir}')
    # Prüfe Collections
    for item in vector_db_dir.iterdir():
        if item.is_dir():
            print(f'   📁 Collection: {item.name}')
else:
    print('❌ Vector Store nicht gefunden')

print()
print('📋 FAZIT:')
print('PDF-Handling funktioniert teilweise korrekt,')
print('aber es fehlt PDF-URL-Caching für Effizienz!')