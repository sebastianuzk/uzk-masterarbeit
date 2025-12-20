import chromadb

client = chromadb.PersistentClient(path='data/vector_db')
collection = client.get_collection('wiso_documents')

result = collection.get(
    where_document={"$contains": "staatlich finanzierte Hochschule"},
    include=['documents', 'metadatas']
)

print('=' * 100)
print('ZIEL-CHUNK VOLLSTÄNDIG')
print('=' * 100)
print(f"URL: {result['metadatas'][0].get('url')}")
print(f"Content-Type: {result['metadatas'][0].get('content_type')}")
print(f"Chunk-Index: {result['metadatas'][0].get('chunk_index')}")
print(f"Länge: {len(result['documents'][0])} Zeichen")
print()
print('INHALT:')
print('-' * 100)
print(result['documents'][0])
