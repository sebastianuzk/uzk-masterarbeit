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

import os
import uuid
import json
import re
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field, ValidationError, field_validator
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from config.settings import settings
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


# ============================================================================
# PYDANTIC SCHEMAS FÜR TOOL-CALLS
# ============================================================================

class ToolDecision(BaseModel):
    """Entscheidung des Agenten: Tool aufrufen oder direkt antworten."""
    action: str = Field(
        description="'tool' wenn ein Tool aufgerufen werden soll, 'respond' für direkte Antwort, 'insufficient_data' wenn Daten fehlen"
    )
    tool_name: Optional[str] = Field(
        default=None,
        description="Name des Tools (nur wenn action='tool')"
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
    semester: str = Field(description="Zielsemester")
    degree_type: str = Field(description="Bachelor, Master oder Promotion")
    study_program: str = Field(description="Name des Studiengangs")
    entry_semester: str = Field(default="1", description="Fachsemester")
    study_form: str = Field(default="Erststudium", description="Erststudium oder Zweitstudium")
    gender: str = Field(description="Geschlecht")
    birth_place: str = Field(description="Geburtsort")
    birth_country: str = Field(default="Deutschland", description="Geburtsland")
    nationality: str = Field(description="Staatsangehörigkeit")
    hzb_date: str = Field(description="Datum der Hochschulzugangsberechtigung")
    hzb_type: str = Field(description="Art der HZB")
    hzb_name: str = Field(description="Bezeichnung des Zeugnisses")
    hzb_grade: str = Field(description="Note der HZB")
    hzb_school: str = Field(description="Name der Schule")
    hzb_country: str = Field(default="Deutschland", description="Land der HZB")
    hzb_place: str = Field(description="Ort der HZB")
    # Optional
    street: Optional[str] = Field(default=None)
    zip_code: Optional[str] = Field(default=None)
    city: Optional[str] = Field(default=None)
    country: Optional[str] = Field(default="Deutschland")
    phone: Optional[str] = Field(default=None)
    prev_uni: Optional[str] = Field(default=None)
    prev_program: Optional[str] = Field(default=None)
    prev_degree: Optional[str] = Field(default=None)
    prev_semesters: Optional[str] = Field(default=None)
    validate_only: bool = Field(default=False)


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
        if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            print(f"✅ LangSmith-Tracing aktiviert für Projekt: {settings.LANGSMITH_PROJECT}")
        
        # Context-Size
        MODEL_CTX_SIZES = {
            "0.5b": 2048, "1b": 4096, "3b": 8192,
            "8b": 8192, "20b": 16384, "70b": 16384,
        }
        
        model_lower = settings.OLLAMA_MODEL.lower()
        ctx_size = 8192
        for size_key, ctx_value in MODEL_CTX_SIZES.items():
            if size_key in model_lower:
                ctx_size = ctx_value
                break
        
        print(f"📐 Initialisiere Constrained Agent mit Modell: {settings.OLLAMA_MODEL} (ctx_size={ctx_size})")
        
        # LLM für Entscheidungen (ohne JSON-Mode für natürliche Antworten)
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            num_ctx=ctx_size,
            timeout=settings.REQUEST_TIMEOUT,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
        
        # LLM mit JSON-Mode für strukturierte Ausgaben
        self.llm_json = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1,  # Niedriger für präzisere Strukturen
            num_ctx=ctx_size,
            timeout=settings.REQUEST_TIMEOUT,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
            format="json",  # Erzwingt JSON-Ausgabe
        )
        
        # Tools initialisieren
        self.tools = self._create_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # System message für Kompatibilität mit Evaluation Harness
        self.system_message = SystemMessage(content=self._get_system_prompt())
        
        # Memory
        self.memory: List[Union[HumanMessage, AIMessage]] = []
        
        # Tracking
        self.schema_validations = 0
        self.schema_repairs = 0
        self.schema_failures = 0
    
    def _get_system_prompt(self) -> str:
        """Kompakter System-Prompt für Constrained Agent."""
        return """Du bist ein KI-Assistent für KLIPS 2.0 der Universität zu Köln.

## WANN EIN TOOL AUFRUFEN?

✅ Tool aufrufen bei: KLIPS2-Aktionen, Uni-Wissensfragen, Internet-Suche, URLs, E-Mails
❌ KEIN Tool bei: Begrüßungen, Fragen über dich, Rechenaufgaben, allgemeine Fragen

## REGELN

1. Wenn Tool passend UND alle Pflichtdaten vorhanden → Tool aufrufen
2. Wenn Tool passend ABER Daten fehlen → Nachfragen (KEIN Tool-Aufruf)
3. Wenn KEIN Tool passend → Direkt antworten
4. Antworte in der Sprache des Nutzers

## TOOLS (Pflichtparameter)

### KLIPS2-Aktionen:
- klips2_register: vorname, nachname, geschlecht, geburtsdatum, email, staatsangehoerigkeit
- klips2_apply_study: username, password, semester, degree_type, study_program (+ weitere)
- klips2_change_address: username, password, street, zip_code, city
- klips2_change_password: username, password, new_password
- klips2_get_course_details: course_id

### Suche & Wissen:
- duckduckgo_search: query (bei "Search for", "Suche im Internet", "online")
- university_knowledge_search: query (bei Uni-Fragen ohne Internet-Keywords)
- web_scraper: url (bei URLs)

### Kommunikation:
- send_email: subject, body"""
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools."""
        tools = []
        
        if settings.ENABLE_WEB_SCRAPER:
            tools.append(create_web_scraper_tool())
        
        if settings.ENABLE_DUCKDUCKGO:
            tools.append(create_duckduckgo_tool())
        
        try:
            tools.append(create_university_rag_tool())
            print("  ✅ Universitäts-RAG-Tool geladen")
        except Exception as e:
            print(f"  ⚠️ RAG-Tool konnte nicht geladen werden: {e}")
        
        try:
            tools.append(create_email_tool())
            print("  ✅ E-Mail-Tool geladen")
        except Exception as e:
            print(f"  ⚠️ E-Mail-Tool konnte nicht geladen werden: {e}")
        
        try:
            tools.append(create_klips2_register_tool())
            tools.append(create_klips2_apply_tool())
            tools.append(create_klips2_change_password_tool())
            tools.append(create_klips2_get_course_details_tool())
            tools.append(create_klips2_change_address_tool())
            print("  ✅ KLIPS2-Tools geladen")
        except Exception as e:
            print(f"  ⚠️ KLIPS2-Tools konnten nicht geladen werden: {e}")
        
        return tools
    
    def _get_decision_prompt(self) -> str:
        """Prompt für die Tool-Entscheidung mit expliziten Anforderungen."""
        # Tool-spezifische Pflichtfelder
        tool_requirements = {
            "klips2_register": ["vorname", "nachname", "geschlecht", "geburtsdatum", "email", "staatsangehoerigkeit"],
            "klips2_apply_study": ["username", "password", "semester", "degree_type", "study_program", "gender", "birth_place", "nationality", "hzb_date", "hzb_type", "hzb_name", "hzb_grade", "hzb_school", "hzb_place"],
            "klips2_change_password": ["username", "old_password", "new_password"],
            "klips2_change_address": ["username", "password", "street", "zip_code", "city", "country"],
            "klips2_get_course_details": ["course_number"],
            "send_email": ["recipient", "subject", "body"],
            "duckduckgo_search": ["query"],
            "university_knowledge_search": ["query"],
            "web_scraper": ["url"]
        }
        
        tool_list = []
        for name, schema in TOOL_SCHEMAS.items():
            desc = schema.__doc__ or 'Keine Beschreibung'
            required = tool_requirements.get(name, [])
            req_str = ", ".join(required) if required else "keine"
            tool_list.append(f"- {name}: {desc}\n  PFLICHT: {req_str}")
        
        tools_str = "\n".join(tool_list)
        
        return f"""Du bist ein KI-Assistent für KLIPS 2.0 der Universität zu Köln.

Analysiere die Nutzeranfrage SORGFÄLTIG und entscheide:
1. Welches Tool benötigt wird (oder keins)
2. Ob ALLE Pflichtfelder VOLLSTÄNDIG und VALIDE vorhanden sind

VERFÜGBARE TOOLS mit Pflichtfeldern:
{tools_str}

ENTSCHEIDUNGSLOGIK (STRENG):
1. Prüfe ob Tool-Aktion angefordert wird
2. Prüfe JEDES Pflichtfeld einzeln nach diesen Kriterien:
   - Ist der Wert EXPLIZIT im Text angegeben?
   - Ist der Wert VOLLSTÄNDIG (kein Platzhalter, keine Auslassung)?
   - Ist der Wert VALIDE (korrekte Formatierung)?
3. WENN ein oder mehrere Pflichtfelder fehlen/ungültig → action='insufficient_data' mit missing_fields
4. NUR WENN alle Pflichtfelder vollständig vorhanden → action='tool'
5. Bei vagen Fragen/allgemeinen Informationen → action='respond'

WICHTIGE VALIDIERUNGSREGELN:
✗ REJECT (insufficient_data):
  - Email ohne @: "email max.mustermann"
  - Platzhalter-Email: "keine-echte-email@example.com"
  - Partielles Datum: "1995" (nur Jahr), "15.03" (ohne Jahr)
  - Ungültiges Datum: "32.13.2020"
  - Fehlende Stadt: "Adresse: Hauptstraße 1, PLZ 12345" (Stadt fehlt)
  - Vage Suche: "irgendwelche Kurse", "könnte ich Infos zu..."
  - Fehlender Betreff: Email ohne Subject
  - Unvollständige Anmeldedaten: Fehlende HZB-Infos, Geburtsdaten, etc.

✓ ACCEPT (action='tool'):
  - Alle Pflichtfelder explizit vorhanden
  - Valide Formate (email@domain.de, DD.MM.YYYY, 5-stellige PLZ)
  - Bei mehrstufigen Konversationen: "Previous conversation:" im Prompt
    → Falls dort bereits Daten genannt wurden, gelten diese als vorhanden

SPEZIALFALL: Multi-Step-Konversationen
Wenn "Previous conversation:" vorhanden:
  1. Prüfe ZUERST vorherige Nachrichten auf fehlende Daten
  2. Kombiniere Informationen aus aktuellem + vorherigem Kontext
  3. Nur fehlende Felder müssen nachgefragt werden

Antworte im JSON-Format:
{{"action": "tool", "tool_name": "<name>", "reason": "Alle Daten vollständig vorhanden"}}
oder
{{"action": "insufficient_data", "tool_name": "<name>", "reason": "Fehlende/ungültige Daten", "missing_fields": ["feld1", "feld2"]}}
oder
{{"action": "respond", "reason": "Nur Frage/Information, kein Tool benötigt"}}"""

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
        
        return f"""Extrahiere die Parameter für {tool_name} aus dem Nutzertext.

WICHTIGE REGELN:
- Extrahiere NUR Daten die EXPLIZIT im Text stehen
- Bei "Previous conversation:"-Kontext: Kombiniere aktuelle + vorherige Daten
- NIEMALS Daten erfinden oder raten
- Bei mehrdeutigen/unvollständigen Daten: Lasse Feld weg
- Nutze EXAKT diese Feldnamen (keine Variationen!)
- Normalisiere Formate:
  * Datum → TT.MM.JJJJ
  * Email → lowercase
  * Namen → Capitalize first letter

Ausgabeformat (JSON):
{{
{fields_str}
}}

Lasse optionale Felder weg wenn nicht vorhanden.
PFLICHT-Felder MÜSSEN vorhanden sein (sollte bereits validiert sein)."""

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
            tool_name = decision_result.tool_name
            if tool_name not in TOOL_SCHEMAS:
                response_text = f"Unbekanntes Tool: {tool_name}"
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
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
                # Schema-Validierung fehlgeschlagen
                response_text = f"Ich konnte die Daten nicht korrekt verarbeiten: {error}\nBitte überprüfe die Angaben."
                self.memory.append(AIMessage(content=response_text))
                return response_text
            
            # Schritt 5: Tool ausführen
            args_dict = validated_args.model_dump(exclude_none=True)
            tool_result = self._execute_tool(tool_name, args_dict)
            
            # Schritt 6: Antwort formulieren
            response_text = self._format_tool_response(tool_name, tool_result)
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
    
    def _generate_fallback_response(self, message: str) -> str:
        """Fallback wenn Entscheidung nicht geparst werden konnte."""
        return self._generate_direct_response(message)
    
    def _format_tool_response(self, tool_name: str, result: str) -> str:
        """Formatiere Tool-Ergebnis für Nutzer."""
        # Kurze Zusammenfassung + Ergebnis
        tool_descriptions = {
            "klips2_register": "KLIPS2-Registrierung",
            "klips2_apply_study": "Studienbewerbung",
            "klips2_change_address": "Adressänderung",
            "klips2_change_password": "Passwortänderung",
            "klips2_get_course_details": "Kursdetails",
            "university_knowledge_search": "Wissensdatenbank-Suche",
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
    
    def get_tool_selection(self, message: str) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl mit Constrained-Decoding-Logik (für Evaluierung).
        
        Diese Methode führt die spezifische Constrained-Agent-Logik durch:
        1. Entscheidung ob Tool oder direkte Antwort (mit JSON-Mode)
        2. Argument-Extraktion mit Pydantic-Schema-Validierung
        
        Args:
            message: Die Nutzeranfrage
            
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
            decision_result, error = self._parse_and_validate(
                decision_response.content, 
                ToolDecision
            )
            
            if error or not decision_result:
                return []  # Keine Tool-Auswahl möglich
            
            # Check for insufficient data (NEU!)
            if decision_result.action == "insufficient_data":
                return []  # Fehlende Daten → kein Tool-Call
            
            if decision_result.action == "respond":
                return []  # Direkte Antwort, kein Tool
            
            # Schritt 2: Tool-Argumente mit Schema extrahieren
            tool_name = decision_result.tool_name
            if tool_name not in TOOL_SCHEMAS:
                return []  # Unbekanntes Tool
            
            schema = TOOL_SCHEMAS[tool_name]
            extraction_prompt = self._get_extraction_prompt(tool_name, schema)
            
            extraction_messages = [
                SystemMessage(content=extraction_prompt),
                HumanMessage(content=f"Nutzertext: {message}")
            ]
            
            extraction_response = self.llm_json.invoke(extraction_messages)
            validated_args, error = self._parse_and_validate(
                extraction_response.content,
                schema
            )
            
            if error:
                # Schema-Validierung fehlgeschlagen, aber Tool wurde gewählt
                # Gebe Tool trotzdem zurück mit leeren Args für Evaluierung
                return [{"name": tool_name, "args": {}}]
            
            # Erfolgreiche Extraktion
            args_dict = validated_args.model_dump(exclude_none=True)
            return [{"name": tool_name, "args": args_dict}]
            
        except Exception as e:
            return []  # Bei Fehler keine Tool-Auswahl


def create_constrained_agent() -> ConstrainedAgent:
    """Factory-Funktion für den Constrained Agent."""
    return ConstrainedAgent()
