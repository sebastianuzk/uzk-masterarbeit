"""
Context Hints
=============

Fügt kontextspezifische Hinweise zu RAG-Ergebnissen hinzu.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ContextHintProvider:
    """
    Fügt query-abhängige Kontext-Hinweise hinzu.
    """
    
    # Hint-Regeln basierend auf Keywords
    HINT_RULES = {
        'bewerbung': [
            "💡 Tipp: Bewerbungsfristen variieren je nach Studiengang",
            "📧 Kontakt: Bei Bewerbungsfragen wenden Sie sich an das Studierendensekretariat"
        ],
        'prüfung': [
            "📅 Wichtig: Beachten Sie die Anmeldefristen für Prüfungen",
            "📧 Kontakt: Prüfungsamt für weitere Informationen"
        ],
        'klips': [
            "💻 KLIPS2: Ihre Plattform für Anmeldungen und Verwaltung",
            "🔧 Support: IT-Helpdesk bei technischen Problemen"
        ],
        'master': [
            "🎓 Master-Programme haben spezifische Zulassungsvoraussetzungen",
            "📄 Dokumentation: Prüfen Sie die erforderlichen Unterlagen"
        ],
        'fachsemester': [
            "⚠️ Höhere Fachsemester: Bewerbungsprozess unterscheidet sich",
            "📧 Beratung: Fachstudienberatung für individuelle Fragen"
        ],
        'ausland': [
            "🌍 International Office: Ansprechpartner für Auslandsaufenthalte",
            "📅 Planung: Mindestens 1 Jahr Vorlaufzeit einplanen"
        ]
    }
    
    def __init__(self, enable_hints: bool = True):
        """
        Initialisiere den Context Hint Provider.
        
        Args:
            enable_hints: Aktiviere Kontext-Hinweise
        """
        self.enable_hints = enable_hints
        
    def add_hints(
        self,
        formatted_text: str,
        query: str,
        results: List[Dict[str, Any]] = None
    ) -> str:
        """
        Füge Kontext-Hinweise zu formatiertem Text hinzu.
        
        Args:
            formatted_text: Bereits formatierter Ergebnis-Text
            query: Originale Suchanfrage
            results: Optional: Original-Ergebnisse für zusätzliche Analyse
            
        Returns:
            Text mit Kontext-Hinweisen
        """
        if not self.enable_hints:
            return formatted_text
        
        hints = self._generate_hints(query, results)
        
        if hints:
            hint_section = "\n\n" + "="*60 + "\n"
            hint_section += "💡 HILFREICHE HINWEISE\n"
            hint_section += "="*60 + "\n"
            
            for hint in hints:
                hint_section += f"\n{hint}"
            
            hint_section += "\n" + "="*60
            
            return formatted_text + hint_section
        
        return formatted_text
    
    def _generate_hints(
        self,
        query: str,
        results: List[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Generiere relevante Hinweise basierend auf Query.
        
        Args:
            query: Suchanfrage
            results: Optional: Ergebnisse für Kontext
            
        Returns:
            Liste von Hinweisen
        """
        query_lower = query.lower()
        hints = []
        
        # Prüfe Query gegen Hint-Regeln
        for keyword, keyword_hints in self.HINT_RULES.items():
            if keyword in query_lower:
                hints.extend(keyword_hints)
        
        # Result-basierte Hints
        if results:
            # Prüfe ob nur PDFs oder nur HTMLs
            content_types = set()
            for result in results:
                if 'metadata' in result:
                    content_type = result['metadata'].get('content_type', '')
                    content_types.add(content_type)
            
            if content_types == {'pdf'}:
                hints.append("📕 Info: Ergebnisse stammen aus offiziellen Dokumenten (PDFs)")
            elif content_types == {'html'}:
                hints.append("🌐 Info: Ergebnisse stammen von Webseiten")
        
        # Dedupliziere Hints
        return list(dict.fromkeys(hints))
    
    def get_contact_hint(self, topic: str) -> Optional[str]:
        """
        Gib Kontakt-Hinweis für spezifisches Thema.
        
        Args:
            topic: Themenbereich
            
        Returns:
            Kontakt-Hinweis oder None
        """
        contacts = {
            'bewerbung': "📧 Studierendensekretariat: studierendensekretariat@uni-koeln.de",
            'prüfung': "📧 Prüfungsamt: pruefungsamt@wiso.uni-koeln.de",
            'klips': "💻 IT-Helpdesk: it-helpdesk@uni-koeln.de",
            'ausland': "🌍 International Office: international@wiso.uni-koeln.de",
            'beratung': "💬 Fachstudienberatung: Siehe Fakultäts-Website"
        }
        
        return contacts.get(topic.lower())
