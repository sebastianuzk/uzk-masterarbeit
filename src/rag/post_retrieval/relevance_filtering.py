"""
Relevance Filtering
===================

Filtert Results nach Relevanz-Schwellwert.
"""

from typing import List, Dict, Any


class RelevanceFilter:
    """
    Filtert Results die unter dem Relevanz-Threshold liegen.
    
    Vorteile:
    - Höhere Precision durch Ausschluss irrelevanter Results
    - Reduziert Noise im Context
    """
    
    def __init__(self, enabled: bool = True, threshold: float = 0.1):
        self.enabled = enabled
        self.threshold = threshold
    
    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtert Results nach Relevanz.
        
        Args:
            results: Liste von Results mit relevance_score
            threshold: Minimale Relevanz
            
        Returns:
            Gefilterte Results
        """
        if not self.enabled:
            return results
        
        filtered = []
        for result in results:
            relevance = result.get('metadata', {}).get('relevance_score', 0)
            if relevance >= self.threshold:
                filtered.append(result)
        
        return filtered
