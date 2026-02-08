#!/usr/bin/env python3
"""Durchsucht alle Tabellen im url_cache.db nach PDF-URLs."""

import sqlite3
from pathlib import Path

db_path = Path(__file__).parent.parent / "data" / "url_cache.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("=== URL-CACHE ANALYSE ===\n")

# Alle Tabellen
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print(f"Tabellen: {tables}\n")

for table in tables:
    if table == 'sqlite_sequence':
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
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} LIKE '%.pdf%'")
            pdf_count = cur.fetchone()[0]
            if pdf_count > 0:
                print(f"  -> {col}: {pdf_count} Einträge mit '.pdf'")
                
                # Zeige Beispiele
                cur.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE '%.pdf%' LIMIT 5")
                for row in cur.fetchall():
                    print(f"     {str(row[0])[:100]}")
        except:
            pass
    
    print()

conn.close()
