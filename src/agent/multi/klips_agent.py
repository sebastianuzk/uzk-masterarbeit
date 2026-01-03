"""
KLIPS Agent - Spezialisierter Agent für KLIPS2-Funktionalität.

Verantwortlich für alle KLIPS2-bezogenen Operationen:
- Account-Registrierung
- Studienbewerbung
- Passwort-Änderung
- Adress-Änderung
- Kursdetails-Abfrage
"""

from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from src.tools.klips import (
    create_klips2_register_tool,
    create_klips2_apply_tool,
    create_klips2_change_password_tool,
    create_klips2_get_course_details_tool,
    create_klips2_change_address_tool,
)

from .base_agent import BaseSpecializedAgent


class KlipsAgent(BaseSpecializedAgent):
    """
    Spezialisierter Agent für KLIPS2-Funktionalität.
    
    Dieser Agent bearbeitet alle Anfragen, die mit dem KLIPS2 
    Campus-Management-System der Universität zu Köln zusammenhängen.
    """
    
    def __init__(self, share_llm: Optional[ChatOllama] = None):
        """Initialisiere den KLIPS-Agenten."""
        super().__init__(share_llm)
        print(f"✅ {self.name} initialisiert mit {len(self.tools)} Tools")
    
    @property
    def name(self) -> str:
        return "KLIPS-Agent"
    
    @property
    def description(self) -> str:
        return (
            "Spezialisiert auf KLIPS2 Campus-Management-System: "
            "Account-Registrierung, Studienbewerbung, Passwort-Änderung, "
            "Adress-Änderung, Kursdetails und Lehrveranstaltungen. "
            "Nutze diesen Agenten für alle KLIPS2-bezogenen Anfragen."
        )
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle alle KLIPS2-Tools."""
        tools = []
        
        tool_creators = [
            ("KLIPS2-Registrierung", create_klips2_register_tool),
            ("KLIPS2-Bewerbung", create_klips2_apply_tool),
            ("KLIPS2-Passwort", create_klips2_change_password_tool),
            ("KLIPS2-Kursdetails", create_klips2_get_course_details_tool),
            ("KLIPS2-Adresse", create_klips2_change_address_tool),
        ]
        
        for name, creator in tool_creators:
            try:
                tool = creator()
                tools.append(tool)
            except Exception as e:
                print(f"⚠️  {name}-Tool konnte nicht geladen werden: {e}")
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt für den KLIPS-Agenten."""
        return """Du bist der KLIPS-Spezialist, ein KI-Agent für das KLIPS2 Campus-Management-System der Universität zu Köln.

## DEINE AUFGABE
Du bearbeitest alle Anfragen rund um KLIPS2:
- Neue Accounts registrieren (für Erstbenutzer)
- Studienbewerbungen einreichen
- Passwörter ändern
- Adressen aktualisieren
- Kursdetails und Lehrveranstaltungen abfragen

## KRITISCHE REGELN

1. **STOPP-REGEL**: Bevor du EIN Tool aufrufst, PRÜFE ob ALLE Pflichtparameter angegeben wurden.
   - Fehlt auch nur EIN Pflichtparameter → KEIN Tool-Aufruf, sondern NACHFRAGEN!
   - NIEMALS fehlende Daten erfinden oder mit Platzhaltern ausfüllen!

2. **VALIDIERUNGS-REGEL**: Prüfe das korrekte Format BEVOR du ein Tool aufrufst:
   - E-Mail: Muss @ und Punkt enthalten
   - Datum: Format TT.MM.JJJJ (z.B. 15.03.1999)

3. **SPRACHANPASSUNG**: Antworte in der Sprache des Nutzers.

## VERFÜGBARE TOOLS

### klips2_register
Neuen KLIPS2-Account erstellen.
Pflichtparameter: vorname, nachname, geschlecht, geburtsdatum, email, staatsangehoerigkeit

### klips2_apply_study
Studienbewerbung einreichen.
Pflichtparameter: username, password, semester, degree_type, study_program, entry_semester, study_form,
                  gender, birth_place, birth_country, nationality,
                  hzb_date, hzb_type, hzb_name, hzb_grade, hzb_school, hzb_country, hzb_place

### klips2_change_address
Adresse aktualisieren.
Pflichtparameter: username, password, street, zip_code, city

### klips2_change_password
Passwort ändern.
Pflichtparameter: username, password, new_password

### klips2_get_course_details
Kursdetails abrufen.
Pflichtparameter: course_id

## ANTWORTSTIL
- Präzise und hilfsbereit
- Bei fehlenden Parametern: Liste sie klar auf und frage nach
- Erfolge klar bestätigen
- Fehler verständlich erklären"""
