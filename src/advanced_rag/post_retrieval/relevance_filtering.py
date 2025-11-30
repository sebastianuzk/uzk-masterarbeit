"""
Relevance Filtering
===================

Filtert Ergebnisse unter Relevanz-Schwellenwert.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class RelevanceFilter:
    """
    Filtert Ergebnisse basierend auf Relevanz-Score.
    """
    
    def __init__(self, threshold: float = 0.1):
        """
        Initialisiere den Relevance Filter.
        
        Args:
            threshold: Minimaler Relevance Score (0-1)
        """
        self.threshold = threshold
        
    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtere irrelevante Ergebnisse.
        
        Args:
            results: Liste von Ergebnissen mit 'relevance' Key
            
        Returns:
            Gefilterte Ergebnisse
        """
        if not results:
            return []
        
        # Filtere nach Threshold
        filtered = [
            result for result in results
            if result.get('relevance', 0.0) >= self.threshold
        ]
        
        if len(filtered) < len(results):
            removed_count = len(results) - len(filtered)
            logger.info(
                f"Relevance Filtering: {removed_count} Ergebnisse entfernt "
                f"(Threshold: {self.threshold})"
            )
        
        return filtered
    
    def get_quality_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Berechne Qualitätsstatistiken.
        
        Args:
            results: Liste von Ergebnissen
            
        Returns:
            Statistiken-Dictionary
        """
        if not results:
            return {
                'count': 0,
                'avg_relevance': 0.0,
                'min_relevance': 0.0,
                'max_relevance': 0.0
            }
        
        relevance_scores = [r.get('relevance', 0.0) for r in results]
        
        return {
            'count': len(results),
            'avg_relevance': sum(relevance_scores) / len(relevance_scores),
            'min_relevance': min(relevance_scores),
            'max_relevance': max(relevance_scores),
            'above_threshold': sum(1 for score in relevance_scores if score >= self.threshold)
        }
