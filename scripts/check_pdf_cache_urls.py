#!/usr/bin/env python3
"""Prüft PDF-URLs im HTML-Cache."""

import sqlite3
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse

# HTML Cache prüfen
cache_path = Path(__file__).parent.parent / "data" / "html_cache" / "html_cache.db"
conn = sqlite3.connect(cache_path)
cur = conn.cursor()

# Tabellen anzeigen
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f"Tabellen im HTML-Cache: {tables}")

# Spalten der html_cache Tabelle
cur.execute("PRAGMA table_info(html_cache)")
columns = [c[1] for c in cur.fetchall()]
print(f"Spalten: {columns}")

# PDF URLs im Cache
cur.execute("SELECT url FROM html_cache WHERE url LIKE '%.pdf'")
pdf_urls = [r[0] for r in cur.fetchall()]
print(f"\nGesamt PDF-URLs im HTML-Cache: {len(pdf_urls)}")

print("\nBeispiel PDF-URLs (Original Web-URLs):")
for url in pdf_urls[:10]:
    print(f"  {url}")

# Jetzt Endpunkt-Zuordnung mit den echten Web-URLs
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
total = 0
for endpunkt in sorted(zugeordnet.keys()):
    count = len(zugeordnet[endpunkt])
    total += count
    print(f"  {endpunkt}: {count} PDFs")
    if count <= 3:
        for url in zugeordnet[endpunkt]:
            print(f"    - {url}")

if pdf_urls:
    print(f"\n  SUMME: {total} PDFs ({100*total/len(pdf_urls):.1f}%)")
else:
    print(f"\n  SUMME: {total} PDFs (keine PDF-URLs gefunden)")

print(f"\nNicht zuordenbar: {len(nicht_zugeordnet)} PDFs")
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
    if len(urls) <= 5:
        for url in urls:
            print(f"    - {url}")

conn.close()
