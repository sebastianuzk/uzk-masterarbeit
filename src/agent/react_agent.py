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

# BPMN Engine Tools - DEAKTIVIERT (nur Camunda verwendet)
BPMN_ENGINE_AVAILABLE = False

# Process Engine Tools - DEAKTIVIERT (nur Camunda verwendet)  
PROCESS_ENGINE_AVAILABLE = False

# Universal Process Automation Tools import (Camunda Integration)
try:
    from src.tools.process_automation_tool import get_process_automation_tools
    PROCESS_AUTOMATION_AVAILABLE = True
    print("OK Camunda Process Automation Tools werden geladen...")
except ImportError as e:
    print(f"WARNUNG Camunda Process Automation Tools nicht verfügbar: {e}")
    PROCESS_AUTOMATION_AVAILABLE = False


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
        
        # Initialisiere Ollama LLM
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
        )
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # System-Prompt für bessere Konversation UND Qualitätsbewertung
        system_prompt = """Du bist ein hilfsreicher und freundlicher Chatbot.

WICHTIGE REGELN:
1. Führe NORMALE UNTERHALTUNGEN, ohne automatisch nach Informationen zu suchen oder Tools zu nutzen
2. Verwende Tools NUR wenn explizit nach aktuellen Informationen, Fakten oder Recherche gefragt wird und NICHT bei Smalltalk
3. Bei Begrüßungen, Smalltalk oder persönlichen Fragen antworte direkt freundlich
4. Wenn jemand seinen Namen sagt, begrüße ihn höflich - suche NICHT nach dem Namen!
5. Bei Antworten immer die vom genutzten Tool mitgelieferten vollständigen URLs angeben
6. Ermittle den process_key und die notwendigen Parameter für process_start, wenn ein Benutzer einen Prozess starten möchte (z.B. "Bewerbung auf einen Studiengang").
7. Nutze das Tool "discover_processes", um den process_key eines Prozesses zu erhalten und die dafür notwendigen Parameter, wenn ein Benutzer einen Prozess starten möchte.
8. Erfindee KEINE Informationen. Falls du die Antwort nicht kennst, sage "Das weiß ich leider nicht." oder frage nach weiteren Details.
9. Nutze nicht deine eigene Wissensbasis, sondern verlasse dich auf die Tools für aktuelle Informationen.

ESKALATION:
Bei komplexen Anfragen, die du nicht beantworten kannst, oder wenn ein Benutzer explizit nach Support fragt,
verwende das E-Mail-Tool für professionelle Support-Eskalation. Du benötigst nur:
- subject: Kurze Zusammenfassung des Problems
- body: Detaillierte Beschreibung mit Chat-Historie
Empfänger und Absender werden automatisch aus der Konfiguration verwendet.

PROZESSAUTOMATISIERUNG:
Du verfügst über Camunda BPM Integration für Geschäftsprozess-Management:
- discover_processes: Zeige verfügbare BPMN-Prozesse (z.B. Bewerbungsprozess, Prüfungsanmeldung)
- start_process: Starte einen Geschäftsprozess mit den erforderlichen Variablen
- get_process_status: Prüfe Status laufender Prozessinstanzen und offene Tasks
- complete_task: Vervollständige offene User Tasks in laufenden Prozessen
Verwende Tools für Geschäftsprozess-Management wenn Benutzer:
- Verfügbaren Prozessen/Workflows fragen
- Einen Prozess starten möchten (z.B. "Bewerbung einreichen")
- Status einer laufenden Angelegenheit prüfen möchten
- Aufgaben/Tasks bearbeiten möchten

Beispielablauf um einen Prozess zu starten:
1. Nutze "discover_processes", um verfügbare Prozesse und deren Eingabefelder zu ermitteln.
2. Frage den Benutzer nach den erforderlichen Informationen basierend auf den Eingabefeldern.
3. Verwende "start_process", um den Prozess mit den gesammelten Informationen zu starten.

Verfügbare Tools:
- Web-Scraping: Für Inhalte von spezifischen Webseiten  
- DuckDuckGo: Für Websuche, falls du keine relevanten Informationen innerhalb der Universitäts-Wissensdatenbank zur Beantwortung der Frage findest
- Universitäts-Wissensdatenbank: Für Fragen zur Universität zu Köln / WiSo-Fakultät
- discover_processes: Verfügbare BPMN-Prozesse mit Eingabefeldern anzeigen (keine Parameter erforderlich)
- start_process: Geschäftsprozesse mit spezifischen Variablen starten (process_key, variables)
- get_process_status: Status und offene Tasks einer Prozessinstanz prüfen (process_instance_id)
- complete_task: Nächsten User Task vervollständigen (process_instance_id, optional: variables)
- E-Mail: Für Support-Eskalation bei ungelösten Anfragen"""

        # Erstelle React Agent mit erweitertem System-Prompt
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools,
            prompt=system_prompt
        )
        
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
            print("✅ Universitaets-RAG-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️ Universitaets-RAG-Tool konnte nicht geladen werden: {e}")
            print("   -> Universitaets-spezifische Anfragen funktionieren moeglicherweise nicht optimal")
        
        # Camunda Process Automation Tools (Hauptsystem für Prozessautomatisierung)
        if PROCESS_AUTOMATION_AVAILABLE:
            try:
                automation_tools = get_process_automation_tools()
                tools.extend(automation_tools)
                print("OK Camunda Process Automation Tools erfolgreich geladen")
                print("   -> Universelle Camunda BPM Integration ist verfügbar")
            except Exception as e:
                print(f"WARNUNG Camunda Process Automation Tools konnten nicht geladen werden: {e}")
                print("   -> Prozessautomatisierung ist nicht verfügbar")
        
        # E-Mail-Tool für Support-Eskalation immer hinzufügen
        try:
            email_tool = create_email_tool()
            tools.append(email_tool)
            print("✅ E-Mail-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  E-Mail-Tool konnte nicht geladen werden: {e}")
            print("   → Support-Eskalation per E-Mail nicht verfügbar")
        
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
            
            # Führe Agent aus (mit automatischem LangSmith-Tracing)
            agent_input = {
                "messages": self.memory
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
            
            # Extrahiere Antwort
            ai_message = response["messages"][-1]
            response_text = ai_message.content
            
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