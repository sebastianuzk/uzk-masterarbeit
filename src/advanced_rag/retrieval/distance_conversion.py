"""
Distance to Relevance Conversion
=================================

Konvertiert Cosine-Distance (0-2) zu intuitivem Relevance-Score (0-1).
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class DistanceConverter:
    """
    Konvertiert Distanz-Werte zu Relevanz-Scores.
    
    ChromaDB verwendet Cosine Distance:
    - 0.0 = identisch
    - 1.0 = orthogonal  
    - 2.0 = entgegengesetzt
    
    Konversion zu Relevance Score:
    - 1.0 = perfekt relevant
    - 0.5 = neutral
    - 0.0 = irrelevant
    """
    
    def __init__(self, distance_type: str = 'cosine'):
        """
        Initialisiere den Distance Converter.
        
        Args:
            distance_type: Typ der Distanz ('cosine', 'euclidean', 'l2')
        """
        self.distance_type = distance_type
        
    def convert(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Konvertiere Distance zu Relevance Score.
        
        Args:
            results: Liste von Ergebnissen mit 'distance' Key
            
        Returns:
            Ergebnisse mit zusätzlichem 'relevance' Key
        """
        converted = []
        
        for result in results:
            distance = result.get('distance', 2.0)
            
            if self.distance_type == 'cosine':
                # Cosine Distance: 0-2 → Relevance: 1-0
                relevance = 1.0 - (distance / 2.0)
            elif self.distance_type in ['euclidean', 'l2']:
                # Euclidean/L2: Je kleiner, desto relevanter
                # Normalisierung auf 0-1 (angenommen max distance ~2.0)
                relevance = 1.0 / (1.0 + distance)
            else:
                # Fallback: Invertiere einfach
                relevance = 1.0 - min(distance, 1.0)
            
            # Stelle sicher dass Relevance in [0, 1]
            relevance = max(0.0, min(1.0, relevance))
            
            result_copy = result.copy()
            result_copy['relevance'] = relevance
            converted.append(result_copy)
        
        logger.debug(
            f"Distance→Relevance konvertiert: "
            f"avg relevance = {sum(r['relevance'] for r in converted) / len(converted):.3f}"
            if converted else "keine Ergebnisse"
        )
        
        return converted
    
    def get_relevance_label(self, relevance: float) -> str:
        """
        Gib menschenlesbares Label für Relevance Score.
        
        Args:
            relevance: Relevance Score (0-1)
            
        Returns:
            Label wie "Sehr relevant", "Relevant", etc.
        """
        if relevance >= 0.9:
            return "🎯 Sehr relevant"
        elif relevance >= 0.7:
            return "✅ Relevant"
        elif relevance >= 0.5:
            return "⚠️ Möglicherweise relevant"
        elif relevance >= 0.3:
            return "❓ Wenig relevant"
        else:
            return "❌ Irrelevant"
