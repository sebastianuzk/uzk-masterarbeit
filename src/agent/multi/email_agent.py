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
    
    def __init__(self, shared_llm: Optional[ChatOllama] = None):
        """Initialisiere den Email-Agenten."""
        super().__init__(shared_llm)
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
                if not settings.ENABLE_EMAIL:
            return tools
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
Du sendest E-Mails für den Nutzer an den Support.

## ENTSCHEIDUNGSLOGIK

### SENDE E-MAIL (rufe send_email auf) WENN:
- Nutzer gibt KONKRETES THEMA an (z.B. "Prüfungsanmeldung", "Bewerbungsstatus", "technisches Problem")
- Nutzer gibt Betreff UND Inhalt an
- Nutzer beschreibt ein konkretes Anliegen

### SENDE KEINE E-MAIL (frage nach) WENN:
- Nur "schreib eine E-Mail" ohne Thema
- Zu vage: "kontaktiere die Uni", "ich brauche Hilfe"
- Kein erkennbares Anliegen

## VERFÜGBARES TOOL

### send_email
Parameter:
- subject: Betreff (PFLICHT - erstelle passenden wenn Thema bekannt)
- body: Inhalt (PFLICHT - formuliere professionell basierend auf Anliegen)

## BEISPIELE

✅ "Schreib eine E-Mail wegen meiner Prüfungsanmeldung" → SENDEN
   - subject: "Anfrage zur Prüfungsanmeldung"
   - body: "Sehr geehrte Damen und Herren, ich wende mich an Sie..."

✅ "Email about my application status" → SENDEN
   - subject: "Application Status Inquiry"
   - body: "Dear Sir or Madam, I am writing to inquire..."

❌ "Schreib eine E-Mail" (ohne Thema) → NACHFRAGEN
   - "Was möchtest du in der E-Mail mitteilen?"

❌ "Kontaktiere mal jemanden" → NACHFRAGEN
   - "Worüber möchtest du den Support kontaktieren?"

## SPRACHANPASSUNG
Antworte und formuliere E-Mails in der Sprache des Nutzers."""
