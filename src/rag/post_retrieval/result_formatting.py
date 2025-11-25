"""
Result Formatting
=================

Formatiert Results für LLM-Konsum.
"""

from typing import List, Dict, Any, Set


class ResultFormatter:
    """
    Formatiert Results zu strukturierter, LLM-freundlicher Ausgabe.
    
    Vorteile:
    - Strukturierte Darstellung mit Metadaten
    - Source Attribution für Nachvollziehbarkeit
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def format(self, results: List[Dict[str, Any]]) -> tuple[str, Set[str]]:
        """
        Formatiert Results zu String.
        
        Args:
            results: Liste von Results
            
        Returns:
            (formatted_string, searched_collections)
        """
        if not self.enabled or not results:
            return ("", set())
        
        formatted_results = []
        searched_collections = set()
        
        for i, result in enumerate(results, 1):
            doc = result.get('document', '')
            metadata = result.get('metadata', {})
            
            # Sammle Collections
            collection = metadata.get('collection', 'unbekannt')
            searched_collections.add(collection)
            
            # Formatierung
            relevance = metadata.get('relevance_score', 0)
            
            if relevance > 0.1:  # Nur relevante anzeigen
                source_info = ""
                collection_info = f" [aus: {collection}]"
                
                title = metadata.get('title', '')
                source_url = metadata.get('source_url', '')
                
                if title:
                    source_info = f" (Quelle: {title})"
                elif source_url:
                    source_info = f" (Quelle: {source_url})"
                
                doc_text = doc.strip() if doc else ""
                if doc_text:
                    formatted_results.append(
                        f"📄 **Information {i}**{source_info}{collection_info}:\n{doc_text}"
                    )
        
        if not formatted_results:
            return ("", searched_collections)
        
        response = (
            f"🎓 **Informationen aus der Universitäts-Wissensdatenbank** "
            f"(durchsuchte Collections: {', '.join(searched_collections)}):\n\n"
            + "\n\n".join(formatted_results)
        )
        
        return (response, searched_collections)
    
    def format_naive(self, results: List[Dict[str, Any]]) -> str:
        """
        Naive Formatierung: Nur rohe Dokumente ohne Metadaten.
        
        Args:
            results: Liste von Results
            
        Returns:
            Einfacher concatenated String
        """
        if not results:
            return ""
        
        documents = [result.get('document', '') for result in results]
        return "\n\n".join(doc for doc in documents if doc.strip())
