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
    _use_sparse: bool = False
    _advanced_available: bool = False
    
    # Embedding model (lazy loaded)
    _embedding_model: Optional[Any] = None
    
    # Reranker (lazy loaded - nur bei lokalem Reranking wichtig für Performance)
    _reranker: Optional[Any] = None
    
    def __init__(self, **data):
        """Initialize RAG tool with optional advanced techniques."""
        super().__init__(**data)
        
        # Wenn config übergeben wurde, nutze es
        if self.config is not None:
            self._use_advanced = self._should_use_advanced()
            self._use_sparse = self._should_use_sparse()
            logger.info(f"RAG-Tool initialisiert mit übergebener Config (Advanced: {self._use_advanced}, Sparse: {self._use_sparse})")
        # Sonst: Load configuration from env
        elif CONFIG_AVAILABLE and RAGConfig is not None:
            try:
                self.config = RAGConfig.load_from_env()
                self._use_advanced = self._should_use_advanced()
                self._use_sparse = self._should_use_sparse()
                logger.info(f"RAG-Tool initialisiert (Advanced: {self._use_advanced}, Sparse: {self._use_sparse})")
            except Exception as e:
                logger.warning(f"Fehler beim Laden der RAG-Config: {e}")
                self.config = None
                self._use_advanced = False
        else:
            logger.info("RAG-Tool initialisiert (Naive RAG)")
    
    def _get_embedding_model(self):
        """Lazy-load des Embedding-Modells für Query-Encoding."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            from config.settings import SENTENCE_TRANSFORMER_MODEL, EMBEDDING_MAX_SEQ_LENGTH
            self._embedding_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL, trust_remote_code=True)
            # Setze max_seq_length entsprechend der Konfiguration
            self._embedding_model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH
            logger.info(f"Embedding-Modell geladen: {SENTENCE_TRANSFORMER_MODEL} (max_seq_length={EMBEDDING_MAX_SEQ_LENGTH})")
        return self._embedding_model
    
    def _get_reranker(self):
        """
        Lazy-load des Rerankers - wird einmal initialisiert und wiederverwendet.
        
        Bei lokalem Reranking (CrossEncoder) wird das Modell einmalig geladen,
        um wiederholte Initialisierungen bei aufeinanderfolgenden Requests zu vermeiden.
        
        Returns:
            Reranker-Instanz (VoyageReranker, CohereReranker oder LocalReranker)
        """
        if self._reranker is None and self.config and self.config.use_reranking:
            from src.advanced_rag.post_retrieval.reranking import create_reranker
            
            self._reranker = create_reranker(
                provider=self.config.reranking_provider,
                model=self.config.reranking_model
            )
            
            # Bei lokalem Reranking: Modell sofort laden (nicht erst beim ersten rerank())
            # So wird VRAM bereits beim Tool-Init allokiert
            if self.config.reranking_provider == 'local':
                # Trigger lazy-load des CrossEncoder-Modells
                _ = self._reranker.model
                logger.info(f"Reranker vorgeladen: {self.config.reranking_provider}")
            else:
                logger.info(f"Reranker initialisiert: {self.config.reranking_provider} ({self.config.reranking_model})")
        
        return self._reranker
    
    def _should_use_advanced(self) -> bool:
        """
        Prüfe ob Advanced Retrieval (Hybrid und/oder ReRanking und/oder MMR) aktiviert ist.
        
        Gibt True zurück wenn:
        - Hybrid Retrieval (Dense + BM25 mit RRF) aktiviert ist, ODER
        - ReRanking aktiviert ist (auch ohne Hybrid), ODER
        - MMR aktiviert ist (für Diversität)
        
        In allen Fällen wird _advanced_retrieve() verwendet.
        """
        if not self.config:
            return False
        
        # use_* Properties berücksichtigen naive_setup-Flag (bei baseline=True immer False)
        return self.config.use_hybrid_retrieval or self.config.use_reranking or self.config.use_mmr
    
    def _should_use_sparse(self) -> bool:
        """
        Prüfe ob Sparse Retrieval (nur BM25 ohne Dense) aktiviert ist.
        """
        if not self.config:
            return False
        
        # use_sparse_retrieval berücksichtigt naive_setup-Flag
        return self.config.use_sparse_retrieval
    
    def _get_chromadb_client(self):
        """Hole ChromaDB Client (Shared Helper)."""
        import chromadb
        from pathlib import Path
        
        # ChromaDB: relative Pfade für plattformübergreifende Kompatibilität
        vector_db_paths = [
            "data/vector_db",
            "src/scraper/vector_db"
        ]
        
        for path_str in vector_db_paths:
            if Path(path_str).exists():
                return chromadb.PersistentClient(path=path_str)
        
        raise FileNotFoundError("Vector DB nicht gefunden")
    
    @traceable(run_type="retriever")
    def _naive_retrieve(self, query: str, k: int = 5, include_embeddings: bool = False) -> List[Dict[str, Any]]:
        """
        Naives RAG: Einfache Vektorsuche in Single Collection.
        
        Args:
            query: Die Suchanfrage
            k: Anzahl der Ergebnisse
            include_embeddings: Wenn True, werden auch Embeddings in metadata zurückgegeben
            
        Returns:
            Liste von Dokumenten mit Metadaten (simples Format)
            Bei include_embeddings=True enthält metadata['embedding'] den Embedding-Vektor
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
            
            # Bestimme include-Liste basierend auf include_embeddings
            include_list = ['distances', 'metadatas', 'documents']
            if include_embeddings:
                include_list.append('embeddings')
            
            results = collection.query(
                query_embeddings=query_embedding,
                n_results=k,
                include=include_list
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
                
                # Füge Distanz/Similarity hinzu
                if results.get('distances') and results['distances'][0]:
                    distance = results['distances'][0][i]
                    # Cosine Distance → Similarity (1 - distance für normalisierte Vektoren)
                    similarity = 1.0 - distance
                    doc_dict['metadata']['similarity_score'] = similarity
                    doc_dict['metadata']['distance'] = distance
                
                # Füge Embedding hinzu (falls angefordert)
                if include_embeddings and results.get('embeddings') and len(results['embeddings']) > 0:
                    doc_dict['metadata']['embedding'] = results['embeddings'][0][i]
                
                # Füge IDs hinzu
                if results.get('ids') and results['ids'][0]:
                    doc_dict['metadata']['chunk_id'] = results['ids'][0][i]
                
                documents.append(doc_dict)
        
        return documents
    
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
    def _advanced_retrieve(self, query: str) -> List[Dict[str, Any]]:
        """
        Advanced RAG: Unterstützt verschiedene Retrieval-Modi mit optionalem ReRanking.
        
        Modi:
        1. Hybrid + ReRanking: Dense + BM25 + RRF Fusion + Voyage ReRanking
        2. Hybrid ohne ReRanking: Dense + BM25 + RRF Fusion
        3. Dense + ReRanking: Nur Dense Retrieval + Voyage ReRanking
        
        Args:
            query: Die Suchanfrage
            
        Returns:
            Liste von Dokumenten mit Metadaten (gleiches Format wie _naive_retrieve)
        """
        k_final = TOP_K if TOP_K else 5
        reranking_candidates = self.config.reranking_candidates if self.config else 40
        
        # Entscheide: Hybrid Retrieval oder nur Dense Retrieval?
        # use_hybrid_retrieval berücksichtigt naive_setup-Flag
        if self.config and self.config.use_hybrid_retrieval:
            # === HYBRID RETRIEVAL (Dense + BM25 + RRF) ===
            from src.advanced_rag.retrieval.hybrid_retrieval_rrf import hybrid_retrieve
            
            k_retrieve = self.config.hybrid_retrieval_k_retrieve if self.config else 80
            rrf_k = self.config.hybrid_retrieval_rrf_k if self.config else 60
            sparse_index_dir = "data/sparse_index"
            vector_db_path = self.config.vector_db_path if self.config else "data/vector_db"
            
            # Lade Embedding-Modell einmalig und übergebe es dem HybridRetriever
            embedding_model = self._get_embedding_model()
            
            # Hole alle Collections aus der Vektordatenbank
            collection_names = self._get_collection_names()
            
            # Prüfe ob MMR aktiviert ist - dann müssen Embeddings mit geladen werden
            include_emb_for_mmr = self.config.use_mmr if self.config else False
            
            all_results = []
            for collection_name in collection_names:
                try:
                    # Hybrid Retrieval pro Collection - gibt ALLE fusionierten Dokumente zurück
                    # include_embeddings=True falls MMR aktiviert (EIN Request, keine separate Abfrage!)
                    results = hybrid_retrieve(
                        query=query,
                        k_retrieve=k_retrieve,
                        collection_name=collection_name,
                        sparse_index_dir=sparse_index_dir,
                        vector_db_path=vector_db_path,
                        rrf_k=rrf_k,
                        embedding_model=embedding_model,  # Vorgeladenes Modell übergeben
                        include_embeddings=include_emb_for_mmr  # Embeddings für MMR in einem Request
                    )
                    all_results.extend(results)
                except FileNotFoundError as e:
                    logger.warning(f"Sparse Index für '{collection_name}' nicht gefunden: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Fehler bei Hybrid Retrieval für '{collection_name}': {e}")
                    continue
            
            # Konvertiere zu Document-Format
            documents = []
            for result in all_results:
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
                
                # Füge Embedding hinzu falls vorhanden (für MMR)
                if include_emb_for_mmr and result.get('embedding') is not None:
                    doc_dict['metadata']['embedding'] = result.get('embedding')
                
                documents.append(doc_dict)
            
            logger.info(f"Hybrid Retrieval: {len(documents)} Dokumente aus RRF Fusion" +
                       (f" (mit Embeddings für MMR)" if include_emb_for_mmr else ""))
        
        else:
            # === DENSE-ONLY RETRIEVAL (für ReRanking ohne Hybrid) ===
            # Hole reranking_candidates Dokumente für späteres ReRanking
            # include_embeddings=True für MMR (falls aktiviert) - EIN Request!
            include_emb = self.config.use_mmr if self.config else False
            documents = self._naive_retrieve(query, k=reranking_candidates, include_embeddings=include_emb)
            
            # Konvertiere zu einheitlichem Format mit chunk_id in metadata
            for i, doc in enumerate(documents):
                if 'chunk_id' not in doc.get('metadata', {}):
                    # Generiere chunk_id aus Index falls nicht vorhanden
                    doc['metadata']['chunk_id'] = f"dense_{i}"
            
            logger.info(f"Dense Retrieval: {len(documents)} Dokumente für ReRanking")
        
        # === RERANKING (optional) ===
        if self.config and self.config.use_reranking:
            # Limitiere auf reranking_candidates VOR dem ReRanking (kosteneffizienter)
            documents_for_reranking = documents[:reranking_candidates]
            
            logger.info(f"ReRanking: {len(documents_for_reranking)} Dokumente werden reranked...")
            
            # Hole vorgeladenen Reranker (NICHT jedes Mal neu erstellen!)
            # Bei lokalem Reranking vermeidet dies das wiederholte Laden des CrossEncoder-Modells
            reranker = self._get_reranker()
            
            # Übergebe Embedding-Modell für Token-Berechnung (nur bei Cohere/local nötig)
            if self.config.reranking_provider in ('cohere', 'local'):
                documents = reranker.rerank(
                    query, 
                    documents_for_reranking,
                    embedding_model=self._get_embedding_model()
                )
            else:
                # Voyage gibt Tokens selbst zurück
                documents = reranker.rerank(query, documents_for_reranking)
            
            logger.info(f"ReRanking angewendet mit Provider: {self.config.reranking_provider}, Modell: {self.config.reranking_model}")
        
        # === MMR (Maximum Marginal Relevance) für Diversität (optional) ===
        if self.config and self.config.use_mmr and len(documents) > k_final:
            from src.advanced_rag.post_retrieval.maximum_marginal_relevance import create_mmr
            import numpy as np
            
            logger.info(f"MMR: Anwenden auf {len(documents)} Dokumente für Diversität...")
            
            # Erstelle MMR mit konfigurierten Parametern
            mmr = create_mmr(
                lambda_param=self.config.mmr_lambda,
                similarity_metric=self.config.mmr_similarity_metric
            )
            
            # Extrahiere Embeddings aus metadata (bereits bei _naive_retrieve geholt!)
            embeddings_list = []
            for doc in documents:
                emb = doc.get('metadata', {}).get('embedding')
                if emb is not None:
                    embeddings_list.append(emb)
                else:
                    # Sollte nicht passieren wenn include_embeddings=True
                    logger.warning(f"Kein Embedding für Dokument gefunden!")
                    embeddings_list.append(np.zeros(1024))  # Fallback
            
            document_embeddings = np.array(embeddings_list)
            
            # Extrahiere Relevanz-Scores (ReRank > Similarity > RRF)
            relevance_scores = []
            for doc in documents:
                meta = doc.get('metadata', {})
                score = meta.get('rerank_score', 
                        meta.get('similarity_score', 
                        meta.get('rrf_score', 0.0)))
                relevance_scores.append(score)
            
            # MMR-Auswahl
            mmr_result = mmr.select(
                documents=documents,
                document_embeddings=document_embeddings,
                relevance_scores=relevance_scores,
                k_final=k_final,
                query=query
            )
            
            final_documents = mmr_result.documents
            logger.info(f"MMR: {len(final_documents)} Dokumente ausgewählt, {len(mmr_result.swaps)} Swaps durchgeführt")
        else:
            # Ohne MMR: Einfach Top-k_final nehmen
            final_documents = documents[:k_final]
            logger.info(f"Finale Auswahl: Top-{k_final} von {len(documents)} Dokumenten")
        
        # === CLEANUP: Entferne Embeddings aus Metadaten ===
        # Embeddings werden nur für MMR gebraucht, nicht für LLM-Response!
        # (1024 Floats pro Dokument würden das LLM überlasten)
        for doc in final_documents:
            if 'metadata' in doc and 'embedding' in doc['metadata']:
                del doc['metadata']['embedding']
        
        return final_documents

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
            k_final = TOP_K if TOP_K else 5
            
            # Retrieval basierend auf Modus
            if self._use_advanced and self.config:
                # Advanced: Hybrid Retrieval und/oder ReRanking
                documents = self._advanced_retrieve(query)
                return self._format_naive_results(documents)
            elif self._use_sparse and self.config:
                # Sparse: Nur BM25 ohne Dense Retrieval
                documents = self._sparse_retrieve(query)
                # Sparse verwendet eigene Formatierung (naive Format)
                return self._format_naive_results(documents)
            else:
                # Naive: Single Collection Search (ohne ReRanking)
                documents = self._naive_retrieve(query, k=k_final)
            
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
            
            response_parts.append(f"\n{i}. {content}")
            
            # Füge Quelle hinzu wenn vorhanden
            if 'source' in metadata:
                response_parts.append(f"   (Quelle: {metadata['source']})")
        
        return "\n".join(response_parts)
    
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
