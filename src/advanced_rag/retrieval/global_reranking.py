"""
Global Re-Ranking
=================

Globales Ranking über alle Quellen hinweg.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class GlobalReranker:
    """
    Führt globales Re-Ranking über aggregierte Ergebnisse durch.
    """
    
    def __init__(self, use_relevance: bool = True):
        """
        Initialisiere den Global Reranker.
        
        Args:
            use_relevance: Nutze Relevance Score statt Distance
        """
        self.use_relevance = use_relevance
        
    def rerank(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Globales Re-Ranking der Ergebnisse.
        
        Args:
            results: Liste von Ergebnissen
            
        Returns:
            Neu sortierte Ergebnisse
        """
        if not results:
            return []
        
        # Entscheide Ranking-Strategie
        if self.use_relevance and 'relevance' in results[0]:
            # Sortiere nach Relevance (absteigend)
            ranked = sorted(
                results,
                key=lambda x: x.get('relevance', 0.0),
                reverse=True
            )
            metric = 'relevance'
        else:
            # Fallback: Sortiere nach Distance (aufsteigend)
            ranked = sorted(
                results,
                key=lambda x: x.get('distance', float('inf'))
            )
            metric = 'distance'
        
        # Füge Ranking-Position hinzu
        for i, result in enumerate(ranked):
            result['rank'] = i + 1
        
        logger.info(
            f"Global Re-Ranking: {len(ranked)} Ergebnisse "
            f"(sortiert nach {metric})"
        )
        
        return ranked
    
    def apply_diversity_penalty(
        self,
        results: List[Dict[str, Any]],
        max_per_source: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Fördere Diversität durch Limitierung pro Quelle.
        
        Args:
            results: Gerankde Ergebnisse
            max_per_source: Maximale Ergebnisse pro Collection
            
        Returns:
            Diversifizierte Ergebnisse
        """
        source_count = {}
        diverse_results = []
        
        for result in results:
            source = result.get('collection', 'unknown')
            current_count = source_count.get(source, 0)
            
            if current_count < max_per_source:
                diverse_results.append(result)
                source_count[source] = current_count + 1
        
        if len(diverse_results) < len(results):
            logger.debug(
                f"Diversity-Penalty angewendet: "
                f"{len(results)} → {len(diverse_results)}"
            )
        
        return diverse_results
