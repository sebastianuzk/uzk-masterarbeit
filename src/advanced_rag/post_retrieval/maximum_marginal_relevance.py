"""
Maximum Marginal Relevance (MMR) Module for Advanced RAG
========================================================

MMR balanciert Relevanz und Diversität bei der Dokumenten-Auswahl.
Vermeidet redundante/ähnliche Dokumente im finalen Ergebnis.

Formel:
    MMR = λ * Sim(d, q) - (1 - λ) * max(Sim(d, d_i))
    
    wobei:
    - d: Kandidaten-Dokument
    - q: Query
    - d_i: Bereits ausgewählte Dokumente
    - λ: Trade-off zwischen Relevanz (1.0) und Diversität (0.0)

Verwendung:
    - Nach Retrieval und ReRanking
    - Reduziert Redundanz in den finalen Top-K Ergebnissen
    - Besonders nützlich wenn viele ähnliche Chunks zum gleichen Thema existieren

Optimiert für:
    - Vorberechnete Embeddings (keine Neuberechnung)
    - Frühe Terminierung nach k_final Dokumenten
    - Detailliertes LangSmith-Tracing für Austausche
"""

import logging
import numpy as np
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from langsmith import traceable

logger = logging.getLogger(__name__)


@dataclass
class MMRSwapInfo:
    """Information über einen Dokumenten-Austausch durch MMR."""
    original_position: int  # Position des ersetzten Dokuments (1-basiert)
    original_chunk_id: str  # Chunk-ID des ersetzten Dokuments
    original_text_preview: str  # Text-Vorschau des ersetzten Dokuments
    original_relevance: float  # Relevanz-Score des ersetzten Dokuments
    
    new_position: int  # Neue Position des eingetauschten Dokuments (1-basiert)
    new_chunk_id: str  # Chunk-ID des eingetauschten Dokuments
    new_text_preview: str  # Text-Vorschau des eingetauschten Dokuments
    new_relevance: float  # Relevanz-Score des eingetauschten Dokuments
    new_mmr_score: float  # MMR-Score des eingetauschten Dokuments
    
    swap_reason: str = ""  # Grund für den Austausch (Diversität)


@dataclass
class MMRResult:
    """Ergebnis der MMR-Auswahl mit Tracing-Informationen."""
    documents: List[Dict[str, Any]]  # Ausgewählte Dokumente
    swaps: List[MMRSwapInfo]  # Liste aller Austausche
    total_candidates: int  # Anzahl der Kandidaten
    selected_count: int  # Anzahl ausgewählter Dokumente
    lambda_param: float  # Verwendeter Lambda-Parameter


class MaximumMarginalRelevance:
    """
    Maximum Marginal Relevance (MMR) für diversifizierte Dokumenten-Auswahl.
    
    Wählt Dokumente basierend auf einem Trade-off zwischen:
    - Relevanz zur Query (höher = besser)
    - Diversität zu bereits ausgewählten Dokumenten (unterschiedlicher = besser)
    
    Optimiert für Nutzung mit vorberechneten Embeddings.
    """
    
    def __init__(
        self,
        lambda_param: float = 0.5,
        similarity_metric: str = "cosine"
    ):
        """
        Initialisiert MMR.
        
        Args:
            lambda_param: Trade-off Parameter (0.0 = nur Diversität, 1.0 = nur Relevanz)
                         Default 0.5 für ausgeglichene Balance
            similarity_metric: Ähnlichkeitsmetrik ("cosine" oder "dot")
        """
        if not 0.0 <= lambda_param <= 1.0:
            raise ValueError(f"lambda_param muss zwischen 0.0 und 1.0 liegen, war: {lambda_param}")
        
        self.lambda_param = lambda_param
        self.similarity_metric = similarity_metric
        logger.info(f"MMR initialisiert (λ={lambda_param}, metric={similarity_metric})")
    
    def _compute_similarity_matrix(
        self,
        embeddings: np.ndarray
    ) -> np.ndarray:
        """
        Berechnet paarweise Ähnlichkeitsmatrix für alle Embeddings.
        
        Args:
            embeddings: Matrix mit Embeddings (n_docs x embedding_dim)
            
        Returns:
            Ähnlichkeitsmatrix (n_docs x n_docs)
        """
        if self.similarity_metric == "cosine":
            # Normalisiere Embeddings
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1  # Vermeide Division durch 0
            normalized = embeddings / norms
            # Cosine Similarity Matrix via Dot Product
            return np.dot(normalized, normalized.T)
        elif self.similarity_metric == "dot":
            return np.dot(embeddings, embeddings.T)
        else:
            raise ValueError(f"Unbekannte Similarity-Metrik: {self.similarity_metric}")
    
    def _get_text_preview(self, text: str, max_length: int = 150) -> str:
        """Erstellt eine Textvorschau für Tracing."""
        if len(text) <= max_length:
            return text
        return text[:max_length] + "..."
    
    def _get_chunk_id(self, doc: Dict[str, Any], index: int) -> str:
        """Extrahiert Chunk-ID aus Dokument oder generiert Fallback."""
        metadata = doc.get('metadata', {})
        return metadata.get('chunk_id', metadata.get('id', f'doc_{index}'))
    
    def _get_relevance_score(self, doc: Dict[str, Any]) -> float:
        """Extrahiert Relevanz-Score aus Dokument (ReRank oder Similarity)."""
        metadata = doc.get('metadata', {})
        # Priorisiere rerank_score, dann similarity_score, dann rrf_score
        return metadata.get('rerank_score', 
               metadata.get('similarity_score', 
               metadata.get('rrf_score', 0.0)))
    
    @traceable(
        run_type="chain",
        name="MMR_Selection",
        metadata={"technique": "maximum_marginal_relevance"}
    )
    def _trace_mmr_result(
        self,
        result: MMRResult,
        query: str
    ) -> Dict[str, Any]:
        """
        LangSmith Trace für MMR-Ergebnis.
        
        Args:
            result: MMR-Ergebnis mit Dokumenten und Swap-Informationen
            query: Die ursprüngliche Query
            
        Returns:
            Dict mit Tracing-Informationen
        """
        # Extrahiere Informationen über Austausche
        swap_details = []
        for swap in result.swaps:
            swap_details.append({
                "original": {
                    "position": swap.original_position,
                    "chunk_id": swap.original_chunk_id,
                    "text_preview": swap.original_text_preview,
                    "relevance_score": swap.original_relevance
                },
                "replacement": {
                    "position": swap.new_position,
                    "chunk_id": swap.new_chunk_id,
                    "text_preview": swap.new_text_preview,
                    "relevance_score": swap.new_relevance,
                    "mmr_score": swap.new_mmr_score
                },
                "reason": swap.swap_reason
            })
        
        # Extrahiere finale Dokument-Informationen
        final_docs = []
        for i, doc in enumerate(result.documents):
            metadata = doc.get('metadata', {})
            final_docs.append({
                "position": i + 1,
                "chunk_id": self._get_chunk_id(doc, i),
                "text_preview": self._get_text_preview(doc.get('page_content', '')),
                "relevance_score": self._get_relevance_score(doc),
                "mmr_score": metadata.get('mmr_score', 0.0)
            })
        
        return {
            "query": query,
            "lambda": result.lambda_param,
            "total_candidates": result.total_candidates,
            "selected_count": result.selected_count,
            "num_swaps": len(result.swaps),
            "swaps": swap_details,
            "final_documents": final_docs
        }
    
    def select(
        self,
        documents: List[Dict[str, Any]],
        document_embeddings: np.ndarray,
        relevance_scores: List[float],
        k_final: int,
        query: str = ""
    ) -> MMRResult:
        """
        Wählt k_final Dokumente mittels MMR aus vorsortierten Kandidaten.
        
        Die Dokumente sind bereits nach Relevanz sortiert (von ReRanking oder Retrieval).
        MMR prüft, ob Dokumente in den Top-k_final durch diversere Alternativen
        ersetzt werden sollten.
        
        Optimierung: Stoppt sobald k_final Dokumente ausgewählt sind.
        
        Args:
            documents: Vorsortierte Dokumente (mit 'page_content' und 'metadata')
            document_embeddings: Vorberechnete Embeddings (n_docs x embedding_dim)
            relevance_scores: Relevanz-Scores für alle Dokumente (ReRank oder Similarity)
            k_final: Anzahl der auszuwählenden Dokumente
            query: Die ursprüngliche Query (für Tracing)
            
        Returns:
            MMRResult mit ausgewählten Dokumenten und Swap-Informationen
        """
        n_docs = len(documents)
        swaps: List[MMRSwapInfo] = []
        
        if n_docs == 0:
            logger.warning("Keine Dokumente für MMR-Auswahl übergeben")
            return MMRResult(
                documents=[],
                swaps=[],
                total_candidates=0,
                selected_count=0,
                lambda_param=self.lambda_param
            )
        
        if k_final >= n_docs:
            logger.info(f"MMR: k_final={k_final} >= n_docs={n_docs}, gebe alle Dokumente zurück")
            # Füge MMR-Score hinzu (= Relevanz-Score, da keine Diversität nötig)
            for i, doc in enumerate(documents):
                if 'metadata' not in doc:
                    doc['metadata'] = {}
                doc['metadata']['mmr_score'] = relevance_scores[i]
                doc['metadata']['mmr_rank'] = i + 1
            return MMRResult(
                documents=documents,
                swaps=[],
                total_candidates=n_docs,
                selected_count=n_docs,
                lambda_param=self.lambda_param
            )
        
        # Validiere Embedding-Dimensionen
        if len(document_embeddings) != n_docs:
            raise ValueError(
                f"Anzahl Embeddings ({len(document_embeddings)}) != Anzahl Dokumente ({n_docs})"
            )
        
        # Konvertiere zu numpy array
        relevance_array = np.array(relevance_scores)
        
        # Berechne paarweise Dokument-Ähnlichkeiten (für Diversität)
        # Nur einmal berechnen - wird für alle Iterationen wiederverwendet
        doc_similarity_matrix = self._compute_similarity_matrix(document_embeddings)
        
        # MMR Greedy Selection
        # Starte mit den Top-k_final Dokumenten als Ausgangspunkt
        # und ersetze bei Bedarf durch diversere Alternativen
        selected_indices: List[int] = []
        remaining_indices = set(range(n_docs))
        mmr_scores: List[float] = []
        
        # Merke Original-Reihenfolge für Swap-Tracking
        original_top_k = list(range(min(k_final, n_docs)))
        
        for position in range(k_final):
            if not remaining_indices:
                break
            
            best_idx = -1
            best_mmr = float('-inf')
            
            for idx in remaining_indices:
                # Relevanz-Term: λ * relevance_score
                relevance_term = self.lambda_param * relevance_array[idx]
                
                # Diversität-Term: (1 - λ) * max(Sim(d, d_i)) für alle bereits ausgewählten d_i
                if selected_indices:
                    max_sim_to_selected = max(
                        doc_similarity_matrix[idx, sel_idx]
                        for sel_idx in selected_indices
                    )
                    diversity_penalty = (1 - self.lambda_param) * max_sim_to_selected
                else:
                    # Erstes Dokument: Kein Diversitäts-Penalty
                    diversity_penalty = 0.0
                
                # MMR Score: Relevanz - Diversitäts-Penalty
                mmr_score = relevance_term - diversity_penalty
                
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx
            
            if best_idx >= 0:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)
                mmr_scores.append(best_mmr)
                
                # Tracke Swap wenn ein Dokument außerhalb der ursprünglichen Top-k gewählt wurde
                if best_idx >= k_final and position < k_final:
                    # Ein Dokument von außerhalb der Top-k wurde eingetauscht
                    # Finde das nächste nicht-ausgewählte Dokument aus den ursprünglichen Top-k
                    # das an dieser Position hätte sein sollen
                    skipped_originals = [
                        idx for idx in original_top_k 
                        if idx not in selected_indices[:-1]  # Ohne das gerade ausgewählte
                    ]
                    
                    if skipped_originals:
                        original_idx = skipped_originals[0]  # Das erste übersprungene Original
                        original_doc = documents[original_idx]
                        new_doc = documents[best_idx]
                        
                        # Berechne Ähnlichkeit des Originals zu bereits ausgewählten (ohne das neue)
                        if len(selected_indices) > 1:
                            max_sim = max(
                                doc_similarity_matrix[original_idx, sel_idx]
                                for sel_idx in selected_indices[:-1]  # Ohne das gerade ausgewählte
                            )
                            reason = f"Original (Dok {original_idx+1}) hatte hohe Ähnlichkeit ({max_sim:.3f}) zu bereits ausgewählten Dokumenten"
                        else:
                            reason = "Diversitätsoptimierung"
                        
                        swap = MMRSwapInfo(
                            original_position=position + 1,
                            original_chunk_id=self._get_chunk_id(original_doc, original_idx),
                            original_text_preview=self._get_text_preview(original_doc.get('page_content', '')),
                            original_relevance=float(relevance_array[original_idx]),
                            new_position=position + 1,
                            new_chunk_id=self._get_chunk_id(new_doc, best_idx),
                            new_text_preview=self._get_text_preview(new_doc.get('page_content', '')),
                            new_relevance=float(relevance_array[best_idx]),
                            new_mmr_score=best_mmr,
                            swap_reason=reason
                        )
                        swaps.append(swap)
        
        # Erstelle Ergebnis-Liste mit MMR-Scores
        selected_documents = []
        for rank, (idx, score) in enumerate(zip(selected_indices, mmr_scores)):
            doc = documents[idx].copy()
            if 'metadata' not in doc:
                doc['metadata'] = {}
            doc['metadata']['mmr_score'] = score
            doc['metadata']['mmr_rank'] = rank + 1
            doc['metadata']['original_rank'] = idx + 1
            doc['metadata']['original_relevance'] = float(relevance_array[idx])
            selected_documents.append(doc)
        
        # Logging
        logger.info(
            f"MMR: {len(selected_documents)} von {n_docs} Dokumenten ausgewählt "
            f"(λ={self.lambda_param}, Swaps: {len(swaps)})"
        )
        if swaps:
            logger.info(f"MMR-Swaps: {len(swaps)} Dokumente wurden wegen höherer Diversität ersetzt")
        
        result = MMRResult(
            documents=selected_documents,
            swaps=swaps,
            total_candidates=n_docs,
            selected_count=len(selected_documents),
            lambda_param=self.lambda_param
        )
        
        # LangSmith Tracing
        self._trace_mmr_result(result, query)
        
        return result


# ============================================================================
# Factory Functions
# ============================================================================
def create_mmr(
    lambda_param: float = 0.5,
    similarity_metric: str = "cosine"
) -> MaximumMarginalRelevance:
    """
    Factory-Funktion für MMR.
    
    Args:
        lambda_param: Trade-off (0.0 = Diversität, 1.0 = Relevanz)
        similarity_metric: "cosine" oder "dot"
        
    Returns:
        MaximumMarginalRelevance-Instanz
    """
    return MaximumMarginalRelevance(
        lambda_param=lambda_param,
        similarity_metric=similarity_metric
    )
