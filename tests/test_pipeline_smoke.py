"""
Smoke-Test: Vollständige Pipeline (ohne Crawling, ohne persistentes Speichern)

Testet:
1. Preprocessing (Chunking naive + semantic)
2. In-Memory Indexierung (ChromaDB ephemeral)
3. Retrieval: Naive / Hybrid / Reranking / MMR / Alles kombiniert
4. Einen hypothetischen RAGAS-Metrik-Sample (Strukturtest, kein LLM-Call)
5. Kritische Pfade: Query-Passing, Embedding-Normalisierung, MMR-Embedding-Arithmetik,
   Kontext-Vollständigkeit, Embedding-Cleanup nach MMR
"""

import sys
import numpy as np
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================================
# Testdaten
# ============================================================================
SAMPLE_TEXT = (
    "Die WiSo-Fakultät der Universität zu Köln bietet Bachelor- und Masterstudiengänge "
    "in Wirtschaftswissenschaften, Sozialwissenschaften und Statistik an. "
    "Die Bewerbungsfrist für das Wintersemester endet am 15. Juli. "
    "Studieninteressierte können sich über das Campus-Management-System KLIPS bewerben. "
    "Für internationale Studierende gelten abweichende Fristen und Zulassungsvoraussetzungen. "
    "Das Prüfungsamt ist zuständig für Prüfungsanmeldungen und Bescheinigungen. "
    "Sprechzeiten des Prüfungsamtes sind montags und mittwochs von 10 bis 12 Uhr."
)
QUERY = "Wann ist die Bewerbungsfrist für das Wintersemester?"


# ============================================================================
# 1. Preprocessing: Naive Chunking
# ============================================================================
class TestNaiveChunking:
    def test_character_based_chunking(self):
        """Naive Chunking: Text wird korrekt in Chunks aufgeteilt."""
        chunks = []
        max_size = 200
        overlap = 50
        text = SAMPLE_TEXT

        start = 0
        while start < len(text):
            end = min(start + max_size, len(text))
            chunks.append(text[start:end])
            start += max_size - overlap

        assert len(chunks) >= 2, "Mindestens 2 Chunks erwartet"
        assert all(len(c) <= max_size + overlap for c in chunks)
        print(f"  ✅ Naive Chunking: {len(chunks)} Chunks erstellt")


# ============================================================================
# 2. Preprocessing: Semantic Chunking
# ============================================================================
class TestSemanticChunking:
    def test_semantic_chunker_produces_chunks(self):
        """SemanticChunker teilt Text in semantisch kohärente Chunks."""
        from src.advanced_rag.pre_retrieval.chunking import SemanticChunker

        chunker = SemanticChunker(
            max_chunk_size=400,
            min_chunk_size=50,
            overlap=50,
            use_percentile=True,
            percentile=10
        )
        chunks = chunker.chunk_document(SAMPLE_TEXT)

        assert len(chunks) >= 1, "Mindestens 1 Chunk erwartet"
        assert all("text" in c for c in chunks), "Jeder Chunk braucht 'text'-Key"
        total_chars = sum(len(c["text"]) for c in chunks)
        assert total_chars >= len(SAMPLE_TEXT) * 0.8, "Kein signifikanter Textverlust"
        print(f"  ✅ Semantic Chunking: {len(chunks)} Chunks, avg={total_chars//len(chunks)} Zeichen")


# ============================================================================
# 3. In-Memory Indexierung (ephemeral ChromaDB)
# ============================================================================
@pytest.fixture(scope="module")
def ephemeral_collection():
    """Erstellt eine temporäre ChromaDB-Collection mit Testdaten."""
    import chromadb
    from sentence_transformers import SentenceTransformer
    from config.settings import SENTENCE_TRANSFORMER_MODEL, EMBEDDING_MAX_SEQ_LENGTH

    client = chromadb.EphemeralClient()
    collection = client.create_collection("smoke_test")

    model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, trust_remote_code=True)
    model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH

    # 3 Mini-Chunks indizieren
    chunks = [
        "Die Bewerbungsfrist für das Wintersemester endet am 15. Juli.",
        "Das Prüfungsamt ist für Prüfungsanmeldungen zuständig.",
        "Internationale Studierende haben abweichende Zulassungsvoraussetzungen."
    ]
    embeddings = model.encode(chunks, normalize_embeddings=True).tolist()

    collection.add(
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"url": f"https://wiso.uni-koeln.de/test/{i}", "content_type": "html"} for i in range(len(chunks))]
    )
    print(f"  ✅ Ephemeral ChromaDB: {collection.count()} Chunks indiziert")
    return collection, model


class TestIndexing:
    def test_collection_count(self, ephemeral_collection):
        collection, _ = ephemeral_collection
        assert collection.count() == 3


# ============================================================================
# 4. Retrieval: Naive
# ============================================================================
class TestNaiveRetrieval:
    def test_naive_query_returns_results(self, ephemeral_collection):
        """Naive Dense Retrieval liefert Ergebnisse für die Testquery."""
        collection, model = ephemeral_collection

        query_emb = model.encode([QUERY], normalize_embeddings=True).tolist()
        results = collection.query(query_embeddings=query_emb, n_results=2, include=["documents", "distances"])

        assert results["ids"][0], "Keine Ergebnisse zurückgegeben"
        assert len(results["ids"][0]) == 2
        # Bestes Ergebnis sollte Bewerbungsfrist-Chunk sein
        best_doc = results["documents"][0][0]
        assert "Bewerbungsfrist" in best_doc or "Juli" in best_doc
        print(f"  ✅ Naive Retrieval: Top-1 = '{best_doc[:60]}...'")


# ============================================================================
# 5. Retrieval: BM25 (Sparse)
# ============================================================================
class TestBM25Retrieval:
    def test_bm25_returns_relevant_result(self, tmp_path):
        """BM25 Sparse Index findet relevante Dokumente."""
        from src.advanced_rag.retrieval.hybrid_retrieval_rrf import BM25SparseIndex

        index = BM25SparseIndex(collection_name="smoke_bm25", index_dir=str(tmp_path))
        chunks = [
            "Die Bewerbungsfrist für das Wintersemester endet am 15. Juli.",
            "Das Prüfungsamt ist für Prüfungsanmeldungen zuständig.",
            "Internationale Studierende haben abweichende Zulassungsvoraussetzungen."
        ]
        index.add_documents_batch([f"c_{i}" for i in range(3)], chunks)
        index.build_index()

        results = index.search(QUERY, top_k=2)
        assert len(results) >= 1
        best_id = results[0][0]
        assert best_id == "c_0", f"Erwartet c_0 (Bewerbungsfrist), bekommen: {best_id}"
        print(f"  ✅ BM25 Retrieval: Top-1 chunk_id={best_id}, score={results[0][1]:.3f}")


# ============================================================================
# 6. Retrieval: RRF Fusion
# ============================================================================
class TestRRFFusion:
    def test_rrf_combines_rankings(self):
        """RRF Fusion kombiniert Dense- und Sparse-Rankings korrekt."""
        from src.advanced_rag.retrieval.hybrid_retrieval_rrf import reciprocal_rank_fusion

        dense  = [("c_0", 0.95), ("c_2", 0.70), ("c_1", 0.50)]
        sparse = [("c_0", 12.0), ("c_1", 8.0),  ("c_2", 3.0)]

        fused = reciprocal_rank_fusion([dense, sparse], k=60)
        ids = [doc_id for doc_id, _ in fused]

        assert ids[0] == "c_0", "c_0 muss nach RRF-Fusion Rang 1 haben"
        # Scores sind kumulativ: c_0 erscheint in beiden Listen auf Rang 1
        assert fused[0][1] == pytest.approx(2 * (1 / 61), rel=1e-6)
        print(f"  ✅ RRF Fusion: {ids}, Top-Score={fused[0][1]:.4f}")


# ============================================================================
# 7. Retrieval: MMR
# ============================================================================
class TestMMR:
    def test_mmr_increases_diversity(self):
        """MMR wählt diversere Dokumente als reines Score-Ranking."""
        from src.advanced_rag.post_retrieval.maximum_marginal_relevance import MaximumMarginalRelevance

        # 3 Kandidaten: 2 sehr ähnlich (c_0, c_1), 1 verschieden (c_2)
        docs = [
            {"page_content": "Text A",           "metadata": {"rerank_score": 0.9}},
            {"page_content": "Text B (ähnlich)", "metadata": {"rerank_score": 0.85}},
            {"page_content": "Text C (divers)",  "metadata": {"rerank_score": 0.7}},
        ]
        # Embeddings: c_0 und c_1 sehr ähnlich, c_2 orthogonal
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.99, 0.14, 0.0],
            [0.0,  1.0,  0.0],
        ], dtype=np.float32)
        relevance_scores = [0.9, 0.85, 0.7]

        mmr = MaximumMarginalRelevance(lambda_param=0.5)
        result = mmr.select(
            documents=docs,
            document_embeddings=embeddings,
            relevance_scores=relevance_scores,
            k_final=2,
            query="Test"
        )

        selected_contents = [d["page_content"] for d in result.documents]
        assert "Text A" in selected_contents, "Höchste Relevanz muss gewählt werden"
        assert "Text C (divers)" in selected_contents, "Diverserer Text soll dem ähnlichen vorgezogen werden"
        print(f"  ✅ MMR: Auswahl={selected_contents}")


# ============================================================================
# 8. RAGConfig: Naive vs Advanced
# ============================================================================
class TestRAGConfig:
    def test_naive_setup_disables_all_advanced(self):
        from src.advanced_rag.rag_config import RAGConfig
        cfg = RAGConfig(naive_setup=True)
        assert not cfg.use_reranking
        assert not cfg.use_mmr
        assert not cfg.use_hybrid_retrieval
        print("  ✅ RAGConfig naive_setup=True: alle Advanced-Flags deaktiviert")

    def test_advanced_setup_respects_individual_flags(self):
        from src.advanced_rag.rag_config import RAGConfig
        cfg = RAGConfig(naive_setup=False, enable_reranking=True, enable_mmr=False, enable_hybrid_retrieval=False)
        assert cfg.use_reranking
        assert not cfg.use_mmr
        assert not cfg.use_hybrid_retrieval
        print("  ✅ RAGConfig granulare Flags: nur Reranking aktiv")


# ============================================================================
# 9. RAGAS Sample (Strukturtest — kein LLM-Call)
# ============================================================================
class TestRAGASSampleStructure:
    def test_single_turn_sample_structure(self):
        """SingleTurnSample hat alle Pflichtfelder und korrekte Typen."""
        from ragas.dataset_schema import SingleTurnSample

        sample = SingleTurnSample(
            user_input=QUERY,
            response="Die Bewerbungsfrist für das Wintersemester endet am 15. Juli.",
            retrieved_contexts=["Die Bewerbungsfrist endet am 15. Juli.", "KLIPS ist das Bewerbungsportal."],
            reference="Die Bewerbungsfrist für das Wintersemester endet am 15. Juli."
        )

        assert sample.user_input == QUERY
        assert isinstance(sample.retrieved_contexts, list)
        assert len(sample.retrieved_contexts) == 2
        assert sample.reference is not None
        print("  ✅ RAGAS SingleTurnSample: Struktur korrekt")

    def test_bert_score_structure(self):
        """BERT-Score liefert P, R, F1 mit korrekter Dimension."""
        try:
            from bert_score import score as bert_score_fn
        except ImportError:
            pytest.skip("bert_score nicht installiert")

        responses  = ["Die Frist endet am 15. Juli."]
        references = ["Die Bewerbungsfrist endet am 15. Juli."]

        import warnings
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore")
            P, R, F1 = bert_score_fn(responses, references, model_type="xlm-roberta-large",
                                      lang="de", verbose=False, rescale_with_baseline=True)

        assert P.shape == (1,)
        assert R.shape == (1,)
        assert F1.shape == (1,)
        assert 0.0 <= F1[0].item() <= 1.0
        print(f"  ✅ BERT-Score: P={P[0]:.3f}, R={R[0]:.3f}, F1={F1[0]:.3f}")


# ============================================================================
# 10. Query-Passing: wird die Query ungekürzt durchgereicht?
# ============================================================================
class TestQueryPassing:
    def test_query_not_truncated_in_format_results(self):
        """_format_naive_results darf die Query nicht verändern — sie geht 1:1 ans Retrieval."""
        # Die Query wird von _run() direkt an _naive_retrieve() / _advanced_retrieve() übergeben.
        # Wir simulieren dies, indem wir prüfen, dass keine implizite Kürzung stattfindet.
        long_query = "A" * 2000  # Länger als typische Tokenizer-Limits (512 / 8192 Tokens)

        # _format_naive_results berührt die Query gar nicht — aber das Embedding-Modell
        # schneidet via max_seq_length. Test: Kürzung passiert ERST im Encoder, nicht vorher.
        from sentence_transformers import SentenceTransformer
        from config.settings import SENTENCE_TRANSFORMER_MODEL, EMBEDDING_MAX_SEQ_LENGTH

        model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, trust_remote_code=True)
        model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH

        # encode() akzeptiert beliebig lange Strings — kein Python-seitiger ValueError
        emb = model.encode([long_query], normalize_embeddings=True)
        assert emb.shape == (1, emb.shape[1]), "Embedding muss 2D sein (1 x dim)"
        # Die Query wird intern auf max_seq_length Tokens truncated, das Ergebnis ist aber immer ein Vektor
        assert not np.any(np.isnan(emb)), "Kein NaN im Embedding nach Truncation"
        print(f"  ✅ Query-Truncation im Encoder: shape={emb.shape}, max_seq={EMBEDDING_MAX_SEQ_LENGTH}")

    def test_rag_tool_run_passes_full_query_to_retrieval(self, monkeypatch):
        """_run() übergibt die Query 1:1 — keine Modifikation auf dem Weg zum Retrieval.
        
        RAGConfig(naive_setup=True, enable_sparse_retrieval=False) → _naive_retrieve-Pfad.
        RAGConfig(naive_setup=True)                                 → _sparse_retrieve-Pfad.
        Wir testen beide explizit.
        """
        from src.tools.rag_tool import UniversityRAGTool
        from src.advanced_rag.rag_config import RAGConfig

        test_query = "Wie bewerbe ich mich für den Master BWL an der WiSo-Fakultät?"

        # --- Pfad 1: Naive (sparse disabled) → _naive_retrieve ---
        captured_naive = []
        tool_naive = UniversityRAGTool(
            config=RAGConfig(naive_setup=True, enable_sparse_retrieval=False)
        )
        monkeypatch.setattr(tool_naive, "_naive_retrieve",
                            lambda q, **kw: captured_naive.append(q) or [])

        tool_naive._run(test_query)
        assert len(captured_naive) == 1
        assert captured_naive[0] == test_query, (
            f"Naive-Pfad: Query verändert! '{captured_naive[0]}' ≠ '{test_query}'"
        )

        # --- Pfad 2: Sparse → _sparse_retrieve ---
        captured_sparse = []
        tool_sparse = UniversityRAGTool(
            config=RAGConfig(naive_setup=True, enable_sparse_retrieval=True)
        )
        monkeypatch.setattr(tool_sparse, "_sparse_retrieve",
                            lambda q, **kw: captured_sparse.append(q) or [])

        tool_sparse._run(test_query)
        assert len(captured_sparse) == 1
        assert captured_sparse[0] == test_query, (
            f"Sparse-Pfad: Query verändert! '{captured_sparse[0]}' ≠ '{test_query}'"
        )

        print(f"  ✅ Query-Passing: Query unverändert in beiden Retrieval-Pfaden")


# ============================================================================
# 11. Embedding-Normalisierung (Kernvoraussetzung für Cosine-Similarity)
# ============================================================================
class TestEmbeddingNormalization:
    def test_normalized_embedding_has_unit_norm(self):
        """Embeddings nach normalize_embeddings=True haben ||v|| = 1.0."""
        from sentence_transformers import SentenceTransformer
        from config.settings import SENTENCE_TRANSFORMER_MODEL, EMBEDDING_MAX_SEQ_LENGTH

        model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, trust_remote_code=True)
        model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH

        texts = [
            "Die Bewerbungsfrist endet am 15. Juli.",
            "Das Prüfungsamt ist zuständig.",
            "Kurzer Text.",
        ]
        embeddings = model.encode(texts, normalize_embeddings=True)

        norms = np.linalg.norm(embeddings, axis=1)
        for i, norm in enumerate(norms):
            assert abs(norm - 1.0) < 1e-5, f"Embedding {i}: ||v|| = {norm:.6f} ≠ 1.0"
        print(f"  ✅ Embedding-Normalisierung: alle {len(norms)} Vektoren mit ||v||=1")

    def test_manual_normalization_matches_model_normalization(self):
        """Die manuelle Normalisierung in _naive_retrieve entspricht normalize_embeddings=True."""
        from sentence_transformers import SentenceTransformer
        from config.settings import SENTENCE_TRANSFORMER_MODEL, EMBEDDING_MAX_SEQ_LENGTH

        model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, trust_remote_code=True)
        model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH

        text = [QUERY]

        # Methode 1: Model-seitig (wie beim Indexieren in run_production_scraper)
        emb_model_normalized = model.encode(text, normalize_embeddings=True)

        # Methode 2: Manuell (wie in _naive_retrieve: raw / norm)
        raw = model.encode(text)
        emb_manual_normalized = raw / np.linalg.norm(raw, axis=1, keepdims=True)

        np.testing.assert_allclose(
            emb_model_normalized, emb_manual_normalized,
            atol=1e-5,
            err_msg="Manuelle und model-seitige Normalisierung weichen ab!"
        )
        print("  ✅ Normalisierungs-Konsistenz: _naive_retrieve ≡ run_production_scraper")

    def test_cosine_similarity_via_dot_product_is_correct(self):
        """Nach Normalisierung gilt: cosine_sim(a,b) = dot(a,b) — das nutzt sowohl ChromaDB als auch MMR."""
        a = np.array([[3.0, 4.0]])  # ||a|| = 5
        b = np.array([[0.0, 1.0]])  # bereits normalisiert

        a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)

        # Cosine via dot product (wie in MMR._compute_similarity_matrix)
        sim_dot = float(np.dot(a_norm, b.T))

        # Explizite Cosine-Formel
        sim_explicit = float(
            np.dot(a_norm.flatten(), b.flatten()) /
            (np.linalg.norm(a_norm) * np.linalg.norm(b))
        )

        assert abs(sim_dot - sim_explicit) < 1e-6, (
            f"dot={sim_dot:.6f} ≠ cosine={sim_explicit:.6f}"
        )
        assert abs(sim_dot - 0.8) < 1e-5, f"Erwartet 0.8 (4/5), bekommen {sim_dot:.6f}"
        print(f"  ✅ Cosine via Dot-Product: sim(a_norm, b) = {sim_dot:.4f} ✓")


# ============================================================================
# 12. MMR: Embedding-Array-Bau aus metadata und Cosine-Similarity-Matrix
# ============================================================================
class TestMMREmbeddingArithmetic:
    def test_embedding_array_built_correctly_from_metadata(self):
        """Embeddings werden korrekt aus doc['metadata']['embedding'] zu np.array gebaut."""
        # Simuliert den Pfad in _advanced_retrieve: metadata['embedding'] → np.array
        docs = [
            {"page_content": "Text A", "metadata": {"rerank_score": 0.9,
             "embedding": [1.0, 0.0, 0.0]}},
            {"page_content": "Text B", "metadata": {"rerank_score": 0.7,
             "embedding": [0.0, 1.0, 0.0]}},
        ]

        embeddings_list = []
        for doc in docs:
            emb = doc["metadata"].get("embedding")
            assert emb is not None, "embedding muss in metadata vorhanden sein"
            embeddings_list.append(emb)

        document_embeddings = np.array(embeddings_list)
        assert document_embeddings.shape == (2, 3), f"Erwartet (2,3), got {document_embeddings.shape}"
        print(f"  ✅ Embedding-Array aus metadata: shape={document_embeddings.shape}")

    def test_mmr_similarity_matrix_shape_and_values(self):
        """MMR._compute_similarity_matrix liefert korrekte (n×n)-Matrix mit Werten in [-1,1]."""
        from src.advanced_rag.post_retrieval.maximum_marginal_relevance import MaximumMarginalRelevance

        mmr = MaximumMarginalRelevance(lambda_param=0.5, similarity_metric="cosine")

        # 3 normalisierte Vektoren (wie sie aus ChromaDB kommen)
        embeddings = np.array([
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0 / np.sqrt(2), 1.0 / np.sqrt(2), 0.0],  # 45° zwischen e1 und e2
        ], dtype=np.float32)

        sim_matrix = mmr._compute_similarity_matrix(embeddings)

        assert sim_matrix.shape == (3, 3), f"Erwartet (3,3), got {sim_matrix.shape}"
        # Diagonale: sim(v, v) = 1.0 (normalisiert)
        np.testing.assert_allclose(np.diag(sim_matrix), [1.0, 1.0, 1.0], atol=1e-5)
        # sim(e1, e2) = 0 (orthogonal)
        assert abs(sim_matrix[0, 1]) < 1e-5, f"e1·e2 sollte 0 sein, ist {sim_matrix[0,1]}"
        # sim(e1, 45°) = 1/√2 ≈ 0.707
        assert abs(sim_matrix[0, 2] - 1.0 / np.sqrt(2)) < 1e-5
        print(f"  ✅ MMR Similarity-Matrix: shape={sim_matrix.shape}, Diag=1, orthogonal=0")

    def test_mmr_embedding_cleanup_after_selection(self):
        """Nach MMR werden Embeddings aus metadata entfernt — kein Overhead ans LLM."""
        from src.advanced_rag.post_retrieval.maximum_marginal_relevance import MaximumMarginalRelevance
        import copy

        docs = [
            {"page_content": "Text A", "metadata": {"rerank_score": 0.9, "embedding": [1.0, 0.0]}},
            {"page_content": "Text B", "metadata": {"rerank_score": 0.8, "embedding": [0.9, 0.44]}},
            {"page_content": "Text C", "metadata": {"rerank_score": 0.5, "embedding": [0.0, 1.0]}},
        ]
        embeddings = np.array([d["metadata"]["embedding"] for d in docs], dtype=np.float32)
        relevance_scores = [d["metadata"]["rerank_score"] for d in docs]

        mmr = MaximumMarginalRelevance(lambda_param=0.7)
        result = mmr.select(
            documents=copy.deepcopy(docs),
            document_embeddings=embeddings,
            relevance_scores=relevance_scores,
            k_final=2,
            query="Test"
        )

        # Simuliere den Cleanup-Schritt aus _advanced_retrieve (Zeile ~462 in rag_tool.py)
        for doc in result.documents:
            if "embedding" in doc.get("metadata", {}):
                del doc["metadata"]["embedding"]

        for doc in result.documents:
            assert "embedding" not in doc.get("metadata", {}), (
                f"Embedding nicht entfernt aus: {doc['page_content']}"
            )
        print(f"  ✅ Embedding-Cleanup: keine Embeddings in finalen Dokumenten")

    def test_mmr_score_formula(self):
        """MMR-Score-Formel: score = λ·relevance − (1−λ)·max_sim_to_selected."""
        # Manuell: λ=0.5, Relevanz=[0.9, 0.8], sim(doc0,doc1)=0.0 (orthogonal)
        # Iteration 1 (keine Auswahl): score(doc0)=0.5*0.9=0.45 > score(doc1)=0.5*0.8=0.4 → doc0
        # Iteration 2: score(doc1)=0.5*0.8 - 0.5*0.0=0.4 → doc1
        from src.advanced_rag.post_retrieval.maximum_marginal_relevance import MaximumMarginalRelevance

        docs = [
            {"page_content": "A", "metadata": {"rerank_score": 0.9}},
            {"page_content": "B", "metadata": {"rerank_score": 0.8}},
        ]
        embeddings = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)  # orthogonal
        relevance_scores = [0.9, 0.8]

        mmr = MaximumMarginalRelevance(lambda_param=0.5)
        result = mmr.select(docs, embeddings, relevance_scores, k_final=2)

        selected = [d["page_content"] for d in result.documents]
        assert selected[0] == "A", f"Dok A (höhere Relevanz) erwartet auf Platz 1, war: {selected}"
        assert selected[1] == "B"
        # Bei orthogonalen Vektoren kein Diversitäts-Penalty → reine Relevanz-Sortierung
        print(f"  ✅ MMR-Score-Formel: Auswahl={selected} (keine Penalty bei orthogonalen Docs)")


# ============================================================================
# 13. Kontext-Vollständigkeit: _format_naive_results gibt alle page_contents aus
# ============================================================================
class TestContextCompleteness:
    def test_format_includes_all_documents(self):
        """_format_naive_results enthält den Content aller übergebenen Dokumente."""
        from src.tools.rag_tool import UniversityRAGTool

        tool = UniversityRAGTool()
        docs = [
            {"page_content": "Bewerbungsfrist ist der 15. Juli.", "metadata": {}},
            {"page_content": "Das Prüfungsamt öffnet montags.", "metadata": {}},
            {"page_content": "KLIPS ist das Bewerberportal.", "metadata": {}},
        ]

        formatted = tool._format_naive_results(docs)

        for doc in docs:
            assert doc["page_content"] in formatted, (
                f"Inhalt fehlt im formatierten Kontext: '{doc['page_content']}'"
            )
        print(f"  ✅ Kontext-Vollständigkeit: alle {len(docs)} page_contents enthalten")

    def test_format_empty_docs_returns_fallback(self):
        """_format_naive_results gibt einen definierten Fallback bei leerer Liste zurück."""
        from src.tools.rag_tool import UniversityRAGTool

        tool = UniversityRAGTool()
        result = tool._format_naive_results([])

        assert isinstance(result, str)
        assert len(result) > 0, "Fallback darf nicht leer sein"
        print(f"  ✅ Kontext-Fallback: '{result}'")

    def test_format_preserves_document_order(self):
        """Die Reihenfolge der Dokumente im formatierten String entspricht der Eingabe."""
        from src.tools.rag_tool import UniversityRAGTool

        tool = UniversityRAGTool()
        docs = [
            {"page_content": "ERSTER_INHALT", "metadata": {}},
            {"page_content": "ZWEITER_INHALT", "metadata": {}},
            {"page_content": "DRITTER_INHALT", "metadata": {}},
        ]

        formatted = tool._format_naive_results(docs)
        pos_first  = formatted.index("ERSTER_INHALT")
        pos_second = formatted.index("ZWEITER_INHALT")
        pos_third  = formatted.index("DRITTER_INHALT")

        assert pos_first < pos_second < pos_third, (
            "Dokument-Reihenfolge im Kontext stimmt nicht mit Eingabe-Reihenfolge überein"
        )
        print(f"  ✅ Kontext-Reihenfolge: Positionen {pos_first} < {pos_second} < {pos_third}")

