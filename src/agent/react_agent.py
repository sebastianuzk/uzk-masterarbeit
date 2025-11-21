"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama
"""
import os
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from langgraph.prebuilt import create_react_agent as create_langgraph_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from config.settings import settings
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.email_tool import create_email_tool
from src.tools.klips2_register_tool import create_klips2_register_tool


class ReactAgent:
    """Autonomer React Agent mit LangGraph und Ollama"""
    
    def __init__(self):
        # Validiere Einstellungen
        settings.validate()
        
        # LangSmith Tracing konfigurieren (falls aktiviert)
        if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
            os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
            os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
            print(f"✅ LangSmith-Tracing aktiviert für Projekt: {settings.LANGSMITH_PROJECT}")
        
        # Initialisiere Ollama LLM (optimiert für Performance)
        # Kleinere Context-Size für kleine Modelle
        if "0.5b" in settings.OLLAMA_MODEL:
            ctx_size = 1024
        elif "3b" in settings.OLLAMA_MODEL:
            ctx_size = 2048
        else:
            ctx_size = 4096
        
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            num_ctx=ctx_size,  # Adaptiver Context für schnellere Antworten
            timeout=settings.REQUEST_TIMEOUT,
            keep_alive="5m",  # Modell im RAM halten für schnellere Antworten
        )
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # Optimierter System-Prompt für bessere Tool-Nutzung
        system_prompt = """Du bist ein Uni-Assistent. Nutze Tools effektiv:

KLIPS2-Registrierung:
- Wenn User "registrieren" oder "KLIPS2 Account" sagt: Nutze klips2_register Tool
- Benötigte Daten: vorname, nachname, geschlecht, geburtsdatum, email, staatsangehoerigkeit
- Wenn Daten im Prompt sind: Direkt Tool aufrufen
- Wenn Daten fehlen: User fragen
- WICHTIG: Gib die komplette Tool-Ausgabe an den User weiter, ohne sie zu verändern oder zusammenzufassen!

Uni-Fragen:
- university_knowledge_search für Bewerbung, Prüfungen, Module, Fristen

Andere Tools:
- web_scraper/duckduckgo: Web-Suche
- email_tool: Support-Eskalation

Bei Smalltalk: Direkt antworten ohne Tools

WICHTIG: Gib Tool-Ergebnisse IMMER vollständig und unverändert an den User weiter!"""

        # Erstelle React Agent mit kompaktem System-Prompt
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools
        )
        
        # Füge System-Prompt manuell zum Memory hinzu
        self.system_message = SystemMessage(content=system_prompt)
        
        # Memory für Konversationshistorie
        self.memory = []
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools einschließlich E-Mail-Tool"""
        tools = []
        
        if settings.ENABLE_WEB_SCRAPER:
            tools.append(create_web_scraper_tool())
        
        if settings.ENABLE_DUCKDUCKGO:
            tools.append(create_duckduckgo_tool())
        
        # RAG-Tool für Universitäts-Wissensdatenbank immer hinzufügen
        try:
            rag_tool = create_university_rag_tool()
            tools.append(rag_tool)
            print("✅ Universitäts-RAG-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  Universitäts-RAG-Tool konnte nicht geladen werden: {e}")
            print("   → Universitäts-spezifische Anfragen funktionieren möglicherweise nicht optimal")
        
        # E-Mail-Tool für Support-Eskalation immer hinzufügen
        try:
            email_tool = create_email_tool()
            tools.append(email_tool)
            print("✅ E-Mail-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  E-Mail-Tool konnte nicht geladen werden: {e}")
            print("   → Support-Eskalation per E-Mail nicht verfügbar")
        
        # KLIPS2-Registrierungs-Tool hinzufügen
        try:
            klips2_tool = create_klips2_register_tool()
            tools.append(klips2_tool)
            print("✅ KLIPS2-Registrierungs-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  KLIPS2-Registrierungs-Tool konnte nicht geladen werden: {e}")
            print("   → KLIPS2-Account-Erstellung nicht verfügbar")
        
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
            config = None
            if settings.LANGSMITH_TRACING:
                config = {
                    "metadata": {
                        "session_id": session_id,
                        "user_message": message[:100] + "..." if len(message) > 100 else message,
                        "available_tools": len(self.tools)
                    }
                }

            if config is not None:
                response = self.agent.invoke(agent_input, config=config)
            else:
                response = self.agent.invoke(agent_input)
            
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

def create_react_agent() -> ReactAgent:
    """Factory-Funktion für den React Agent"""
    return ReactAgent()