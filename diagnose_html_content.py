"""
Diagnose-Script: Vergleiche RAW-HTML mit bereinigtem Content
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sqlite3
import gzip
from pathlib import Path
from bs4 import BeautifulSoup

# Datenbank-Pfad
DB_PATH = Path("data/content_database.db")

def analyze_html_document(doc_id: int = 3198):
    """Analysiere ein HTML-Dokument aus der Datenbank."""
    
    print("=" * 80)
    print("HTML-CONTENT DIAGNOSE")
    print("=" * 80)
    
    # Lade Dokument aus Datenbank
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT url, title, content, metadata FROM documents WHERE id = ?",
            (doc_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            print(f"❌ Dokument ID {doc_id} nicht gefunden!")
            return
        
        url, title, compressed_content, metadata = row
    
    print(f"\n📄 Dokument ID: {doc_id}")
    print(f"   URL: {url}")
    print(f"   Titel: {title[:50]}...")
    
    # Dekomprimiere Content
    raw_html = gzip.decompress(compressed_content).decode('utf-8')
    
    print(f"\n1. RAW-HTML Statistiken:")
    print(f"   Gesamt-Länge: {len(raw_html):,} Zeichen")
    
    # Prüfe ob es wirklich HTML ist
    has_html_tags = '<html' in raw_html.lower()
    has_head = '<head' in raw_html.lower()
    has_body = '<body' in raw_html.lower()
    
    print(f"   Enthält <html> Tag: {has_html_tags}")
    print(f"   Enthält <head> Tag: {has_head}")
    print(f"   Enthält <body> Tag: {has_body}")
    
    # Zeige erste 500 Zeichen
    print(f"\n2. Erste 500 Zeichen des RAW-HTML:")
    print("-" * 80)
    print(raw_html[:500])
    print("-" * 80)
    
    # Parse HTML
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # Analysiere HTML-Struktur
    print(f"\n3. HTML-Struktur:")
    print(f"   <script> Tags: {len(soup.find_all('script'))}")
    print(f"   <style> Tags: {len(soup.find_all('style'))}")
    print(f"   <nav> Tags: {len(soup.find_all('nav'))}")
    print(f"   <header> Tags: {len(soup.find_all('header'))}")
    print(f"   <footer> Tags: {len(soup.find_all('footer'))}")
    print(f"   <main> Tags: {len(soup.find_all('main'))}")
    print(f"   <article> Tags: {len(soup.find_all('article'))}")
    
    # Extrahiere reinen Text (wie BeautifulSoup es macht)
    plain_text = soup.get_text(separator=' ', strip=True)
    print(f"\n4. Reiner Text (nach Tag-Entfernung):")
    print(f"   Länge: {len(plain_text):,} Zeichen")
    print(f"   Reduktion: {(1 - len(plain_text)/len(raw_html)) * 100:.1f}%")
    
    # Zeige erste 500 Zeichen des Textes
    print(f"\n5. Erste 500 Zeichen des reinen Texts:")
    print("-" * 80)
    print(plain_text[:500])
    print("-" * 80)
    
    # Finde main-Content
    main_element = soup.find('main')
    if main_element:
        main_text = main_element.get_text(separator=' ', strip=True)
        print(f"\n6. Main-Element gefunden:")
        print(f"   Länge: {len(main_text):,} Zeichen")
        print(f"   Anteil am Gesamt: {len(main_text)/len(plain_text)*100:.1f}%")
        print(f"\n   Erste 500 Zeichen des Main-Contents:")
        print("-" * 80)
        print(main_text[:500])
        print("-" * 80)
    else:
        print(f"\n6. Kein <main> Element gefunden")
    
    # Schätze Boilerplate-Anteil
    print(f"\n7. Geschätzte Content-Verteilung:")
    total_chars = len(raw_html)
    tags_overhead = total_chars - len(plain_text)
    print(f"   HTML-Tags & Struktur: {tags_overhead:,} Zeichen ({tags_overhead/total_chars*100:.1f}%)")
    print(f"   Reiner Text: {len(plain_text):,} Zeichen ({len(plain_text)/total_chars*100:.1f}%)")
    
    if main_element:
        boilerplate_text = len(plain_text) - len(main_text)
        print(f"   Boilerplate (Navigation, Footer, etc.): {boilerplate_text:,} Zeichen ({boilerplate_text/total_chars*100:.1f}%)")
        print(f"   Haupt-Content: {len(main_text):,} Zeichen ({len(main_text)/total_chars*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("✅ DIAGNOSE ABGESCHLOSSEN")
    print("=" * 80)

if __name__ == "__main__":
    analyze_html_document()
