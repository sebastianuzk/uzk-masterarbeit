import chromadb

client = chromadb.PersistentClient(path='data/vector_db')
col = client.get_collection('wiso_documents')

# Suche nach Chunks die 'E-PLUS' enthalten
results = col.get(where_document={'$contains': 'E-PLUS'}, include=['documents', 'metadatas'])

print(f"Gefunden: {len(results['ids'])} Chunks mit 'E-PLUS'")
print("=" * 80)

for i, (doc_id, doc, meta) in enumerate(zip(results['ids'], results['documents'], results['metadatas'])):
    print(f"\n--- Chunk {i+1} ---")
    print(f"ID: {doc_id}")
    print(f"URL: {meta.get('url', 'N/A')[:100]}...")
    print(f"Text (erste 500 Zeichen):")
    print(doc[:500])
    print("...")
