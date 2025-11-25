"""
Empty Result Handler
====================

Behandelt leere Suchergebnisse mit hilfreichen Nachrichten.
"""


class EmptyResultHandler:
    """
    Liefert intelligente Fehlermeldungen bei leeren Results.
    
    Vorteile:
    - Bessere User Experience bei Fehlschlägen
    - Vorschläge für alternative Suchen
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def handle_empty(self, query: str, no_data: bool = False) -> str:
        """
        Generiert Fehler-/Hinweismeldung bei leeren Results.
        
        Args:
            query: Original Query
            no_data: Ob überhaupt keine Daten verfügbar sind
            
        Returns:
            Fehlermeldung
        """
        if not self.enabled:
            return "Keine Ergebnisse gefunden."
        
        if no_data:
            return (
                f"❌ Keine relevanten Informationen zu '{query}' gefunden. "
                f"Möglicherweise sind noch keine Daten zu diesem Thema "
                f"in der Universitäts-Wissensdatenbank verfügbar."
            )
        else:
            return (
                f"❌ Die gefundenen Informationen zu '{query}' sind nicht "
                f"relevant genug. Versuchen Sie eine andere Formulierung "
                f"oder allgemeinere Begriffe."
            )
    
    def handle_naive(self, query: str) -> str:
        """Naive Fehlerbehandlung: Einfache Meldung."""
        return f"Keine Ergebnisse für '{query}' gefunden."
