"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama
"""
from typing import List, Dict, Any
from langgraph.prebuilt import create_react_agent as create_langgraph_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from config.settings import settings
from src.tools.wikipedia_tool import create_wikipedia_tool
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool

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
        
        # Initialisiere Ollama LLM
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
        )
        
        # Initialisiere Tools
        self.tools = self._create_tools()
        
        # System-Prompt für bessere Konversation
        system_prompt = """Du bist ein hilfsreicher und freundlicher Chatbot-Assistent für die Universität zu Köln. 

GRUNDPRINZIPIEN:
1. Führe natürliche, menschliche Unterhaltungen
2. Verstehe den Kontext und die Absicht hinter den Nachrichten
3. Bei Begrüßungen, Smalltalk oder persönlichen Fragen antworte direkt freundlich
4. Wenn jemand seinen Namen sagt, begrüße ihn höflich - suche NICHT nach dem Namen!
5. Bei Antworten immer die vom genutzten Tool mitgelieferten vollständigen URLs angeben
6. Wenn du ein Tool benutzt, erkläre kurz WARUM du es benutzt
7. Wenn dir Informationen fehlen, gib das offen zu - erfinde keine Informationen. Frage den Benutzer nach mehr Details.
8. Bevor du eine Antwort gibst, überlege ob du mehrere Tools nacheinander verwenden musst um das Anliegen zu erfüllen. Beispielsweise erst discover_processes, dann start_process

INTELLIGENTE PROZESS-UNTERSTÜTZUNG:
Du hast Zugriff auf ein universelles Camunda-Prozessautomatisierungssystem. Wenn ein Benutzer Unterstützung bei universitären Prozessen benötigt (wie Bewerbungen, Anträge, Anmeldungen oder ähnliche administrative Vorgänge), kannst du:

1. Zunächst discover_processes verwenden, um verfügbare Prozesse zu erkunden
2. Bei Bedarf einen geeigneten Prozess starten und durch die Schritte führen

INTELLIGENTE KONTEXT-ERKENNUNG:
Analysiere die Benutzeranfrage sorgfältig. Wenn jemand:
- Unterstützung bei administrativen Universitätsprozessen sucht
- Hilfe bei Anträgen oder Bewerbungen benötigt
- Interesse an strukturierten Abläufen zeigt
- Nach Schritt-für-Schritt-Anleitungen fragt

...dann prüfe verfügbare Prozesse und biete entsprechende Automatisierung an.

Verfügbare Tools:
- Wikipedia: Für Enzyklopädie-Informationen
- Web-Scraping: Für Inhalte von spezifischen Webseiten  
- DuckDuckGo: Für Websuche, falls du keine relevanten Informationen innerhalb der Universitäts-Wissensdatenbank zur Beantwortung der Frage findest
- Universitäts-Wissensdatenbank: Für Fragen zur Universität zu Köln / WiSo-Fakultät
- Camunda Process Automation: Universelle Prozessautomatisierung für strukturierte universitäre Abläufe

ÜBER CAMUNDA PROCESS AUTOMATION:
Das Camunda-System bietet strukturierte Unterstützung für universitäre Prozesse. Es kann verschiedene Arten von Abläufen automatisieren und durch komplexe Schritte führen. Die verfügbaren Prozesse können sich dynamisch ändern, daher solltest du bei Bedarf zuerst discover_processes verwenden, um aktuelle Möglichkeiten zu erkunden.

- discover_processes: Zeigt verfügbare automatisierte Prozesse
- start_process: Startet einen Prozess mit gegebenen Parametern  
- complete_task: Schließt Tasks in laufenden Prozessen ab
- get_process_status: Prüft Status laufender Prozessinstanzen

Denke daran: Jeder Benutzer kann mehrere Prozesse gleichzeitig haben. Das System ist darauf ausgelegt, verschiedene Anwendungsfälle parallel zu unterstützen.

TOOL-VERWENDUNG NACH KONTEXT:
Verwende normale Recherche-Tools bei:
- "Was sind die neuesten Nachrichten über..."
- "Suche mir Informationen über..."
- "Was steht auf der Webseite..."
- "Was benötige ich für die Bewerbung..." (nutze university_knowledge_search)
- "Wie sind die Fristen für..." (nutze university_knowledge_search)
- "Erkläre mir das Thema..."

Verwende KEINE Tools bei:
- Begrüßungen ("Hallo", "Hi")
- Persönlichen Vorstellungen ("Ich heiße...")
- Smalltalk
- Allgemeinen Fragen ohne Recherchebedarf

Sei intelligent und kontextbewusst. Verstehe die echte Absicht hinter den Nachrichten und wähle die passenden Tools entsprechend aus."""

        # Erstelle React Agent mit System-Prompt
        self.agent = create_langgraph_agent(
            self.llm,
            self.tools,
            prompt=system_prompt
        )
        
        # Memory für Konversationshistorie
        self.memory = []
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle Liste der verfügbaren Tools"""
        tools = []
        
        if settings.ENABLE_WIKIPEDIA:
            tools.append(create_wikipedia_tool())
        
        if settings.ENABLE_WEB_SCRAPER:
            tools.append(create_web_scraper_tool())
        
        if settings.ENABLE_DUCKDUCKGO:
            tools.append(create_duckduckgo_tool())
        
        # RAG-Tool für Universitäts-Wissensdatenbank immer hinzufügen
        try:
            rag_tool = create_university_rag_tool()
            tools.append(rag_tool)
            print("OK Universitaets-RAG-Tool erfolgreich geladen")
        except Exception as e:
            print(f"WARNUNG Universitaets-RAG-Tool konnte nicht geladen werden: {e}")
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
        
        return tools
    
    def chat(self, message: str) -> str:
        """Führe eine Unterhaltung mit dem Agenten"""
        try:
            # Füge Nachricht zum Memory hinzu
            self.memory.append(HumanMessage(content=message))
            
            # Begrenze Memory-Größe
            if len(self.memory) > settings.MEMORY_SIZE:
                self.memory = self.memory[-settings.MEMORY_SIZE:]
            
            # Führe Agent aus
            response = self.agent.invoke({
                "messages": self.memory
            })
            
            # Extrahiere Antwort
            ai_message = response["messages"][-1]
            response_text = ai_message.content
            
            # Füge Antwort zum Memory hinzu
            self.memory.append(AIMessage(content=response_text))
            
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