"""
Distance to Relevance Conversion
=================================

Konvertiert Distanz-Metriken in intuitive Relevanz-Scores.
"""

from typing import List, Dict, Any


class DistanceToRelevanceConverter:
    """
    Konvertiert Distance (0=perfect, 2=worst) zu Relevance (0=worst, 1=perfect).
    
    Vorteile:
    - Intuitivere Scores für Benutzer
    - Einfachere Threshold-Logik
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def convert(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Fügt relevance_score zu jedem Result hinzu.
        
        Args:
            results: Liste von Results mit 'distance'
            
        Returns:
            Results mit 'relevance_score'
        """
        if not self.enabled:
            return results
        
        for result in results:
            distance = result.get('distance', 1.0)
            # Cosine distance range: 0 (identical) to 2 (opposite)
            # Convert to relevance: 1 (perfect) to 0 (irrelevant)
            relevance = max(0, 1 - distance)
            
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['relevance_score'] = float(relevance)
        
        return results
