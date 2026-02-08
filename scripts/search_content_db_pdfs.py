#!/usr/bin/env python3
"""Durchsucht content_database.db nach PDF-URLs."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "content_database.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== CONTENT_DATABASE ANALYSE ===\n")

# Alle Tabellen
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f"Tabellen: {tables}\n")

for table in tables:
    if table.startswith('documents_fts') or table == 'sqlite_sequence':
        continue
        
    print(f"--- Tabelle: {table} ---")
    
    # Spalten
    cur.execute(f"PRAGMA table_info({table})")
    columns = [c[1] for c in cur.fetchall()]
    print(f"Spalten: {columns}")
    
    # Anzahl Einträge
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    total = cur.fetchone()[0]
    print(f"Gesamt Einträge: {total}")
    
    # Suche nach PDF in allen text-Spalten
    for col in columns:
        try:
            # Suche nach https URLs die auf .pdf enden
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} LIKE 'https://%.pdf'")
            pdf_count = cur.fetchone()[0]
            if pdf_count > 0:
                print(f"  -> {col}: {pdf_count} Web-PDF-URLs (https://...pdf)")
                
                # Zeige Beispiele
                cur.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE 'https://%.pdf' LIMIT 5")
                for row in cur.fetchall():
                    print(f"     {str(row[0])[:100]}")
            
            # Suche nach wiso.uni-koeln.de URLs mit .pdf
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} LIKE '%wiso.uni-koeln.de%.pdf'")
            pdf_count2 = cur.fetchone()[0]
            if pdf_count2 > 0 and pdf_count2 != pdf_count:
                print(f"  -> {col}: {pdf_count2} wiso.uni-koeln.de PDF-URLs")
                cur.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE '%wiso.uni-koeln.de%.pdf' LIMIT 5")
                for row in cur.fetchall():
                    print(f"     {str(row[0])[:100]}")
        except Exception as e:
            pass
    
    print()

conn.close()
