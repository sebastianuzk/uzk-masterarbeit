"""
Empty Result Handler
====================

Intelligente Fehlermeldungen für leere Suchergebnisse.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmptyResultHandler:
    """
    Behandelt Fälle ohne Suchergebnisse intelligent.
    """
    
    def __init__(self):
        """Initialisiere den Empty Result Handler."""
        pass
    
    def handle_empty_results(
        self,
        query: str,
        had_results_before_filtering: bool = False,
        relevance_threshold: float = 0.1
    ) -> str:
        """
        Generiere informative Nachricht für leere Ergebnisse.
        
        Args:
            query: Originale Suchanfrage
            had_results_before_filtering: Gab es Ergebnisse vor Relevanz-Filterung?
            relevance_threshold: Verwendeter Relevanz-Schwellenwert
            
        Returns:
            Informative Fehlermeldung
        """
        # Fall 1: Keine Ergebnisse in Datenbank
        if not had_results_before_filtering:
            return self._no_data_message(query)
        
        # Fall 2: Ergebnisse vorhanden, aber alle unter Threshold
        return self._low_relevance_message(query, relevance_threshold)
    
    def _no_data_message(self, query: str) -> str:
        """
        Nachricht: Keine Daten in Datenbank.
        
        Args:
            query: Suchanfrage
            
        Returns:
            Fehlermeldung
        """
        message = [
            "ℹ️ Keine Informationen gefunden\n",
            "="*60,
            f"\n🔍 Ihre Suche: \"{query}\"",
            "\n❌ Zu diesem Thema sind leider keine Informationen in der Datenbank vorhanden.\n",
            "💡 Mögliche Gründe:",
            "   • Das Thema ist nicht in den gespeicherten Dokumenten enthalten",
            "   • Die Formulierung ist zu spezifisch",
            "   • Möglicherweise Tippfehler in der Anfrage\n",
            "📝 Versuchen Sie:",
            "   • Allgemeinere Begriffe verwenden",
            "   • Alternative Formulierungen",
            "   • Deutsche statt englische Begriffe (oder umgekehrt)\n",
            "📧 Bei weiteren Fragen:",
            "   Wenden Sie sich direkt an das Studierendensekretariat oder",
            "   besuchen Sie die offizielle Website der WiSo-Fakultät.",
            "\n" + "="*60
        ]
        
        return "\n".join(message)
    
    def _low_relevance_message(self, query: str, threshold: float) -> str:
        """
        Nachricht: Ergebnisse gefunden, aber Relevanz zu niedrig.
        
        Args:
            query: Suchanfrage
            threshold: Relevanz-Schwellenwert
            
        Returns:
            Fehlermeldung
        """
        message = [
            "⚠️ Keine ausreichend relevanten Informationen gefunden\n",
            "="*60,
            f"\n🔍 Ihre Suche: \"{query}\"",
            "\n❓ Es wurden Dokumente gefunden, aber keines erfüllt den ",
            f"   Relevanz-Schwellenwert (>{threshold*100:.0f}%).\n",
            "💡 Das bedeutet:",
            "   Die Datenbank enthält möglicherweise verwandte Informationen,",
            "   aber keine präzise Antwort auf Ihre spezifische Frage.\n",
            "📝 Versuchen Sie:",
            "   • Formulieren Sie Ihre Frage allgemeiner",
            "   • Nutzen Sie Schlüsselbegriffe statt vollständiger Sätze",
            "   • Teilen Sie komplexe Fragen in mehrere einfache Fragen auf\n",
            "🔧 Für Experten:",
            f"   Relevanz-Threshold: {threshold} (kann in Konfiguration angepasst werden)\n",
            "📧 Bei dringenden Anliegen:",
            "   Kontaktieren Sie direkt die zuständige Stelle an der Fakultät.",
            "\n" + "="*60
        ]
        
        return "\n".join(message)
    
    def suggest_alternatives(self, query: str) -> Optional[str]:
        """
        Schlage alternative Suchbegriffe vor.
        
        Args:
            query: Originale Suchanfrage
            
        Returns:
            Vorschläge oder None
        """
        query_lower = query.lower()
        
        # Häufige Synonyme/Alternativen
        suggestions_map = {
            'anmeldung': ['Registrierung', 'Einschreibung', 'Bewerbung'],
            'master': ['Masterstudium', 'Master-Programm', 'M.Sc.'],
            'bachelor': ['Bachelorstudium', 'Bachelor-Programm', 'B.Sc.'],
            'bewerbung': ['Zulassung', 'Einschreibung', 'Immatrikulation'],
            'prüfung': ['Klausur', 'Examination', 'Leistungsnachweis'],
            'frist': ['Deadline', 'Termin', 'Anmeldefrist']
        }
        
        for keyword, alternatives in suggestions_map.items():
            if keyword in query_lower:
                return f"💡 Alternative Suchbegriffe: {', '.join(alternatives)}"
        
        return None
