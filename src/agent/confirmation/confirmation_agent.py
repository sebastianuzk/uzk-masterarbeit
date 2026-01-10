"""
Confirmation Agent - Agent mit interner Validierungsschleife.

Der Agent führt vor jedem kritischen Tool-Aufruf eine Selbstvalidierung durch:
1. Analysiert die Anfrage und plant den Tool-Aufruf
2. Führt eine interne Bestätigung durch (Self-Critique)
3. Führt das Tool nur bei erfolgreicher Validierung aus

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
        "validations": {
            "email": r"^[^@]+@[^@]+\.[^@]+$",
            "geburtsdatum": r"^\d{2}\.\d{2}\.\d{4}$"
        }
    },
    "klips2_apply_study": {
        "description": "Studienbewerbung einreichen",
        "required_params": ["username", "password", "semester", "degree_type", "study_program"],
        "validations": {}
    },
    "klips2_change_password": {
        "description": "KLIPS2-Passwort ändern",
        "required_params": ["username", "password", "new_password"],
        "validations": {}
    },
    "klips2_change_address": {
        "description": "KLIPS2-Adresse ändern",
        "required_params": ["username", "password", "street", "zip_code", "city"],
        "validations": {
            "zip_code": r"^\d{4,5}$"
        }
    },
    "send_email": {
        "description": "E-Mail senden",
        "required_params": ["subject", "body"],
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
        
        try:
            email_tool = create_email_tool()
            tools.append(email_tool)
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
        Validiere einen Tool-Aufruf intern (Self-Critique).
        
        Prüft:
        1. Erforderliche Parameter vorhanden
        2. Parameter-Formate korrekt
        3. Keine Platzhalter oder erfundene Daten
        4. Stadt bei klips2_change_address MUSS explizit angegeben sein
        
        Returns:
            Dict mit:
            - confirmed: bool - Ob die Validierung erfolgreich war
            - reason: str - Begründung bei Fehlschlag
            - missing_params: List[str] - Fehlende Parameter
            - invalid_params: List[str] - Ungültige Parameter
        """
        config = CRITICAL_TOOLS.get(tool_name, {})
        required_params = config.get("required_params", [])
        validations = config.get("validations", {})
        
        missing_params = []
        invalid_params = []
        
        # 1. Prüfe erforderliche Parameter
        for param in required_params:
            value = args.get(param)
            # Prüfe ob Wert fehlt: None oder leerer String (False und 0 sind gültige Werte)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing_params.append(param)
            # KRITISCH: Verhindere Platzhalter-Werte
            elif isinstance(value, str):
                value_lower = value.lower().strip()
                # Prüfe auf Platzhalter
                if value_lower in ['n/a', 'tbd', 'unknown', 'unbekannt', 'keine angabe']:
                    missing_params.append(f"{param} (Platzhalter: '{value}')")
        
        # 1b. SPEZIAL: Bei klips2_change_address MUSS city EXPLIZIT gegeben sein
        # Verhindere dass Agent Stadt aus PLZ ableitet!
        if tool_name == "klips2_change_address":
            city = args.get("city", "").strip()
            zip_code = args.get("zip_code", "").strip()
            
            # Wenn Stadt leer ist oder nur aus PLZ abgeleitet
            if not city:
                missing_params.append("city (MUSS explizit angegeben werden)")
            # Prüfe ob Stadt wahrscheinlich aus PLZ inferiert wurde
            # (z.B. 50667 → "Köln", aber Stadt war nicht im Input)
            elif city and zip_code:
                # Bekannte PLZ-Stadt-Mappings die vermieden werden sollten
                known_mappings = {
                    "50667": "köln", "51063": "köln", "50672": "köln",
                    "10115": "berlin", "80331": "münchen"
                }
                if zip_code in known_mappings and city.lower() == known_mappings[zip_code]:
                    # Warnung: Dies könnte eine Inferenz sein
                    # Wir akzeptieren es, aber mit Vorsicht
                    pass  # Könnte verschärft werden zu: missing_params.append("city (erscheint inferiert)")
        
        # 2. Prüfe Format-Validierungen
        for param, pattern in validations.items():
            value = args.get(param)
            if value and not re.match(pattern, str(value)):
                invalid_params.append(f"{param} (Format ungültig: {value})")
        
        # 3. Ergebnis zusammenstellen
        if missing_params or invalid_params:
            reasons = []
            if missing_params:
                reasons.append(f"Fehlende Parameter: {', '.join(missing_params)}")
            if invalid_params:
                reasons.append(f"Ungültige Parameter: {', '.join(invalid_params)}")
            
            return {
                "confirmed": False,
                "reason": "\n".join(reasons),
                "missing_params": missing_params,
                "invalid_params": invalid_params
            }
        
        return {
            "confirmed": True,
            "reason": "Alle Parameter vorhanden und gültig",
            "missing_params": [],
            "invalid_params": []
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
                    }
                }
            
            if config is not None:
                response = self.agent.invoke(agent_input, config=config)
            else:
                response = self.agent.invoke(agent_input)
            
            ai_message = response["messages"][-1]
            response_text = ai_message.content
            
            if not response_text:
                for msg in reversed(response["messages"]):
                    if hasattr(msg, 'content') and msg.content:
                        response_text = msg.content
                        break
                
                if not response_text:
                    response_text = "Ich konnte keine Antwort generieren. Bitte versuchen Sie es erneut."
            
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
        2. Tool-Calls extrahieren
        3. Validierung durchführen (wie bei echtem Aufruf, aber ohne Ausführung)
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            Liste der ausgewählten Tool-Calls (nach Validierung bestätigt oder abgelehnt)
        """
        from langchain_core.messages import HumanMessage
        
        try:
            # LLM mit gewrappten Tools aufrufen
            llm_with_tools = self.llm.bind_tools(self.wrapped_tools)
            
            messages = [
                self.system_message,
                HumanMessage(content=message)
            ]
            
            response = llm_with_tools.invoke(messages)
            
            # Tool-Calls extrahieren
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_name = tc.get("name", "")
                    tool_args = tc.get("args", {})
                    
                    # Wenn kritisches Tool: Validierung durchführen
                    if tool_name in CRITICAL_TOOLS:
                        validation_result = self._validate_tool_call(tool_name, tool_args)
                        
                        # Tracking (wie bei echtem Aufruf)
                        self.confirmation_count += 1
                        
                        if validation_result["confirmed"]:
                            self.confirmed_count += 1
                            tool_calls.append({"name": tool_name, "args": tool_args})
                        else:
                            # Tool wurde abgelehnt - trotzdem zurückgeben mit Flag
                            self.rejected_count += 1
                            tool_calls.append({
                                "name": tool_name,
                                "args": tool_args,
                                "validation_failed": True,
                                "validation_reason": validation_result["reason"]
                            })
                    else:
                        # Nicht-kritische Tools direkt durchreichen
                        tool_calls.append({"name": tool_name, "args": tool_args})
            
            return tool_calls
            
        except Exception as e:
            return []  # Bei Fehler keine Tool-Auswahl


def create_confirmation_agent() -> ConfirmationAgent:
    """Factory-Funktion für den Confirmation Agent."""
    return ConfirmationAgent()
