#!/usr/bin/env python3
"""Prüft ob Original-URLs in PDF-Metadaten gespeichert sind."""

import sqlite3
import json
from pathlib import Path

# Content Database
db_path = Path(__file__).parent.parent / "data" / "content_database.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== PDF-Metadaten in content_database.db ===\n")

cur.execute("SELECT url, metadata FROM documents WHERE url LIKE '%.pdf' LIMIT 10")
for url, meta in cur.fetchall():
    filename = url.split('/')[-1] if url else 'unknown'
    print(f"Datei: {filename[:70]}")
    if meta:
        m = json.loads(meta)
        print(f"  Metadata Keys: {list(m.keys())}")
        # Suche nach URL-bezogenen Keys
        for key in ['original_url', 'source_url', 'web_url', 'download_url', 'pdf_url']:
            if key in m:
                print(f"  {key}: {m[key]}")
    print()

# Prüfe auch die PDF-Metadaten Datei falls vorhanden
pdf_metadata_file = Path(__file__).parent.parent / "src" / "scraper" / "pipelines" / "pdf_metadata.json"
if pdf_metadata_file.exists():
    print("\n=== pdf_metadata.json ===\n")
    with open(pdf_metadata_file, 'r', encoding='utf-8') as f:
        pdf_meta = json.load(f)
    print(f"Anzahl Einträge: {len(pdf_meta)}")
    if pdf_meta:
        print(f"Keys im ersten Eintrag: {list(pdf_meta[0].keys())}")
        print(f"\nBeispiel:")
        print(json.dumps(pdf_meta[0], indent=2, ensure_ascii=False)[:500])

conn.close()
