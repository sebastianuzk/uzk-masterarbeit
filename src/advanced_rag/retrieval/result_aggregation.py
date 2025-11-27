"""
Result Aggregation
==================

Aggregiert und sortiert Ergebnisse aus mehreren Quellen.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Aggregiert Ergebnisse aus mehreren Collections.
    """
    
    def __init__(self, top_k: int = 5):
        """
        Initialisiere den Result Aggregator.
        
        Args:
            top_k: Anzahl finale Top-Ergebnisse
        """
        self.top_k = top_k
        
    def aggregate(
        self,
        results: List[Dict[str, Any]],
        sort_by: str = 'distance'
    ) -> List[Dict[str, Any]]:
        """
        Aggregiere und sortiere Ergebnisse.
        
        Args:
            results: Liste von Ergebnissen
            sort_by: Sortier-Key ('distance' oder 'relevance')
            
        Returns:
            Sortierte Top-K Ergebnisse
        """
        if not results:
            return []
        
        # Sortiere nach Distance (aufsteigend) oder Relevance (absteigend)
        reverse = (sort_by == 'relevance')
        sorted_results = sorted(
            results,
            key=lambda x: x.get(sort_by, float('inf') if not reverse else 0),
            reverse=reverse
        )
        
        # Nimm Top-K
        top_results = sorted_results[:self.top_k]
        
        logger.info(
            f"Aggregiert: {len(results)} → {len(top_results)} "
            f"(sortiert nach {sort_by})"
        )
        
        return top_results
    
    def deduplicate(
        self,
        results: List[Dict[str, Any]],
        key: str = 'id'
    ) -> List[Dict[str, Any]]:
        """
        Entferne Duplikate basierend auf Key.
        
        Args:
            results: Liste von Ergebnissen
            key: Deduplication-Key
            
        Returns:
            Deduplizierte Ergebnisse
        """
        seen = set()
        unique = []
        
        for result in results:
            identifier = result.get(key)
            if identifier not in seen:
                seen.add(identifier)
                unique.append(result)
        
        if len(unique) < len(results):
            logger.debug(f"Duplikate entfernt: {len(results)} → {len(unique)}")
        
        return unique
