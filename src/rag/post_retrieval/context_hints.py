"""
Context-Aware Hints
===================

Fügt kontextabhängige Hinweise basierend auf Query hinzu.
"""

from typing import Dict


class ContextHintGenerator:
    """
    Generiert spezifische Hinweise basierend auf Query-Keywords.
    
    Vorteile:
    - Proaktive Hilfestellung für häufige Fragen
    - Bessere User Experience
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        
        # Keyword → Hint Mapping
        self.hint_rules = {
            ('bewerbung', 'fachsemester', 'höher'): (
                "\n\n💡 **Wichtiger Hinweis**: Bei Bewerbungen für höhere "
                "Fachsemester sind oft spezielle Bescheinigungen vom "
                "Prüfungsamt der WiSo-Fakultät erforderlich."
            ),
            ('klips', 'klips2', 'registrierung'): (
                "\n\n💡 **Wichtiger Hinweis**: Für die KLIPS2-Registrierung "
                "benötigen Sie Ihre Matrikelnummer und Ihr Passwort."
            ),
            ('deadline', 'frist', 'bewerbungsfrist'): (
                "\n\n💡 **Wichtiger Hinweis**: Beachten Sie die Bewerbungsfristen! "
                "Diese sind je nach Studiengang unterschiedlich."
            )
        }
    
    def generate_hint(self, query: str, response: str) -> str:
        """
        Fügt passenden Hint zur Response hinzu.
        
        Args:
            query: Original Query
            response: Formatierte Response
            
        Returns:
            Response mit optionalem Hint
        """
        if not self.enabled:
            return response
        
        query_lower = query.lower()
        
        # Prüfe alle Hint-Rules
        for keywords, hint in self.hint_rules.items():
            if any(keyword in query_lower for keyword in keywords):
                return response + hint
        
        return response
