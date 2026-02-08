import sqlite3
import chromadb

# 1. Prüfe Content-Datenbank
print("=" * 80)
print("1. Suche in Content-Datenbank (content_database.db)")
print("=" * 80)

conn = sqlite3.connect('data/content_database.db')
cursor = conn.execute("""
    SELECT id, url, title 
    FROM documents 
    WHERE url LIKE '%Meet_your_AD_Winfo%'
""")
results = cursor.fetchall()
conn.close()

if results:
    print(f"✅ Dokument in Content-DB gefunden:")
    for r in results:
        print(f"   ID: {r[0]}")
        print(f"   URL: {r[1]}")
        print(f"   Title: {r[2]}")
else:
    print("❌ Dokument NICHT in Content-DB gefunden!")

# 2. Prüfe ChromaDB
print()
print("=" * 80)
print("2. Suche in ChromaDB (vector_db)")
print("=" * 80)

client = chromadb.PersistentClient(path='data/vector_db')
collection = client.get_collection('wiso_documents')
results = collection.get(include=['metadatas'])

found_in_chroma = []
for meta in results['metadatas']:
    if meta and 'url' in meta:
        if 'Meet_your_AD_Winfo' in meta['url']:
            found_in_chroma.append(meta)

if found_in_chroma:
    print(f"✅ Dokument in ChromaDB gefunden ({len(found_in_chroma)} Chunks):")
    for m in found_in_chroma[:3]:
        print(f"   URL: {m.get('url', 'N/A')}")
        print(f"   Title: {m.get('title', 'N/A')}")
else:
    print("❌ Dokument NICHT in ChromaDB gefunden!")

# 3. Zeige die erwartete URL aus dem Testset
print()
print("=" * 80)
print("3. Erwartete URL aus Testset")
print("=" * 80)

expected_url = "file://D:/Uni-Köln/Masterarbeit/Software/uzk-masterarbeit/data/pdf_cache/__wiso.uni-koeln.de_sites_fakultaet_dokumente_downloads_bachelor_Bachelor_Begruessung_Praesentationen_Meet_your_AD_Winfo.pdf"
print(f"   {expected_url}")

# 4. Suche nach ähnlichen URLs in ChromaDB
print()
print("=" * 80)
print("4. Ähnliche URLs in ChromaDB (Bachelor_Begruessung)")
print("=" * 80)

similar_urls = []
for meta in results['metadatas']:
    if meta and 'url' in meta:
        if 'Bachelor_Begruessung' in meta['url'] or 'Begruessung' in meta['url']:
            if meta['url'] not in similar_urls:
                similar_urls.append(meta['url'])

if similar_urls:
    print(f"Gefunden ({len(similar_urls)} URLs):")
    for url in similar_urls[:10]:
        print(f"   {url}")
else:
    print("Keine ähnlichen URLs gefunden")

# 5. Suche in Content-DB nach Bachelor_Begruessung
print()
print("=" * 80)
print("5. Suche in Content-DB (Bachelor_Begruessung)")
print("=" * 80)

conn = sqlite3.connect('data/content_database.db')
cursor = conn.execute("""
    SELECT id, url, title 
    FROM documents 
    WHERE url LIKE '%Bachelor_Begruessung%'
""")
results_db = cursor.fetchall()
conn.close()

if results_db:
    print(f"Gefunden ({len(results_db)} Dokumente):")
    for r in results_db:
        print(f"   ID: {r[0]}, URL: {r[1][:80]}...")
else:
    print("Keine Dokumente mit 'Bachelor_Begruessung' in Content-DB!")
