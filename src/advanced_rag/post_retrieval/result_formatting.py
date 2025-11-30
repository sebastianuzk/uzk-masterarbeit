"""
Result Formatting
=================

Formatiert Ergebnisse mit Metadaten, Quellen und Emojis.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class ResultFormatter:
    """
    Formatiert RAG-Ergebnisse für bessere Lesbarkeit.
    """
    
    def __init__(self, include_metadata: bool = True, include_sources: bool = True):
        """
        Initialisiere den Result Formatter.
        
        Args:
            include_metadata: Füge Metadaten hinzu
            include_sources: Füge Quellenangaben hinzu
        """
        self.include_metadata = include_metadata
        self.include_sources = include_sources
        
    def format(self, results: List[Dict[str, Any]], query: str = None) -> str:
        """
        Formatiere Ergebnisse als strukturierten Text.
        
        Args:
            results: Liste von Ergebnissen
            query: Originale Suchanfrage
            
        Returns:
            Formatierter Text
        """
        if not results:
            return "ℹ️ Keine relevanten Informationen gefunden."
        
        output_lines = []
        
        # Header
        if query:
            output_lines.append(f"🔍 Suchergebnisse für: \"{query}\"\n")
        
        output_lines.append(f"📊 {len(results)} relevante Dokumente gefunden:\n")
        
        # Formatiere jedes Ergebnis
        for i, result in enumerate(results, 1):
            output_lines.append(f"\n{'='*60}")
            output_lines.append(f"📄 Ergebnis {i}/{len(results)}")
            
            # Relevanz-Indikator
            if 'relevance' in result:
                relevance = result['relevance']
                emoji = self._get_relevance_emoji(relevance)
                output_lines.append(f"{emoji} Relevanz: {relevance:.1%}")
            
            # Titel
            if self.include_metadata and 'metadata' in result:
                metadata = result['metadata']
                title = metadata.get('title', 'Kein Titel')
                output_lines.append(f"📌 Titel: {title}")
                
                # Content-Type
                content_type = metadata.get('content_type', '').upper()
                if content_type:
                    type_emoji = "📄" if content_type == "HTML" else "📕"
                    output_lines.append(f"{type_emoji} Typ: {content_type}")
                
                # Collection
                if 'collection' in result:
                    output_lines.append(f"📦 Collection: {result['collection']}")
            
            # Inhalt
            document = result.get('document', '')
            if len(document) > 500:
                document = document[:500] + "..."
            output_lines.append(f"\n💬 Inhalt:")
            output_lines.append(document)
            
            # Quelle
            if self.include_sources and 'metadata' in result:
                url = result['metadata'].get('url', '')
                if url:
                    output_lines.append(f"\n🔗 Quelle: {url}")
        
        output_lines.append(f"\n{'='*60}\n")
        
        return "\n".join(output_lines)
    
    def _get_relevance_emoji(self, relevance: float) -> str:
        """Gib Emoji basierend auf Relevanz."""
        if relevance >= 0.9:
            return "🎯"
        elif relevance >= 0.7:
            return "✅"
        elif relevance >= 0.5:
            return "⚠️"
        else:
            return "❓"
    
    def format_compact(self, results: List[Dict[str, Any]]) -> str:
        """
        Kompakte Formatierung (nur Text, keine Metadaten).
        
        Args:
            results: Liste von Ergebnissen
            
        Returns:
            Kompakter Text
        """
        if not results:
            return "ℹ️ Keine relevanten Informationen gefunden."
        
        documents = [result.get('document', '') for result in results]
        return "\n\n".join(documents)
