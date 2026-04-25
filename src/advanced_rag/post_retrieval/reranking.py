"""
ReRanking Module for Advanced RAG
=================================

ReRanking mittels Voyage AI, Cohere oder lokalen Cross-Encoder Modellen.
Sortiert alle übergebenen Dokumente nach semantischer Relevanz zur Query.

Unterstützte Provider:
- Voyage AI (rerank-2.5, rerank-2.5-lite)
- Cohere (rerank-v3.5, rerank-english-v3.0, rerank-multilingual-v3.0)
- Local (cross-encoder/msmarco-MiniLM-L12-en-de-v1) - läuft auf GPU

Inkludiert LangSmith-Tracing für Token-Usage-Tracking.
"""

import logging
import os
from typing import Any, Dict, List, Optional, Protocol

from langsmith import traceable

logger = logging.getLogger(__name__)


class RerankerProtocol(Protocol):
    """Protocol für Reranker - definiert die gemeinsame Schnittstelle."""
    
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        embedding_model: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Rerankt Dokumente nach Relevanz zur Query."""
        ...


class VoyageReranker:
    """
    ReRanking mittels Voyage AI rerank-2.5 Modell.
    
    Nimmt Dokumente entgegen, sortiert sie nach Relevanz zur Query,
    gibt ALLE Dokumente sortiert zurück.
    
    Die Auswahl/Limitierung der Dokumente erfolgt NICHT hier,
    sondern im aufrufenden Code (z.B. advanced_retrieve).
    
    Inkludiert LangSmith-Tracing für Token-Usage-Tracking.
    """
    
    def __init__(self, model: str = "rerank-2.5"):
        """
        Initialisiert den VoyageReranker.
        
        Args:
            model: Name des Voyage Reranking-Modells (default: "rerank-2.5")
        """
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy-load des Voyage AI Clients."""
        if self._client is None:
            try:
                import voyageai
                # API-Key wird aus VOYAGE_API_KEY Umgebungsvariable gelesen
                api_key = os.getenv("VOYAGE_API_KEY")
                if not api_key:
                    raise ValueError("VOYAGE_API_KEY Umgebungsvariable nicht gesetzt")
                self._client = voyageai.Client(api_key=api_key)
                logger.info(f"Voyage AI Client initialisiert (Modell: {self.model})")
            except ImportError:
                raise ImportError("voyageai nicht installiert. Bitte installieren mit: pip install voyageai")
        return self._client
    
    @traceable(
        run_type="llm",
        name="VoyageReranker",
        metadata={"provider": "voyage"}
    )
    def _trace_reranking(
        self, 
        query: str, 
        input_documents: List[Dict[str, Any]],
        output_documents: List[Dict[str, Any]],
        total_tokens: int
    ) -> Dict[str, Any]:
        """
        LangSmith Trace für ReRanking.
        
        Args:
            query: Die Suchanfrage
            input_documents: Dokumente vor Reranking (RRF-Reihenfolge)
            output_documents: Dokumente nach Reranking mit Score
            total_tokens: Verbrauchte Tokens
            
        Returns:
            Dict mit Output-Informationen für LangSmith
        """
        # Output: chunk_ids nach Reranking (alle)
        output_chunk_ids = [
            doc.get('metadata', {}).get('id', f'doc_{i}') 
            for i, doc in enumerate(output_documents)
        ]
        
        # Output: Scores nach Reranking (alle)
        output_scores = [
            doc.get('metadata', {}).get('rerank_score', 0.0) 
            for doc in output_documents
        ]
        
        # Output: Texte nach Reranking (alle, vollständig)
        output_texts = [
            doc.get('page_content', '') 
            for doc in output_documents
        ]
        
        top_score = output_scores[0] if output_scores else 0.0
        
        return {
            "model": self.model,
            "num_documents": len(input_documents),
            "output_chunk_ids": output_chunk_ids,
            "output_scores": output_scores,
            "output_texts": output_texts,
            "top_score": top_score,
            "usage_metadata": {
                "total_tokens": total_tokens,
                "input_tokens": total_tokens,
                "output_tokens": 0
            }
        }
    
    def rerank(self, query: str, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Sortiert ALLE Dokumente nach Relevanz zur Query.
        
        Die Sortierung erfolgt INNERHALB dieser Methode.
        Gibt ALLE Dokumente zurück - keine Limitierung!
        
        Traced in LangSmith mit Token-Usage.
        
        Args:
            query: Die Suchanfrage
            documents: Liste von Dokumenten (mit 'page_content' Key)
            
        Returns:
            Nach Relevanz sortierte Dokumente (ALLE, mit rerank_score in metadata)
        """
        if not documents:
            logger.warning("Keine Dokumente zum Reranken übergeben")
            return documents
        
        # Kopie der Input-Dokumente für LangSmith Trace (vor Sortierung)
        import copy
        input_documents_copy = copy.deepcopy(documents)
        
        try:
            # 1. Extrahiere Texte für Voyage API
            texts = [doc.get('page_content', '') for doc in documents]
            
            if not any(texts):
                logger.warning("Alle Dokumente haben leeren page_content")
                return documents
            
            # 2. Voyage API Call
            logger.info(f"ReRanking {len(documents)} Dokumente mit Voyage {self.model}...")
            
            rerank_response = self.client.rerank(
                query=query,
                documents=texts,
                model=self.model
            )
            
            # 3. Extrahiere Token-Usage für LangSmith-Tracing
            total_tokens = getattr(rerank_response, 'total_tokens', 0) or 0
            
            # Log Token-Usage
            logger.info(f"ReRanking Token-Usage: {total_tokens} tokens")
            
            # 4. Erstelle Mapping: Index → Score
            # Voyage gibt RerankingResult mit .results zurück
            index_to_score = {}
            for result in rerank_response.results:
                index_to_score[result.index] = result.relevance_score
            
            # 5. Füge rerank_score zu metadata hinzu
            for i, doc in enumerate(documents):
                if 'metadata' not in doc:
                    doc['metadata'] = {}
                doc['metadata']['rerank_score'] = index_to_score.get(i, 0.0)
            
            # 6. Sortiere nach rerank_score (absteigend)
            documents.sort(
                key=lambda x: x.get('metadata', {}).get('rerank_score', 0.0),
                reverse=True
            )
            
            top_score = documents[0]['metadata'].get('rerank_score', 0) if documents else 0
            logger.info(f"ReRanking abgeschlossen. Top-Score: {top_score:.4f}")
            
            # 7. LangSmith Tracing
            self._trace_reranking(
                query=query,
                input_documents=input_documents_copy,
                output_documents=documents,
                total_tokens=total_tokens
            )
            
            return documents
            
        except Exception as e:
            logger.error(f"Fehler beim ReRanking: {e}", exc_info=True)
            # Bei Fehler: Original-Reihenfolge beibehalten
            logger.warning("Fallback: Original-Reihenfolge wird beibehalten")
            return documents


# ============================================================================
# Cohere Reranker
# ============================================================================
class CohereReranker:
    """
    ReRanking mittels Cohere Rerank Modellen.
    
    Unterstützte Modelle:
    - rerank-v3.5 (neuestes, empfohlen)
    - rerank-english-v3.0
    - rerank-multilingual-v3.0
    - rerank-english-v2.0
    
    Nimmt Dokumente entgegen, sortiert sie nach Relevanz zur Query,
    gibt ALLE Dokumente sortiert zurück.
    
    Inkludiert LangSmith-Tracing für Token-Usage-Tracking.
    """
    
    def __init__(self, model: str = "rerank-v3.5"):
        """
        Initialisiert den CohereReranker.
        
        Args:
            model: Name des Cohere Reranking-Modells (default: "rerank-v3.5")
        """
        self.model = model
        self._client = None
    
    @property
    def client(self):
        """Lazy-load des Cohere Clients."""
        if self._client is None:
            try:
                import cohere
                # API-Key wird aus COHERE_API_KEY Umgebungsvariable gelesen
                api_key = os.getenv("COHERE_API_KEY")
                if not api_key:
                    raise ValueError("COHERE_API_KEY Umgebungsvariable nicht gesetzt")
                self._client = cohere.Client(api_key=api_key)
                logger.info(f"Cohere Client initialisiert (Modell: {self.model})")
            except ImportError:
                raise ImportError("cohere nicht installiert. Bitte installieren mit: pip install cohere")
        return self._client
    
    @traceable(
        run_type="llm",
        name="CohereReranker",
        metadata={"provider": "cohere"}
    )
    def _trace_reranking(
        self, 
        query: str, 
        input_documents: List[Dict[str, Any]],
        output_documents: List[Dict[str, Any]],
        total_tokens: int,
        search_units: float = 0.0
    ) -> Dict[str, Any]:
        """
        LangSmith Trace für ReRanking.
        
        Args:
            query: Die Suchanfrage
            input_documents: Dokumente vor Reranking
            output_documents: Dokumente nach Reranking mit Score
            total_tokens: Geschätzte Tokens (Cohere gibt keine echten Tokens zurück!)
            search_units: Cohere Billing Units (search_units)
            
        Returns:
            Dict mit Output-Informationen für LangSmith
        """
        output_chunk_ids = [
            doc.get('metadata', {}).get('id', f'doc_{i}') 
            for i, doc in enumerate(output_documents)
        ]
        
        output_scores = [
            doc.get('metadata', {}).get('rerank_score', 0.0) 
            for doc in output_documents
        ]
        
        output_texts = [
            doc.get('page_content', '') 
            for doc in output_documents
        ]
        
        top_score = output_scores[0] if output_scores else 0.0
        
        return {
            "model": self.model,
            "num_documents": len(input_documents),
            "output_chunk_ids": output_chunk_ids,
            "output_scores": output_scores,
            "output_texts": output_texts,
            "top_score": top_score,
            "search_units": search_units,  # Cohere-spezifisch
            "usage_metadata": {
                "total_tokens": total_tokens,  # Geschätzt!
                "input_tokens": total_tokens,
                "output_tokens": 0
            }
        }
    
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        embedding_model: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Sortiert ALLE Dokumente nach Relevanz zur Query.
        
        Die Sortierung erfolgt INNERHALB dieser Methode.
        Gibt ALLE Dokumente zurück - keine Limitierung!
        
        Traced in LangSmith mit Token-Usage.
        
        Token-Berechnung erfolgt intern:
        - Dokument-Tokens: Aus metadata['token_count'] (falls vorhanden) oder Schätzung
        - Query-Tokens: Via embedding_model.tokenize() (falls übergeben) oder Schätzung
        
        Args:
            query: Die Suchanfrage
            documents: Liste von Dokumenten (mit 'page_content' Key und optional 'metadata.token_count')
            embedding_model: Optional - Embedding-Modell für exakte Query-Token-Berechnung
                             (z.B. SentenceTransformer mit tokenize()-Methode)
            
        Returns:
            Nach Relevanz sortierte Dokumente (ALLE, mit rerank_score in metadata)
        """
        if not documents:
            logger.warning("Keine Dokumente zum Reranken übergeben")
            return documents
        
        # Kopie der Input-Dokumente für LangSmith Trace (vor Sortierung)
        import copy
        input_documents_copy = copy.deepcopy(documents)
        
        try:
            # 1. Extrahiere Texte für Cohere API
            texts = [doc.get('page_content', '') for doc in documents]
            
            if not any(texts):
                logger.warning("Alle Dokumente haben leeren page_content")
                return documents
            
            # 2. Cohere API Call
            logger.info(f"ReRanking {len(documents)} Dokumente mit Cohere {self.model}...")
            
            rerank_response = self.client.rerank(
                query=query,
                documents=texts,
                model=self.model,
                return_documents=False  # Wir brauchen nur die Scores/Indices
            )
            
            # 3. Extrahiere Token-Usage für LangSmith-Tracing
            # Cohere gibt billed_units.search_units zurück (nicht echte Tokens!)
            search_units = 0.0
            billed_units = getattr(rerank_response.meta, 'billed_units', None)
            if billed_units:
                search_units = getattr(billed_units, 'search_units', 0) or 0
            
            # Token-Berechnung: Nutze token_count aus Dokument-Metadaten (falls vorhanden)
            # Sonst Fallback auf Schätzung (~4 Zeichen pro Token)
            num_documents = len(documents)
            doc_tokens = 0
            for doc in documents:
                meta = doc.get('metadata', {})
                if 'token_count' in meta and meta['token_count']:
                    doc_tokens += int(meta['token_count'])
                else:
                    # Fallback: Schätzung basierend auf Zeichenlänge
                    doc_tokens += len(doc.get('page_content', '')) // 4
            
            # Query-Tokens: Nutze Embedding-Modell für exakte Berechnung oder schätze
            # Die Query wird für JEDES Dokument verarbeitet, daher * num_documents
            if embedding_model is not None and hasattr(embedding_model, 'tokenize'):
                # Exakte Token-Berechnung via Tokenizer
                tokens = embedding_model.tokenize([query])
                query_tokens_per_doc = tokens['attention_mask'].sum().item()
            else:
                # Fallback: Schätzung (~4 Zeichen pro Token)
                query_tokens_per_doc = len(query) // 4
            total_query_tokens = query_tokens_per_doc * num_documents
            
            # Gesamte Tokens = (Query * Anzahl Dokumente) + alle Dokumente
            total_tokens = total_query_tokens + doc_tokens
            
            # Log Token-Usage
            logger.info(f"ReRanking: {search_units} search_units, {total_tokens} Tokens (Query: {query_tokens_per_doc}x{num_documents}={total_query_tokens}, Docs: {doc_tokens})")
            
            # 4. Erstelle Mapping: Index → Score
            # Cohere gibt RerankResponse mit .results zurück
            index_to_score = {}
            for result in rerank_response.results:
                index_to_score[result.index] = result.relevance_score
            
            # 5. Füge rerank_score zu metadata hinzu
            for i, doc in enumerate(documents):
                if 'metadata' not in doc:
                    doc['metadata'] = {}
                doc['metadata']['rerank_score'] = index_to_score.get(i, 0.0)
            
            # 6. Sortiere nach rerank_score (absteigend)
            documents.sort(
                key=lambda x: x.get('metadata', {}).get('rerank_score', 0.0),
                reverse=True
            )
            
            top_score = documents[0]['metadata'].get('rerank_score', 0) if documents else 0
            logger.info(f"ReRanking abgeschlossen. Top-Score: {top_score:.4f}")
            
            # 7. LangSmith Tracing (mit berechneten Tokens)
            self._trace_reranking(
                query=query,
                input_documents=input_documents_copy,
                output_documents=documents,
                total_tokens=total_tokens,
                search_units=search_units
            )
            
            return documents
            
        except Exception as e:
            logger.error(f"Fehler beim Cohere ReRanking: {e}", exc_info=True)
            # Bei Fehler: Original-Reihenfolge beibehalten
            logger.warning("Fallback: Original-Reihenfolge wird beibehalten")
            return documents


# ============================================================================
# Local Cross-Encoder Reranker
# ============================================================================
class LocalReranker:
    """
    ReRanking mittels lokalem Cross-Encoder Modell.
    
    Nutzt das ms-marco-MiniLM-L-12-v2 Modell (oder anderes Cross-Encoder Modell)
    für lokales Reranking ohne API-Kosten.
    
    Das Modell wird auf der GPU ausgeführt. Bei gleichzeitiger Nutzung mit dem
    Chatbot-LLM muss genügend VRAM vorhanden sein.
    - ms-marco-MiniLM-L-12-v2: ~120MB VRAM
    - Chatbot (z.B. llama3.1:8b): ~5-6GB VRAM
    - Beide zusammen: ~6GB VRAM
    
    Inkludiert LangSmith-Tracing für Token-Usage-Tracking (geschätzt).
    """
    
    # Default Modell - Mehrsprachig (Englisch + Deutsch)
    DEFAULT_MODEL = "cross-encoder/msmarco-MiniLM-L12-en-de-v1"
    
    def __init__(self, model: str = None):
        """
        Initialisiert den LocalReranker.
        
        Args:
            model: Name des Cross-Encoder Modells (default: cross-encoder/msmarco-MiniLM-L12-en-de-v1)
        """
        self.model_name = model or self.DEFAULT_MODEL
        self._model = None
        self._device = None
    
    @property
    def model(self):
        """Lazy-load des Cross-Encoder Modells."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                import torch
                
                # Bestimme Device (GPU wenn verfügbar)
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # Lade Cross-Encoder
                self._model = CrossEncoder(self.model_name, device=self._device)
                
                # Log VRAM-Nutzung wenn GPU
                if self._device == "cuda":
                    vram_mb = torch.cuda.memory_allocated() / 1024 / 1024
                    logger.info(
                        f"Local Reranker geladen: {self.model_name} "
                        f"(Device: {self._device}, VRAM: ~{vram_mb:.0f}MB)"
                    )
                else:
                    logger.info(f"Local Reranker geladen: {self.model_name} (Device: {self._device})")
                    
            except ImportError:
                raise ImportError(
                    "sentence-transformers nicht installiert. "
                    "Bitte installieren mit: pip install sentence-transformers"
                )
        return self._model
    
    @traceable(
        run_type="llm",
        name="LocalReranker",
        metadata={"provider": "local"}
    )
    def _trace_reranking(
        self, 
        query: str, 
        input_documents: List[Dict[str, Any]],
        output_documents: List[Dict[str, Any]],
        total_tokens: int
    ) -> Dict[str, Any]:
        """
        LangSmith Trace für ReRanking.
        
        Args:
            query: Die Suchanfrage
            input_documents: Dokumente vor Reranking
            output_documents: Dokumente nach Reranking mit Score
            total_tokens: Geschätzte Tokens
            
        Returns:
            Dict mit Output-Informationen für LangSmith
        """
        output_chunk_ids = [
            doc.get('metadata', {}).get('id', f'doc_{i}') 
            for i, doc in enumerate(output_documents)
        ]
        
        output_scores = [
            doc.get('metadata', {}).get('rerank_score', 0.0) 
            for doc in output_documents
        ]
        
        output_texts = [
            doc.get('page_content', '') 
            for doc in output_documents
        ]
        
        top_score = output_scores[0] if output_scores else 0.0
        
        return {
            "model": self.model_name,
            "device": self._device or "unknown",
            "num_documents": len(input_documents),
            "output_chunk_ids": output_chunk_ids,
            "output_scores": output_scores,
            "output_texts": output_texts,
            "top_score": top_score,
            "usage_metadata": {
                "total_tokens": total_tokens,
                "input_tokens": total_tokens,
                "output_tokens": 0
            }
        }
    
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        embedding_model: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Sortiert ALLE Dokumente nach Relevanz zur Query mittels Cross-Encoder.
        
        Der Cross-Encoder bewertet jedes (Query, Document) Paar einzeln
        und gibt einen Relevanz-Score zurück.
        
        Token-Berechnung (wie bei Cohere):
        - Dokument-Tokens: Aus metadata['token_count'] oder Schätzung (~4 Zeichen/Token)
        - Query-Tokens: Via embedding_model.tokenize() oder Schätzung
        - Query wird für JEDES Dokument verarbeitet
        
        Args:
            query: Die Suchanfrage
            documents: Liste von Dokumenten (mit 'page_content' Key)
            embedding_model: Optional - für exakte Token-Berechnung
            
        Returns:
            Nach Relevanz sortierte Dokumente (ALLE, mit rerank_score in metadata)
        """
        if not documents:
            logger.warning("Keine Dokumente zum Reranken übergeben")
            return documents
        
        # Kopie der Input-Dokumente für LangSmith Trace
        import copy
        input_documents_copy = copy.deepcopy(documents)
        
        try:
            # 1. Extrahiere Texte für Cross-Encoder
            texts = [doc.get('page_content', '') for doc in documents]
            
            if not any(texts):
                logger.warning("Alle Dokumente haben leeren page_content")
                return documents
            
            # 2. Erstelle Query-Document Paare für Cross-Encoder
            pairs = [(query, text) for text in texts]
            
            # 3. Cross-Encoder Prediction
            logger.info(f"ReRanking {len(documents)} Dokumente mit lokalem {self.model_name}...")
            
            # Cross-Encoder gibt Scores direkt zurück (höher = relevanter)
            scores = self.model.predict(pairs, show_progress_bar=False)
            
            # 4. Token-Berechnung (wie bei Cohere - geschätzt)
            num_documents = len(documents)
            doc_tokens = 0
            for doc in documents:
                meta = doc.get('metadata', {})
                    # Tokens sind bereits als Metadata pro Chunk vorhanden
                if 'token_count' in meta and meta['token_count']:
                    doc_tokens += int(meta['token_count'])
                else:
                    # Fallback: Schätzung basierend auf Zeichenlänge
                    doc_tokens += len(doc.get('page_content', '')) // 4
            
            # Query-Tokens
            if embedding_model is not None and hasattr(embedding_model, 'tokenize'):
                tokens = embedding_model.tokenize([query])
                query_tokens_per_doc = tokens['attention_mask'].sum().item()
            else:
                query_tokens_per_doc = len(query) // 4
            
            total_query_tokens = query_tokens_per_doc * num_documents
            total_tokens = total_query_tokens + doc_tokens
            
            logger.info(
                f"ReRanking: {total_tokens} Tokens geschätzt "
                f"(Query: {query_tokens_per_doc}x{num_documents}={total_query_tokens}, Docs: {doc_tokens})"
            )
            
            # 5. Füge rerank_score zu metadata hinzu (rohe Logits, ordinales Ranking)
            # CrossEncoder gibt unkalibrierte Logits aus – nur für Sortierung geeignet,
            # nicht als absolute Relevanzmaße (Nogueira & Cho, 2019)
            for i, doc in enumerate(documents):
                if 'metadata' not in doc:
                    doc['metadata'] = {}
                doc['metadata']['rerank_score'] = float(scores[i])
            
            # 6. Sortiere nach rerank_score (absteigend)
            documents.sort(
                key=lambda x: x.get('metadata', {}).get('rerank_score', 0.0),
                reverse=True
            )
            
            top_score = documents[0]['metadata'].get('rerank_score', 0) if documents else 0
            logger.info(f"ReRanking abgeschlossen. Top-Score: {top_score:.4f}")
            
            # 7. LangSmith Tracing
            self._trace_reranking(
                query=query,
                input_documents=input_documents_copy,
                output_documents=documents,
                total_tokens=total_tokens
            )
            
            return documents
            
        except Exception as e:
            logger.error(f"Fehler beim lokalen ReRanking: {e}", exc_info=True)
            logger.warning("Fallback: Original-Reihenfolge wird beibehalten")
            return documents
    
    def check_vram_compatibility(self) -> Dict[str, Any]:
        """
        Prüft VRAM-Verfügbarkeit und Kompatibilität mit Chatbot.
        
        Returns:
            Dict mit VRAM-Informationen und Empfehlung
        """
        try:
            import torch
            
            if not torch.cuda.is_available():
                return {
                    "gpu_available": False,
                    "message": "Keine GPU verfügbar - Modell läuft auf CPU"
                }
            
            # Hole VRAM Info
            total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
            allocated_vram = torch.cuda.memory_allocated() / 1024**3
            free_vram = total_vram - allocated_vram
            
            # Geschätzte Größen
            reranker_vram = 0.12  # ~120MB für ms-marco-MiniLM-L-12-v2
            chatbot_vram = 5.5    # ~5.5GB für llama3.1:8b
            
            can_run_both = free_vram >= (reranker_vram + chatbot_vram)
            
            return {
                "gpu_available": True,
                "total_vram_gb": round(total_vram, 2),
                "allocated_vram_gb": round(allocated_vram, 2),
                "free_vram_gb": round(free_vram, 2),
                "reranker_vram_gb": reranker_vram,
                "chatbot_vram_gb": chatbot_vram,
                "can_run_both": can_run_both,
                "message": (
                    f"✅ Genug VRAM für Reranker + Chatbot"
                    if can_run_both else
                    f"⚠️ Möglicherweise nicht genug VRAM für beide Modelle gleichzeitig"
                )
            }
        except Exception as e:
            return {
                "gpu_available": False,
                "error": str(e),
                "message": f"Fehler bei VRAM-Prüfung: {e}"
            }


# ============================================================================
# Factory Functions
# ============================================================================
def create_voyage_reranker(model: str = "rerank-2.5") -> VoyageReranker:
    """
    Factory-Funktion für VoyageReranker.
    
    Args:
        model: Name des Voyage Reranking-Modells
        
    Returns:
        VoyageReranker-Instanz
    """
    return VoyageReranker(model=model)


def create_cohere_reranker(model: str = "rerank-v3.5") -> CohereReranker:
    """
    Factory-Funktion für CohereReranker.
    
    Args:
        model: Name des Cohere Reranking-Modells
        
    Returns:
        CohereReranker-Instanz
    """
    return CohereReranker(model=model)


def create_local_reranker(model: str = None) -> LocalReranker:
    """
    Factory-Funktion für LocalReranker.
    
    Args:
        model: Name des Cross-Encoder Modells (default: ms-marco-MiniLM-L-12-v2)
        
    Returns:
        LocalReranker-Instanz
    """
    return LocalReranker(model=model)


def create_reranker(
    provider: str = "voyage",
    model: Optional[str] = None
) -> RerankerProtocol:
    """
    Universelle Factory-Funktion für Reranker.
    
    Args:
        provider: "voyage", "cohere" oder "local"
        model: Optionaler Modellname (sonst Provider-Default)
        
    Returns:
        Reranker-Instanz (VoyageReranker, CohereReranker oder LocalReranker)
        
    Raises:
        ValueError: Bei unbekanntem Provider
    """
    provider = provider.lower()
    
    if provider == "voyage":
        return VoyageReranker(model=model or "rerank-2.5")
    elif provider == "cohere":
        return CohereReranker(model=model or "rerank-v3.5")
    elif provider == "local":
        return LocalReranker(model=model)  # Default wird in Klasse gesetzt
    else:
        raise ValueError(
            f"Unbekannter Reranking-Provider: '{provider}'. "
            f"Unterstützt: 'voyage', 'cohere', 'local'"
        )