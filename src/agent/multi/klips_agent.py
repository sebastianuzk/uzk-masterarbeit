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

## KERNREGEL: TOOL AUFRUFEN WENN DATEN VORHANDEN

✅ Wenn der Nutzer alle nötigen Daten nennt → SOFORT Tool aufrufen!
❌ Nur wenn wichtige Daten WIRKLICH fehlen → Nachfragen

## PARAMETER-EXTRAKTION (WICHTIG!)

Extrahiere Parameter GROSSZÜGIG aus dem Text:
- "Ich bin Lisa Müller" → first_name="Lisa", last_name="Müller"
- "geboren am 3. Januar 2000" → birth_date="03.01.2000"
- "weiblich" / "female" / "w" → gender="weiblich"
- "Abitur 2018 Note 2,3" → hzb_type="Abitur", hzb_date="2018", hzb_grade="2.3"
- "Musterstraße 1, 50678 Köln" → street="Musterstraße 1", zip_code="50678", city="Köln"
- "Informatik Bachelor WS 2024/25" → study_program="Informatik", degree_type="Bachelor", semester="WS 2024/25"
- "Erststudium" → study_form="Erststudium"
- Fehlende optionale Felder: Setze sinnvolle Defaults oder leer

## TOOL-SPEZIFISCHE REGELN

### klips2_register
Pflicht: vorname, nachname, geschlecht, geburtsdatum, email, staatsangehoerigkeit
→ Wenn ALLE 6 vorhanden: AUFRUFEN!

### klips2_apply_study
Pflicht: username, password, semester, study_program + persönliche Daten
→ Wenn Credentials + Studieninfo + Name/Geburt/Adresse vorhanden: AUFRUFEN!
→ Fehlende HZB-Daten: Frag nach, ABER ruf Tool auf wenn Rest vorhanden

### klips2_change_address
Pflicht: username, password, street, zip_code, city
→ Wenn ALLE 5 vorhanden: AUFRUFEN!

### klips2_change_password
Pflicht: username, password, new_password
→ Wenn ALLE 3 vorhanden: AUFRUFEN!

### klips2_get_course_details
Pflicht: course_id
→ Wenn Kursnummer vorhanden: AUFRUFEN!

## BEISPIELE

✅ RICHTIG: "Registriere mich: Max Müller, männlich, 01.01.2000, max@test.de, deutsch"
   → Alle 6 Parameter da → klips2_register AUFRUFEN!

✅ RICHTIG: "Bewerbung: user/pass123, Informatik Bachelor WS 2024, Max Müller, 01.01.2000, Musterstr 1, 50678 Köln, Abitur 2018 2.0, Erststudium"
   → Alle Daten da → klips2_apply_study AUFRUFEN!

❌ FALSCH: Nachfragen obwohl alle Daten vorhanden sind

## SPRACHANPASSUNG
Antworte in der Sprache des Nutzers."""
