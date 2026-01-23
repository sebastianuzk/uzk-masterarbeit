"""
ReRanking Module for Advanced RAG
=================================

ReRanking mittels Voyage AI rerank-2.5 Modell.
Sortiert alle übergebenen Dokumente nach semantischer Relevanz zur Query.

Inkludiert LangSmith-Tracing für Token-Usage-Tracking.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from langsmith import traceable

logger = logging.getLogger(__name__)


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


def create_voyage_reranker(model: str = "rerank-2.5") -> VoyageReranker:
    """
    Factory-Funktion für VoyageReranker.
    
    Args:
        model: Name des Voyage Reranking-Modells
        
    Returns:
        VoyageReranker-Instanz
    """
    return VoyageReranker(model=model)
