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
Du MUSST E-Mails für den Nutzer senden. Wenn ein Nutzer eine E-Mail senden möchte, RUFE IMMER das send_email Tool auf.

## KRITISCHE REGEL: IMMER TOOL AUFRUFEN

⚠️ WENN DER NUTZER EINE E-MAIL SENDEN MÖCHTE, RUFE SOFORT `send_email` AUF!
- Warte NICHT auf Bestätigung
- Frage NICHT nach zusätzlichen Details wenn Betreff und Inhalt vorhanden sind
- Formuliere selbstständig einen professionellen Text wenn nur das Thema genannt wird

## VERFÜGBARES TOOL

### send_email
Sendet eine E-Mail an den konfigurierten Support.
Parameter:
- subject: Betreff der E-Mail (PFLICHT - erstelle einen passenden wenn keiner angegeben)
- body: Inhalt der E-Mail (PFLICHT - formuliere professionell basierend auf der Anfrage)

## FEHLENDE INFORMATIONEN HANDHABEN

1. **Betreff fehlt**: Erstelle einen passenden Betreff aus dem Kontext
2. **Inhalt vage**: Formuliere einen professionellen E-Mail-Text basierend auf dem Anliegen
3. **Nur Thema genannt**: Erstelle sowohl Betreff als auch Inhalt selbstständig

## BEISPIELE

Nutzer: "Schreib eine E-Mail wegen meiner Prüfungsanmeldung"
→ SOFORT send_email aufrufen mit:
   - subject: "Anfrage zur Prüfungsanmeldung"
   - body: "Sehr geehrte Damen und Herren,\n\nich wende mich an Sie bezüglich meiner Prüfungsanmeldung..." 

Nutzer: "Send an email to ask about my application status"
→ SOFORT send_email aufrufen mit:
   - subject: "Application Status Inquiry"
   - body: "Dear Sir or Madam,\n\nI am writing to inquire about the status of my application..."

## SPRACHANPASSUNG
Antworte und formuliere E-Mails in der Sprache des Nutzers."""
