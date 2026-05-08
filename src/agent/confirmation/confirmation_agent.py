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

import re
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

from config.logging_config import get_logger
from config.settings import settings
from src.agent.agent_config import setup_langsmith_tracing, get_recursion_limit
from src.agent.llm_factory import create_llm, create_json_llm
from src.agent.tool_loader import load_tool_safely, load_tools_batch, load_klips_tools
from src.agent.tool_specs import TOOL_SPECS
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
logger = get_logger(__name__)


# Tools die eine Bestätigung vor der Ausführung erfordern
CRITICAL_TOOL_NAMES = {
    "klips2_register",
    "klips2_apply_study",
    "klips2_change_password",
    "klips2_change_address",
    "send_email",
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
        setup_langsmith_tracing()
        
        # LLM initialisieren mit zentraler Factory
        self.llm = create_llm()
        # Separater LLM mit JSON-Modus für strukturierte Validierungs-/Reflexions-Antworten.
        # Wichtig: format="json" als invoke()-Kwarg wird von ChatOllama nicht zuverlässig
        # übernommen und von ChatOpenAI/ChatAnthropic stillschweigend ignoriert.
        self.llm_json = create_json_llm()

        logger.info(f"🔒 Initialisiere Confirmation Agent mit Modell: {settings.OLLAMA_MODEL}")
        
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
        
        # Recursion Limit from centralized config
        self.recursion_limit = get_recursion_limit("confirmation")
        
        # Memory
        self.memory = []
        
        # Tracking für Evaluierung
        self.last_confirmation_result: Optional[Dict[str, Any]] = None
        self.confirmation_count = 0
        self.confirmed_count = 0
        self.rejected_count = 0
        self.conversation_trace: List[Dict[str, Any]] = []
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools."""
        tools = []
        
        logger.debug(f"Tool Flags: WEB={settings.ENABLE_WEB_SCRAPER}, DDG={settings.ENABLE_DUCKDUCKGO}, EMAIL={settings.ENABLE_EMAIL}, KLIPS={settings.ENABLE_KLIPS}")
        
        if settings.ENABLE_WEB_SCRAPER:
            web_tool = load_tool_safely(create_web_scraper_tool, "Web-Scraper")
            if web_tool:
                tools.append(web_tool)
        
        if settings.ENABLE_DUCKDUCKGO:
            ddg_tool = load_tool_safely(create_duckduckgo_tool, "DuckDuckGo")
            if ddg_tool:
                tools.append(ddg_tool)
        
        rag_tool = load_tool_safely(create_university_rag_tool, "Universitäts-RAG") if settings.ENABLE_RAG_TOOL else None
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
    
    def _create_wrapped_tools(self) -> List[BaseTool]:
        """Erstelle gewrappte Tools mit Bestätigungslogik."""
        wrapped = []
        
        for tool in self.tools:
            if tool.name in CRITICAL_TOOL_NAMES:
                # Kritische Tools mit Confirmation-Wrapper
                wrapped.append(self._wrap_critical_tool(tool))
            else:
                # Nicht-kritische Tools direkt durchreichen
                wrapped.append(tool)
        
        return wrapped
    
    def _wrap_critical_tool(self, original_tool: BaseTool) -> BaseTool:
        """Wrappe ein kritisches Tool mit Bestätigungslogik."""
        from langchain_core.tools import StructuredTool
        
        tool_spec = TOOL_SPECS.get(original_tool.name, {})
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
                logger.info(f"✅ Tool '{tool_name}' bestätigt und wird ausgeführt")
                
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
                logger.warning(f"❌ Tool '{tool_name}' abgelehnt: {validation_result['reason']}")
                
                return (
                    f"⚠️ Validierung fehlgeschlagen für {tool_spec.get('description', tool_name)}:\n"
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
    
    def _validate_tool_call(
        self, tool_name: str, args: Dict[str, Any], user_message: str = ""
    ) -> Dict[str, Any]:
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
        spec = TOOL_SPECS.get(tool_name, {})
        tool_description = spec.get("description", tool_name)
        
        # Formatiere Argumente für LLM-Bewertung
        args_formatted = json.dumps(args, indent=2, ensure_ascii=False)
        
        # Formatiere ALLE kritischen Tools mit ihren Feldern (Kontext für LLM)
        all_tools_formatted = []
        for t_name in CRITICAL_TOOL_NAMES:
            t_spec = TOOL_SPECS.get(t_name, {})
            t_desc = t_spec.get("description", t_name)
            
            req_fields = [f'      "{fname}": <{desc}>'
                          for fname, desc in t_spec.get("required_params", {}).items()]
            opt_fields = [f'      "{fname}": <{desc}>'
                          for fname, desc in t_spec.get("optional_params", {}).items()]
            
            tool_str = f"  • {t_name} - {t_desc}"
            if req_fields:
                tool_str += "\n    PFLICHT:\n" + "\n".join(req_fields)
            if opt_fields:
                tool_str += "\n    OPTIONAL:\n" + "\n".join(opt_fields)
            
            all_tools_formatted.append(tool_str)
        
        all_tools_str = "\n\n".join(all_tools_formatted)
        
        # Separate Felder für das AKTUELLE Tool (zur Hervorhebung)
        required_fields = [f'    "{fname}": <{desc}>'
                           for fname, desc in spec.get("required_params", {}).items()]
        optional_fields = [f'    "{fname}": <{desc}>'
                           for fname, desc in spec.get("optional_params", {}).items()]
        
        required_str = "\n".join(required_fields) if required_fields else "    (keine)"
        optional_str = "\n".join(optional_fields) if optional_fields else "    (keine)"
        
        # Resolve user_message from memory if not supplied
        if not user_message:
            for msg in reversed(self.memory):
                if isinstance(msg, HumanMessage):
                    user_message = msg.content
                    break

        user_message_section = (
            f"\nORIGINALE NUTZERNACHRICHT (einschlie\u00dflich \"Previous conversation:\"-Kontext):\n"
            f"{user_message}\n"
        ) if user_message else ""

        # Validation Prompt für LLM
        validation_prompt = f"""Du bist ein Validierungs-Agent. Bewerte ob dieser Tool-Call sinnvoll und vollständig ist.

KONTEXT: Verfügbare kritische Tools mit ihren Feldern:
{all_tools_str}
{user_message_section}
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
1. Leere Strings oder None zählen als "fehlend" — jedes Pflichtfeld muss einen echten Wert haben.
2. HALLUZINATIONS-PRÜFUNG: Ist die originale Nutzernachricht vorhanden, muss jeder Pflichtfeld-Wert
   dort EXPLIZIT genannt sein. Werte, die der Nutzer nie erwähnt hat, sind halluziniert → confirmed=false.
3. Keine Platzhalter wie "TBD", "N/A", "unbekannt", "keine Angabe", generische Beispiel-Werte.
4. Keine offensichtlich erfundenen / typischen Beispiel-Daten.
5. Bei Email-Feldern: Muss @ enthalten.
6. Bei Datums-Feldern: Muss vollständiges Datum sein (TT.MM.JJJJ oder ähnlich).
7. Bei Stadt/Ort-Feldern: MUSS explizit vom Nutzer genannt worden sein.
8. Bei klips2_apply_study mit study_form='Zweitstudium': prev_uni, prev_program und
   prev_semesters müssen vorhanden sein (auch wenn als optional gelistet).

WICHTIG:
- Wenn auch nur EIN Pflichtfeld fehlt, leer oder nicht vom Nutzer angegeben ist → confirmed=false.
- Format-Variationen sind OK (z.B. "m"/"männlich", verschiedene Datumsformate).
- Optionale Felder dürfen fehlen (kein Problem).
- Bei Ablehnung: Nenne die KONKRETEN fehlenden/ungültigen Felder.

ENTSCHEIDUNG:
Antworte EXAKT in diesem JSON-Format:
{{"confirmed": true, "reason": "Alle Pflichtfelder vollständig und in Nutzernachricht vorhanden"}}
oder
{{"confirmed": false, "reason": "Fehlende/halluzinierte Pflichtfelder: <feldname1, feldname2, ...>"}}

Sei STRENG bei Pflichtfeldern und Halluzinations-Prüfung, FAIR bei Formaten."""

        try:
            # LLM-Bewertung einholen (JSON-Modus über dedizierten LLM)
            response = self.llm_json.invoke(
                [SystemMessage(content=validation_prompt)]
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
        # Erstelle Set der verfügbaren Tool-Namen
        available_tool_names = {tool.name for tool in self.tools}
        
        # Dynamische Tool-Liste basierend auf verfügbaren Tools
        tool_examples = []
        if any(name in available_tool_names for name in ["klips2_register", "klips2_apply_study", "klips2_change_password", "klips2_change_address"]):
            tool_examples.append("- KLIPS2-Aktionen (registrieren, bewerben, Adresse/Passwort ändern, Kurs abfragen)\n  * NUR wenn ALLE erforderlichen Daten VOLLSTÄNDIG vorliegen\n  * NUR wenn die Anfrage SPEZIFISCH und KLAR ist")
        if "university_knowledge_search" in available_tool_names:
            tool_examples.append("- **IMMER** bei Fragen zur Universität zu Köln → university_knowledge_search\n  * Studiengänge, Fakultäten, Einrichtungen, Prozesse, Termine\n  * Nutze das Tool für ALLE universitätsbezogenen Wissensfragen")
        if "duckduckgo_search" in available_tool_names:
            tool_examples.append("- Explizite Internet-Suche → duckduckgo_search (bei \"Search for\", \"Suche im Internet\")")
        if "web_scraper" in available_tool_names:
            tool_examples.append("- URL genannt → web_scraper")
        if "send_email" in available_tool_names:
            tool_examples.append("- E-Mail senden → send_email (mit vollständigem Betreff und Text)")
        
        tool_examples_text = "\n".join(tool_examples) if tool_examples else "- Nutze die verfügbaren Tools je nach Anfrage"
        
        # Dynamische Tool-Liste für kritische Tools (aus TOOL_SPECS abgeleitet)
        critical_tools_list = []
        for tool_name in CRITICAL_TOOL_NAMES:
            if tool_name not in available_tool_names:
                continue
            spec = TOOL_SPECS.get(tool_name, {})
            required = ", ".join(spec.get("required_params", {}).keys())
            entry = f"- **{tool_name}**: Pflicht: {required}"
            if tool_name == "klips2_apply_study":
                entry += "; Wenn study_form=Zweitstudium: zusätzlich prev_uni, prev_program, prev_semesters"
            critical_tools_list.append(entry)
        
        critical_tools_text = "\n".join(critical_tools_list) if critical_tools_list else ""
        
        # Nicht-kritische Tools
        noncritical_tools_list = []
        if "university_knowledge_search" in available_tool_names:
            noncritical_tools_list.append("- **university_knowledge_search**: PFLICHT für alle Fragen zur Universität Köln (Studiengänge, Fakultäten, Einrichtungen, Prozesse, Termine)")
        if "duckduckgo_search" in available_tool_names:
            noncritical_tools_list.append("- **duckduckgo_search**: Bei \"Search for\", \"Suche im Internet\"")
        if "web_scraper" in available_tool_names:
            noncritical_tools_list.append("- **web_scraper**: Bei konkreten URLs")
        if "klips2_get_course_details" in available_tool_names:
            noncritical_tools_list.append("- **klips2_get_course_details**: Bei Kursabfragen")
        
        noncritical_tools_text = "\n".join(noncritical_tools_list) if noncritical_tools_list else ""
        
        # Baue den Prompt zusammen
        critical_section = f"""
### Kritische Tools (mit Validierung):
{critical_tools_text}
""" if critical_tools_text else ""
        
        noncritical_section = f"""
### Nicht-kritische Tools:
{noncritical_tools_text}
""" if noncritical_tools_text else ""
        
        return f"""Du bist ein KI-Assistent für KLIPS 2.0, das Campus-Management-System der Universität zu Köln.

## WANN EIN TOOL AUFRUFEN?

✅ Tool aufrufen bei:
{tool_examples_text}

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
{critical_section}{noncritical_section}

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
                # LLM-Reflexion (JSON-Modus über dedizierten LLM)
                reflection_response = self.llm_json.invoke(
                    [SystemMessage(content=reflection_prompt)]
                )

                reflection_text = reflection_response.content.strip()
                
                # Bereinige JSON
                if reflection_text.startswith("```"):
                    reflection_text = re.sub(r'^```(?:json)?\n?', '', reflection_text)
                    reflection_text = re.sub(r'\n?```$', '', reflection_text)
                
                reflection = json.loads(reflection_text)
                
                # Wenn zufrieden: Fertig
                if reflection.get("satisfactory", False):
                    logger.info(f"✅ Self-Reflection: Antwort nach {iteration + 1} Iteration(en) akzeptiert")
                    break
                
                # Wenn nicht zufrieden: Überarbeite
                issues = reflection.get("issues", [])
                suggestion = reflection.get("suggestion", "")
                
                logger.info(f"🔄 Self-Reflection: Überarbeite Antwort (Iteration {iteration + 1}). Issues: {issues}")
                
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

KRITISCH WICHTIG:
Antworte NUR mit der verbesserten Antwort selbst.
Wiederhole NICHT die Nutzerfrage.
Füge KEINE Labels wie "VERBESSERTE ANTWORT:" hinzu.
Schreibe die Antwort so, als würdest du direkt mit dem Nutzer sprechen."""

                improved_response = self.llm.invoke([HumanMessage(content=improvement_prompt)])
                raw_response = improved_response.content.strip()
                
                # Extrahiere nur die finale Antwort, falls LLM Labels hinzugefügt hat
                if "VERBESSERTE ANTWORT:" in raw_response:
                    # Falls LLM trotzdem Labels hinzugefügt hat, extrahiere nur die Antwort
                    parts = raw_response.split("VERBESSERTE ANTWORT:", 1)
                    current_response = parts[1].strip() if len(parts) > 1 else raw_response
                elif "NUTZERFRAGE:" in raw_response and "ANTWORT:" in raw_response:
                    # Falls vollständige Struktur vorhanden, nimm nur letzten Teil
                    parts = raw_response.split("ANTWORT:")
                    current_response = parts[-1].strip()
                else:
                    current_response = raw_response
                
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
    
    def clear_conversation_trace(self):
        """Lösche den Conversation-Trace."""
        self.conversation_trace = []

    def get_tool_selection(self, message: str, enable_trace: bool = False) -> List[Dict[str, Any]]:
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

                # Trace: raw LLM response for this attempt
                if enable_trace:
                    raw_calls = []
                    if hasattr(response, 'tool_calls') and response.tool_calls:
                        for tc in response.tool_calls:
                            raw_calls.append({"name": tc.get("name", ""), "args": tc.get("args", {})})
                    self.conversation_trace.append({
                        "step": f"llm_call_attempt_{attempt + 1}",
                        "raw_output": response.content if hasattr(response, 'content') else "",
                        "tool_calls_proposed": raw_calls,
                        "timestamp": datetime.now().isoformat(),
                    })
                
                # Tool-Calls extrahieren
                current_tool_calls = []
                has_rejection = False
                
                if hasattr(response, 'tool_calls') and response.tool_calls:
                    for tc in response.tool_calls:
                        tool_name = tc.get("name", "")
                        tool_args = tc.get("args", {})
                        tool_call_id = tc.get("id", f"call_{len(current_tool_calls)}")
                        
                        # Wenn kritisches Tool: Validierung durchführen
                        if tool_name in CRITICAL_TOOL_NAMES:
                            validation_result = self._validate_tool_call(tool_name, tool_args)
                            
                            # Tracking (wie bei echtem Aufruf)
                            self.confirmation_count += 1
                            
                            if validation_result["confirmed"]:
                                self.confirmed_count += 1
                                if enable_trace:
                                    self.conversation_trace.append({
                                        "step": "validation",
                                        "tool_name": tool_name,
                                        "parsed_result": tool_args,
                                        "validation_success": True,
                                        "validation_error": None,
                                    })
                                current_tool_calls.append({
                                    "name": tool_name,
                                    "args": tool_args,
                                    "id": tool_call_id
                                })
                            else:
                                # Tool wurde abgelehnt
                                self.rejected_count += 1
                                has_rejection = True
                                if enable_trace:
                                    self.conversation_trace.append({
                                        "step": "validation",
                                        "tool_name": tool_name,
                                        "parsed_result": tool_args,
                                        "validation_success": False,
                                        "validation_error": validation_result["reason"],
                                    })
                                
                                # Fehlermeldung für Retry
                                error_message = (
                                    f"⚠️ Validierung fehlgeschlagen für {TOOL_SPECS.get(tool_name, {}).get('description', tool_name)}:\n"
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
                            if enable_trace:
                                self.conversation_trace.append({
                                    "step": "validation",
                                    "tool_name": tool_name,
                                    "parsed_result": tool_args,
                                    "validation_success": True,
                                    "validation_error": None,
                                })
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
