"""
Detaillierter Test: Hybrid Retrieval mit dem echten ReAct-Agent
================================================================
Testet den vollständigen Chatbot-Workflow mit Hybrid Retrieval und
dokumentiert welche Dokumente von Dense vs. Sparse kommen.
Zeigt auch Vorher/Nachher-Vergleich bei ReRanking.
"""

import os
import sys
import logging
import copy

# Logging konfigurieren um Retrieval-Details zu sehen
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

# Setze Environment für Hybrid Retrieval
os.environ['ENABLE_HYBRID_RETRIEVAL'] = 'true'
os.environ['RAG_NAIVE_SETUP'] = 'false'

from src.advanced_rag.retrieval.hybrid_retrieval_rrf import HybridRetriever, reciprocal_rank_fusion
from src.advanced_rag.rag_config import RAGConfig
from config.settings import Settings
from src.agent.react_agent import create_react_agent

# Lade Hyperparameter aus Config
config = RAGConfig.load_from_env()
TOP_K = Settings.TOP_K
K_RETRIEVE = config.hybrid_retrieval_k_retrieve
RRF_K = config.hybrid_retrieval_rrf_k


def analyze_hybrid_retrieval(query: str, k_retrieve: int = None, k_final: int = None):
    """
    Analysiert das Hybrid Retrieval separat für Dokumentation.
    """
    # Nutze Config-Werte als Default
    k_retrieve = k_retrieve or K_RETRIEVE
    k_final = k_final or TOP_K
    
    print("\n" + "=" * 100)
    print(f"📊 HYBRID RETRIEVAL ANALYSE (vor Agent-Aufruf)")
    print(f"Query: \"{query}\"")
    print(f"Hyperparameter: k_retrieve={k_retrieve}, k_final={k_final}, rrf_k={RRF_K}")
    print("=" * 100)
    
    retriever = HybridRetriever(
        collection_name="wiso_documents",
        sparse_index_dir="data/sparse_index",
        vector_db_path="data/vector_db",
        rrf_k=RRF_K
    )
    
    # Dense Retrieval - ALLE Kandidaten
    dense_results = retriever._dense_retrieve(query, k_retrieve)
    print(f"\n🟢 DENSE RETRIEVAL (ChromaDB) - Alle {len(dense_results)} Kandidaten:")
    for i, (chunk_id, score) in enumerate(dense_results, 1):
        print(f"  {i:3}. {chunk_id:<35} Similarity: {score:.4f}")
    
    # Sparse Retrieval - ALLE Kandidaten
    sparse_results = retriever._sparse_retrieve(query, k_retrieve)
    print(f"\n🟡 SPARSE RETRIEVAL (BM25) - Alle {len(sparse_results)} Kandidaten:")
    for i, (chunk_id, score) in enumerate(sparse_results, 1):
        print(f"  {i:3}. {chunk_id:<35} BM25: {score:.4f}")
    
    # RRF Fusion - ALLE fusionierten Ergebnisse
    fused = reciprocal_rank_fusion([dense_results, sparse_results], k=RRF_K)
    dense_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(dense_results, 1)}
    sparse_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(sparse_results, 1)}
    
    print(f"\n🔵 RRF FUSION - Alle {len(fused)} fusionierten Ergebnisse:")
    for i, (chunk_id, rrf_score) in enumerate(fused, 1):
        d_rank = dense_ranks.get(chunk_id, "-")
        s_rank = sparse_ranks.get(chunk_id, "-")
        print(f"  {i:3}. {chunk_id:<35} RRF: {rrf_score:.6f}  D:{d_rank:<3} S:{s_rank}")
    
    # Finale Ergebnisse
    print(f"\n📄 FINALE TOP-{k_final} (werden dem Agent übergeben):")
    # Hole alle fusionierten Ergebnisse (k_final wird nicht mehr übergeben)
    final_results = retriever.retrieve(query, k_retrieve=k_retrieve)
    
    # Limitiere manuell auf k_final für die Anzeige
    final_results = final_results[:k_final]
    
    only_dense = 0
    only_sparse = 0
    both = 0
    
    for i, result in enumerate(final_results, 1):
        d_rank = result['dense_rank']
        s_rank = result['sparse_rank']
        
        if d_rank and s_rank:
            source = "🔵 BEIDE"
            both += 1
        elif d_rank:
            source = "🟢 DENSE"
            only_dense += 1
        else:
            source = "🟡 SPARSE"
            only_sparse += 1
        
        url = result['metadata'].get('url', 'N/A')[:60]
        print(f"\n  {i}. {source}")
        print(f"     ID: {result['chunk_id']}")
        print(f"     RRF: {result['rrf_score']:.6f} | Dense: {d_rank or '-'} | Sparse: {s_rank or '-'}")
        print(f"     URL: {url}...")
        print(f"     Text: {result['page_content'][:150]}...")
    
    print(f"\n📈 HERKUNFT: Dense-only: {only_dense} | Sparse-only: {only_sparse} | Beide: {both}")
    
    return final_results


def test_reranking_comparison(query: str):
    """
    Testet ReRanking und zeigt Vorher/Nachher-Vergleich.
    Zeigt ALLE Dokumente die dem ReRanker übergeben werden (nicht nur Top-K).
    """
    from src.advanced_rag.post_retrieval.reranking import VoyageReranker
    from src.advanced_rag.retrieval.hybrid_retrieval_rrf import HybridRetriever, reciprocal_rank_fusion
    
    print("\n" + "=" * 100)
    print("🔄 RERANKING VORHER/NACHHER-VERGLEICH")
    print(f"Query: \"{query}\"")
    print(f"k_retrieve={K_RETRIEVE} (Kandidaten pro Methode)")
    print(f"reranking_candidates={config.reranking_candidates} (Top-N für ReRanking)")
    print(f"k_final={TOP_K} (finale Auswahl NACH ReRanking)")
    print("=" * 100)
    
    # Hole ALLE Dokumente via Hybrid Retrieval (ohne k_final Limitierung!)
    retriever = HybridRetriever(
        collection_name="wiso_documents",
        sparse_index_dir="data/sparse_index",
        vector_db_path="data/vector_db",
        rrf_k=RRF_K
    )
    
    # Dense + Sparse Retrieval
    dense_results = retriever._dense_retrieve(query, K_RETRIEVE)
    sparse_results = retriever._sparse_retrieve(query, K_RETRIEVE)
    
    # RRF Fusion - gibt ALLE fusionierten Ergebnisse zurück
    fused = reciprocal_rank_fusion([dense_results, sparse_results], k=RRF_K)
    
    # Erstelle Rank-Mappings
    dense_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(dense_results, 1)}
    sparse_ranks = {doc_id: rank for rank, (doc_id, _) in enumerate(sparse_results, 1)}
    
    # Hole Content für alle fusionierten Dokumente direkt aus ChromaDB
    all_chunk_ids = [chunk_id for chunk_id, _ in fused]
    rrf_scores = {chunk_id: score for chunk_id, score in fused}
    
    collection = retriever._get_chroma_collection()
    chroma_data = collection.get(
        ids=all_chunk_ids,
        include=['documents', 'metadatas']
    )
    
    # Baue Lookup-Dict für ChromaDB-Daten
    chroma_lookup = {}
    for i, chunk_id in enumerate(chroma_data['ids']):
        chroma_lookup[chunk_id] = {
            'document': chroma_data['documents'][i] if chroma_data.get('documents') else '',
            'metadata': chroma_data['metadatas'][i] if chroma_data.get('metadatas') else {}
        }
    
    # Konvertiere zu Document-Format (wie in rag_tool.py) - behalte RRF-Reihenfolge!
    documents_before = []
    for chunk_id, rrf_score in fused:
        content_data = chroma_lookup.get(chunk_id, {})
        doc_dict = {
            'page_content': content_data.get('document', ''),
            'type': 'Document',
            'metadata': {
                **content_data.get('metadata', {}),
                'rrf_score': rrf_score,
                'dense_rank': dense_ranks.get(chunk_id),
                'sparse_rank': sparse_ranks.get(chunk_id),
                'chunk_id': chunk_id
            }
        }
        documents_before.append(doc_dict)
    
    # Kopiere für Vergleich - nur die Top-N Kandidaten für ReRanking!
    reranking_candidates = config.reranking_candidates
    documents_for_reranking = copy.deepcopy(documents_before[:reranking_candidates])
    
    # VORHER - ALLE RRF-fusionierten Dokumente
    print(f"\n📋 ALLE RRF-FUSIONIERTEN DOKUMENTE ({len(documents_before)} Dokumente):")
    print("-" * 100)
    for i, doc in enumerate(documents_before, 1):
        meta = doc['metadata']
        chunk_id = meta.get('chunk_id', 'N/A')
        rrf_score = meta.get('rrf_score', 0)
        dense_rank = meta.get('dense_rank', '-')
        sparse_rank = meta.get('sparse_rank', '-')
        marker = "→" if i <= reranking_candidates else " "
        print(f"  {marker} {i:3}. {chunk_id:<35} RRF: {rrf_score:.6f} | D:{str(dense_rank or '-'):<3} S:{str(sparse_rank or '-'):<3}")
    
    print(f"\n📋 TOP-{reranking_candidates} FÜR RERANKING (RRF-Reihenfolge):")
    print("-" * 100)
    for i, doc in enumerate(documents_for_reranking, 1):
        meta = doc['metadata']
        chunk_id = meta.get('chunk_id', 'N/A')
        rrf_score = meta.get('rrf_score', 0)
        dense_rank = meta.get('dense_rank', '-')
        sparse_rank = meta.get('sparse_rank', '-')
        print(f"  {i:3}. {chunk_id:<35} RRF: {rrf_score:.6f} | D:{str(dense_rank or '-'):<3} S:{str(sparse_rank or '-'):<3}")
    
    # ReRanking durchführen - mit Top-N Kandidaten!
    # WICHTIG: Speichere Reihenfolge VOR ReRanking als Liste (nicht deepcopy!)
    # da rerank() in-place sortiert
    order_before_reranking = [doc['metadata'].get('chunk_id', '') for doc in documents_for_reranking]
    
    print(f"\n⏳ Führe ReRanking durch mit {len(documents_for_reranking)} Dokumenten...")
    reranker = VoyageReranker(model=config.reranking_model)
    documents_after = reranker.rerank(query, documents_for_reranking)
    
    # Reihenfolge NACH ReRanking
    order_after_reranking = [doc['metadata'].get('chunk_id', '') for doc in documents_after]
    
    # NACHHER - ReRanked Dokumente
    print(f"\n📋 NACH RERANKING (Voyage {config.reranking_model} Reihenfolge, {len(documents_after)} Dokumente):")
    print("-" * 100)
    for i, doc in enumerate(documents_after, 1):
        meta = doc['metadata']
        chunk_id = meta.get('chunk_id', 'N/A')
        rerank_score = meta.get('rerank_score', 0)
        rrf_score = meta.get('rrf_score', 0)
        dense_rank = meta.get('dense_rank', '-')
        sparse_rank = meta.get('sparse_rank', '-')
        print(f"  {i:3}. {chunk_id:<35} ReRank: {rerank_score:.4f} | RRF: {rrf_score:.6f} | D:{str(dense_rank or '-'):<3} S:{str(sparse_rank or '-'):<3}")
    
    # Vergleich: Ranking-Änderungen
    print(f"\n📊 RANKING-ÄNDERUNGEN (Top-{min(20, len(documents_after))} nach ReRanking):")
    print("-" * 100)
    
    before_order = order_before_reranking
    after_order = order_after_reranking
    
    for i, chunk_id in enumerate(after_order[:20], 1):
        old_pos = before_order.index(chunk_id) + 1 if chunk_id in before_order else '-'
        change = old_pos - i if isinstance(old_pos, int) else 0
        
        if change > 0:
            arrow = f"⬆️ +{change}"
        elif change < 0:
            arrow = f"⬇️ {change}"
        else:
            arrow = "➡️  0"
        
        print(f"  {i:3}. {chunk_id:<35} {arrow} (vorher: Pos {old_pos})")
    
    # Finale Auswahl: Top-K nach ReRanking
    final_top_k = documents_after[:TOP_K]
    print(f"\n🎯 FINALE TOP-{TOP_K} (werden dem Agent übergeben):")
    print("-" * 100)
    for i, doc in enumerate(final_top_k, 1):
        meta = doc['metadata']
        chunk_id = meta.get('chunk_id', 'N/A')
        rerank_score = meta.get('rerank_score', 0)
        print(f"  {i}. {chunk_id:<35} ReRank: {rerank_score:.4f}")
    
    return documents_before, documents_after


def test_with_react_agent(query: str):
    """
    Testet mit dem echten ReAct-Agent (wie im Chatbot).
    """
    print("\n" + "=" * 100)
    print("🤖 TEST MIT ECHTEM REACT-AGENT")
    print("=" * 100)
    
    # Erstelle Agent
    print("\n⏳ Initialisiere ReAct-Agent...")
    agent = create_react_agent()
    
    print(f"   Tools: {agent.get_available_tools()}")
    print(f"   LLM: {agent.llm.model_name if hasattr(agent.llm, 'model_name') else 'N/A'}")
    
    print(f"\n📝 USER QUERY: \"{query}\"")
    print("-" * 100)
    
    # Rufe Agent auf
    print("\n⏳ Agent verarbeitet Anfrage...\n")
    response = agent.chat(query)
    
    print("\n" + "=" * 100)
    print("🤖 AGENT RESPONSE:")
    print("=" * 100)
    print(response)
    
    # Memory-Info
    print("\n" + "-" * 50)
    print("📊 AGENT MEMORY:")
    print(agent.get_memory_summary())
    
    return response


if __name__ == "__main__":
    # Test-Query für Hybrid-Debugging
    test_query = "Vorteile eines Studiums an der WiSo-Fakultät"
    
    print("\n" + "=" * 100)
    print("📋 KONFIGURATION AUS rag.env / settings.py:")
    print(f"   TOP_K (finale Dokumente): {TOP_K}")
    print(f"   K_RETRIEVE (Kandidaten pro Methode): {K_RETRIEVE}")
    print(f"   RRF_K (RRF Parameter): {RRF_K}")
    print(f"   RERANKING: {config.use_reranking} (Modell: {config.reranking_model}, Kandidaten: {config.reranking_candidates})")
    print("=" * 100)
    
    # 1. Analysiere Hybrid Retrieval (zeigt welche Dokumente woher kommen)
    retrieval_results = analyze_hybrid_retrieval(test_query)
    
    # 2. ReRanking-Test deaktiviert
    # if config.use_reranking:
    #     before, after = test_reranking_comparison(test_query)
    
    # 3. Agent-Test deaktiviert
    # user_query = "Welche ersten Schritte soll ich laut Notfallplan unternehmen, wenn ich einen Viren- oder Trojanerbefall vermute?"
    # agent_response = test_with_react_agent(user_query)
    
    print("\n" + "=" * 100)
    print("✅ HYBRID RETRIEVAL DEBUG ABGESCHLOSSEN")
    print("=" * 100)
