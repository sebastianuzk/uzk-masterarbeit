"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from langgraph.prebuilt import create_react_agent as create_langgraph_agent
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool

from config.settings import settings
from src.tools.wikipedia_tool import create_wikipedia_tool
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.email_tool import create_email_tool


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
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # System-Prompt für bessere Konversation UND Qualitätsbewertung
        system_prompt = """Du bist ein hilfsreicher und freundlicher Chatbot-Assistent mit der Fähigkeit zur Selbstreflexion.

WICHTIGE REGELN:
1. Führe NORMALE UNTERHALTUNGEN, ohne automatisch nach Informationen zu suchen
2. Verwende Tools NUR wenn explizit nach aktuellen Informationen, Fakten oder Recherche gefragt wird
3. Bei Begrüßungen, Smalltalk oder persönlichen Fragen antworte direkt freundlich
4. Wenn jemand seinen Namen sagt, begrüße ihn höflich - suche NICHT nach dem Namen!
5. Bei Antworten immer die vom genutzten Tool mitgelieferten vollständigen URLs angeben

QUALITÄTSBEWERTUNG:
Nach jeder Antwort bewerte selbstkritisch OHNE dies im Chat zu erwähnen:
- Konnte ich die Frage vollständig beantworten?
- War meine Antwort präzise und hilfreich?
- Hat der Benutzer möglicherweise eine unzufriedene Reaktion?
- Sollte diese Anfrage eskaliert werden?

ESKALATION:
Bei komplexen Anfragen, die du nicht beantworten kannst, oder wenn ein Benutzer explizit nach Support fragt,
verwende das E-Mail-Tool für professionelle Support-Eskalation. Du benötigst nur:
- subject: Kurze Zusammenfassung des Problems
- body: Detaillierte Beschreibung mit Chat-Historie

Empfänger und Absender werden automatisch aus der Konfiguration verwendet.

Verfügbare Tools:
- Wikipedia: Für Enzyklopädie-Informationen
- Web-Scraping: Für Inhalte von spezifischen Webseiten  
- DuckDuckGo: Für Websuche, falls du keine relevanten Informationen innerhalb der Universitäts-Wissensdatenbank zur Beantwortung der Frage findest
- Universitäts-Wissensdatenbank: Für Fragen zur Universität zu Köln / WiSo-Fakultät
- E-Mail: Für Support-Eskalation bei ungelösten Anfragen

Verwende Tools nur bei entsprechenden Anfragen, nicht bei Smalltalk."""

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
        
        return tools
    
    def chat(self, message: str) -> str:
        """Führe eine Unterhaltung mit dem Agenten"""
        try:
            # Füge Nachricht zum Memory hinzu
            human_message = HumanMessage(content=message)
            self.memory.append(human_message)
            
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