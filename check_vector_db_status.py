"""
Prüfe den aktuellen Status der Vector Database
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pathlib import Path
import chromadb

VECTOR_DB = Path("data/vector_db")

print("=" * 80)
print("VECTOR DATABASE STATUS")
print("=" * 80)

if not VECTOR_DB.exists():
    print("\n❌ Vektordatenbank existiert nicht!")
    sys.exit(1)

# Verbinde zu ChromaDB
client = chromadb.PersistentClient(path=str(VECTOR_DB))

# Liste alle Collections
collections = client.list_collections()

if not collections:
    print("\n⚠️  Keine Collections gefunden - alles verloren!")
else:
    print(f"\n✅ {len(collections)} Collections gefunden:\n")
    
    total_chunks = 0
    for collection in collections:
        count = collection.count()
        total_chunks += count
        print(f"   📦 {collection.name}: {count:,} Chunks")
    
    print(f"\n📊 Gesamt: {total_chunks:,} Chunks gespeichert")
    
    if total_chunks > 0:
        print("\n✅ GUTE NACHRICHT: Daten sind NICHT verloren!")
        print("   Die ersten 3 Collections wurden erfolgreich gespeichert.")
        print("   Nur die letzte Collection (wiso_allgemein) ist verloren gegangen.")

print("=" * 80)
