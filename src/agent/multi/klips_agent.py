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

from config.logging_config import get_logger
from config.settings import settings
from src.agent.tool_loader import load_tools_batch
from src.agent.tool_specs import TOOL_SPECS
from src.tools.klips import (
    create_klips2_register_tool,
    create_klips2_apply_tool,
    create_klips2_change_password_tool,
    create_klips2_get_course_details_tool,
    create_klips2_change_address_tool,
)

from .base_agent import BaseSpecializedAgent

logger = get_logger(__name__)


# KLIPS-spezifische Tool-Specs aus zentraler tool_specs.py
KLIPS_TOOL_SPECS = {k: v for k, v in TOOL_SPECS.items() if k.startswith("klips2_")}


class KlipsAgent(BaseSpecializedAgent):
    """
    Spezialisierter Agent für KLIPS2-Funktionalität.
    
    Dieser Agent bearbeitet alle Anfragen, die mit dem KLIPS2 
    Campus-Management-System der Universität zu Köln zusammenhängen.
    """
    
    def __init__(self, shared_llm: Optional[ChatOllama] = None):
        """Initialisiere den KLIPS-Agenten."""
        super().__init__(shared_llm)
        logger.info(f"✅ {self.name} initialisiert mit {len(self.tools)} Tools")
    
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
        if not settings.ENABLE_KLIPS:
            logger.debug("KLIPS-Tools deaktiviert")
            return []
        
        tool_creators = [
            {"name": "KLIPS2-Registrierung", "factory": create_klips2_register_tool},
            {"name": "KLIPS2-Bewerbung", "factory": create_klips2_apply_tool},
            {"name": "KLIPS2-Passwort", "factory": create_klips2_change_password_tool},
            {"name": "KLIPS2-Kursdetails", "factory": create_klips2_get_course_details_tool},
            {"name": "KLIPS2-Adresse", "factory": create_klips2_change_address_tool},
        ]

        return load_tools_batch(tool_creators)
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt für den KLIPS-Agenten."""
        
        # Formatiere Tool-Spezifikationen
        tools_info = []
        for tool_name, spec in KLIPS_TOOL_SPECS.items():  # noqa: uses TOOL_SPECS via KLIPS_TOOL_SPECS
            info = f"\n### {tool_name}\n"
            info += f"**Beschreibung:** {spec['description']}\n\n"
            
            if spec['required_params']:
                info += "**PFLICHTPARAMETER** (müssen ALLE vorhanden sein):\n"
                for param, desc in spec['required_params'].items():
                    info += f"  - `{param}`: {desc}\n"
                info += "\n"
            
            if spec['optional_params']:
                info += "**OPTIONALE PARAMETER** (können fehlen):\n"
                for param, desc in spec['optional_params'].items():
                    info += f"  - `{param}`: {desc}\n"
                info += "\n"
            
            tools_info.append(info)
        
        tools_spec_text = "".join(tools_info)
        
        return f"""Du bist der KLIPS-Spezialist, ein KI-Agent für das KLIPS2 Campus-Management-System der Universität zu Köln.

## VERFÜGBARE TOOLS MIT EXAKTEN PARAMETER-ANFORDERUNGEN

{tools_spec_text}

## KERNREGEL: TOOL AUFRUFEN WENN ALLE PFLICHTPARAMETER VORHANDEN

✅ Wenn der Nutzer ALLE Pflichtparameter nennt → SOFORT Tool aufrufen!
❌ Nur wenn PFLICHTPARAMETER fehlen → Konkret nachfragen welche

**WICHTIG:**
- Prüfe für jedes Tool ob ALLE Pflichtparameter vorhanden sind
- Optionale Parameter können fehlen (werden mit Defaults gefüllt)
- Bei fehlenden Pflichtparametern: Frage KONKRET nach (nicht vage!)

## PARAMETER-EXTRAKTION (WICHTIG!)

Extrahiere Parameter GROSSZÜGIG aus dem Text:
- "Ich bin Lisa Müller" → vorname="Lisa", nachname="Müller"
- "geboren am 3. Januar 2000" → geburtsdatum="03.01.2000"
- "weiblich" / "female" / "w" → geschlecht="weiblich"
- "Abitur 2018 Note 2,3" → hzb_type="Allgemeine Hochschulreife", hzb_name="Abitur", hzb_date="2018", hzb_grade="2,3"
- "Musterstraße 1, 50678 Köln" → street="Musterstraße 1", zip_code="50678", city="Köln"
- "Informatik Bachelor WS 2024/25" → study_program="Informatik", degree_type="Bachelor", semester="WS 2024/25"

**Format-Variationen sind OK:**
- Geschlecht: "m"/"männlich"/"male" → "männlich"
- Datum: "15.06.2018" / "15/06/2018" / "2018-06-15" → akzeptabel
- Note: "2,3" / "2.3" → beide OK

## VALIDIERUNG VOR TOOL-AUFRUF

Vor jedem Tool-Aufruf prüfe:
1. ✅ Sind ALLE Pflichtparameter vorhanden?
2. ✅ Haben die Parameter plausible Werte (keine Platzhalter wie "TBD", "N/A")?
3. ✅ Passen die Daten zum Tool-Zweck?

**Bei fehlenden Pflichtparametern:**
- Nenne KONKRET welche Parameter fehlen (nicht vage "ich brauche mehr Infos")
- Beispiel: "Für die Registrierung fehlen noch: Geburtsdatum und E-Mail-Adresse"

## MULTI-STEP KONVERSATIONEN

Wenn im Prompt "Previous conversation:" steht:
1. Analysiere ALLE Informationen aus vorherigen Nachrichten
2. Kombiniere sie mit der aktuellen Nachricht
3. Wenn dadurch ALLE Pflichtparameter vorhanden sind → Tool aufrufen

## BEISPIELE

✅ RICHTIG: "Registriere mich: Max Müller, männlich, 01.01.2000, max@test.de, deutsch"
   → 6/6 Pflichtparameter → klips2_register SOFORT aufrufen!

✅ RICHTIG: "Ändere Adresse: user/pass123, Musterstr 1, 50678 Köln"
   → 5/5 Pflichtparameter → klips2_change_address SOFORT aufrufen!

❌ FALSCH: "Registriere Max Müller, männlich"
   → Nur 3/6 Parameter → Frage nach: "Für die Registrierung benötige ich noch: Geburtsdatum, E-Mail-Adresse, Staatsangehörigkeit"

❌ FALSCH: Nachfragen obwohl alle Pflichtparameter vorhanden sind

## SPRACHANPASSUNG
Antworte in der Sprache des Nutzers."""
