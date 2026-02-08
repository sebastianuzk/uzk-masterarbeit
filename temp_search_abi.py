import chromadb
from sentence_transformers import SentenceTransformer
import numpy as np

client = chromadb.PersistentClient(path='data/vector_db')
col = client.get_collection('wiso_documents')

# Query
query = "Bewerbung trotzdem Sinn bei schlechtem Abiturschnitt"

# Embedding-Modell laden (gleiches wie in RAG)
model = SentenceTransformer('BAAI/bge-m3')
query_embedding = model.encode([query], normalize_embeddings=True)[0]

# Suche Top 10
results = col.query(
    query_embeddings=[query_embedding.tolist()],
    n_results=10,
    include=['documents', 'metadatas', 'distances']
)

print(f"Query: {query}\n")
print("Top 10 Ergebnisse:")
for i, (doc, meta, dist) in enumerate(zip(results['documents'][0], results['metadatas'][0], results['distances'][0])):
    url = meta.get('url', '?')
    has_abi = 'Abiturschnitt' in doc
    marker = "✓ ABITURSCHNITT" if has_abi else ""
    print(f"{i+1}. Distance: {dist:.4f} | {marker}")
    print(f"   URL: {url}")
    print(f"   Text: {doc[:150]}...")
    print()
