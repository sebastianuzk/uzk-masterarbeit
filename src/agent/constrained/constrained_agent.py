"""
Constrained Agent - Agent mit Schema-beschränkter Generierung.

Dieser Agent verwendet strukturierte Output-Generierung um sicherzustellen,
dass Tool-Calls immer syntaktisch korrekt sind:

1. Verwendet Ollama's JSON-Modus für garantiert valides JSON
2. Definiert explizite Pydantic-Schemas für jedes Tool
3. Validiert Ausgaben gegen Schemas vor Ausführung
4. Repariert automatisch kleine Formatfehler

Unterschied zu Confirmation Agent:
- Confirmation: Prüft NACH Generierung ob Werte semantisch korrekt sind
- Constrained: Erzwingt WÄHREND Generierung syntaktisch korrekte Struktur

Basierend auf: LMQL (Beurer-Kellner et al., 2022) - Constrained Decoding
"""

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, ValidationError, field_validator
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool

from config.logging_config import get_logger
from config.settings import settings
from src.agent.agent_config import setup_langsmith_tracing, get_recursion_limit
from src.agent.llm_factory import create_llm, create_json_llm
from src.agent.tool_loader import load_tool_safely, load_klips_tools
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.email_tool import create_email_tool
from src.tools.klips import (
    create_klips2_register_tool,
    create_klips2_apply_tool,
    create_klips2_change_password_tool,
    create_klips2_get_course_details_tool,
    create_klips2_change_address_tool
)
from src.tools.rag_tool import create_university_rag_tool
from src.tools.web_scraper_tool import create_web_scraper_tool


logger = get_logger(__name__)


# ============================================================================
# PYDANTIC SCHEMAS FÜR TOOL-CALLS
# ============================================================================

class ToolDecision(BaseModel):
    """Entscheidung des Agenten: Tool aufrufen oder direkt antworten."""
    action: str = Field(
        description="'tool' wenn ein Tool aufgerufen werden soll, 'respond' für direkte Antwort, 'insufficient_data' wenn Daten fehlen"
    )
    tool_names: Optional[List[str]] = Field(
        default=None,
        description="Liste der Tool-Namen (nur wenn action='tool'). Kann ein oder mehrere Tools enthalten."
    )
    reason: Optional[str] = Field(
        default=None,
        description="Kurze Begründung für die Entscheidung"
    )
    missing_fields: Optional[List[str]] = Field(
        default=None,
        description="Liste der fehlenden Pflichtfelder (nur wenn action='insufficient_data')"
    )

    @field_validator('action')
    @classmethod
    def validate_action(cls, v):
        if v not in ('tool', 'respond', 'insufficient_data'):
            raise ValueError("action must be 'tool', 'respond', or 'insufficient_data'")
        return v
    
    @field_validator('tool_names')
    @classmethod
    def validate_tool_names(cls, v, info):
        """Stelle sicher, dass tool_names bei action='tool' vorhanden ist."""
        action = info.data.get('action')
        if action == 'tool' and not v:
            raise ValueError("tool_names muss gesetzt sein wenn action='tool'")
        # Bei insufficient_data ist tool_names optional (zeigt an welches Tool gemeint war)
        return v


class RegisterToolCall(BaseModel):
    """Schema für klips2_register Tool-Aufruf."""
    vorname: str = Field(description="Vorname der Person")
    nachname: str = Field(description="Nachname der Person")
    geschlecht: str = Field(description="männlich, weiblich oder divers")
    geburtsdatum: str = Field(description="Geburtsdatum im Format TT.MM.JJJJ")
    email: str = Field(description="E-Mail-Adresse mit @")
    staatsangehoerigkeit: str = Field(description="Staatsangehörigkeit")
    geburtsname: Optional[str] = Field(default=None, description="Geburtsname falls abweichend")
    sprache: str = Field(default="Deutsch", description="Deutsch oder Englisch")

    @field_validator('vorname', 'nachname')
    @classmethod
    def validate_not_empty(cls, v, info):
        """Verhindere leere Strings für kritische Felder."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} darf nicht leer sein")
        return v.strip()

    @field_validator('geburtsdatum')
    @classmethod
    def validate_date(cls, v):
        # Erlaube flexible Formate, normalisiere zu TT.MM.JJJJ
        v = v.strip()
        # Versuche verschiedene Formate
        patterns = [
            (r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', '{:02d}.{:02d}.{}'),
            (r'^(\d{1,2})/(\d{1,2})/(\d{4})$', '{:02d}.{:02d}.{}'),
            (r'^(\d{4})-(\d{1,2})-(\d{1,2})$', '{:02d}.{:02d}.{}'),  # ISO
        ]
        for pattern, fmt in patterns:
            match = re.match(pattern, v)
            if match:
                groups = match.groups()
                if pattern.startswith(r'^(\d{4})'):  # ISO format
                    return fmt.format(int(groups[2]), int(groups[1]), groups[0])
                return fmt.format(int(groups[0]), int(groups[1]), groups[2])
        return v  # Return as-is, let tool handle validation

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError("E-Mail muss @ enthalten")
        return v.strip()

    @field_validator('geschlecht')
    @classmethod
    def normalize_gender(cls, v):
        v_lower = v.lower().strip()
        if v_lower in ('m', 'male', 'männlich', 'mann'):
            return 'männlich'
        if v_lower in ('f', 'w', 'female', 'weiblich', 'frau'):
            return 'weiblich'
        if v_lower in ('d', 'diverse', 'divers'):
            return 'divers'
        return v


class ApplyToolCall(BaseModel):
    """Schema für klips2_apply_study Tool-Aufruf."""
    username: str = Field(description="KLIPS2-Benutzername")
    password: str = Field(description="KLIPS2-Passwort")
    semester: str = Field(description="Zielsemester (z.B. Wintersemester 2024/25, WS 2024)")
    degree_type: str = Field(description="Bachelor, Master oder Promotionsstudium")
    study_program: str = Field(description="Name des Studiengangs (z.B. Informatik, Medizin)")
    entry_semester: str = Field(default="1", description="Fachsemester (Standard: 1)")
    study_form: str = Field(description="Studienform: Erststudium oder Zweitstudium")
    gender: str = Field(description="Geschlecht (männlich, weiblich, divers)")
    birth_place: str = Field(description="Geburtsort")
    birth_country: Optional[str] = Field(default="Deutschland", description="Geburtsland (Standard: Deutschland)")
    nationality: str = Field(description="Staatsangehörigkeit")
    hzb_date: str = Field(description="Datum der HZB (TT.MM.JJJJ, z.B. 15.06.2018)")
    hzb_type: str = Field(description="Art der HZB (z.B. Allgemeine Hochschulreife, Fachhochschulreife)")
    hzb_name: Optional[str] = Field(default="Abitur", description="Bezeichnung des Zeugnisses (Standard: Abitur)")
    hzb_grade: str = Field(description="Note der HZB (z.B. 2,3 oder 2.3)")
    hzb_school: Optional[str] = Field(default="Gymnasium", description="Name der Schule (Standard: Gymnasium)")
    hzb_country: Optional[str] = Field(default="Deutschland", description="Land der HZB (Standard: Deutschland)")
    hzb_place: str = Field(description="Ort/Kreis der HZB")
    # Optional
    street: Optional[str] = Field(default=None, description="Straße und Hausnummer")
    zip_code: Optional[str] = Field(default=None, description="Postleitzahl")
    city: Optional[str] = Field(default=None, description="Stadt")
    country: Optional[str] = Field(default="Deutschland", description="Land (Standard: Deutschland)")
    phone: Optional[str] = Field(default=None, description="Telefonnummer")
    prev_uni: Optional[str] = Field(default=None, description="Vorherige Hochschule (PFLICHT bei Zweitstudium)")
    prev_program: Optional[str] = Field(default=None, description="Vorheriger Studiengang (PFLICHT bei Zweitstudium)")
    prev_degree: Optional[str] = Field(default=None, description="Angestrebter/erreichter Abschluss (optional bei Zweitstudium)")
    prev_semesters: Optional[str] = Field(default=None, description="Anzahl Semester an vorheriger Hochschule (PFLICHT bei Zweitstudium)")
    validate_only: bool = Field(default=False)
    delete_existing_hzb: bool = Field(default=False, description="Vorhandene HZB-Einträge löschen. NUR wenn explizit gewünscht!")
    delete_existing_vorbildung: bool = Field(default=False, description="Vorhandene Vorbildungs-Einträge löschen. NUR wenn explizit gewünscht!")

    @field_validator('username', 'password', 'nationality')
    @classmethod
    def validate_not_empty(cls, v, info):
        """Verhindere leere Strings für kritische Felder."""
        if not v or not v.strip():
            raise ValueError(f"{info.field_name} darf nicht leer sein")
        return v.strip()

    @field_validator('gender')
    @classmethod
    def normalize_gender(cls, v):
        v_lower = v.lower().strip()
        if v_lower in ('m', 'male', 'männlich', 'mann'):
            return 'männlich'
        if v_lower in ('f', 'w', 'female', 'weiblich', 'frau'):
            return 'weiblich'
        if v_lower in ('d', 'diverse', 'divers'):
            return 'divers'
        return v

    @field_validator('study_form')
    @classmethod
    def normalize_study_form(cls, v):
        v_lower = v.lower().strip()
        if v_lower in ('erststudium', 'first', 'first-time', 'erstmals', 'first study', 'erster'):
            return 'Erststudium'
        if v_lower in ('zweitstudium', 'second', 'second degree', 'zweites', 'zweites studium'):
            return 'Zweitstudium'
        # Capitalize first letter if recognized prefix
        if v.strip():
            return v.strip().capitalize() if v.strip()[0].islower() else v.strip()
        return v


class ChangeAddressToolCall(BaseModel):
    """Schema für klips2_change_address Tool-Aufruf."""
    username: str = Field(description="KLIPS2-Benutzername")
    password: str = Field(description="KLIPS2-Passwort")
    street: str = Field(description="Straße und Hausnummer")
    zip_code: str = Field(description="Postleitzahl")
    city: str = Field(description="Stadt")
    country: str = Field(default="Deutschland", description="Land")

    @field_validator('zip_code')
    @classmethod
    def validate_zip(cls, v):
        v = v.strip()
        # Erlaube internationale Postleitzahlen/ZIP-Codes:
        # - 2 bis 10 Zeichen
        # - Buchstaben, Ziffern, Leerzeichen oder Bindestrich
        # Beispiele: "50678" (DE), "1010" (AT), "SW1A 1AA" (UK), "K1A 0B1" (CA)
        if not re.match(r'^[A-Za-z0-9 -]{2,10}$', v):
            raise ValueError("Postleitzahl/ZIP muss 2-10 Zeichen (Buchstaben, Ziffern, Leerzeichen oder '-') enthalten")
        return v


class ChangePasswordToolCall(BaseModel):
    """Schema für klips2_change_password Tool-Aufruf."""
    username: str = Field(description="Benutzername")
    password: str = Field(description="Aktuelles Passwort")
    new_password: str = Field(description="Neues Passwort")


class CourseDetailsToolCall(BaseModel):
    """Schema für klips2_get_course_details Tool-Aufruf."""
    course_id: str = Field(description="Kursnummer")
    semester: Optional[str] = Field(default=None, description="Semester")


class SearchToolCall(BaseModel):
    """Schema für Suchanfragen (RAG, DuckDuckGo)."""
    query: str = Field(description="Suchanfrage")

class WebScraperToolCall(BaseModel):
    """Schema für web_scraper Tool-Aufruf."""
    url: str = Field(description="URL der Webseite")

    @field_validator('url')
    @classmethod
    def validate_url(cls, v):
        v = v.strip()
        if not v.startswith(('http://', 'https://')):
            v = 'https://' + v
        return v


class EmailToolCall(BaseModel):
    """Schema für send_email Tool-Aufruf."""
    subject: str = Field(description="Betreff der E-Mail")
    body: str = Field(description="Nachrichteninhalt")


class DirectResponse(BaseModel):
    """Schema für direkte Antwort ohne Tool-Aufruf."""
    response: str = Field(description="Antwort an den Nutzer")
    missing_info: Optional[List[str]] = Field(
        default=None,
        description="Liste fehlender Informationen falls nachgefragt werden muss"
    )


# Mapping Tool-Name -> Schema
TOOL_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "klips2_register": RegisterToolCall,
    "klips2_apply_study": ApplyToolCall,
    "klips2_change_address": ChangeAddressToolCall,
    "klips2_change_password": ChangePasswordToolCall,
    "klips2_get_course_details": CourseDetailsToolCall,
    "university_knowledge_search": SearchToolCall,
    "duckduckgo_search": SearchToolCall,
    "web_scraper": WebScraperToolCall,
    "send_email": EmailToolCall,
}


class ConstrainedAgent:
    """
    Agent mit Schema-beschränkter Generierung.
    
    Verwendet einen zweistufigen Prozess:
    1. Entscheidung: Tool oder direkte Antwort? (mit ToolDecision Schema)
    2. Ausführung: Tool-Argumente oder Antwort generieren (mit entsprechendem Schema)
    
    Vorteile:
    - Garantiert syntaktisch korrektes JSON
    - Keine Tippfehler in Feldnamen
    - Automatische Typ-Konvertierung
    - Automatische Format-Normalisierung (Datum, Geschlecht, etc.)
    """
    
    def __init__(self):
        """Initialisiere den Constrained Agent."""
        settings.validate()
        
        # LangSmith Tracing
        setup_langsmith_tracing()
        
        logger.info(f"📐 Initialisiere Constrained Agent mit Modell: {settings.OLLAMA_MODEL}")
        
        # LLM für Entscheidungen (ohne JSON-Mode für natürliche Antworten)
        self.llm = create_llm()
        
        # LLM mit JSON-Mode für strukturierte Ausgaben
        self.llm_json = create_json_llm()
        
        # Tools initialisieren
        self.tools = self._create_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # System message für Kompatibilität mit Evaluation Harness
        self.system_message = SystemMessage(content=self._get_system_prompt())
        
        # Recursion Limit from centralized config
        self.recursion_limit = get_recursion_limit("constrained")
        
        # Memory
        self.memory: List[Union[HumanMessage, AIMessage]] = []
        
        # Tracking
        self.schema_validations = 0
        self.schema_repairs = 0
        self.schema_failures = 0
        
        # Conversation Trace für Debugging/Evaluation
        self.conversation_trace = []
    
    def _get_system_prompt(self) -> str:
        """Kompakter System-Prompt für Constrained Agent."""
        # Erstelle Set der verfügbaren Tool-Namen
        available_tool_names = {tool.name for tool in self.tools}
        
        # Dynamische Tool-Kategorien
        tool_categories = []
        if any(name.startswith("klips2_") for name in available_tool_names):
            tool_categories.append("KLIPS2-Aktionen")
        if "university_knowledge_search" in available_tool_names:
            tool_categories.append("Uni-Wissensfragen")
        if "duckduckgo_search" in available_tool_names:
            tool_categories.append("Internet-Suche")
        if "web_scraper" in available_tool_names:
            tool_categories.append("URLs")
        if "send_email" in available_tool_names:
            tool_categories.append("E-Mails")
        
        tool_categories_text = ", ".join(tool_categories) if tool_categories else "Verfügbare Tools je nach Anfrage"
        
        # Dynamische Tool-Liste mit Pflichtparametern
        klips_tools = []
        if "klips2_register" in available_tool_names:
            klips_tools.append("- klips2_register: vorname, nachname, geschlecht, geburtsdatum, email, staatsangehoerigkeit")
        if "klips2_apply_study" in available_tool_names:
            klips_tools.append("- klips2_apply_study: username, password, semester, degree_type, study_program, study_form, gender, birth_place, nationality, hzb_date, hzb_type, hzb_grade, hzb_place")
        if "klips2_change_address" in available_tool_names:
            klips_tools.append("- klips2_change_address: username, password, street, zip_code, city")
        if "klips2_change_password" in available_tool_names:
            klips_tools.append("- klips2_change_password: username, password, new_password")
        if "klips2_get_course_details" in available_tool_names:
            klips_tools.append("- klips2_get_course_details: course_id")
        
        search_tools = []
        if "duckduckgo_search" in available_tool_names:
            search_tools.append("- duckduckgo_search: query (bei \"Search for\", \"Suche im Internet\", \"online\")")
        if "university_knowledge_search" in available_tool_names:
            search_tools.append("- university_knowledge_search: query (bei Uni-Fragen ohne Internet-Keywords)")
        if "web_scraper" in available_tool_names:
            search_tools.append("- web_scraper: url (bei URLs)")
        
        comm_tools = []
        if "send_email" in available_tool_names:
            comm_tools.append("- send_email: subject, body")
        
        # Baue Tool-Sektionen zusammen
        tools_section = ""
        if klips_tools:
            tools_section += "\n### KLIPS2-Aktionen:\n" + "\n".join(klips_tools) + "\n"
        if search_tools:
            tools_section += "\n### Suche & Wissen:\n" + "\n".join(search_tools) + "\n"
        if comm_tools:
            tools_section += "\n### Kommunikation:\n" + "\n".join(comm_tools)
        
        # Dynamic multi-tool examples based on available tools
        multi_tool_examples = []
        if len(available_tool_names) >= 2:
            if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
                multi_tool_examples.append('- "Suche X **und dann** hole Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]')
            if "klips2_get_course_details" in available_tool_names and "send_email" in available_tool_names:
                multi_tool_examples.append('- "Hole Kursdetails **und schicke** E-Mail" → BEIDE Tools aufrufen: [klips2_get_course_details, send_email]')
            if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
                multi_tool_examples.append('- "Recherchiere X, **dann** Details zu Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]')
        
        # Build multi-tool section
        multi_tool_section = ""
        if multi_tool_examples:
            multi_tool_section = f"""## MULTI-TOOL-ANFRAGEN (WICHTIG!)

**Wenn der User MEHRERE Aktionen in EINER Nachricht fordert:**
{chr(10).join(multi_tool_examples)}

Signalwörter für Multi-Tool:
- "und dann", "danach", "anschließend", "then"
- "und schicke", "und sende", "and send"
- Mehrere Aktionsverben in einer Anfrage

**REGEL:** Bei Multi-Tool-Anfragen → ALLE relevanten Tools aufrufen!

"""
        
        return f"""Du bist ein KI-Assistent für KLIPS 2.0, das Campus-Management-System der Universität zu Köln.

## WANN EIN TOOL AUFRUFEN?

✅ Tool aufrufen bei: {tool_categories_text}
❌ KEIN Tool bei: Begrüßungen, Fragen über dich, Rechenaufgaben, allgemeine Fragen

## REGELN

1. Wenn Tool passend UND alle Pflichtdaten vorhanden → Tool aufrufen
2. Wenn Tool passend ABER Daten fehlen → Nachfragen (KEIN Tool-Aufruf)
3. Wenn KEIN Tool passend → Direkt antworten

## TOOLS (Pflichtparameter)
{tools_section}

## MULTI-STEP KONVERSATIONEN

Wenn im Prompt "Previous conversation:" steht:
1. Analysiere ALLE Informationen aus vorherigen Nachrichten
2. Kombiniere sie mit der aktuellen Nachricht
3. Wenn dadurch ALLE Pflichtparameter vorhanden sind → Tool aufrufen

{multi_tool_section}Antworte in der Sprache des Nutzers."""
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools."""
        tools = []
        
        if settings.ENABLE_WEB_SCRAPER:
            web_tool = load_tool_safely(create_web_scraper_tool, "Web-Scraper")
            if web_tool:
                tools.append(web_tool)
        
        if settings.ENABLE_DUCKDUCKGO:
            ddg_tool = load_tool_safely(create_duckduckgo_tool, "DuckDuckGo")
            if ddg_tool:
                tools.append(ddg_tool)
        
        rag_tool = load_tool_safely(create_university_rag_tool, "Universitäts-RAG")
        if rag_tool:
            tools.append(rag_tool)
        
        if settings.ENABLE_EMAIL:
            email_tool = load_tool_safely(create_email_tool, "E-Mail")
            if email_tool:
                tools.append(email_tool)
        
        if settings.ENABLE_KLIPS:
            klips_tools = load_klips_tools()
            tools.extend(klips_tools)
        
        return tools
    
    def _get_decision_prompt(self) -> str:
        """Prompt für die Tool-Entscheidung mit expliziten Anforderungen."""
        # Tool-spezifische Pflichtfelder
        tool_requirements = {
            "klips2_register": ["vorname", "nachname", "geschlecht", "geburtsdatum", "email", "staatsangehoerigkeit"],
            "klips2_apply_study": ["username", "password", "semester", "degree_type", "study_program", "study_form", "gender", "birth_place", "nationality", "hzb_date", "hzb_type", "hzb_grade", "hzb_place"],
            "klips2_change_password": ["username", "password", "new_password"],
            "klips2_change_address": ["username", "password", "street", "zip_code", "city"],
            "klips2_get_course_details": ["course_id"],
            "send_email": ["subject", "body"],  # Both required - agent must not invent them if absent
            "duckduckgo_search": ["query"],
            "university_knowledge_search": ["query"],
            "web_scraper": ["url"]
        }
        
        # Erstelle Set der verfügbaren Tool-Namen basierend auf self.tools
        available_tool_names = {tool.name for tool in self.tools}
        
        # Nur Tools auflisten, die auch tatsächlich verfügbar sind
        tool_list = []
        for name, schema in TOOL_SCHEMAS.items():
            if name not in available_tool_names:
                continue  # Tool ist deaktiviert, überspringe es
            desc = schema.__doc__ or 'Keine Beschreibung'
            required = tool_requirements.get(name, [])
            req_str = ", ".join(required) if required else "keine"
            tool_list.append(f"- {name}: {desc}\n  PFLICHT: {req_str}")
        
        tools_str = "\n".join(tool_list)
        
        # Build dynamic tool trigger sections based on available tools
        tool_trigger_sections = []
        
        if "klips2_register" in available_tool_names or "klips2_apply_study" in available_tool_names or \
           "klips2_change_password" in available_tool_names or "klips2_change_address" in available_tool_names:
            klips_examples = []
            if "klips2_register" in available_tool_names:
                klips_examples.append('- "Registriere mich" → klips2_register')
            if "klips2_apply_study" in available_tool_names:
                klips_examples.append('- "Bewerbe mich für [Studiengang]" → klips2_apply_study')
            if "klips2_change_password" in available_tool_names:
                klips_examples.append('- "Ändere mein Passwort" → klips2_change_password')
            if "klips2_change_address" in available_tool_names:
                klips_examples.append('- "Ändere meine Adresse" → klips2_change_address')
            
            tool_trigger_sections.append("**KLIPS2-Aktionen (Tool aufrufen):**\n" + "\n".join(klips_examples))
        
        if "klips2_get_course_details" in available_tool_names:
            tool_trigger_sections.append('''**KURS-ABFRAGEN (Tool aufrufen):**
- "Mehr über Kurs [X] erfahren" → klips2_get_course_details
- "Wann findet Kurs [X] statt?" → klips2_get_course_details
- "Wer hält Kurs [X]?" → klips2_get_course_details
- "Details zu Kurs [X]" → klips2_get_course_details''')
        
        # Multi-tool examples (only if we have 2+ tools available)
        if len(available_tool_names) >= 2:
            multi_tool_examples = []
            if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
                multi_tool_examples.append('1. "Suche im Internet nach Kurs X **und** hole dann Details aus KLIPS"\n   → ["duckduckgo_search", "klips2_get_course_details"]')
            if "klips2_get_course_details" in available_tool_names and "send_email" in available_tool_names:
                multi_tool_examples.append('2. "Hole Kursdetails **und** sende E-Mail"\n   → ["klips2_get_course_details", "send_email"]')
            if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
                multi_tool_examples.append('3. "Recherchiere X, **dann** Details zu Kurs Y"\n   → ["duckduckgo_search", "klips2_get_course_details"]')
            
            if multi_tool_examples:
                tool_trigger_sections.append(f'''**MULTI-TOOL-ANFRAGEN (MEHRERE TOOLS - WICHTIG!):**

PRÜFE ZUERST: Fordert der User MEHRERE Aktionen nacheinander?

Signalwörter für Multi-Tool (= MEHRERE Tools erforderlich):
- "und dann", "danach", "anschließend"
- "and then", "then", "after that"
- Mehrere Verben in EINER Anfrage: "Suche... hole...", "Search... get...", "Schau... schicke..."

BEISPIELE für Multi-Tool (= tool_names muss LISTE mit 2+ Tools sein):
{chr(10).join(multi_tool_examples)}

WICHTIG: 
- Reihenfolge der Tools beachten (chronologisch wie in Anfrage)!''')
        
        if "university_knowledge_search" in available_tool_names or "duckduckgo_search" in available_tool_names:
            search_rules = []
            if "duckduckgo_search" in available_tool_names:
                search_rules.append('''1. **IMMER duckduckgo_search bei:**
   - Expliziten Such-Keywords: "Search", "Suche", "Such", "Find", "Finde", "Look up" mit Suchbegriff
   - "Search for [X]" → duckduckgo_search
   - "Suche nach [X]" → duckduckgo_search
   - "Google [X]" → duckduckgo_search''')
            
            if "university_knowledge_search" in available_tool_names:
                search_rules.append('''2. **NUR university_knowledge_search bei:**
   - Direkten Fragen OHNE Such-Keywords:
     * "Wie bewerbe ich mich für Master?" (Frage, kein Such-Keyword)
     * "Welche Fristen gibt es?" (Frage, kein Such-Keyword)
     * "Was kostet das Studium?" (Frage, kein Such-Keyword)''')
            
            if search_rules:
                tool_trigger_sections.append("**WISSENS-SUCHE (Tool aufrufen):**\n\nWICHTIG - Entscheidungslogik für Suchen:\n\n" + "\n\n".join(search_rules))
        
        if "send_email" in available_tool_names:
            tool_trigger_sections.append('''**E-MAIL (Tool aufrufen, NUR wenn Betreff UND Inhalt vorhanden):**
- "Sende eine E-Mail" → send_email
- "Schicke eine Mail" → send_email
- "Verfasse eine E-Mail" → send_email
- "Schreibe eine E-Mail" → send_email
- "Sende eine Nachricht" → send_email
- "E-Mail versenden" → send_email
- "send an email" / "send email" → send_email
- "Schicke eine Nachfolge-E-Mail" → send_email

WICHTIG: Nur aufrufen wenn BEIDE Pflichtfelder vorhanden:
  ✓ subject (Betreff - MUSS explizit genannt werden)
  ✓ body (Inhalt - MUSS erkennbarer Nachrichtentext vorhanden sein)
  ✗ NUR Betreff ohne Inhalt → insufficient_data
  ✗ NUR vager Auftrag ohne Betreff → insufficient_data''')
        
        tool_trigger_text = "\n\n".join(tool_trigger_sections) if tool_trigger_sections else "Keine Tool-spezifischen Trigger definiert."
        
        # Build completeness rules section dynamically
        completeness_rules = []
        if "klips2_register" in available_tool_names:
            completeness_rules.append("  - klips2_register: Vorname UND Nachname UND Email UND Geburtsdatum UND Geschlecht UND Staatsangehörigkeit")
        if "klips2_apply_study" in available_tool_names:
            completeness_rules.append("  - klips2_apply_study: username UND password UND semester UND degree_type UND study_program UND study_form (Erststudium/Zweitstudium) UND gender UND birth_place UND nationality UND hzb_date UND hzb_type UND hzb_grade UND hzb_place")
            completeness_rules.append("  - Wenn study_form='Zweitstudium': ZUSÄTZLICH prev_uni UND prev_program UND prev_semesters erforderlich")
        if "send_email" in available_tool_names:
            completeness_rules.append("  - send_email: subject UND body (beide Felder müssen im Text vorhanden sein)")
        completeness_text = "\n".join(completeness_rules) if completeness_rules else "  (Keine tool-spezifischen Regeln)"
        
        # JSON example only if both tools are available
        if "duckduckgo_search" in available_tool_names and "klips2_get_course_details" in available_tool_names:
            json_example = '\nBeispiel: "Suche X und hole dann Y" → {{"action": "tool", "tool_names": ["duckduckgo_search", "klips2_get_course_details"], "reason": "Multi-Tool: Suche + KLIPS"}}'
        else:
            json_example = ""
        
        return f"""Du bist ein KI-Assistent für KLIPS 2.0 der Universität zu Köln.

Analysiere die Nutzeranfrage und entscheide:
1. Welches Tool benötigt wird (oder keins)
2. Ob die wichtigsten Pflichtfelder vorhanden sind

VERFÜGBARE TOOLS mit Pflichtfeldern:
{tools_str}

ENTSCHEIDUNGSLOGIK:

## 1. TOOL-TRIGGER: Wann welches Tool aufrufen?

{tool_trigger_text}

**KEINE TOOLS (respond):**
- Begrüßungen: "Hallo!", "Wie geht's?", "Guten Tag", "Hi"
- System-Fragen: "Was kannst du?", "Welche Funktionen hast du?", "Hilfe"
- Einfache Berechnungen: "Was ist 2+2?", "Rechne 10 * 5"
- Übersetzungen: "Übersetze X nach Y", "Was heißt X auf Englisch?"
- Allgemeine Wissensfragen ohne Uni-Bezug: "Was ist ein Bachelor?" (generisch, nicht Uni-spezifisch)
- Small Talk: "Wie ist das Wetter?", "Erzähl einen Witz"


## 2. PFLICHTFELD-PRÜFUNG (STRENG!)

PRÜFREGEL: Gehe Pflichtfeld für Pflichtfeld durch und notiere:
  ✓ "vorname: [Wert aus Text]"
  ✓ "nachname: [Wert aus Text]"  
  ✓ "email: [Wert aus Text]"
  ... etc.

Wenn Tool identifiziert:
- Prüfe JEDES EINZELNE Pflichtfeld für das gewählte Tool
- Ist das Feld EXPLIZIT im Text genannt? (Nicht raten/ableiten!)
- Sind die Werte konkret und vollständig?

**KRITISCHE REGELN:**

NAMES/IDENTITÄT (STRENGSTE PRÜFUNG!):
  ✗ "Login: kim@uni-koeln.de" → KEINE NAMEN! → insufficient_data (fehlen: vorname, nachname)
  ✗ "Divers, 01.01.2000, Berlin" → KEINE NAMEN! → insufficient_data (fehlen: vorname, nachname)
  ✗ "Name: Thomas Klein" → UNKLAR ob Vor-/Nachname → insufficient_data (fehlt Trennung)
  ✓ "Ich heiße Peter Bauer" → OK: "Peter" = vorname, "Bauer" = nachname
  ✓ "Vorname: Lisa, Nachname: Müller" → OK: Explizit getrennt
  
  REGEL: Vorname UND Nachname müssen BEIDE EXPLIZIT identifizierbar sein!

KLIPS-LOGIN (username/password):
  ✗ "Bewerbung Informatik Bachelor" → KEINE Zugangsdaten! → insufficient_data (fehlen: username, password)
  ✗ "Erststudium, 1. Semester" → KEINE Zugangsdaten! → insufficient_data (fehlen: username, password)
  ✓ "Login: max@uni-koeln.de / pass123" → OK: username + password vorhanden

PERSÖNLICHE DATEN (gender, birth_place, nationality):
  ✗ "Bewerbung Informatik Bachelor" → NICHTS über Person! → insufficient_data (fehlen: gender, birth_place, nationality)
  ✓ "männlich, geboren 15.03.1999 in Köln" → OK: gender + birth_place vorhanden
  ✓ "Staatsangehörigkeit: deutsch" → OK: nationality vorhanden

HZB-DATEN (hzb_date, hzb_type, hzb_grade, hzb_place):
  ✗ "Abitur 2,3 vom 01.06.2018" → hzb_place fehlt! → insufficient_data (fehlt: hzb_place)
  ✓ "Abitur 2,3 vom 01.06.2018, Gymnasium Bonn, Bonn" → OK: alle HZB-Pflichtfelder vorhanden
  
  HINWEIS: hzb_name (Zeugnis-Bezeichnung) und hzb_school (Schulname) sind OPTIONAL mit Standardwerten.

EMAIL (nur für klips2_register - die Registrierungs-E-Mail-Adresse des Nutzers):
  - MUSS @ enthalten: "max@test.de" ✓
  - Fake-Emails ABLEHNEN: "noemail@nodomain.com", "keine-email@test.de" ✗
  - Phrase "E-Mail: wird nachgereicht" → insufficient_data
  HINWEIS: Diese Regel gilt NUR für den klips2_register-Parameter 'email', NICHT für send_email!

DATUM:
  - "Geburtsdatum: 15.03.1999" ✓
  - "Geboren 1999" → insufficient_data (nur Jahr)
  - "Geburtsdatum: TBA" / "noch unklar" → insufficient_data

VOLLSTÄNDIGKEIT:
{completeness_text}
  - Fehlt EIN EINZIGES Pflichtfeld → action='insufficient_data'
  - Platzhalter wie "TBD", "N/A", "wird ergänzt" → insufficient_data

**WENN Pflichtfelder fehlen:** action='insufficient_data' mit missing_fields
**WENN ALLE Pflichtfelder vorhanden:** action='tool'

WICHTIG: Lieber EINMAL ZU VIEL nachfragen als mit unvollständigen Daten Tool aufrufen!

## 3. FORMAT-TOLERANZ (WICHTIG):

✓ ACCEPT verschiedene Formate:
  - Datum: "15.03.1995", "1995-03-15", "March 15, 1995" (alle gültig)
  - Geschlecht: "m", "w", "d", "männlich", "male", "female", "divers" (alle gültig)
  - Email: Jede Email mit @ ist gültig (auch nicht-deutsche Domains)
  - Namen: Auch englische/internationale Namen akzeptieren
  - Sprache: Deutsch UND Englisch akzeptieren

✗ REJECT nur offensichtliche Probleme:
  - Email OHNE @: "email max.mustermann"
  - Fake-Emails: "keine-echte-email@example.com", "noemail@nodomain.com"
  - Partielles Datum: "1995" (nur Jahr), "15.03" (ohne Jahr)
  - Ungültiges Datum: "32.13.2020", "99.99.9999"
  - Fehlende Stadt bei Adresse: "Hauptstraße 1, PLZ 12345" (Stadt fehlt)
  - Vage Suche: "irgendwelche Kurse", "könnte ich Infos zu..."

## 4. SPEZIALFALL: Multi-Step-Konversationen (KRITISCH!)

**WICHTIG: Wenn "Previous conversation:" vorhanden ist:**

SCHRITT 1 - DATEN SAMMELN:
  - Lies ALLE vorherigen User-Nachrichten komplett durch
  - Sammle JEDES erwähnte Datenfeld (auch aus mehreren Nachrichten!)
  - Notiere dir: "In vorherigen Nachrichten habe ich: [Liste]"
  
SCHRITT 2 - AKTUELLE NACHRICHT:
  - Lies die aktuelle User-Nachricht
  - Notiere: "In aktueller Nachricht habe ich zusätzlich: [Liste]"
  
SCHRITT 3 - KOMBINIERE:
  - Vereinige ALLE Daten (vorherige + aktuelle)
  - Prüfe: Sind JETZT alle Pflichtfelder vorhanden?
  - JA → action='tool' | NEIN → action='insufficient_data'

TYPISCHE MULTI-STEP-MUSTER:
  ✓ "Zugangsdaten nachliefern": User gibt initial Studiengang/Daten, später Username/Password → DANN tool aufrufen!
  ✓ "Fehlende HZB": User gibt initial Persönliches, später Abitur-Daten → DANN tool aufrufen!
  ✓ "Korrekturen": User sagt "sorry, ich meinte X statt Y" → Nutze korrigierten Wert und tool aufrufen!
  
  ✗ "Abbruch": User sagt "doch nicht" / "abbrechen" → action='respond'
  ✗ "Immer noch unvollständig": Auch nach Nachfrage fehlen Pflichtfelder → action='insufficient_data'

Antworte im JSON-Format:

**EIN TOOL:**
{{"action": "tool", "tool_names": ["<name1>"], "reason": "Ein Tool identifiziert"}}

**MEHRERE TOOLS (Multi-Tool bei "und dann", "und schicke", etc.):**
{{"action": "tool", "tool_names": ["<name1>", "<name2>"], "reason": "Mehrere Tools identifiziert"}}
{json_example}

**FEHLENDE DATEN:**
{{"action": "insufficient_data", "tool_names": ["<name>"], "reason": "Pflichtfelder fehlen", "missing_fields": ["feld1", "feld2"]}}

**KEINE TOOLS:**
{{"action": "respond", "reason": "Nur Frage/Information, keine Aktion gewünscht"}}"""""

    def _get_extraction_prompt(self, tool_name: str, schema: Type[BaseModel]) -> str:
        """Prompt für die Argument-Extraktion."""
        # Hole Feld-Beschreibungen aus dem Schema
        fields = []
        for name, field in schema.model_fields.items():
            required = field.is_required()
            desc = field.description or ""
            req_str = "PFLICHT" if required else "optional"
            fields.append(f'  "{name}": "<{desc}>" // {req_str}')
        
        fields_str = ",\n".join(fields)

        # Tool-spezifische Normalisierungshinweise
        tool_hints = ""
        if tool_name == "klips2_apply_study":
            tool_hints = """
HZB-NORMALISIERUNG:
  * "Abitur" → hzb_type="Allgemeine Hochschulreife", hzb_name="Abitur"
  * "A-Levels" → hzb_type="Allgemeine Hochschulreife", hzb_name="A-Levels"
  * "Fachhochschulreife" / "FHR" → hzb_type="Fachhochschulreife"
  * "Fachgebundene Hochschulreife" → hzb_type="Fachgebundene Hochschulreife"
  * "High School Diploma" → hzb_type="Ausländische Hochschulzugangsberechtigung"

SEMESTER-NORMALISIERUNG:
  * "WS 2024/25" / "WS24/25" / "Wintersemester 2024" → "Wintersemester 2024/25"
  * "SS 2025" / "SoSe 2025" / "Sommersemester 25" → "Sommersemester 2025"

HZB-ORT: "Gymnasium Köln" → hzb_school="Gymnasium Köln", hzb_place="Köln" (Stadt aus Schulname ableiten wenn kein separater Ort genannt)
"""
        
        return f"""Extrahiere die Parameter für {tool_name} aus dem Nutzertext.

WICHTIGE REGELN:
- Extrahiere NUR Daten die im Text stehen (aktuell ODER in "Previous conversation:")
- Bei "Previous conversation:": Lies ALLE vorherigen Nachrichten und sammle Daten
- Bei Korrekturen ("sorry, ich meinte X statt Y"): Nutze korrigierte Werte
- NIEMALS Daten erfinden oder raten
- Nutze EXAKT diese Feldnamen (keine Variationen!)
- Normalisiere Formate flexibel:
  * Datum: "15.03.1995", "1995-03-15", "March 15, 1995" → "15.03.1995"
  * Geschlecht: "m"→"männlich", "w"→"weiblich", "d"→"divers", "male"→"männlich", etc.
  * Email: lowercase, beliebige Domains OK (auch .edu, .org, etc.)
  * Namen: Capitalize first letter, auch internationale Namen
{tool_hints}
FORMAT-TOLERANZ:
- Akzeptiere verschiedene Datumsformate (DD.MM.YYYY, YYYY-MM-DD, Month DD, YYYY)
- Akzeptiere Abkürzungen (m/w/d, DE/USA, etc.)
- Akzeptiere englische Texte
- Konvertiere automatisch zu erwarteten Formaten

Ausgabeformat (JSON):
{{
{fields_str}
}}

Lasse optionale Felder weg wenn nicht vorhanden.
PFLICHT-Felder sollten vorhanden sein (wurden bereits validiert)."""

    def _parse_and_validate(
        self, 
        json_str: str, 
        schema: Type[BaseModel]
    ) -> tuple[Optional[BaseModel], Optional[str]]:
        """
        Parse JSON und validiere gegen Schema.
        
        Returns:
            (validated_model, None) bei Erfolg
            (None, error_message) bei Fehler
        """
        self.schema_validations += 1
        
        # 1. JSON parsen
        try:
            # Bereinige JSON (entferne Markdown-Blöcke falls vorhanden)
            json_str = json_str.strip()
            if json_str.startswith("```"):
                json_str = re.sub(r'^```(?:json)?\n?', '', json_str)
                json_str = re.sub(r'\n?```$', '', json_str)
            
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Versuche Reparatur
            repaired = self._repair_json(json_str)
            if repaired:
                self.schema_repairs += 1
                data = repaired
            else:
                self.schema_failures += 1
                return None, f"JSON-Parse-Fehler: {e}"
        
        # 2. Gegen Schema validieren
        try:
            validated = schema.model_validate(data)
            return validated, None
        except ValidationError as e:
            self.schema_failures += 1
            errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
            return None, f"Validierungsfehler: {'; '.join(errors)}"
    
    def _repair_json(self, json_str: str) -> Optional[Dict]:
        """Versuche häufige JSON-Fehler zu reparieren."""
        # Entferne Trailing Commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # Füge fehlende Quotes um Keys hinzu
        json_str = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # Ersetze single quotes durch double quotes
        # (vorsichtig - nur wenn nicht innerhalb eines strings)
        json_str = json_str.replace("'", '"')
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Führe Tool mit validierten Argumenten aus."""
        tool = self.tool_map.get(tool_name)
        if not tool:
            return f"Fehler: Tool '{tool_name}' nicht gefunden"
        
        try:
            result = tool.invoke(args)
            return result
        except Exception as e:
            return f"Fehler bei Tool-Ausführung: {str(e)}"
    
    def chat(self, message: str, session_id: str = None) -> str:
        """
        Führe eine Unterhaltung mit dem Constrained Agent.
        
        Prozess:
        1. Entscheide ob Tool oder direkte Antwort (mit Schema)
        2. Bei Tool: Extrahiere Argumente (mit Schema)
        3. Validiere gegen Pydantic-Schema
        4. Führe Tool aus oder gib Antwort
        """
        try:
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            human_message = HumanMessage(
                content=message,
                additional_kwargs={"session_id": session_id},
            )
            self.memory.append(human_message)
            
            if len(self.memory) > settings.MEMORY_SIZE:
                self.memory = self.memory[-settings.MEMORY_SIZE:]
            
            # Erstelle erweiterten Kontext mit vorherigen Nachrichten
            context_messages = []
            if len(self.memory) > 1:
                # Inkludiere letzte 3 Nachrichtenpaare für Kontext
                prev_context = []
                for msg in self.memory[-7:-1]:  # Letzte 6 Nachrichten (ohne die aktuelle)
                    if isinstance(msg, HumanMessage):
                        prev_context.append(f"User: {msg.content}")
                    elif isinstance(msg, AIMessage):
                        prev_context.append(f"Assistant: {msg.content}")
                
                if prev_context:
                    context_str = "\n".join(prev_context)
                    enriched_message = f"Previous conversation:\n{context_str}\n\nCurrent message:\n{message}"
                else:
                    enriched_message = message
            else:
                enriched_message = message
            
            # Schritt 1: Entscheidung (mit erweitertem Kontext)
            decision_prompt = self._get_decision_prompt()
            decision_messages = [
                SystemMessage(content=decision_prompt),
                HumanMessage(content=enriched_message)
            ]
            
            decision_response = self.llm_json.invoke(decision_messages)
            decision_result, error = self._parse_and_validate(
                decision_response.content, 
                ToolDecision
            )
            
            if error or not decision_result:
                # Fallback: Direkte Antwort generieren
                response_text = self._generate_fallback_response(message)
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Schritt 2: Prüfe auf fehlende Daten
            if decision_result.action == "insufficient_data":
                # Fehlende Pflichtfelder → Nachfragen
                missing = decision_result.missing_fields or []
                field_names = ", ".join(missing)
                response_text = f"Um fortzufahren, benötige ich noch folgende Informationen: {field_names}. Bitte ergänze diese Angaben."
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Schritt 3: Action ausführen
            if decision_result.action == "respond":
                # Direkte Antwort generieren
                response_text = self._generate_direct_response(message)
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Schritt 4: Tool-Argumente extrahieren (mit erweitertem Kontext)
            tool_names = decision_result.tool_names
            if not tool_names:
                response_text = "Keine Tools identifiziert."
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Multi-Tool: Verarbeite alle Tools sequentiell
            all_results = []
            for tool_name in tool_names:
                if tool_name not in TOOL_SCHEMAS:
                    all_results.append(f"Unbekanntes Tool: {tool_name}")
                    continue
                
                schema = TOOL_SCHEMAS[tool_name]
                extraction_prompt = self._get_extraction_prompt(tool_name, schema)
                
                extraction_messages = [
                    SystemMessage(content=extraction_prompt),
                    HumanMessage(content=f"Nutzertext (mit Kontext):\n{enriched_message}")
                ]
                
                extraction_response = self.llm_json.invoke(extraction_messages)
                validated_args, error = self._parse_and_validate(
                    extraction_response.content,
                    schema
                )
                
                if error:
                    # Retry: Gebe Feedback und eine weitere Chance
                    retry_prompt = f"""Die vorherige JSON-Generierung hatte Fehler:
{error}

Bitte korrigiere die Fehler und generiere das JSON erneut.
Nur die fehlenden/fehlerhaften Felder müssen korrigiert werden.

Ursprünglicher Nutzertext: {enriched_message}"""
                    
                    retry_messages = [
                        SystemMessage(content=extraction_prompt),
                        HumanMessage(content=f"Nutzertext (mit Kontext):\n{enriched_message}"),
                        AIMessage(content=extraction_response.content),
                        HumanMessage(content=retry_prompt)
                    ]
                    
                    retry_response = self.llm_json.invoke(retry_messages)
                    validated_args_retry, error_retry = self._parse_and_validate(
                        retry_response.content,
                        schema
                    )
                    
                    if error_retry:
                        # Auch nach Retry fehlgeschlagen
                        all_results.append(f"{tool_name}: Fehler bei Datenverarbeitung: {error_retry}")
                        continue
                    
                    # Retry erfolgreich - verwende korrigierte Args
                    validated_args = validated_args_retry
                
                # Schritt 5: Tool ausführen
                args_dict = validated_args.model_dump(exclude_none=True)
                tool_result = self._execute_tool(tool_name, args_dict)
                all_results.append(self._format_tool_response(tool_name, tool_result))
            
            # Schritt 6: Kombiniere alle Ergebnisse
            if not all_results:
                response_text = "Keine Tools konnten erfolgreich ausgeführt werden."
            elif len(all_results) == 1:
                response_text = all_results[0]
            else:
                response_text = "\n\n---\n\n".join(all_results)
            
            # Safety check: Ensure we never return raw JSON to users
            if response_text.strip().startswith('{') and '"action"' in response_text:
                response_text = "Entschuldigung, ich hatte ein technisches Problem. Bitte formulieren Sie Ihre Frage erneut."
            
            self.memory.append(AIMessage(content=response_text))
            return response_text
            
        except Exception as e:
            error_msg = f"Fehler: {str(e)}"
            self.memory.append(AIMessage(content=error_msg))
            return error_msg
    
    def _generate_direct_response(self, message: str) -> str:
        """Generiere direkte Antwort ohne Tool."""
        prompt = """Du bist ein hilfreicher Assistent für KLIPS 2.0.
Beantworte die Frage direkt und präzise.
Falls Informationen für einen Tool-Aufruf fehlen, frage gezielt nach."""
        
        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=message)
        ]
        
        response = self.llm.invoke(messages)
        return response.content
    
    def _synthesize_rag_response(self, rag_result: str) -> str:
        """Synthesiere RAG-Ergebnisse in eine kohärente Antwort.
        
        Args:
            rag_result: Rohe RAG-Tool-Ausgabe mit Context-Chunks
            
        Returns:
            Natürliche, kohärente Antwort basierend auf dem RAG-Kontext
        """
        # Wenn RAG-Tool keine Ergebnisse fand
        if "Keine relevanten Informationen" in rag_result or "❌" in rag_result:
            return rag_result
        
        # Hole die letzte User-Nachricht für Kontext
        last_user_message = ""
        for msg in reversed(self.memory):
            if isinstance(msg, HumanMessage):
                last_user_message = msg.content
                break
        
        synthesis_prompt = f"""Du bist ein hilfreicher Universitäts-Assistent. 

Die folgende Frage wurde gestellt:
{last_user_message}

Hierzu wurden folgende Informationen aus der Wissensdatenbank abgerufen:
{rag_result}

Aufgabe: Beantworte die Frage präzise und natürlich basierend auf den abgerufenen Informationen.

REGELN:
1. Formuliere eine direkte, kohärente Antwort (NICHT "Laut Wissensdatenbank...")  
2. Integriere die relevanten Informationen nahtlos
3. Behalte wichtige Details bei (Zahlen, Namen, Anforderungen)
4. Strukturiere die Antwort übersichtlich (Absätze, Aufzählungen wenn sinnvoll)
5. Vermeide Redundanzen
6. Schreibe NICHT die ursprüngliche Frage oder Einleitungen wie "Die Antwort ist:"

Antworte direkt und natürlich:"""
        
        try:
            messages = [
                SystemMessage(content=synthesis_prompt)
            ]
            response = self.llm.invoke(messages)
            synthesized = response.content.strip()
            
            # Entferne mögliche Meta-Sätze die das LLM trotzdem hinzufügt
            patterns_to_remove = [
                r"^(Basierend auf|Laut|Gemäß|Nach) (den|der) (abgerufenen )?Informationen[^.]*[.:]\s*",
                r"^Die Antwort (lautet|ist)[^.]*[.:]\s*",
                r"^Hier ist die Antwort[^.]*[.:]\s*",
            ]
            
            for pattern in patterns_to_remove:
                synthesized = re.sub(pattern, "", synthesized, flags=re.IGNORECASE)
            
            return synthesized.strip()
            
        except Exception as e:
            logger.error(f"Fehler bei RAG-Synthese: {e}", exc_info=True)
            # Fallback: Gebe RAG-Ergebnis direkt zurück
            return rag_result
    
    def _generate_fallback_response(self, message: str) -> str:
        """Fallback wenn Entscheidung nicht geparst werden konnte."""
        return self._generate_direct_response(message)
    
    def _format_tool_response(self, tool_name: str, result: str) -> str:
        """Formatiere Tool-Ergebnis für Nutzer."""
        # Für RAG-Tool: Synthesiere Antwort aus Kontext
        if tool_name == "university_knowledge_search":
            return self._synthesize_rag_response(result)
        
        # Für andere Tools: Standard-Formatierung
        tool_descriptions = {
            "klips2_register": "KLIPS2-Registrierung",
            "klips2_apply_study": "Studienbewerbung",
            "klips2_change_address": "Adressänderung",
            "klips2_change_password": "Passwortänderung",
            "klips2_get_course_details": "Kursdetails",
            "duckduckgo_search": "Web-Suche",
            "web_scraper": "Webseiten-Inhalt",
            "send_email": "E-Mail-Versand",
        }
        
        desc = tool_descriptions.get(tool_name, tool_name)
        return f"{desc}:\n\n{result}"
    
    def get_available_tools(self) -> List[str]:
        """Gebe Liste der verfügbaren Tools zurück."""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self):
        """Lösche Konversationshistorie."""
        self.memory = []
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Gebe eine Zusammenfassung des aktuellen Konversationsspeichers zurück.

        Rückgabeformat ist kompatibel zu anderen Agenten:
        - total_messages: Gesamtanzahl aller Nachrichten
        - human_messages: Anzahl der HumanMessage-Nachrichten
        - ai_messages: Anzahl der AIMessage-Nachrichten
        - last_messages: Liste der letzten Nachrichten (max. 5) als einfache Dicts
        """
        messages = self.memory

        total_messages = len(messages)
        human_messages = sum(1 for m in messages if isinstance(m, HumanMessage))
        ai_messages = sum(1 for m in messages if isinstance(m, AIMessage))

        # Formatiere die letzten Nachrichten in ein einfaches, serialisierbares Format
        last_raw = messages[-5:] if total_messages > 5 else messages
        last_messages: List[Dict[str, Any]] = []
        for m in last_raw:
            # Versuche, Rolle/Typ und Inhalt möglichst konsistent zu extrahieren
            role: str
            if isinstance(m, HumanMessage):
                role = "human"
            elif isinstance(m, AIMessage):
                role = "ai"
            elif isinstance(m, SystemMessage):
                role = "system"
            else:
                role = getattr(m, "type", "unknown")

            content = getattr(m, "content", None)
            last_messages.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return {
            "total_messages": total_messages,
            "human_messages": human_messages,
            "ai_messages": ai_messages,
            "last_messages": last_messages,
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Gebe Statistiken über Schema-Validierungen zurück."""
        return {
            "total_validations": self.schema_validations,
            "repairs": self.schema_repairs,
            "failures": self.schema_failures,
            "success_rate": (
                (self.schema_validations - self.schema_failures) / self.schema_validations
                if self.schema_validations > 0 else 0
            )
        }
    
    def get_conversation_trace(self) -> List[Dict[str, Any]]:
        """Gebe den kompletten Conversation-Trace zurück."""
        return self.conversation_trace
    
    def clear_conversation_trace(self):
        """Lösche den Conversation-Trace."""
        self.conversation_trace = []
    
    def save_conversation_trace(self, filepath: str):
        """
        Speichere den Conversation-Trace als JSON-Datei.
        
        Args:
            filepath: Pfad zur Ausgabedatei
        """
        from pathlib import Path
        
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.conversation_trace, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Conversation-Trace gespeichert: {output_path}")
    
    def get_tool_selection(self, message: str, enable_trace: bool = False, max_retries: int = 1) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl mit Constrained-Decoding-Logik (für Evaluierung).
        
        Diese Methode führt die spezifische Constrained-Agent-Logik durch:
        1. Entscheidung ob Tool oder direkte Antwort (mit JSON-Mode)
        2. Argument-Extraktion mit Pydantic-Schema-Validierung
        3. Bei Validierungsfehlern: Retry mit Feedback (max_retries Versuche)
        
        Args:
            message: Die Nutzeranfrage
            enable_trace: Wenn True, wird der Conversation-Trace aufgezeichnet
            max_retries: Maximale Anzahl an Versuchen bei Validierungsfehlern (Standard: 2)
            
        Returns:
            Liste der ausgewählten Tool-Calls mit validierten Argumenten
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        
        try:
            human_message = HumanMessage(content=message)
            
            # Schritt 1: Entscheidung mit JSON-Mode LLM
            decision_prompt = self._get_decision_prompt()
            decision_messages = [
                SystemMessage(content=decision_prompt),
                human_message
            ]
            
            decision_response = self.llm_json.invoke(decision_messages)
            
            # Log Step 1: Decision (optional)
            if enable_trace:
                trace_step = {
                    "step": "decision",
                    "scenario": message,
                    "prompt": decision_prompt,
                    "raw_output": decision_response.content,
                    "timestamp": datetime.now().isoformat()
                }
            
            decision_result, error = self._parse_and_validate(
                decision_response.content, 
                ToolDecision
            )
            
            if enable_trace:
                trace_step["validation_success"] = error is None
                trace_step["validation_error"] = error
                trace_step["parsed_result"] = decision_result.model_dump() if decision_result else None
                self.conversation_trace.append(trace_step)
            
            if error or not decision_result:
                return []  # Keine Tool-Auswahl möglich
            
            # Check for insufficient data: retry once with explicit hint
            if decision_result.action == "insufficient_data":
                identified_tool = (decision_result.tool_names or [None])[0]
                # No-required-fields tools (e.g. send_email) should never be insufficient_data
                no_required = {
                    "send_email", "university_knowledge_search", "duckduckgo_search",
                    "web_scraper", "klips2_get_course_details",
                }
                if identified_tool in no_required:
                    missing = decision_result.missing_fields or []
                    retry_hint = (
                        f"Deine vorherige Entscheidung war 'insufficient_data' mit fehlenden Feldern {missing}. "
                        f"ABER: Das Tool '{identified_tool}' hat PFLICHT: keine – es kann IMMER aufgerufen werden. "
                        f"Bitte entscheide erneut. Antworte nur im JSON-Format."
                    )
                    retry_decision_msgs = [
                        SystemMessage(content=decision_prompt),
                        HumanMessage(content=message),
                        AIMessage(content=decision_response.content),
                        HumanMessage(content=retry_hint),
                    ]
                    retry_decision_response = self.llm_json.invoke(retry_decision_msgs)
                    retry_decision_result, retry_err = self._parse_and_validate(
                        retry_decision_response.content, ToolDecision
                    )
                    if not retry_err and retry_decision_result and retry_decision_result.action == "tool":
                        decision_result = retry_decision_result
                    else:
                        return []  # Still wrong after retry
                else:
                    return []  # Fehlende Daten → kein Tool-Call
            
            # Also retry if model said 'respond' but message clearly contains email keywords
            # (sub-second failures indicate model skipped the tool entirely)
            if decision_result.action == "respond":
                available_tool_names = {tool.name for tool in self.tools}
                email_keywords = (
                    "send_email" in available_tool_names and any(
                        kw in message.lower() for kw in [
                            "e-mail", "email", "mail", "sende", "schicke", "schreibe",
                            "verfasse", "nachricht", "send", "write",
                        ]
                    )
                )
                if email_keywords:
                    retry_hint = (
                        "Deine vorherige Entscheidung war 'respond', aber die Nachricht enthält "
                        "eindeutige E-Mail-Signalwörter. Das Tool 'send_email' hat PFLICHT: keine "
                        "und kann immer aufgerufen werden. Bitte entscheide erneut: "
                        "action='tool', tool_names=['send_email']. Antworte nur im JSON-Format."
                    )
                    retry_decision_msgs = [
                        SystemMessage(content=decision_prompt),
                        HumanMessage(content=message),
                        AIMessage(content=decision_response.content),
                        HumanMessage(content=retry_hint),
                    ]
                    retry_decision_response = self.llm_json.invoke(retry_decision_msgs)
                    retry_decision_result, retry_err = self._parse_and_validate(
                        retry_decision_response.content, ToolDecision
                    )
                    if not retry_err and retry_decision_result and retry_decision_result.action == "tool":
                        decision_result = retry_decision_result
                    else:
                        return []  # Still wrong after retry
                else:
                    return []  # Direkte Antwort, kein Tool
            
            # Schritt 2: Tool-Argumente mit Schema extrahieren (Multi-Tool Support)
            tool_names = decision_result.tool_names
            if not tool_names:
                return []  # Keine Tools identifiziert
            
            # Multi-Tool: Verarbeite alle Tools sequentiell
            all_tool_calls = []
            for tool_name in tool_names:
                if tool_name not in TOOL_SCHEMAS:
                    if enable_trace:
                        trace_step = {
                            "step": "error",
                            "tool_name": tool_name,
                            "scenario": message,
                            "error": f"Unknown tool: {tool_name}",
                            "timestamp": datetime.now().isoformat()
                        }
                        self.conversation_trace.append(trace_step)
                    continue  # Skip unbekanntes Tool
                
                schema = TOOL_SCHEMAS[tool_name]
                extraction_prompt = self._get_extraction_prompt(tool_name, schema)
                
                extraction_messages = [
                    SystemMessage(content=extraction_prompt),
                    HumanMessage(content=f"Nutzertext: {message}")
                ]
                
                extraction_response = self.llm_json.invoke(extraction_messages)
                
                # Log Step 2: Initial Extraction (optional)
                if enable_trace:
                    trace_step = {
                        "step": "extraction_initial",
                        "tool_name": tool_name,
                        "scenario": message,
                        "prompt": extraction_prompt,
                        "raw_output": extraction_response.content,
                        "timestamp": datetime.now().isoformat()
                    }
                
                validated_args, error = self._parse_and_validate(
                    extraction_response.content,
                    schema
                )
                
                if enable_trace:
                    trace_step["validation_success"] = error is None
                    trace_step["validation_error"] = error
                    trace_step["parsed_result"] = validated_args.model_dump() if validated_args else None
                    self.conversation_trace.append(trace_step)
                
                # Erfolg beim ersten Versuch
                if not error:
                    args_dict = validated_args.model_dump(exclude_none=True)
                    if enable_trace:
                        final_step = {
                            "step": "final_result",
                            "tool_name": tool_name,
                            "scenario": message,
                            "status": "success_first_attempt",
                            "reason": "Schema-Validierung erfolgreich beim ersten Versuch",
                            "result": {"name": tool_name, "args": args_dict},
                            "timestamp": datetime.now().isoformat()
                        }
                        self.conversation_trace.append(final_step)
                    all_tool_calls.append({"name": tool_name, "args": args_dict})
                    continue  # Nächstes Tool
                
                # Bei Fehler: Retry-Schleife
                last_response = extraction_response.content
                last_error = error
                messages_history = extraction_messages.copy()
                
                for retry_num in range(max_retries):
                    retry_prompt = f"""Die vorherige JSON-Generierung hatte Fehler (Versuch {retry_num + 1}/{max_retries}):
{last_error}

Bitte korrigiere die Fehler und generiere das JSON erneut.
Nur die fehlenden/fehlerhaften Felder müssen korrigiert werden.

Ursprünglicher Nutzertext: {message}"""
                    
                    # History erweitern
                    messages_history.append(AIMessage(content=last_response))
                    messages_history.append(HumanMessage(content=retry_prompt))
                    
                    retry_response = self.llm_json.invoke(messages_history)
                    
                    # Log Retry (optional)
                    if enable_trace:
                        trace_step = {
                            "step": f"extraction_retry_{retry_num + 1}",
                            "tool_name": tool_name,
                            "scenario": message,
                            "previous_error": last_error,
                            "retry_prompt": retry_prompt,
                            "raw_output": retry_response.content,
                            "timestamp": datetime.now().isoformat()
                        }
                    
                    validated_args_retry, error_retry = self._parse_and_validate(
                        retry_response.content,
                        schema
                    )
                    
                    if enable_trace:
                        trace_step["validation_success"] = error_retry is None
                        trace_step["validation_error"] = error_retry
                        trace_step["parsed_result"] = validated_args_retry.model_dump() if validated_args_retry else None
                        self.conversation_trace.append(trace_step)
                    
                    # Erfolg nach Retry
                    if not error_retry:
                        args_dict = validated_args_retry.model_dump(exclude_none=True)
                        if enable_trace:
                            final_step = {
                                "step": "final_result",
                                "tool_name": tool_name,
                                "scenario": message,
                                "status": f"success_after_retry_{retry_num + 1}",
                                "reason": f"Schema-Validierung erfolgreich nach {retry_num + 1} Retry(s)",
                                "result": {"name": tool_name, "args": args_dict},
                                "timestamp": datetime.now().isoformat()
                            }
                            self.conversation_trace.append(final_step)
                        all_tool_calls.append({"name": tool_name, "args": args_dict})
                        break  # Retry erfolgreich, nächstes Tool
                    
                    # Update für nächste Iteration
                    last_response = retry_response.content
                    last_error = error_retry
                else:
                    # Alle Retries fehlgeschlagen für dieses Tool
                    if enable_trace:
                        final_step = {
                            "step": "final_result",
                            "tool_name": tool_name,
                            "scenario": message,
                            "status": f"failed_after_{max_retries}_retries",
                            "reason": f"Schema-Validierung fehlgeschlagen nach {max_retries} Retry(s)",
                            "initial_error": error,
                            "final_error": last_error,
                            "result": None,  # Kein Tool-Aufruf bei Validierungsfehler
                            "timestamp": datetime.now().isoformat()
                        }
                        self.conversation_trace.append(final_step)
                    # Tool wird übersprungen, fahre mit nächstem fort
            
            # Gebe alle erfolgreich verarbeiteten Tools zurück
            return all_tool_calls
            
        except Exception as e:
            if enable_trace:
                trace_step = {
                    "step": "error",
                    "scenario": message,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                self.conversation_trace.append(trace_step)
            return []  # Bei Fehler keine Tool-Auswahl


def create_constrained_agent() -> ConstrainedAgent:
    """Factory-Funktion für den Constrained Agent."""
    return ConstrainedAgent()
