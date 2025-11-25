"""
Result Aggregation
==================

Kombiniert Ergebnisse aus mehreren Sources.
"""

from typing import List, Dict, Any


class ResultAggregation:
    """
    Aggregiert und sortiert Ergebnisse aus mehreren Quellen.
    
    Vorteile:
    - Einheitliche Ranking-Metrik über alle Sources
    - Bessere Ergebnis-Qualität durch Diversität
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def aggregate(self, results: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Aggregiert Results und wählt Top-K.
        
        Args:
            results: Liste von Result-Dictionaries
            top_k: Anzahl finaler Results
            
        Returns:
            Top-K aggregierte Results
        """
        if not self.enabled or not results:
            return results[:top_k]
        
        # Sortiere nach Distance (niedrigster = relevantester)
        sorted_results = sorted(results, key=lambda x: x['distance'])
        
        return sorted_results[:top_k]
