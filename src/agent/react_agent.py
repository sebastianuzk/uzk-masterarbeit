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

# Process Engine Tool import mit Fehlerbehandlung
try:
    from src.tools.process_engine_tool import ProcessEngineTool
    PROCESS_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Process Engine Tool nicht verfügbar: {e}")
    PROCESS_ENGINE_AVAILABLE = False


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

WICHTIGE REGELN:
1. Führe NORMALE UNTERHALTUNGEN, ohne automatisch nach Informationen zu suchen
2. Verwende Tools NUR wenn explizit nach aktuellen Informationen, Fakten oder Recherche gefragt wird
3. Bei Begrüßungen, Smalltalk oder persönlichen Fragen antworte direkt freundlich
4. Wenn jemand seinen Namen sagt, begrüße ihn höflich - suche NICHT nach dem Namen!
5. Bei Antworten immer die vom genutzten Tool mitgelieferten vollständigen URLs angeben

Verfügbare Tools:
- Wikipedia: Für Enzyklopädie-Informationen
- Web-Scraping: Für Inhalte von spezifischen Webseiten  
- DuckDuckGo: Für Websuche, falls du keine relevanten Informationen innerhalb der Universitäts-Wissensdatenbank zur Beantwortung der Frage findest
- Universitäts-Wissensdatenbank: Für Fragen zur Universität zu Köln / WiSo-Fakultät
- Process Engine: Für automatische Bearbeitung von Universitätsprozessen

PROCESS ENGINE - SPEZIFISCHE ANWENDUNGSFÄLLE:
Verwende das Process Engine Tool AUTOMATISCH wenn Studierende nach folgenden Diensten fragen:

🎓 ZEUGNIS/TRANSCRIPT ANFRAGEN:
- "Ich brauche ein Zeugnis", "Transcript", "Notenbescheinigung", "Leistungsnachweis"
- "Kann ich meine Noten bekommen?", "Notenübersicht für Bewerbung"
- Aktion: process_engine mit action="start_workflow" und workflow="transcript_request"

📝 PRÜFUNGSANMELDUNGEN:
- "Prüfungsanmeldung", "Klausuranmeldung", "zur Prüfung anmelden"
- "Wie melde ich mich für die Klausur an?", "Prüfungsregistrierung"
- Aktion: process_engine mit action="start_workflow" und workflow="exam_registration"

📊 NOTENABFRAGEN:
- "Wie sind meine Noten?", "Prüfungsergebnisse", "Note abfragen"
- "Sind meine Klausurergebnisse da?", "Bewertung einsehen"
- Aktion: process_engine mit action="start_workflow" und workflow="grade_inquiry"

📚 KURSEINSCHREIBUNGEN:
- "Kurs anmelden", "Vorlesung einschreiben", "Seminar registrieren"
- "Wie kann ich mich für das Fach anmelden?", "Courseregistration"
- Aktion: process_engine mit action="start_workflow" und workflow="course_enrollment"

📅 STUNDENPLAN ANFRAGEN:
- "Stundenplan", "Termine", "Zeitplan", "Schedule"
- "Wann sind meine Vorlesungen?", "Semesterplanung"
- Aktion: process_engine mit action="start_workflow" und workflow="schedule_request"

🔍 WORKFLOW ANALYSE:
Bei unklaren Anfragen zu Universitätsprozessen:
- Verwende process_engine mit action="analyze" um herauszufinden welcher Workflow passend ist
- Beispiel: "Ich habe ein Problem mit meinem Studium" → erst analysieren, dann passenden Workflow starten

WICHTIG: 
- Sammle IMMER zuerst alle benötigten Daten (Matrikelnummer, E-Mail, Name) bevor du einen Workflow startest
- Erkläre dem Studierenden WAS der automatische Prozess machen wird
- Informiere über den Status und nächste Schritte

Normale Recherche-Tools verwenden bei:
- "Was sind die neuesten Nachrichten über..."
- "Suche mir Informationen über..."
- "Was steht auf der Webseite..."
- "Was benötige ich für die Bewerbung..." (nutze university_knowledge_search)
- "Wie sind die Fristen für..." (nutze university_knowledge_search)
- "Erkläre mir das Thema..."

NICHT bei:
- Begrüßungen ("Hallo", "Hi")
- Persönlichen Vorstellungen ("Ich heiße...")
- Smalltalk
- Allgemeinen Fragen ohne Recherchebedarf"""

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
            print("✅ Universitäts-RAG-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️ Universitäts-RAG-Tool konnte nicht geladen werden: {e}")
            print("   → Universitäts-spezifische Anfragen funktionieren möglicherweise nicht optimal")
        
        # Process Engine Tool
        try:
            process_tool = ProcessEngineTool()
            tools.append(process_tool)
            print("✅ Process Engine Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️ Process Engine Tool konnte nicht geladen werden: {e}")
            print("   → Automatisierte Universitätsprozesse sind eingeschränkt verfügbar")
        
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