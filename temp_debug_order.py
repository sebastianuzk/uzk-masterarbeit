"""Debug: Prüfe Reihenfolge der Hybrid Retrieval Ergebnisse."""
from src.advanced_rag.retrieval.hybrid_retrieval_rrf import HybridRetriever, reciprocal_rank_fusion

# GLEICHE Query wie im Haupttest!
query = 'Welche Fristen gelten für die Bewerbung zum Master Business Administration?'

retriever = HybridRetriever()

# Hole Dense und Sparse mit k=80 (wie im echten Retrieval)
k_retrieve = 80
dense = retriever._dense_retrieve(query, k_retrieve)
sparse = retriever._sparse_retrieve(query, k_retrieve)

print("=" * 80)
print(f"Query: {query}")
print(f"k_retrieve: {k_retrieve}")
print("=" * 80)

# Finde Überlappung
dense_ids = set(id for id, _ in dense)
sparse_ids = set(id for id, _ in sparse)
overlap = dense_ids & sparse_ids

print(f"\nÜBERLAPPUNG: {len(overlap)} Dokumente in BEIDEN Rankings (von je {k_retrieve})")

# RRF Fusion
fused = reciprocal_rank_fusion([dense, sparse], k=60)

print("\n" + "=" * 80)
print("RRF FUSION Top 10:")
print("=" * 80)
for i, (chunk_id, rrf_score) in enumerate(fused[:10], 1):
    in_dense = chunk_id in dense_ids
    in_sparse = chunk_id in sparse_ids
    
    if in_dense and in_sparse:
        source = "🔵 BEIDE"
        d_rank = next(i for i, (id, _) in enumerate(dense, 1) if id == chunk_id)
        s_rank = next(i for i, (id, _) in enumerate(sparse, 1) if id == chunk_id)
    elif in_dense:
        source = "🟢 DENSE"
        d_rank = next(i for i, (id, _) in enumerate(dense, 1) if id == chunk_id)
        s_rank = "-"
    else:
        source = "🟡 SPARSE"
        d_rank = "-"
        s_rank = next(i for i, (id, _) in enumerate(sparse, 1) if id == chunk_id)
    
    print(f"  {i:2}. RRF={rrf_score:.6f} | {source} | D:{d_rank:<3} S:{s_rank:<3} | {chunk_id}")
