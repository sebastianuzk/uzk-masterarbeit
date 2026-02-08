"""Debug: Prüfe die gesamte Pipeline bis zum RAG-Tool."""
import sys
sys.path.insert(0, ".")
import os
os.environ['ENABLE_HYBRID_RETRIEVAL'] = 'true'

from src.advanced_rag.retrieval.hybrid_retrieval_rrf import hybrid_retrieve
from src.tools.rag_tool import UniversityRAGTool

query = 'Welche Fristen gelten für die Bewerbung zum Master Business Administration?'

print("=" * 80)
print("DEBUG: Vergleiche hybrid_retrieve() vs. RAG-Tool._advanced_retrieve()")
print("=" * 80)

# 1. Direkt hybrid_retrieve
print("\n🔵 DIREKT hybrid_retrieve():")
direct_results = hybrid_retrieve(query, k_retrieve=80, k_final=5)
for i, result in enumerate(direct_results, 1):
    print(f"  {i}. {result['chunk_id']} (RRF: {result['rrf_score']:.6f})")

# 2. Über RAG-Tool
print("\n🟢 ÜBER RAG-TOOL._advanced_retrieve():")
rag_tool = UniversityRAGTool()
rag_results = rag_tool._advanced_retrieve(query, k=5)
for i, result in enumerate(rag_results, 1):
    chunk_id = result.get('metadata', {}).get('chunk_id', '?')
    rrf_score = result.get('metadata', {}).get('rrf_score', 0)
    print(f"  {i}. {chunk_id} (RRF: {rrf_score:.6f})")

# 3. Vergleiche
print("\n" + "=" * 80)
print("VERGLEICH:")
print("=" * 80)
direct_ids = [r['chunk_id'] for r in direct_results]
rag_ids = [r.get('metadata', {}).get('chunk_id', '') for r in rag_results]

if direct_ids == rag_ids:
    print("✅ Reihenfolge STIMMT ÜBEREIN")
else:
    print("❌ Reihenfolge WEICHT AB!")
    for i, (d, r) in enumerate(zip(direct_ids, rag_ids), 1):
        match = "✅" if d == r else "❌"
        print(f"  {i}. Direct: {d:<30} RAG: {r:<30} {match}")
