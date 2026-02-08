#!/usr/bin/env python3
"""Prüft PDF-URLs in der Datenbank."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "content_database.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Prüfe alle Tabellen
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f"Alle Tabellen in DB: {tables}")

# Für jede Tabelle prüfen
for table in tables:
    # Spalten der Tabelle
    cur.execute(f"PRAGMA table_info({table})")
    columns = [c[1] for c in cur.fetchall()]
    print(f"\nTabelle '{table}': Spalten = {columns}")
    
    # Wenn url-Spalte existiert, nach PDFs suchen
    if 'url' in columns:
        cur.execute(f"SELECT url FROM {table} WHERE url LIKE ? LIMIT 5", ('%.pdf%',))
        results = cur.fetchall()
        if results:
            print(f"  PDF URLs gefunden:")
            for r in results:
                print(f"    {r[0]}")
        
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE url LIKE ?", ('%.pdf%',))
        pdf_count = cur.fetchone()[0]
        print(f"  Gesamt PDF URLs: {pdf_count}")

# Prüfe ob 'pages' Tabelle existiert und PDF-URLs enthält
if 'pages' in tables:
    cur.execute("SELECT COUNT(*) FROM pages WHERE url LIKE '%.pdf%'")
    pdf_count = cur.fetchone()[0]
    print(f"\nGesamt PDF URLs in 'pages': {pdf_count}")

# Prüfe ob es eine PDF-spezifische Tabelle gibt
for table in tables:
    if 'pdf' in table.lower():
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        count = cur.fetchone()[0]
        print(f"\nTabelle '{table}': {count} Einträge")
        cur.execute(f"SELECT * FROM {table} LIMIT 3")
        for row in cur.fetchall():
            print(f"  {row}")

# Prüfe auch ob PDFs separat gespeichert werden
pdf_cache = Path(__file__).parent.parent / "data" / "pdf_cache"
if pdf_cache.exists():
    pdf_files = list(pdf_cache.glob("*.pdf"))
    print(f"\n\nPDF Cache Ordner: {len(pdf_files)} PDF-Dateien")
    if pdf_files[:5]:
        print("Beispiele:")
        for f in pdf_files[:5]:
            print(f"  {f.name}")

conn.close()
