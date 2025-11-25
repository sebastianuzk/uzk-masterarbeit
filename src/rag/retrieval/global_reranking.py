"""
Global Re-Ranking
=================

Sortiert aggregierte Results global nach Relevanz.
"""

from typing import List, Dict, Any


class GlobalReranker:
    """
    Re-ranked Results global nach finaler Relevanz-Metrik.
    
    Vorteile:
    - Beste Results kommen zuerst, unabhängig von Source
    - Konsistente Ranking-Qualität
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def rerank(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-ranked Results nach Distance/Relevance.
        
        Args:
            results: Liste von Results
            
        Returns:
            Sortierte Results
        """
        if not self.enabled or not results:
            return results
        
        # Sortiere nach Distance (aufsteigend = bessere Relevanz)
        return sorted(results, key=lambda x: x.get('distance', float('inf')))
