"""
Confirmation Agent - Agent mit LLM-basierter Validierung.

Der Agent führt vor jedem kritischen Tool-Aufruf eine Selbstvalidierung durch:
1. Analysiert die Anfrage und plant den Tool-Aufruf
2. LLM bewertet SELBST ob der Tool-Call sinnvoll ist (Self-Critique)
3. Führt das Tool nur bei erfolgreicher LLM-Bestätigung aus

UNTERSCHIED ZUM CONSTRAINED AGENT:
- Constrained Agent: SCHEMA/REGEL-basierte Validierung (Pydantic, strikte Regeln)
- Confirmation Agent: MODELL-basierte Validierung (LLM entscheidet semantisch)

Kritische Tools, die Bestätigung erfordern:
- klips2_register: Account-Erstellung
- klips2_apply_study: Studienbewerbung
- klips2_change_password: Passwortänderung
- klips2_change_address: Adressänderung
- send_email: E-Mail-Versand
"""

import os
import uuid
import re
import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

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


# Logger für Confirmation Agent
logger = logging.getLogger(__name__)


# Tools die eine Bestätigung vor der Ausführung erfordern
CRITICAL_TOOLS = {
    "klips2_register": {
        "description": "KLIPS2-Account erstellen",
        "required_params": ["vorname", "nachname", "geschlecht", "geburtsdatum", "email", "staatsangehoerigkeit"],
        "optional_params": ["geburtsname", "sprache"],
        "fields": {
            "vorname": {"required": True, "desc": "Vorname der Person"},
            "nachname": {"required": True, "desc": "Nachname der Person"},
            "geschlecht": {"required": True, "desc": "männlich, weiblich oder divers"},
            "geburtsdatum": {"required": True, "desc": "Geburtsdatum im Format TT.MM.JJJJ"},
            "email": {"required": True, "desc": "E-Mail-Adresse mit @"},
            "staatsangehoerigkeit": {"required": True, "desc": "Staatsangehörigkeit"},
            "geburtsname": {"required": False, "desc": "Geburtsname falls abweichend"},
            "sprache": {"required": False, "desc": "Deutsch oder Englisch"}
        },
        "validations": {
            "email": r"^[^@]+@[^@]+\.[^@]+$",
            "geburtsdatum": r"^\d{2}\.\d{2}\.\d{4}$"
        }
    },
    "klips2_apply_study": {
        "description": "Studienbewerbung einreichen",
        "required_params": ["username", "password", "semester", "degree_type", "study_program", 
                           "gender", "birth_place", "nationality", "hzb_date", "hzb_type", 
                           "hzb_name", "hzb_grade", "hzb_school", "hzb_place"],
        "optional_params": ["entry_semester", "study_form", "birth_country", "hzb_country", 
                           "street", "zip_code", "city", "country"],
        "fields": {
            "username": {"required": True, "desc": "KLIPS2-Benutzername"},
            "password": {"required": True, "desc": "KLIPS2-Passwort"},
            "semester": {"required": True, "desc": "Zielsemester (z.B. WS2024)"},
            "degree_type": {"required": True, "desc": "Bachelor, Master oder Promotion"},
            "study_program": {"required": True, "desc": "Name des Studiengangs"},
            "gender": {"required": True, "desc": "Geschlecht"},
            "birth_place": {"required": True, "desc": "Geburtsort"},
            "nationality": {"required": True, "desc": "Staatsangehörigkeit"},
            "hzb_date": {"required": True, "desc": "Datum der Hochschulzugangsberechtigung"},
            "hzb_type": {"required": True, "desc": "Art der HZB (z.B. Abitur)"},
            "hzb_name": {"required": True, "desc": "Bezeichnung des Zeugnisses"},
            "hzb_grade": {"required": True, "desc": "Note der HZB"},
            "hzb_school": {"required": True, "desc": "Name der Schule"},
            "hzb_place": {"required": True, "desc": "Ort der HZB"},
            "entry_semester": {"required": False, "desc": "Fachsemester (Standard: 1)"},
            "study_form": {"required": False, "desc": "Erststudium oder Zweitstudium"},
            "birth_country": {"required": False, "desc": "Geburtsland (Standard: Deutschland)"},
            "hzb_country": {"required": False, "desc": "Land der HZB (Standard: Deutschland)"},
            "street": {"required": False, "desc": "Straße und Hausnummer"},
            "zip_code": {"required": False, "desc": "Postleitzahl"},
            "city": {"required": False, "desc": "Stadt"},
            "country": {"required": False, "desc": "Land (Standard: Deutschland)"}
        },
        "validations": {}
    },
    "klips2_change_password": {
        "description": "KLIPS2-Passwort ändern",
        "required_params": ["username", "password", "new_password"],
        "optional_params": [],
        "fields": {
            "username": {"required": True, "desc": "KLIPS2-Benutzername"},
            "password": {"required": True, "desc": "Aktuelles Passwort"},
            "new_password": {"required": True, "desc": "Neues Passwort"}
        },
        "validations": {}
    },
    "klips2_change_address": {
        "description": "KLIPS2-Adresse ändern",
        "required_params": ["username", "password", "street", "zip_code", "city"],
        "optional_params": ["country"],
        "fields": {
            "username": {"required": True, "desc": "KLIPS2-Benutzername"},
            "password": {"required": True, "desc": "KLIPS2-Passwort"},
            "street": {"required": True, "desc": "Straße und Hausnummer"},
            "zip_code": {"required": True, "desc": "Postleitzahl"},
            "city": {"required": True, "desc": "Stadt (MUSS explizit genannt sein!)"},
            "country": {"required": False, "desc": "Land (Standard: Deutschland)"}
        },
        "validations": {
            "zip_code": r"^\d{4,5}$"
        }
    },
    "send_email": {
        "description": "E-Mail senden",
        "required_params": ["subject", "body"],
        "optional_params": ["to"],
        "fields": {
            "to": {"required": False, "desc": "Empfänger-Adresse (Standard: Studierendensekretariat)"},
            "subject": {"required": True, "desc": "Betreff der E-Mail"},
            "body": {"required": True, "desc": "Text der E-Mail"}
        },
        "validations": {}
    }
}


class ConfirmationAgent:
    """
    Agent mit interner Validierungsschleife (Self-Critique Pattern).
    
    Bevor kritische Tools ausgeführt werden, validiert der Agent:
    1. Sind alle erforderlichen Parameter vorhanden?
    2. Haben die Parameter das korrekte Format?
    3. Ist der Tool-Aufruf im Kontext sinnvoll?
    
    Nur bei erfolgreicher Validierung wird das Tool ausgeführt.
    """
    
    def __init__(self):
        """Initialisiere den Confirmation Agent."""
        settings.validate()
        
        # LangSmith Tracing konfigurieren (falls aktiviert)
        if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            print(f"✅ LangSmith-Tracing aktiviert für Projekt: {settings.LANGSMITH_PROJECT}")
        
        # Context-Size nach Modellgröße
        MODEL_CTX_SIZES = {
            "0.5b": 2048,
            "1b": 4096,
            "3b": 8192,
            "8b": 8192,
            "20b": 16384,
            "70b": 16384,
        }
        
        model_lower = settings.OLLAMA_MODEL.lower()
        ctx_size = 8192
        for size_key, ctx_value in MODEL_CTX_SIZES.items():
            if size_key in model_lower:
                ctx_size = ctx_value
                break
        
        print(f"🔒 Initialisiere Confirmation Agent mit Modell: {settings.OLLAMA_MODEL} (ctx_size={ctx_size})")
        
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            num_ctx=ctx_size,
            timeout=settings.REQUEST_TIMEOUT,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
        
        # Tools initialisieren
        self.tools = self._create_tools()
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # Wrapper-Tools für Bestätigung erstellen
        self.wrapped_tools = self._create_wrapped_tools()
        
        # System-Prompt
        self.system_message = SystemMessage(content=self._get_system_prompt())
        
        # Agent erstellen mit gewrappten Tools
        self.agent = create_langgraph_agent(
            self.llm,
            self.wrapped_tools
        )
        
        # Recursion Limit
        self.recursion_limit = getattr(settings, 'CONFIRMATION_AGENT_RECURSION_LIMIT', 25)
        
        # Memory
        self.memory = []
        
        # Tracking für Evaluierung
        self.last_confirmation_result: Optional[Dict[str, Any]] = None
        self.confirmation_count = 0
        self.confirmed_count = 0
        self.rejected_count = 0
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools."""
        tools = []
        
        if settings.ENABLE_WEB_SCRAPER:
            tools.append(create_web_scraper_tool())
        
        if settings.ENABLE_DUCKDUCKGO:
            tools.append(create_duckduckgo_tool())
        
        try:
            rag_tool = create_university_rag_tool()
            tools.append(rag_tool)
            print("  ✅ Universitäts-RAG-Tool geladen")
        except Exception as e:
            print(f"  ⚠️ RAG-Tool konnte nicht geladen werden: {e}")
        
        if settings.ENABLE_EMAIL:
            try:
                email_tool = create_email_tool()
                tools.append(email_tool)
                print("  ✅ E-Mail-Tool geladen")
            except Exception as e:
                print(f"  ⚠️ E-Mail-Tool konnte nicht geladen werden: {e}")
        
        if settings.ENABLE_KLIPS:
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
    
    def _create_wrapped_tools(self) -> List[BaseTool]:
        """Erstelle gewrappte Tools mit Bestätigungslogik."""
        wrapped = []
        
        for tool in self.tools:
            if tool.name in CRITICAL_TOOLS:
                # Kritische Tools mit Confirmation-Wrapper
                wrapped.append(self._wrap_critical_tool(tool))
            else:
                # Nicht-kritische Tools direkt durchreichen
                wrapped.append(tool)
        
        return wrapped
    
    def _wrap_critical_tool(self, original_tool: BaseTool) -> BaseTool:
        """Wrappe ein kritisches Tool mit Bestätigungslogik."""
        from langchain_core.tools import StructuredTool
        
        tool_config = CRITICAL_TOOLS[original_tool.name]
        agent_ref = self  # Referenz auf Agent für den Wrapper
        
        def confirmation_wrapper(**kwargs) -> str:
            """Wrapper der vor Tool-Ausführung validiert."""
            tool_name = original_tool.name
            
            # 1. Validierung durchführen
            validation_result = agent_ref._validate_tool_call(tool_name, kwargs)
            
            # Tracking
            agent_ref.confirmation_count += 1
            agent_ref.last_confirmation_result = {
                "tool": tool_name,
                "args": kwargs,
                "validation": validation_result
            }
            
            if validation_result["confirmed"]:
                # 2. Bei erfolgreicher Validierung: Tool ausführen
                agent_ref.confirmed_count += 1
                logger.info(f"Tool '{tool_name}' bestätigt und wird ausgeführt")
                print(f"  ✅ Bestätigt: {tool_name}")
                
                try:
                    result = original_tool.invoke(kwargs)
                    logger.info(f"Tool '{tool_name}' erfolgreich ausgeführt")
                    return result
                except ValueError as e:
                    # Validierungsfehler (z.B. ungültige Eingabewerte)
                    logger.warning(f"Validierungsfehler bei Tool '{tool_name}': {str(e)}")
                    return f"Validierungsfehler: {str(e)}"
                except ConnectionError as e:
                    # Netzwerkfehler
                    logger.error(f"Netzwerkfehler bei Tool '{tool_name}': {str(e)}")
                    return f"Netzwerkfehler: Das System ist momentan nicht erreichbar."
                except Exception as e:
                    # Unerwartete Fehler - vollständig loggen für Debugging
                    logger.error(
                        f"Unerwarteter Fehler bei Tool-Ausführung '{tool_name}': {str(e)}",
                        exc_info=True
                    )
                    return f"Fehler bei Tool-Ausführung: {str(e)}"
            else:
                # 3. Bei fehlgeschlagener Validierung: Fehler zurückgeben
                agent_ref.rejected_count += 1
                logger.warning(f"Tool '{tool_name}' abgelehnt: {validation_result['reason']}")
                print(f"  ❌ Abgelehnt: {tool_name} - {validation_result['reason']}")
                
                return (
                    f"⚠️ Validierung fehlgeschlagen für {tool_config['description']}:\n"
                    f"{validation_result['reason']}\n\n"
                    "Bitte ergänze die fehlenden Informationen."
                )
        
        # Neues Tool mit gleichem Schema aber Wrapper-Funktion erstellen
        return StructuredTool.from_function(
            func=confirmation_wrapper,
            name=original_tool.name,
            description=original_tool.description,
            args_schema=original_tool.args_schema,
            return_direct=False
        )
    
    def _validate_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM-basierte Validierung eines Tool-Aufrufs (Self-Critique).
        
        Das LLM bewertet SELBST ob der Tool-Call sinnvoll ist:
        - Sind alle wichtigen Parameter vorhanden?
        - Sind die Werte plausibel (keine Platzhalter, keine erfundenen Daten)?
        - Passt der Call zum Tool-Zweck?
        
        Dies ist MODELL-BASIERT, nicht regel-basiert wie beim Constrained Agent.
        
        Returns:
            Dict mit:
            - confirmed: bool - Ob die Validierung erfolgreich war
            - reason: str - Begründung der LLM-Entscheidung
        """
        config = CRITICAL_TOOLS.get(tool_name, {})
        tool_description = config.get("description", tool_name)
        fields = config.get("fields", {})
        
        # Formatiere Argumente für LLM-Bewertung
        args_formatted = json.dumps(args, indent=2, ensure_ascii=False)
        
        # Formatiere ALLE Tools mit ihren Feldern (Kontext für LLM)
        all_tools_formatted = []
        for t_name, t_config in CRITICAL_TOOLS.items():
            t_desc = t_config.get("description", t_name)
            t_fields = t_config.get("fields", {})
            
            req_fields = []
            opt_fields = []
            for fname, finfo in t_fields.items():
                if finfo["required"]:
                    req_fields.append(f'      "{fname}": <{finfo["desc"]}>')
                else:
                    opt_fields.append(f'      "{fname}": <{finfo["desc"]}>')
            
            tool_str = f"  • {t_name} - {t_desc}"
            if req_fields:
                tool_str += f"\n    PFLICHT:\n" + "\n".join(req_fields)
            if opt_fields:
                tool_str += f"\n    OPTIONAL:\n" + "\n".join(opt_fields)
            
            all_tools_formatted.append(tool_str)
        
        all_tools_str = "\n\n".join(all_tools_formatted)
        
        # Separate Felder für das AKTUELLE Tool (zur Hervorhebung)
        required_fields = []
        optional_fields = []
        for field_name, field_info in fields.items():
            desc = field_info["desc"]
            if field_info["required"]:
                required_fields.append(f'    "{field_name}": <{desc}>')
            else:
                optional_fields.append(f'    "{field_name}": <{desc}>')
        
        required_str = "\n".join(required_fields) if required_fields else "    (keine)"
        optional_str = "\n".join(optional_fields) if optional_fields else "    (keine)"
        
        # Validation Prompt für LLM
        validation_prompt = f"""Du bist ein Validierungs-Agent. Bewerte ob dieser Tool-Call sinnvoll und vollständig ist.

KONTEXT: Verfügbare kritische Tools mit ihren Feldern:
{all_tools_str}

================================================================================
ZU VALIDIERENDER TOOL-CALL:
================================================================================

TOOL: {tool_name}
BESCHREIBUNG: {tool_description}

PFLICHTFELDER (müssen ALLE vorhanden sein):
{required_str}

OPTIONALE FELDER (können fehlen):
{optional_str}

GEPLANTER TOOL-CALL:
{args_formatted}

BEWERTUNGSKRITERIEN:
1. Sind ALLE oben aufgelisteten Pflichtfelder vorhanden? (nicht None, nicht leer)
2. Sind die Werte plausibel und realistisch?
3. Keine Platzhalter wie "TBD", "N/A", "unbekannt", "keine Angabe"
4. Keine offensichtlich erfundenen Daten
5. Bei Email-Feldern: Muss @ enthalten
6. Bei Datums-Feldern: Muss vollständiges Datum sein (TT.MM.JJJJ oder ähnlich)
7. Bei Stadt/Ort-Feldern: MUSS explizit genannt sein (nicht aus PLZ ableitbar)

WICHTIG:
- Wenn auch nur EIN Pflichtfeld fehlt oder leer ist → confirmed=false
- Format-Variationen sind OK (z.B. "m"/"männlich", verschiedene Datumsformate)
- Optionale Felder dürfen fehlen (kein Problem)
- Bei Ablehnung: Nenne die KONKRETEN fehlenden/ungültigen Felder

ENTSCHEIDUNG:
Antworte EXAKT in diesem JSON-Format:
{{"confirmed": true, "reason": "Alle Pflichtfelder vollständig und plausibel"}}
oder
{{"confirmed": false, "reason": "Fehlende Pflichtfelder: <feldname1, feldname2, ...>"}}

Sei STRENG bei Pflichtfeldern, FAIR bei Formaten."""

        try:
            # LLM-Bewertung einholen
            response = self.llm.invoke(
                [SystemMessage(content=validation_prompt)],
                format="json"  # Nutze JSON-Modus für strukturierte Antwort
            )
            
            # Parse LLM-Antwort
            result_text = response.content.strip()
            
            # Bereinige JSON (entferne Markdown-Blöcke falls vorhanden)
            if result_text.startswith("```"):
                result_text = re.sub(r'^```(?:json)?\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)
            
            result = json.loads(result_text)
            
            # Validiere Antwort-Struktur
            if "confirmed" not in result:
                logger.error(f"LLM-Validierung fehlerhaft: 'confirmed' fehlt in {result}")
                return {
                    "confirmed": False,
                    "reason": "Interner Fehler: LLM-Validierung fehlgeschlagen (ungültige Antwort)"
                }
            
            return {
                "confirmed": bool(result["confirmed"]),
                "reason": str(result.get("reason", "Keine Begründung")),
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM-Validierung JSON-Parse-Fehler: {e}\nResponse: {result_text}")
            return {
                "confirmed": False,
                "reason": f"Interner Fehler: LLM-Antwort nicht parsebar"
            }
        except Exception as e:
            logger.error(f"LLM-Validierung fehlgeschlagen: {e}", exc_info=True)
            return {
                "confirmed": False,
                "reason": f"Interner Fehler: {str(e)}"
            }
    
    def _get_system_prompt(self) -> str:
        """System-Prompt für den Confirmation Agent."""
        return """Du bist ein KI-Assistent für KLIPS 2.0, das Campus-Management-System der Universität zu Köln.

## WANN EIN TOOL AUFRUFEN?

✅ Tool aufrufen bei:
- KLIPS2-Aktionen (registrieren, bewerben, Adresse/Passwort ändern, Kurs abfragen)
  * NUR wenn ALLE erforderlichen Daten VOLLSTÄNDIG vorliegen
  * NUR wenn die Anfrage SPEZIFISCH und KLAR ist
- Wissensfragen zur Universität → university_knowledge_search
  * NUR bei SPEZIFISCHEN Fragen (z.B. "Wie sind die Öffnungszeiten der Bibliothek?")
- Explizite Internet-Suche → duckduckgo_search (bei "Search for", "Suche im Internet")
- URL genannt → web_scraper
- E-Mail senden → send_email (mit vollständigem Betreff und Text)

❌ KEIN Tool bei:
- Begrüßungen ("Hallo!", "Wie geht's?")
- Fragen über dich selbst ("Was kannst du?")
- Einfache Rechenaufgaben, Übersetzungen
- Allgemeine Wissensfragen ohne Uni-Bezug
- **VAGE Anfragen**: "irgendwann", "irgendwie", "irgendwelche", "vielleicht", "würde gerne"
- **Reine FRAGEN** ohne Handlungsabsicht: "Kann man..?", "Ist es möglich..?"
- **UNVOLLSTÄNDIGE Daten**: Wenn Pflichtfelder fehlen → FRAGE NACH, rufe KEIN Tool auf

## DEINE BESONDERHEIT: INTERNE VALIDIERUNG

Vor jedem kritischen Tool-Aufruf prüft das System automatisch:
1. Ob alle erforderlichen Parameter vorhanden sind
2. Ob die Parameter im korrekten Format vorliegen

## VERFÜGBARE TOOLS

### Kritische Tools (mit Validierung):
- **klips2_register**: Pflicht: vorname, nachname, geschlecht, geburtsdatum, email, staatsangehoerigkeit
- **klips2_apply_study**: Pflicht: username, password, semester, degree_type, study_program
- **klips2_change_password**: Pflicht: username, password, new_password
- **klips2_change_address**: Pflicht: username, password, street, zip_code, city
- **send_email**: Pflicht: subject, body

### Nicht-kritische Tools:
- **university_knowledge_search**: Bei Uni-Wissensfragen
- **duckduckgo_search**: Bei "Search for", "Suche im Internet"
- **web_scraper**: Bei konkreten URLs
- **klips2_get_course_details**: Bei Kursabfragen

## PARAMETER-EXTRAKTION

Extrahiere Daten aus Fließtext:
- "Ich bin Max Müller" → vorname="Max", nachname="Müller"
- "geboren am 15.03.1999" → geburtsdatum="15.03.1999"
- "männlich" / "male" / "m" → geschlecht="männlich"

## MULTI-STEP KONVERSATIONEN

Wenn im Prompt "Previous conversation:" steht:
1. Analysiere ALLE Informationen aus vorherigen Nachrichten
2. Kombiniere sie mit der aktuellen Nachricht
3. Wenn dadurch ALLE Pflichtfelder vorhanden sind → Tool aufrufen
4. Beispiel:
   - Vorherige Nachricht: "Bewerbung Informatik, Login: user@uni.de, ..."
   - Aktuelle Nachricht: "Männlich, geboren 15.03.1999 in Köln"
   - → Kombiniere beide für vollständige klips2_apply_study Daten

## MULTI-TOOL-ANFRAGEN (WICHTIG!)

**Wenn der User MEHRERE Aktionen in EINER Nachricht fordert:**
- "Suche X **und dann** hole Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]
- "Hole Kursdetails **und schicke** E-Mail" → BEIDE Tools aufrufen: [klips2_get_course_details, send_email]
- "Recherchiere X, **dann** Details zu Y" → BEIDE Tools aufrufen: [duckduckgo_search, klips2_get_course_details]

Signalwörter für Multi-Tool:
- "und dann", "danach", "anschließend", "then"
- "und schicke", "und sende", "and send"
- Mehrere Aktionsverben in einer Anfrage

**REGEL:** Bei Multi-Tool-Anfragen → ALLE relevanten Tools aufrufen!

Antworte in der Sprache des Nutzers."""
    
    def chat(self, message: str, session_id: str = None) -> str:
        """Führe eine Unterhaltung mit dem Agenten."""
        try:
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            # Reset confirmation tracking für diesen Chat
            self.last_confirmation_result = None
            
            # PRE-CHECK: Prüfe auf vage Anfragen BEVOR Tools aufgerufen werden
            if self._is_vague_request(message):
                # Direkte Antwort ohne Tool-Aufruf
                vague_response = self._generate_direct_response_for_vague(message)
                ai_response = AIMessage(content=vague_response)
                self.memory.append(HumanMessage(content=message))
                self.memory.append(ai_response)
                return vague_response
            
            human_message = HumanMessage(content=message)
            self.memory.append(human_message)
            
            if len(self.memory) > settings.MEMORY_SIZE:
                self.memory = self.memory[-settings.MEMORY_SIZE:]
            
            agent_input = {
                "messages": [self.system_message] + self.memory
            }
            
            config = None
            if settings.LANGSMITH_TRACING:
                config = {
                    "metadata": {
                        "session_id": session_id,
                        "agent_type": "confirmation",
                        "user_message": message[:100] + "..." if len(message) > 100 else message,
                    },
                    "recursion_limit": self.recursion_limit
                }
            else:
                config = {
                    "recursion_limit": self.recursion_limit
                }
            
            response = self.agent.invoke(agent_input, config=config)
            
            ai_message = response["messages"][-1]
            response_text = ai_message.content
            
            if not response_text:
                for msg in reversed(response["messages"]):
                    if hasattr(msg, 'content') and msg.content:
                        response_text = msg.content
                        break
                
                if not response_text:
                    response_text = "Ich konnte keine Antwort generieren. Bitte versuchen Sie es erneut."
            
            # Self-Reflection: Agent überprüft seine eigene Antwort
            response_text = self._self_reflect_on_response(message, response_text)
            
            ai_response = AIMessage(content=response_text)
            self.memory.append(ai_response)
            
            return response_text
            
        except Exception as e:
            error_msg = f"Fehler beim Verarbeiten der Nachricht: {str(e)}"
            self.memory.append(AIMessage(content=error_msg))
            return error_msg
    
    def get_available_tools(self) -> List[str]:
        """Gebe Liste der verfügbaren Tools zurück."""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self):
        """Lösche Konversationshistorie."""
        self.memory = []
        self.last_confirmation_result = None
    
    def get_confirmation_stats(self) -> Dict[str, Any]:
        """Gebe Statistiken zur Bestätigungslogik zurück."""
        confirmation_rate = 0
        if self.confirmation_count > 0:
            confirmation_rate = self.confirmed_count / self.confirmation_count
        
        return {
            "total_confirmations": self.confirmation_count,
            "confirmed": self.confirmed_count,
            "rejected": self.rejected_count,
            "confirmation_rate": confirmation_rate,
            "last_confirmation": self.last_confirmation_result
        }
    
    def _is_vague_request(self, message: str) -> bool:
        """
        Prüfe ob eine Anfrage zu vage ist für Tool-Aufrufe.
        
        Vage Anfragen sollten direkt beantwortet werden ohne Tool.
        """
        msg_lower = message.lower()
        
        # Vage Muster
        vague_patterns = [
            r"\birgendwann\b",
            r"\birgendwie\b", 
            r"\birgendwelche?\b",
            r"\birgendwo\b",
            r"\bvielleicht\b",
            r"\bwürde gerne\b",
            r"\bkönnte ich\b",
            r"\bwäre es möglich\b",
        ]
        
        # Reine Fragen ohne Handlungsabsicht
        question_patterns = [
            r"^kann man\b",
            r"^ist es möglich\b",
            r"^gibt es\b",
            r"^wie viel\b",
            r"^wann\b",
        ]
        
        # Prüfe vage Patterns
        for pattern in vague_patterns:
            if re.search(pattern, msg_lower):
                return True
        
        # Prüfe Frage-Patterns (nur am Anfang)
        for pattern in question_patterns:
            if re.search(pattern, msg_lower):
                # Zusätzlich: Keine spezifischen Daten (Zahlen, @-Zeichen)
                if not re.search(r'\d|@', message):
                    return True
        
        return False
    
    def _generate_direct_response_for_vague(self, message: str) -> str:
        """
        Generiere eine direkte Antwort für vage Anfragen.
        
        Nutzt das LLM ohne Tools.
        """
        prompt = f"""Beantworte die folgende Frage direkt und hilfreich, OHNE Tools zu verwenden.
Die Frage ist zu vage oder allgemein für eine Tool-Ausführung.

Frage: {message}

Gib eine informative Antwort und ermutige den Nutzer bei Bedarf, spezifischer zu werden."""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def _self_reflect_on_response(self, user_message: str, draft_response: str, max_iterations: int = 3) -> str:
        """
        Self-Reflection: Agent überprüft seine eigene Antwort und verbessert sie.
        
        Der Agent fragt sich selbst:
        1. Ist meine Antwort vollständig?
        2. Beantwortet sie die Nutzerfrage klar?
        3. Fehlen wichtige Informationen?
        4. Ist der Ton angemessen?
        
        Falls nicht zufrieden: Überarbeite die Antwort.
        
        Args:
            user_message: Die ursprüngliche Nutzerfrage
            draft_response: Die initiale Antwort des Agenten
            max_iterations: Maximale Anzahl Reflexionsschleifen
            
        Returns:
            Die finale, verbesserte Antwort
        """
        current_response = draft_response
        
        for iteration in range(max_iterations):
            reflection_prompt = f"""Du bist ein kritischer Reviewer. Bewerte die folgende Antwort.

NUTZERFRAGE:
{user_message}

ENTWURFSANTWORT:
{current_response}

BEWERTUNGSKRITERIEN:
1. Vollständigkeit: Werden alle Aspekte der Frage beantwortet?
2. Klarheit: Ist die Antwort verständlich und strukturiert?
3. Korrektheit: Sind die Informationen korrekt (keine falschen Versprechen)?
4. Hilfsbereitschaft: Wird der Nutzer bei nächsten Schritten unterstützt?
5. Professionalität: Ist der Ton angemessen?

WICHTIG:
- Bei Tool-Ausführungen: Ist das Ergebnis klar kommuniziert?
- Bei Fehlern/Ablehnungen: Wird dem Nutzer geholfen, das Problem zu lösen?
- Bei fehlenden Infos: Wird konkret nachgefragt (nicht vage)?

ENTSCHEIDUNG:
Antworte in diesem JSON-Format:
{{
  "satisfactory": true/false,
  "issues": ["Problem 1", "Problem 2", ...],
  "suggestion": "Konkrete Verbesserungsvorschläge"
}}

Wenn satisfactory=false, beschreibe WIE die Antwort verbessert werden sollte."""

            try:
                # LLM-Reflexion
                reflection_response = self.llm.invoke(
                    [SystemMessage(content=reflection_prompt)],
                    format="json"
                )
                
                reflection_text = reflection_response.content.strip()
                
                # Bereinige JSON
                if reflection_text.startswith("```"):
                    reflection_text = re.sub(r'^```(?:json)?\n?', '', reflection_text)
                    reflection_text = re.sub(r'\n?```$', '', reflection_text)
                
                reflection = json.loads(reflection_text)
                
                # Wenn zufrieden: Fertig
                if reflection.get("satisfactory", False):
                    logger.info(f"Self-Reflection: Antwort nach {iteration + 1} Iteration(en) akzeptiert")
                    print(f"  ✅ Self-Reflection: Antwort OK (Iteration {iteration + 1})")
                    break
                
                # Wenn nicht zufrieden: Überarbeite
                issues = reflection.get("issues", [])
                suggestion = reflection.get("suggestion", "")
                
                logger.info(f"Self-Reflection: Antwort unzureichend. Issues: {issues}")
                print(f"  🔄 Self-Reflection: Überarbeite Antwort (Iteration {iteration + 1})")
                
                # Generiere verbesserte Antwort
                improvement_prompt = f"""Die folgende Antwort ist nicht gut genug. Verbessere sie.

NUTZERFRAGE:
{user_message}

BISHERIGE ANTWORT:
{current_response}

PROBLEME:
{chr(10).join('- ' + issue for issue in issues)}

VERBESSERUNGSVORSCHLAG:
{suggestion}

AUFGABE:
Schreibe eine VERBESSERTE Version der Antwort, die diese Probleme behebt.
Antworte DIREKT mit der verbesserten Antwort (kein JSON, keine Metakommentare)."""

                improved_response = self.llm.invoke([HumanMessage(content=improvement_prompt)])
                current_response = improved_response.content.strip()
                
            except json.JSONDecodeError as e:
                logger.warning(f"Self-Reflection JSON-Parse-Fehler: {e}. Behalte aktuelle Antwort.")
                break
            except Exception as e:
                logger.error(f"Self-Reflection fehlgeschlagen: {e}. Behalte aktuelle Antwort.")
                break
        
        return current_response
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Gebe Zusammenfassung des Memory zurück."""
        human_messages = [msg for msg in self.memory if isinstance(msg, HumanMessage)]
        ai_messages = [msg for msg in self.memory if isinstance(msg, AIMessage)]
        
        return {
            "total_messages": len(self.memory),
            "human_messages": len(human_messages),
            "ai_messages": len(ai_messages),
            "last_messages": [
                msg.content[:100] + "..." if len(msg.content) > 100 else msg.content 
                for msg in self.memory[-5:]
            ]
        }
    
    def get_tool_selection(self, message: str) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl mit Confirmation-Agent-Logik (für Evaluierung).
        
        Diese Methode führt die spezifische Confirmation-Agent-Logik durch:
        1. LLM mit gewrappten Tools aufrufen (Tools haben Bestätigungslogik)
        2. Tool-Calls extrahieren und validieren
        3. Bei Ablehnung: Agent bekommt Fehlermeldung und kann nochmal überlegen
        4. Retry-Schleife (max. 2 Versuche)
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            Liste der ausgewählten Tool-Calls (nach Validierung bestätigt oder abgelehnt)
        """
        from langchain_core.messages import HumanMessage, ToolMessage
        
        try:
            # LLM mit gewrappten Tools aufrufen
            llm_with_tools = self.llm.bind_tools(self.wrapped_tools)
            
            messages = [
                self.system_message,
                HumanMessage(content=message)
            ]
            
            max_retries = 2
            all_tool_calls = []
            
            for attempt in range(max_retries):
                response = llm_with_tools.invoke(messages)
                
                # Tool-Calls extrahieren
                current_tool_calls = []
                has_rejection = False
                
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    for tc in response.tool_calls:
                        tool_name = tc.get("name", "")
                        tool_args = tc.get("args", {})
                        tool_call_id = tc.get("id", f"call_{len(current_tool_calls)}")
                        
                        # Wenn kritisches Tool: Validierung durchführen
                        if tool_name in CRITICAL_TOOLS:
                            validation_result = self._validate_tool_call(tool_name, tool_args)
                            
                            # Tracking (wie bei echtem Aufruf)
                            self.confirmation_count += 1
                            
                            if validation_result["confirmed"]:
                                self.confirmed_count += 1
                                current_tool_calls.append({
                                    "name": tool_name,
                                    "args": tool_args,
                                    "id": tool_call_id
                                })
                            else:
                                # Tool wurde abgelehnt
                                self.rejected_count += 1
                                has_rejection = True
                                
                                # Fehlermeldung für Retry
                                tool_config = CRITICAL_TOOLS[tool_name]
                                error_message = (
                                    f"⚠️ Validierung fehlgeschlagen für {tool_config['description']}:\n"
                                    f"{validation_result['reason']}\n\n"
                                    "Bitte ergänze die fehlenden Informationen."
                                )
                                
                                # Tool-Call mit Ablehnung speichern
                                current_tool_calls.append({
                                    "name": tool_name,
                                    "args": tool_args,
                                    "id": tool_call_id,
                                    "validation_failed": True,
                                    "validation_reason": validation_result["reason"]
                                })
                                
                                # Füge Fehlermeldung als Tool-Response hinzu für nächste Iteration
                                messages.append(response)
                                messages.append(ToolMessage(
                                    content=error_message,
                                    tool_call_id=tool_call_id
                                ))
                        else:
                            # Nicht-kritische Tools direkt durchreichen
                            current_tool_calls.append({
                                "name": tool_name,
                                "args": tool_args,
                                "id": tool_call_id
                            })
                
                # Speichere Tool-Calls dieser Iteration
                all_tool_calls.extend(current_tool_calls)
                
                # Wenn keine Ablehnung oder keine Tool-Calls → fertig
                if not has_rejection or not current_tool_calls:
                    break
                
                # Wenn letzte Iteration → fertig
                if attempt >= max_retries - 1:
                    break
            
            return all_tool_calls
            
        except Exception as e:
            logger.error(f"Fehler bei Tool-Selektion: {e}", exc_info=True)
            return []  # Bei Fehler keine Tool-Auswahl


def create_confirmation_agent() -> ConfirmationAgent:
    """Factory-Funktion für den Confirmation Agent."""
    return ConfirmationAgent()
