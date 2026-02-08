"""Debug-Script um die Reihenfolge der RRF-Ergebnisse im RAG Tool zu testen."""
import sys
sys.path.insert(0, ".")

from src.tools.rag_tool import UniversityRAGTool

# Konfiguration
QUERY = "Welche Fristen gelten für die Bewerbung zum Master Business Administration?"

print("=" * 80)
print(f"Query: {QUERY}")
print("=" * 80)

# RAG Tool initialisieren
rag_tool = UniversityRAGTool()

# Advanced Retrieve aufrufen (wie der Agent es macht)
results = rag_tool._advanced_retrieve(QUERY, k=10)

print(f"\n_advanced_retrieve liefert {len(results)} Dokumente:")
print("=" * 80)

for i, doc in enumerate(results, 1):
    metadata = doc.get('metadata', {})
    rrf_score = metadata.get('rrf_score', 0)
    dense_rank = metadata.get('dense_rank')
    sparse_rank = metadata.get('sparse_rank')
    chunk_id = metadata.get('chunk_id', '')
    
    if dense_rank and sparse_rank:
        source = "🔵 BEIDE"
        ranks = f"D:{dense_rank:<3} S:{sparse_rank:<3}"
    elif dense_rank:
        source = "🟢 DENSE"
        ranks = f"D:{dense_rank:<3} S:-  "
    else:
        source = "🟡 SPARSE"
        ranks = f"D:-   S:{sparse_rank:<3}"
    
    content_preview = doc.get('page_content', '')[:80].replace('\n', ' ')
    print(f"  {i:2}. RRF={rrf_score:.6f} | {source} | {ranks} | {chunk_id}")
    print(f"      Content: {content_preview}...")
