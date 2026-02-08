"""Debug: Schritt-für-Schritt durch _advanced_retrieve."""
import sys
sys.path.insert(0, ".")
import os
os.environ['ENABLE_HYBRID_RETRIEVAL'] = 'true'

from src.advanced_rag.retrieval.hybrid_retrieval_rrf import hybrid_retrieve
from src.tools.rag_tool import UniversityRAGTool

query = 'Welche Fristen gelten für die Bewerbung zum Master Business Administration?'
k = 5

print("=" * 80)
print("DEBUG: Schritt-für-Schritt durch _advanced_retrieve()")
print(f"Query: {query}")
print(f"k: {k}")
print("=" * 80)

# Initialisiere RAG-Tool
rag_tool = UniversityRAGTool()

# SCHRITT 1: Konfiguration
print("\n🔵 SCHRITT 1: Konfiguration")
k_retrieve = 80
rrf_k = rag_tool.config.hybrid_retrieval_rrf_k if rag_tool.config else 60
sparse_index_dir = rag_tool.config.hybrid_retrieval_sparse_index_dir if rag_tool.config else "data/sparse_index"
vector_db_path = rag_tool.config.vector_db_path if rag_tool.config else "data/vector_db"
print(f"  k_retrieve: {k_retrieve}")
print(f"  rrf_k: {rrf_k}")
print(f"  sparse_index_dir: {sparse_index_dir}")
print(f"  vector_db_path: {vector_db_path}")

# SCHRITT 2: Collection Names
print("\n🔵 SCHRITT 2: Collection Names")
collection_names = rag_tool._get_collection_names()
print(f"  Collections: {collection_names}")

# SCHRITT 3: Hybrid Retrieval pro Collection
print("\n🔵 SCHRITT 3: Hybrid Retrieval pro Collection")
all_results = []
for collection_name in collection_names:
    print(f"\n  Collection: {collection_name}")
    try:
        results = hybrid_retrieve(
            query=query,
            k_retrieve=k_retrieve,
            k_final=k,
            collection_name=collection_name,
            sparse_index_dir=sparse_index_dir,
            vector_db_path=vector_db_path,
            rrf_k=rrf_k
        )
        print(f"    Ergebnisse: {len(results)}")
        for i, r in enumerate(results, 1):
            print(f"      {i}. {r['chunk_id']} (RRF: {r['rrf_score']:.6f})")
        all_results.extend(results)
    except Exception as e:
        print(f"    FEHLER: {e}")

# SCHRITT 4: Sortieren nach RRF-Score
print("\n🔵 SCHRITT 4: Sortieren nach RRF-Score")
print(f"  VOR Sortierung (erste 5):")
for i, r in enumerate(all_results[:5], 1):
    print(f"    {i}. {r['chunk_id']} (RRF: {r['rrf_score']:.6f})")

all_results.sort(key=lambda x: x.get('rrf_score', 0), reverse=True)
final_results = all_results[:k]

print(f"\n  NACH Sortierung (finale {k}):")
for i, r in enumerate(final_results, 1):
    print(f"    {i}. {r['chunk_id']} (RRF: {r['rrf_score']:.6f})")

# SCHRITT 5: Konvertierung zu Document-Format
print("\n🔵 SCHRITT 5: Konvertierung zu Document-Format")
documents = []
for result in final_results:
    doc_dict = {
        'page_content': result.get('page_content', ''),
        'type': 'Document',
        'metadata': result.get('metadata', {})
    }
    doc_dict['metadata']['rrf_score'] = result.get('rrf_score', 0.0)
    doc_dict['metadata']['dense_rank'] = result.get('dense_rank')
    doc_dict['metadata']['sparse_rank'] = result.get('sparse_rank')
    doc_dict['metadata']['chunk_id'] = result.get('chunk_id', '')
    documents.append(doc_dict)

print(f"  Konvertierte Dokumente: {len(documents)}")
for i, doc in enumerate(documents, 1):
    chunk_id = doc['metadata'].get('chunk_id', '?')
    rrf_score = doc['metadata'].get('rrf_score', 0)
    dense_rank = doc['metadata'].get('dense_rank')
    sparse_rank = doc['metadata'].get('sparse_rank')
    print(f"    {i}. chunk_id={chunk_id}, rrf={rrf_score:.6f}, dense={dense_rank}, sparse={sparse_rank}")

# SCHRITT 6: Vergleich mit echtem _advanced_retrieve Aufruf
print("\n🔵 SCHRITT 6: Vergleich mit echtem _advanced_retrieve() Aufruf")
real_results = rag_tool._advanced_retrieve(query, k=k)
print(f"  Echte Ergebnisse: {len(real_results)}")
for i, doc in enumerate(real_results, 1):
    chunk_id = doc['metadata'].get('chunk_id', '?')
    rrf_score = doc['metadata'].get('rrf_score', 0)
    print(f"    {i}. chunk_id={chunk_id}, rrf={rrf_score:.6f}")

# Vergleich
print("\n" + "=" * 80)
print("VERGLEICH: Manuell vs. _advanced_retrieve()")
print("=" * 80)
manual_ids = [doc['metadata'].get('chunk_id', '') for doc in documents]
real_ids = [doc['metadata'].get('chunk_id', '') for doc in real_results]

for i, (m, r) in enumerate(zip(manual_ids, real_ids), 1):
    match = "✅" if m == r else "❌"
    print(f"  {i}. Manual: {m:<30} Real: {r:<30} {match}")
