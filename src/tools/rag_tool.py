"""
RAG Tool für den Chatbot-Agent

Naives RAG-Tool für Retrieval-Augmented Generation.
Greift auf die vom Web-Scraper erstellte ChromaDB-Vectordatenbank zu.

Modular erweiterbar mit Advanced RAG Techniken aus src.advanced_rag.
Die Techniken werden optional geladen, basierend auf RAGConfig.

Unterstützt:
- Naive RAG: Single Collection Dense Retrieval
- Advanced RAG: Multi-Collection Search mit Reranking
- Hybrid RAG: Dense + BM25 Sparse mit RRF Fusion
"""

import logging
from typing import Any, Dict, List, Optional
import numpy as np

from langchain.tools import BaseTool
from langsmith import traceable
from pydantic import Field

logger = logging.getLogger(__name__)

# Import RAG Configuration
try:
    from src.advanced_rag.rag_config import RAGConfig
    CONFIG_AVAILABLE = True
except ImportError:
    logger.warning("RAGConfig nicht gefunden - verwende naive RAG")
    CONFIG_AVAILABLE = False
    RAGConfig = None

# Import hyperparameters
try:
    from config.settings import Settings
    TOP_K = Settings.TOP_K
except ImportError:
    TOP_K = 5  # fallback


class UniversityRAGTool(BaseTool):
    """
    Tool für die Universitäts-Wissensdatenbank.
    
    Durchsucht die lokale ChromaDB nach relevanten Informationen
    zu Fragen rund um die Universität zu Köln.
    
    Naives RAG standardmäßig, optional erweiterbar mit Advanced-Techniken.
    """
    
    name: str = "university_knowledge_search"
    description: str = (
        "Durchsucht die Universitäts-Wissensdatenbank für Fragen zu "
        "Bewerbungen, Studiengängen, Fristen, Prüfungen, Fachsemestern "
        "und anderen Themen der Universität zu Köln / WiSo-Fakultät. "
        "Nutze dieses Tool für spezifische Uni-Fragen."
    )
    
    # Configuration (optional)
    config: Optional[Any] = None
    
    # Advanced technique flags
    _use_advanced: bool = False
    _use_hybrid: bool = False
    _use_sparse: bool = False
    _advanced_available: bool = False
    
    # Embedding model (lazy loaded)
    _embedding_model: Optional[Any] = None
    
    def __init__(self, **data):
        """Initialize RAG tool with optional advanced techniques."""
        super().__init__(**data)
        
        # Wenn config übergeben wurde, nutze es
        if self.config is not None:
            self._use_advanced = self._should_use_advanced()
            self._use_hybrid = self._should_use_hybrid()
            self._use_sparse = self._should_use_sparse()
            logger.info(f"RAG-Tool initialisiert mit übergebener Config (Advanced: {self._use_advanced}, Hybrid: {self._use_hybrid}, Sparse: {self._use_sparse})")
        # Sonst: Load configuration from env
        elif CONFIG_AVAILABLE and RAGConfig is not None:
            try:
                self.config = RAGConfig.load_from_env()
                self._use_advanced = self._should_use_advanced()
                self._use_hybrid = self._should_use_hybrid()
                self._use_sparse = self._should_use_sparse()
                logger.info(f"RAG-Tool initialisiert (Advanced: {self._use_advanced}, Hybrid: {self._use_hybrid}, Sparse: {self._use_sparse})")
            except Exception as e:
                logger.warning(f"Fehler beim Laden der RAG-Config: {e}")
                self.config = None
                self._use_advanced = False
                self._use_hybrid = False
        else:
            logger.info("RAG-Tool initialisiert (Naive RAG)")
    
    def _get_embedding_model(self):
        """Lazy-load des Embedding-Modells für Query-Encoding."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            from config.settings import SENTENCE_TRANSFORMER_MODEL, EMBEDDING_MAX_SEQ_LENGTH
            self._embedding_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, trust_remote_code=True)
            # Setze max_seq_length entsprechend der Konfiguration nur bei bge-m3 --> ansonsten Auskommentieren!
            self._embedding_model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH
            logger.info(f"Embedding-Modell geladen: {SENTENCE_TRANSFORMER_MODEL} (max_seq_length={EMBEDDING_MAX_SEQ_LENGTH})")
        return self._embedding_model
    
    def _should_use_advanced(self) -> bool:
        """
        Prüfe ob Advanced-RETRIEVAL-Techniken aktiviert sind.
        
        Nur Retrieval- und Post-Retrieval-Techniken zählen hier.
        Pre-Retrieval-Techniken (Semantic Chunking) betreffen nur das Scraping,
        nicht die Runtime-Suche.
        """
        if not self.config:
            return False
        
        # Nur Advanced wenn Retrieval-Techniken aktiv sind
        # (Multi-Collection, Reranking, Relevance-Filtering, etc.)
        retrieval_features = [
            self.config.enable_multi_collection,
            self.config.enable_result_aggregation,
            self.config.enable_global_reranking,
        ]
        
        post_retrieval_features = [
            self.config.enable_relevance_filtering,
            self.config.enable_result_formatting,
            self.config.enable_context_hints,
            self.config.enable_empty_result_handling,
        ]
        
        return any(retrieval_features) or any(post_retrieval_features)
    
    def _should_use_hybrid(self) -> bool:
        """
        Prüfe ob Hybrid Retrieval (Dense + BM25 mit RRF) aktiviert ist.
        """
        if not self.config:
            return False
        
        # Hybrid Retrieval ist explizit aktiviert
        return self.config.enable_hybrid_retrieval
    
    def _should_use_sparse(self) -> bool:
        """
        Prüfe ob Sparse Retrieval (nur BM25 ohne Dense) aktiviert ist.
        """
        if not self.config:
            return False
        
        # Sparse Retrieval ist explizit aktiviert
        return self.config.enable_sparse_retrieval
    
    def _get_chromadb_client(self):
        """Hole ChromaDB Client (Shared Helper)."""
        import chromadb
        from pathlib import Path
        
        # WICHTIG: Relative Paths benutzen! ChromaDB hat Bug mit absoluten Windows-Pfaden
        vector_db_paths = [
            "data/vector_db",
            "src/scraper/vector_db"
        ]
        
        for path_str in vector_db_paths:
            if Path(path_str).exists():
                return chromadb.PersistentClient(path=path_str)
        
        raise FileNotFoundError("Vector DB nicht gefunden")
    
    @traceable(run_type="retriever")
    def _naive_retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Naives RAG: Einfache Vektorsuche in Single Collection.
        
        Args:
            query: Die Suchanfrage
            k: Anzahl der Ergebnisse
            
        Returns:
            Liste von Dokumenten mit Metadaten (simples Format)
        """
        try:
            client = self._get_chromadb_client()
        except FileNotFoundError:
            return []
        
        # NAIVE: Nur eine Collection - wiso_documents
        try:
            collection = client.get_collection('wiso_documents')
        except Exception as e:
            logger.warning(f"Collection 'wiso_documents' nicht gefunden: {e}")
            return []
        
        # Einfache Vektorsuche mit dem korrekten Embedding-Modell
        try:
            # Erstelle Query-Embedding mit dem gleichen Modell wie beim Scraping
            embedding_model = self._get_embedding_model()
            raw_embedding = embedding_model.encode([query])
            # Normalisiere Query-Embedding (wie bei Indexierung) für echte Cosine-Similarity
            normalized_embedding = raw_embedding / np.linalg.norm(raw_embedding, axis=1, keepdims=True)
            query_embedding = normalized_embedding.tolist()
            
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=k
            )
        except Exception as e:
            logger.error(f"Fehler bei Vektorsuche: {e}")
            return []
        
        # Simples Document-Format (nur für Naive)
        documents = []
        if results and results['documents'] and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                doc_dict = {
                    'page_content': doc,
                    'type': 'Document',
                    'metadata': {}
                }
                
                # Füge Metadaten hinzu
                if results.get('metadatas') and results['metadatas'][0]:
                    doc_dict['metadata'] = results['metadatas'][0][i] or {}
                
                documents.append(doc_dict)
        
        return documents
    
    @traceable(run_type="retriever")
    def _multi_collection_retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Multi-Collection RAG: Importiert komplette Logik aus multi_collection_search.
        
        Args:
            query: Die Suchanfrage
            k: Anzahl der Ergebnisse (wird für k_per_collection verwendet)
            
        Returns:
            Liste von Dokumenten mit erweiterten Metadaten
        """
        from src.advanced_rag.retrieval.multi_collection_search import advanced_retrieve
        
        # Nutze k_per_collection aus Config
        k_per_collection = self.config.multi_collection_k_per_collection if self.config else 3
        
        # Alle Advanced-Logik ist in multi_collection_search.py
        return advanced_retrieve(query, k_per_collection=k_per_collection)
    
    def _get_collection_names(self) -> List[str]:
        """
        Hole alle Collection-Namen aus der Vektordatenbank.
        
        Returns:
            Liste der Collection-Namen
        """
        try:
            client = self._get_chromadb_client()
            collections = client.list_collections()
            return [col.name for col in collections]
        except Exception as e:
            logger.warning(f"Fehler beim Laden der Collections: {e}")
            return ["wiso_documents"]  # Fallback
    
    @traceable(run_type="retriever")
    def _advanced_retrieve(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """
        Advanced RAG: Dense + BM25 Sparse mit RRF Fusion.
        
        Kombiniert Hybrid Retrieval über alle verfügbaren Collections.
        Später erweiterbar mit weiteren Advanced-Techniken.
        
        Args:
            query: Die Suchanfrage
            k: Anzahl der finalen Ergebnisse nach RRF Fusion (optional, nutzt Config)
            
        Returns:
            Liste von Dokumenten mit Metadaten (gleiches Format wie _naive_retrieve)
        """
        from src.advanced_rag.retrieval.hybrid_retrieval_rrf import hybrid_retrieve
        
        # Hole Konfiguration aus rag.env und settings.py
        k_retrieve = self.config.hybrid_retrieval_k_retrieve if self.config else 80
        k_final = k if k is not None else TOP_K
        rrf_k = self.config.hybrid_retrieval_rrf_k if self.config else 60
        sparse_index_dir = "data/sparse_index"  # Fester Pfad
        vector_db_path = self.config.vector_db_path if self.config else "data/vector_db"
        
        # Hole alle Collections aus der Vektordatenbank
        collection_names = self._get_collection_names()
        
        all_results = []
        for collection_name in collection_names:
            try:
                # Hybrid Retrieval pro Collection
                results = hybrid_retrieve(
                    query=query,
                    k_retrieve=k_retrieve,
                    k_final=k_final,
                    collection_name=collection_name,
                    sparse_index_dir=sparse_index_dir,
                    vector_db_path=vector_db_path,
                    rrf_k=rrf_k
                )
                all_results.extend(results)
            except FileNotFoundError as e:
                logger.warning(f"Sparse Index für '{collection_name}' nicht gefunden: {e}")
                continue
            except Exception as e:
                logger.warning(f"Fehler bei Hybrid Retrieval für '{collection_name}': {e}")
                continue
        
        # Sortiere nach RRF-Score und limitiere auf k_final
        all_results.sort(key=lambda x: x.get('rrf_score', 0), reverse=True)
        final_results = all_results[:k_final]
        
        # Konvertiere zu gleichem Format wie _naive_retrieve für LangSmith-Tracing
        documents = []
        for result in final_results:
            doc_dict = {
                'page_content': result.get('page_content', ''),
                'type': 'Document',
                'metadata': result.get('metadata', {})
            }
            # Füge RRF-spezifische Metadaten hinzu
            doc_dict['metadata']['rrf_score'] = result.get('rrf_score', 0.0)
            doc_dict['metadata']['dense_rank'] = result.get('dense_rank')
            doc_dict['metadata']['sparse_rank'] = result.get('sparse_rank')
            doc_dict['metadata']['chunk_id'] = result.get('chunk_id', '')
            
            documents.append(doc_dict)
        
        logger.info(f"Advanced Retrieval: {len(documents)} Ergebnisse aus {len(collection_names)} Collections")
        
        return documents

    @traceable(run_type="retriever")
    def _sparse_retrieve(self, query: str, k: int = None) -> List[Dict[str, Any]]:
        """
        Sparse RAG: Nur BM25 Sparse Index ohne Dense Retrieval.
        
        Nutzt den vorhandenen Sparse Index für rein lexikalische Suche.
        Holt den Content aus ChromaDB basierend auf chunk_ids.
        
        Args:
            query: Die Suchanfrage
            k: Anzahl der finalen Ergebnisse (optional, nutzt Config TOP_K)
            
        Returns:
            Liste von Dokumenten mit Metadaten (gleiches Format wie _naive_retrieve)
        """
        from src.advanced_rag.retrieval.hybrid_retrieval_rrf import BM25SparseIndex
        
        # Hole Konfiguration
        k_final = k if k is not None else TOP_K
        sparse_index_dir = "data/sparse_index"  # Fester Pfad
        
        # Hole alle Collections aus der Vektordatenbank
        collection_names = self._get_collection_names()
        
        all_results = []
        for collection_name in collection_names:
            try:
                # Lade Sparse Index für Collection
                sparse_index = BM25SparseIndex.load(sparse_index_dir, collection_name)
                
                # BM25 Suche - gibt (chunk_id, score) zurück
                sparse_results = sparse_index.search(query, top_k=k_final)
                
                if not sparse_results:
                    continue
                
                # Hole Content aus ChromaDB basierend auf chunk_ids
                client = self._get_chromadb_client()
                collection = client.get_collection(collection_name)
                
                # Extrahiere chunk_ids für Batch-Abfrage
                chunk_ids = [chunk_id for chunk_id, _ in sparse_results]
                
                # Hole Dokumente aus ChromaDB
                chroma_results = collection.get(
                    ids=chunk_ids,
                    include=['documents', 'metadatas']
                )
                
                # Erstelle Mapping: chunk_id -> (document, metadata)
                id_to_doc = {}
                if chroma_results and chroma_results['ids']:
                    for i, cid in enumerate(chroma_results['ids']):
                        doc = chroma_results['documents'][i] if chroma_results['documents'] else ''
                        meta = chroma_results['metadatas'][i] if chroma_results['metadatas'] else {}
                        id_to_doc[cid] = (doc, meta)
                
                # Konvertiere zu Document-Format mit BM25-Ranking
                for rank, (chunk_id, score) in enumerate(sparse_results, 1):
                    doc_content, doc_metadata = id_to_doc.get(chunk_id, ('', {}))
                    
                    doc_dict = {
                        'page_content': doc_content,
                        'type': 'Document',
                        'metadata': {
                            **doc_metadata,
                            'chunk_id': chunk_id,
                            'bm25_score': score,
                            'sparse_rank': rank,
                            'collection': collection_name,
                            'retrieval_type': 'sparse'
                        }
                    }
                    all_results.append(doc_dict)
                    
            except FileNotFoundError as e:
                logger.warning(f"Sparse Index für '{collection_name}' nicht gefunden: {e}")
                continue
            except Exception as e:
                logger.warning(f"Fehler bei Sparse Retrieval für '{collection_name}': {e}")
                continue
        
        # Sortiere nach BM25-Score und limitiere auf k_final
        all_results.sort(key=lambda x: x.get('metadata', {}).get('bm25_score', 0), reverse=True)
        final_results = all_results[:k_final]
        
        logger.info(f"Sparse Retrieval: {len(final_results)} Ergebnisse aus {len(collection_names)} Collections")
        
        return final_results
    
    def _run(self, query: str) -> str:
        """
        Führt eine Suche in der Universitäts-Vectordatenbank durch.
        
        Args:
            query: Die Suchanfrage des Benutzers
            
        Returns:
            Relevante Informationen aus der Wissensdatenbank
        """
        try:
            # Bestimme k basierend auf globaler Settings
            k = TOP_K
            
            # Retrieval basierend auf Modus
            if self._use_hybrid and self.config:
                # Advanced: Hybrid Retrieval (Dense + BM25 mit RRF Fusion)
                # k wird aus Config geladen (hybrid_retrieval_k_final)
                documents = self._advanced_retrieve(query)
                # Hybrid verwendet eigene Formatierung (naive Format)
                return self._format_naive_results(documents)
            elif self._use_sparse and self.config:
                # Sparse: Nur BM25 ohne Dense Retrieval
                documents = self._sparse_retrieve(query)
                # Sparse verwendet eigene Formatierung (naive Format)
                return self._format_naive_results(documents)
            elif self._use_advanced and self.config:
                # Multi-Collection Search (Legacy) mit Post-Processing
                documents = self._multi_collection_retrieve(query, k=k)
                if not documents:
                    return (
                        "ℹ️ Keine relevanten Informationen in der Universitäts-Wissensdatenbank gefunden. "
                        "Möglicherweise ist die Datenbank leer oder Ihre Anfrage konnte nicht zugeordnet werden."
                    )
                return self._advanced_process(query, documents)
            else:
                # Naive: Single Collection Search
                documents = self._naive_retrieve(query, k=k)
            
            if not documents:
                return (
                    "ℹ️ Keine relevanten Informationen in der Universitäts-Wissensdatenbank gefunden. "
                    "Möglicherweise ist die Datenbank leer oder Ihre Anfrage konnte nicht zugeordnet werden."
                )
            
            # Naive Ausgabe: Einfache Formatierung
            return self._format_naive_results(documents)
            
        except ImportError:
            return (
                "❌ ChromaDB ist nicht installiert. Bitte installieren Sie es mit: "
                "pip install chromadb"
            )
        except Exception as e:
            logger.error(f"Fehler beim RAG-Tool: {e}", exc_info=True)
            return (
                f"❌ Fehler beim Zugriff auf die Universitäts-Wissensdatenbank: {e}"
            )
    
    def _format_naive_results(self, documents: List[Dict[str, Any]]) -> str:
        """
        Naive Formatierung der Ergebnisse.
        
        Args:
            documents: Liste von Dokumenten
            
        Returns:
            Formatierter String
        """
        if not documents:
            return "Keine Ergebnisse gefunden."
        
        response_parts = ["📚 Informationen aus der Universitäts-Wissensdatenbank:\n"]
        
        for i, doc in enumerate(documents, 1):
            content = doc.get('page_content', '')
            metadata = doc.get('metadata', {})
            
            response_parts.append(f"\n{i}. {content[:500]}...")
            
            # Füge Quelle hinzu wenn vorhanden
            if 'source' in metadata:
                response_parts.append(f"   (Quelle: {metadata['source']})")
        
        return "\n".join(response_parts)
    
    def _advanced_process(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Verarbeite Ergebnisse mit Advanced-Techniken.
        
        Args:
            query: Die ursprüngliche Anfrage
            documents: Liste von Dokumenten (von _naive_retrieve)
            
        Returns:
            Verarbeiteter Response-String mit allen Advanced-Techniken
        """
        from src.advanced_rag.retrieval import (
            DistanceConverter,
            ResultAggregator,
            GlobalReranker
        )
        from src.advanced_rag.post_retrieval import (
            RelevanceFilter,
            ResultFormatter,
            ContextHintProvider,
            EmptyResultHandler
        )
        
        logger.info("Verwende Advanced RAG-Techniken")
        
        # Merke ob wir Ergebnisse vor Filterung hatten
        had_results = len(documents) > 0
        
        # 1. Distance → Relevance Conversion
        if self.config.use_distance_conversion:
            converter = DistanceConverter()
            documents = converter.convert(documents)
            logger.debug("✓ Distance Conversion angewendet")
        
        # 2. Result Aggregation (deduplizieren + sortieren)
        if self.config.use_result_aggregation:
            aggregator = ResultAggregator(top_k=self.config.top_k)
            documents = aggregator.deduplicate(documents)
            documents = aggregator.aggregate(documents, sort_by='relevance')
            logger.debug("✓ Result Aggregation angewendet")
        
        # 3. Global Re-Ranking
        if self.config.use_global_reranking:
            reranker = GlobalReranker(use_relevance=True)
            documents = reranker.rerank(documents)
            # Optional: Diversity-Penalty
            documents = reranker.apply_diversity_penalty(documents, max_per_source=2)
            logger.debug("✓ Global Re-Ranking angewendet")
        
        # 4. Relevance Filtering
        if self.config.use_relevance_filtering:
            relevance_filter = RelevanceFilter(threshold=self.config.relevance_threshold)
            documents = relevance_filter.filter(documents)
            logger.debug(f"✓ Relevance Filtering angewendet (Threshold: {self.config.relevance_threshold})")
        
        # 5. Prüfe ob noch Ergebnisse vorhanden
        if not documents:
            if self.config.use_empty_result_handling:
                handler = EmptyResultHandler()
                return handler.handle_empty_results(
                    query=query,
                    had_results_before_filtering=had_results,
                    relevance_threshold=self.config.relevance_threshold
                )
            else:
                return "ℹ️ Keine relevanten Informationen gefunden."
        
        # 6. Result Formatting
        if self.config.use_result_formatting:
            formatter = ResultFormatter(include_metadata=True, include_sources=True)
            formatted = formatter.format(documents, query=query)
            logger.debug("✓ Result Formatting angewendet")
        else:
            # Fallback: Kompakte Formatierung
            formatted = "\n\n".join([doc.get('document', '') for doc in documents])
        
        # 7. Context Hints
        if self.config.use_context_hints:
            hint_provider = ContextHintProvider()
            formatted = hint_provider.add_hints(formatted, query=query, results=documents)
            logger.debug("✓ Context Hints hinzugefügt")
        
        logger.info("Advanced RAG-Pipeline abgeschlossen")
        return formatted
    
    async def _arun(self, query: str) -> str:
        """Asynchrone Version - ruft die synchrone Version auf."""
        return self._run(query)


def create_university_rag_tool() -> UniversityRAGTool:
    """
    Erstellt ein neues RAG-Tool für die Universitäts-Wissensdatenbank.
    
    Returns:
        UniversityRAGTool: Konfiguriertes RAG-Tool
    """
    return UniversityRAGTool()


# Test-Funktion
def test_rag_tool():
    """Testet das RAG-Tool mit einer Beispiel-Anfrage."""
    print("🧪 Teste Universitäts-RAG-Tool...")
    print("=" * 60)
    
    tool = create_university_rag_tool()
    test_query = "Was benötige ich für die Bewerbung auf ein höheres Fachsemester?"
    
    print(f"📝 Test-Anfrage: {test_query}")
    print("-" * 60)
    
    result = tool._run(test_query)
    print(result)
    
    print("-" * 60)
    print("✅ Test abgeschlossen")


if __name__ == "__main__":
    test_rag_tool()
