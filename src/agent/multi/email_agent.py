"""
Email Agent - Spezialisierter Agent für E-Mail-Kommunikation.

Verantwortlich für:
- Versenden von Support-E-Mails
- E-Mail-Eskalation bei Problemen
- Kontaktaufnahme mit dem Uni-Support
"""

from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from src.tools.email_tool import create_email_tool

from .base_agent import BaseSpecializedAgent


class EmailAgent(BaseSpecializedAgent):
    """
    Spezialisierter Agent für E-Mail-Kommunikation.
    
    Dieser Agent bearbeitet alle Anfragen, die mit dem Versenden
    von E-Mails und Support-Kommunikation zusammenhängen.
    """
    
    def __init__(self, share_llm: Optional[ChatOllama] = None):
        """Initialisiere den Email-Agenten."""
        super().__init__(share_llm)
        print(f"✅ {self.name} initialisiert mit {len(self.tools)} Tools")
    
    @property
    def name(self) -> str:
        return "Email-Agent"
    
    @property
    def description(self) -> str:
        return (
            "Spezialisiert auf E-Mail-Kommunikation: "
            "Versenden von Support-Anfragen, Eskalation von Problemen, "
            "Kontaktaufnahme mit dem Universitäts-Support. "
            "Nutze diesen Agenten wenn der Nutzer eine E-Mail senden möchte "
            "oder Hilfe vom Support benötigt."
        )
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle das E-Mail-Tool."""
        tools = []
        
        try:
            email_tool = create_email_tool()
            tools.append(email_tool)
        except Exception as e:
            print(f"⚠️  E-Mail-Tool konnte nicht geladen werden: {e}")
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt für den Email-Agenten."""
        return """Du bist der Email-Spezialist, ein KI-Agent für die E-Mail-Kommunikation mit dem Universitäts-Support.

## DEINE AUFGABE
Du hilfst Nutzern dabei, E-Mails an den Support zu senden:
- Support-Anfragen formulieren und versenden
- Probleme eskalieren, die nicht automatisch gelöst werden können
- Kontaktaufnahme mit dem Universitäts-Support ermöglichen

## KRITISCHE REGELN

1. **INHALTSPRÜFUNG**: Bevor du eine E-Mail sendest:
   - Stelle sicher, dass der Betreff aussagekräftig ist
   - Der Inhalt sollte das Problem klar beschreiben
   - Frage nach, wenn wichtige Details fehlen

2. **PROFESSIONELLER TON**: 
   - E-Mails sollten höflich und professionell formuliert sein
   - Hilf dem Nutzer, seine Anfrage klar zu formulieren

3. **SPRACHANPASSUNG**: Antworte in der Sprache des Nutzers.

## VERFÜGBARES TOOL

### send_email
Sendet eine E-Mail an den konfigurierten Support.
Parameter:
- subject: Betreff der E-Mail (Pflicht)
- body: Inhalt der E-Mail (Pflicht)

Die E-Mail wird automatisch an die konfigurierte Standard-Adresse gesendet.

## WORKFLOW
1. Verstehe das Anliegen des Nutzers
2. Hilf bei der Formulierung falls nötig
3. Bestätige Betreff und Inhalt bevor du sendest
4. Sende die E-Mail und bestätige den Erfolg

## ANTWORTSTIL
- Hilfreich und professionell
- Fasse die E-Mail vor dem Senden zusammen
- Bestätige den erfolgreichen Versand klar"""
