#!/usr/bin/env python3
"""Prüft PDF-URLs im URL-Cache."""

import sqlite3
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

# URL Cache prüfen
cache_path = Path(__file__).parent.parent / "data" / "url_cache.db"
conn = sqlite3.connect(cache_path)
cur = conn.cursor()

# Tabellen anzeigen
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f"Tabellen im URL-Cache: {tables}")

# Spalten der url_cache Tabelle
cur.execute("PRAGMA table_info(url_cache)")
columns = [c[1] for c in cur.fetchall()]
print(f"Spalten: {columns}")

# Gesamt URLs
cur.execute("SELECT COUNT(*) FROM url_cache")
total = cur.fetchone()[0]
print(f"\nGesamt URLs im URL-Cache: {total}")

# PDF URLs im Cache
cur.execute("SELECT url FROM url_cache WHERE url LIKE '%.pdf'")
pdf_urls = [r[0] for r in cur.fetchall()]
print(f"Davon PDF-URLs: {len(pdf_urls)}")

if pdf_urls:
    print("\nBeispiel PDF-URLs (Original Web-URLs):")
    for url in pdf_urls[:15]:
        print(f"  {url}")

    # Endpunkt-Zuordnung
    print("\n" + "=" * 70)
    print("PDF-ZUORDNUNG ZU ENDPUNKTEN (basierend auf Original Web-URLs)")
    print("=" * 70)

    endpunkte = [
        'news', 'aktuelles-und-neuigkeiten', 'services', 'corporate', 
        'faculty', 'fakultaet', 'forschung', 'praxis', 'research', 
        'studies', 'studium', 'service', 'pruefungsaemter'
    ]

    zugeordnet = defaultdict(list)
    nicht_zugeordnet = []

    for pdf_url in pdf_urls:
        parsed = urlparse(pdf_url)
        path_parts = parsed.path.strip('/').split('/')
        
        # Sprache entfernen (de/en)
        if path_parts and path_parts[0] in ['de', 'en']:
            path_parts = path_parts[1:]
        
        found = False
        if path_parts:
            first_segment = path_parts[0]
            if first_segment in endpunkte:
                zugeordnet[first_segment].append(pdf_url)
                found = True
        
        if not found:
            nicht_zugeordnet.append(pdf_url)

    print("\nZuordenbar zu Level-2 Endpunkten:")
    total_zugeordnet = 0
    for endpunkt in sorted(zugeordnet.keys()):
        count = len(zugeordnet[endpunkt])
        total_zugeordnet += count
        print(f"  {endpunkt}: {count} PDFs")

    print(f"\n  SUMME: {total_zugeordnet} PDFs ({100*total_zugeordnet/len(pdf_urls):.1f}%)")

    print(f"\nNicht direkt zuordenbar: {len(nicht_zugeordnet)} PDFs")
    
    # Analysiere Pfade der nicht zugeordneten
    path_patterns = defaultdict(list)
    for url in nicht_zugeordnet:
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        if path_parts:
            first = path_parts[0]
            path_patterns[first].append(url)

    print("\nPfad-Muster der nicht zugeordneten PDFs:")
    for pattern, urls in sorted(path_patterns.items(), key=lambda x: -len(x[1])):
        print(f"  {pattern}: {len(urls)} PDFs")
        for url in urls[:3]:
            print(f"    - {url}")
        if len(urls) > 3:
            print(f"    ... und {len(urls)-3} weitere")

conn.close()
