"""
React Agent basierend auf LangGraph für autonomes Verhalten mit Ollama
"""
import os
import uuid
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

from config.settings import settings
from src.tools.rag_tool import create_university_rag_tool


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
        # Context-Size nach Modellgröße - größer für bessere Multi-Turn Gespräche
        MODEL_CTX_SIZES = {
            "0.5b": 2048,
            "1b": 4096,
            "3b": 8192,
            "7b": 14500,
            "8b": 14500,
            "20b": 16384,
            "70b": 16384,
        }
        
        # Modellgröße aus Namen extrahieren
        model_lower = settings.OLLAMA_MODEL.lower()
        ctx_size = 8192  # Standard - ausreichend für die meisten Gespräche
        for size_key, ctx_value in MODEL_CTX_SIZES.items():
            if size_key in model_lower:
                ctx_size = ctx_value
                break
        
        print(f"🤖 Initialisiere ChatOllama mit Modell: {settings.OLLAMA_MODEL} (ctx_size={ctx_size})")

        # seed=42 für Reproduzierbarkeit (zusammen mit temperature aus settings)
        # timeout=90 für max 90s pro Request (verhindert endloses Hängen)
        # num_predict=2048 begrenzt Output-Tokens (verhindert Endlos-Generierung)
        self.llm = ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            seed=42,  # Reproduzierbarkeit
            num_ctx=ctx_size,  # Adaptiver Context für schnellere Antworten
            timeout=90,  # Max 90 Sekunden pro LLM-Request
            #num_predict=2048,  # Max 2048 Output-Tokens (verhindert Endlos-Generierung)
        )
        
        # Initialisiere Tools (einschließlich E-Mail-Tool)
        self.tools = self._create_tools()
        
        # Professioneller System-Prompt für RAG-basierte Universitätsberatung
        system_prompt = """Du bist ein KI-Assistent für die Wirtschafts- und Sozialwissenschaftliche Fakultät (WiSo) der Universität zu Köln. Du unterstützt Studierende und Studieninteressierte bei Fragen zu Studiengängen, Fristen, Bewerbungsverfahren und allgemeinen Universitätsthemen.

## KERNAUFGABE

Du beantwortest Fragen zu:
- Studiengängen und der WiSo-Fakultät im (Bachelor, Master)
- Bewerbungsfristen und -verfahren
- Zulassungsvoraussetzungen
- Studienorganisation und -ablauf
- Prüfungsordnungen und Modulhandbücher
- Allgemeine Informationen zur Universität zu Köln und der WiSo-Fakultät

## TOOL-NUTZUNG

### university_knowledge_search
**Zweck**: Durchsucht die Universitäts-Wissensdatenbank nach relevanten Informationen.
**Parameter**:
  - `query`: Deine Suchanfrage (Pflicht)

**Wann nutzen?**
- Bei JEDER Frage zu WiSo Köln und Universität zu Köln
- IMMER zuerst suchen, DANN antworten
- Auch bei scheinbar einfachen Fragen - die Wissensdatenbank hat aktuelle Informationen

## ANTWORTREGELN

1. **IMMER ERST SUCHEN**: Nutze university_knowledge_search bevor du antwortest
2. **QUELLENBASIERT**: Basiere deine Antworten auf den erhaltenen Suchergebnissen und nicht (!) deinem eigenen Wissen
3. **EHRLICHKEIT**: Wenn keine relevanten Informationen gefunden werden, sage das klar
4. **SPRACHANPASSUNG**: Antworte in der Sprache des Nutzers (Deutsch/Englisch)
5. **PRÄZISION**: Gib konkrete Informationen, keine vagen Aussagen und beziehe dich auf den Suchanfrage sowie den Suchergebnissen

## ANTWORTSTIL

- Freundlich und professionell
- Zusammenfassung der Suchergebnisse, aber informativ
- Bei Unsicherheit: Empfehle Kontakt zur Studienberatung

## BEISPIELE

✅ **RICHTIG**:
Nutzer: "Wann ist die Bewerbungsfrist für den BWL Master?"
→ university_knowledge_search mit query="Bewerbungsfrist BWL Master" aufrufen
→ Basierend auf Ergebnissen antworten

✅ **RICHTIG**:
Nutzer: "What are the requirements for the Economics program?"
→ university_knowledge_search mit query="requirements Economics program admission"
→ Auf Englisch antworten"""

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
        """Erstelle Liste der verfügbaren Tools - nur RAG-Tool"""
        tools = []
        
        # RAG-Tool für Universitäts-Wissensdatenbank
        try:
            rag_tool = create_university_rag_tool()
            tools.append(rag_tool)
            print("✅ Universitäts-RAG-Tool erfolgreich geladen")
        except Exception as e:
            print(f"⚠️  Universitäts-RAG-Tool konnte nicht geladen werden: {e}")
            print("   → Universitäts-spezifische Anfragen funktionieren möglicherweise nicht optimal")
        
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

def create_react_agent() -> ReactAgent:
    """Factory-Funktion für den React Agent"""
    return ReactAgent()