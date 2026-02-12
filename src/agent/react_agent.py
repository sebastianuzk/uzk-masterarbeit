"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama oder OpenAI
"""
import uuid
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

from config.logging_config import get_logger
from config.settings import settings
from src.agent.agent_config import setup_langsmith_tracing, get_recursion_limit
from src.agent.llm_factory import create_llm
from src.agent.tool_specs import TOOL_SPECS
from src.agent.tool_loader import load_tool_safely, load_klips_tools
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.email_tool import create_email_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.web_scraper_tool import create_web_scraper_tool

logger = get_logger(__name__)


# TOOL_SPECS werden jetzt aus src/agent/tool_specs.py importiert


class ReactAgent:
    """Autonomer React Agent mit LangGraph und Ollama oder OpenAI"""
    
    def __init__(self):
        # Validiere Einstellungen
        settings.validate()
        
        # LangSmith Tracing konfigurieren (falls aktiviert)
        setup_langsmith_tracing()
        
        # Initialisiere LLM (Ollama oder OpenAI basierend auf settings.LLM_PROVIDER)
        self.llm = create_llm()
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # System-Prompt mit detaillierten Tool-Spezifikationen
        system_prompt = self._get_system_prompt()
        
        # Erstelle React Agent
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools
        )
        
        # Konfiguriere Recursion Limit für Agent
        self.recursion_limit = get_recursion_limit("single")
        
        # Speichere System-Prompt als SystemMessage für Memory
        self.system_message = SystemMessage(content=system_prompt)
        
        # Memory für Konversationshistorie
        self.memory = []
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt mit detaillierten Tool-Spezifikationen."""
        
        # Erstelle Set der verfügbaren Tool-Namen
        available_tool_names = {tool.name for tool in self.tools}
        
        # Formatiere Tool-Spezifikationen NUR für verfügbare Tools
        tools_info = []
        for tool_name, spec in TOOL_SPECS.items():
            # Skip tools that are not actually loaded
            if tool_name not in available_tool_names:
                continue
                
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
        
        # Generate dynamic tool usage guidance based on available tools
        tool_usage_examples = []
        if "klips2_register" in available_tool_names or "klips2_apply_study" in available_tool_names:
            tool_usage_examples.append("- KLIPS2-Aktionen: Wenn ALLE Pflichtparameter vorhanden sind")
        if "university_knowledge_search" in available_tool_names:
            tool_usage_examples.append("- Wissensfragen zur Universität → university_knowledge_search")
        if "duckduckgo_search" in available_tool_names:
            tool_usage_examples.append("- Explizite Internet-Suche (\"Suche im Internet\", \"Search for\") → duckduckgo_search")
        if "web_scraper" in available_tool_names:
            tool_usage_examples.append("- URL genannt → web_scraper")
        if "send_email" in available_tool_names:
            tool_usage_examples.append("- E-Mail senden gewünscht → send_email (mit Betreff und Text)")
        
        tool_usage_text = "\n".join(tool_usage_examples) if tool_usage_examples else "- Nutze die verfügbaren Tools je nach Anfrage"
        
        return f"""Du bist ein KI-Assistent für KLIPS 2.0, das Campus-Management-System der Universität zu Köln.

## VERFÜGBARE TOOLS MIT EXAKTEN PARAMETER-ANFORDERUNGEN

{tools_spec_text}

## WANN EIN TOOL AUFRUFEN?

✅ Tool aufrufen bei:
{tool_usage_text}

❌ KEIN Tool bei:
- Begrüßungen ("Hallo!", "Wie geht's?")
- Fragen über dich selbst ("Was kannst du?")
- Einfache Rechenaufgaben, Übersetzungen
- Allgemeine Wissensfragen ohne Uni-Bezug
- **UNVOLLSTÄNDIGE Daten**: Wenn Pflichtparameter fehlen → FRAGE NACH, rufe KEIN Tool auf

## PARAMETER-EXTRAKTION

Extrahiere Parameter GROSSZÜGIG aus dem Text:
- "Ich bin Max Müller" → vorname="Max", nachname="Müller"
- "geboren am 15.03.1999" → geburtsdatum="15.03.1999"
- "männlich" / "male" / "m" → geschlecht="männlich"
- "Abitur 2018 Note 2,3" → hzb_type="Abitur", hzb_date="2018", hzb_grade="2.3"
- "Musterstraße 1, 50678 Köln" → street="Musterstraße 1", zip_code="50678", city="Köln"

**Format-Variationen sind OK:**
- Geschlecht: "m"/"männlich"/"male" → "männlich"
- Datum: "15.06.2018" / "15/06/2018" / "2018-06-15" → akzeptabel
- Note: "2,3" / "2.3" → beide OK

## PFLICHTFELD-CHECK

Vor JEDEM Tool-Aufruf:
1. ✅ Sind ALLE Pflichtparameter vorhanden?
2. ✅ Haben die Parameter plausible Werte (keine Platzhalter wie "TBD", "N/A")?
3. ✅ Passen die Daten zum Tool-Zweck?

**Wenn Pflichtparameter fehlen:**
- Nenne KONKRET welche Parameter fehlen
- Beispiel: "Für die Registrierung benötige ich noch: Geburtsdatum und E-Mail-Adresse"
- Rufe KEIN Tool auf mit unvollständigen Daten!

## MULTI-STEP KONVERSATIONEN

Wenn im Prompt "Previous conversation:" steht:
1. Analysiere ALLE Informationen aus vorherigen Nachrichten
2. Kombiniere sie mit der aktuellen Nachricht
3. Wenn dadurch ALLE Pflichtparameter vorhanden sind → Tool aufrufen

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

## BEISPIELE

✅ RICHTIG: "Registriere Max Müller, männlich, 01.01.2000, max@test.de, deutsch"
   → 6/6 Pflichtparameter → klips2_register AUFRUFEN

❌ FALSCH: "Registriere Max Müller"
   → Nur 2/6 Parameter → NACHFRAGEN statt Tool aufrufen

Antworte in der Sprache des Nutzers."""
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools einschließlich E-Mail-Tool"""
        tools = []
        
        if settings.ENABLE_WEB_SCRAPER:
            tool = load_tool_safely(create_web_scraper_tool, "Web Scraper Tool")
            if tool:
                tools.append(tool)
        
        if settings.ENABLE_DUCKDUCKGO:
            tool = load_tool_safely(create_duckduckgo_tool, "DuckDuckGo Tool")
            if tool:
                tools.append(tool)
        
        # RAG-Tool für Universitäts-Wissensdatenbank immer hinzufügen
        rag_tool = load_tool_safely(
            create_university_rag_tool, 
            "Universitäts-RAG-Tool",
            fallback_message="Universitäts-spezifische Anfragen funktionieren möglicherweise nicht optimal"
        )
        if rag_tool:
            tools.append(rag_tool)
        
        # E-Mail-Tool für Support-Eskalation
        if settings.ENABLE_EMAIL:
            email_tool = load_tool_safely(
                create_email_tool,
                "E-Mail-Tool",
                fallback_message="Support-Eskalation per E-Mail nicht verfügbar"
            )
            if email_tool:
                tools.append(email_tool)
        
        # KLIPS2-Tools
        if settings.ENABLE_KLIPS:
            klips_tools = load_klips_tools()
            tools.extend(klips_tools)
        
        logger.info(f"ReactAgent initialized with {len(tools)} tools")
        return tools
    
    def chat(self, message: str, session_id: str = None) -> str:
        """Führe eine Unterhaltung mit dem Agenten"""
        try:
            # Session-ID für Tracing (falls nicht übergeben)
            if session_id is None:
                session_id = str(uuid.uuid4())
            
            # Füge Nachricht zum Memory hinzu
            human_message = HumanMessage(content=message)
            self.memory.append(human_message)
            
            # Begrenze Memory-Größe
            if len(self.memory) > settings.MEMORY_SIZE:
                self.memory = self.memory[-settings.MEMORY_SIZE:]
            
            # Führe Agent aus (mit System-Message und automatischem LangSmith-Tracing)
            agent_input = {
                "messages": [self.system_message] + self.memory
            }

            # Erstelle Config mit Metadaten für LangSmith-Tracing (falls aktiv)
            config = {
                "recursion_limit": self.recursion_limit
            }
            
            if settings.LANGSMITH_TRACING:
                config["metadata"] = {
                    "session_id": session_id,
                    "user_message": message[:100] + "..." if len(message) > 100 else message,
                    "available_tools": len(self.tools)
                }

            response = self.agent.invoke(agent_input, config=config)
            
            # Extrahiere Antwort - prüfe verschiedene Message-Typen
            ai_message = response["messages"][-1]
            
            # Debug: Wenn content leer ist, prüfe andere Message-Typen
            response_text = ai_message.content
            if not response_text:
                # Suche nach einer AIMessage mit Inhalt
                for msg in reversed(response["messages"]):
                    if hasattr(msg, 'content') and msg.content:
                        response_text = msg.content
                        break
                
                # Final fallback if still empty
                if not response_text:
                    response_text = "Ich konnte keine Antwort generieren. Bitte versuchen Sie es erneut."
            
            # Füge Antwort zum Memory hinzu
            ai_response = AIMessage(content=response_text)
            self.memory.append(ai_response)
            
            return response_text
            
        except Exception as e:
            error_msg = f"Fehler beim Verarbeiten der Nachricht: {str(e)}"
            self.memory.append(AIMessage(content=error_msg))
            return error_msg
    
    def get_available_tools(self) -> List[str]:
        """Gebe Liste der verfügbaren Tools zurück"""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self):
        """Lösche Konversationshistorie"""
        self.memory = []
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Gebe Zusammenfassung des Memory zurück"""
        human_messages = [msg for msg in self.memory if isinstance(msg, HumanMessage)]
        ai_messages = [msg for msg in self.memory if isinstance(msg, AIMessage)]
        
        return {
            "total_messages": len(self.memory),
            "human_messages": len(human_messages),
            "ai_messages": len(ai_messages),
            "last_messages": [msg.content[:100] + "..." if len(msg.content) > 100 else msg.content 
                            for msg in self.memory[-5:]]
        }
    
    def get_tool_selection(self, message: str) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl ohne Ausführung (für Evaluierung).
        
        Diese Methode ruft das LLM mit gebundenen Tools auf und
        extrahiert die Tool-Calls, ohne sie auszuführen.
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            Liste der ausgewählten Tool-Calls
        """
        try:
            # LLM mit gebundenen Tools
            llm_with_tools = self.llm.bind_tools(self.tools)
            
            # Message-Liste erstellen
            messages = [
                self.system_message,
                HumanMessage(content=message)
            ]
            
            # LLM aufrufen um Tool-Auswahl zu bekommen (OHNE Ausführung)
            response = llm_with_tools.invoke(messages)
            
            # Tool-Calls extrahieren
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append({
                        "name": tc.get("name", ""),
                        "args": tc.get("args", {})
                    })
            
            return tool_calls
            
        except Exception as e:
            return []  # Bei Fehler keine Tool-Auswahl

def create_react_agent() -> ReactAgent:
    """Factory-Funktion für den React Agent"""
    return ReactAgent()