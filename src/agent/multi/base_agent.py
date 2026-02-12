"""
Base Agent Klasse für spezialisierte Agenten im Multi-Agent-System.

Bietet gemeinsame Funktionalität für alle spezialisierten Agenten:
- LLM-Initialisierung
- Tool-Management
- Memory-Handling
- Agent-Erstellung mit LangGraph
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

from config.logging_config import get_logger
from src.agent.agent_config import get_recursion_limit
from src.agent.llm_factory import create_llm

logger = get_logger(__name__)


class BaseSpecializedAgent(ABC):
    """
    Abstrakte Basisklasse für spezialisierte Agenten.
    
    Jeder spezialisierte Agent:
    - Hat einen eindeutigen Namen und Beschreibung
    - Verfügt über eine Menge von Tools für seinen Aufgabenbereich
    - Kann Anfragen in seinem Bereich bearbeiten
    """
    
    def __init__(self, shared_llm: Optional[ChatOllama] = None):
        """
        Initialisiere den spezialisierten Agenten.
        
        Args:
            shared_llm: Optionale geteilte LLM-Instanz für Ressourceneffizienz
        """
        # LLM initialisieren oder teilen
        self.llm = shared_llm if shared_llm else create_llm()
        
        # Tools für diesen Agenten erstellen
        self.tools = self._create_tools()
        
        # System-Prompt erstellen
        self.system_message = SystemMessage(content=self._get_system_prompt())
        
        # Agent mit LangGraph erstellen
        self.agent = create_langgraph_agent(self.llm, self.tools)
        
        # Recursion Limit from centralized config
        self.recursion_limit = get_recursion_limit("multi")
        
        # Memory für Konversationshistorie (begrenzt)
        self.memory: List[Any] = []
        self._max_memory_size = 20  # Kleinere Memory für spezialisierte Agenten
        
        # Track last agent response for evaluation/debugging
        self.last_agent_response: Optional[Dict[str, Any]] = None
        
        logger.debug(f"Initialized {self.__class__.__name__} with {len(self.tools)} tools")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Eindeutiger Name des Agenten."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Beschreibung des Aufgabenbereichs für das Routing."""
        pass
    
    @abstractmethod
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle die Tools für diesen Agenten."""
        pass
    
    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt für diesen Agenten."""
        pass
    
    def process(self, message: str, context: Optional[str] = None) -> str:
        """
        Verarbeite eine Nachricht und gebe die Antwort zurück.
        
        Args:
            message: Die zu verarbeitende Nachricht
            context: Optionaler Kontext vom Orchestrator
        
        Returns:
            Die Antwort des Agenten
        """
        try:
            # Nachricht mit Kontext anreichern falls vorhanden
            full_message = message
            if context:
                full_message = f"[Kontext vom Orchestrator: {context}]\n\n{message}"
            
            # Füge Nachricht zum Memory hinzu
            human_message = HumanMessage(content=full_message)
            self.memory.append(human_message)
            
            # Memory begrenzen
            if len(self.memory) > self._max_memory_size:
                self.memory = self.memory[-self._max_memory_size:]
            
            # Agent ausführen
            agent_input = {
                "messages": [self.system_message] + self.memory
            }
            
            config = {
                "recursion_limit": self.recursion_limit
            }
            
            response = self.agent.invoke(agent_input, config=config)
            
            # Store the full response for evaluation/debugging
            self.last_agent_response = response
            
            # Antwort extrahieren
            ai_message = response["messages"][-1]
            response_text = ai_message.content
            
            if not response_text:
                # Suche nach einer Message mit Inhalt
                for msg in reversed(response["messages"]):
                    if hasattr(msg, 'content') and msg.content:
                        response_text = msg.content
                        break
                
                if not response_text:
                    response_text = "Ich konnte keine Antwort generieren."
            
            # Antwort zum Memory hinzufügen
            self.memory.append(AIMessage(content=response_text))
            
            return response_text
            
        except Exception as e:
            error_msg = f"Fehler im {self.name}: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def get_tool_names(self) -> List[str]:
        """Gebe Liste der verfügbaren Tool-Namen zurück."""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self) -> None:
        """Lösche die Konversationshistorie."""
        self.memory = []
        self.last_agent_response = None
    
    def get_routing_info(self) -> Dict[str, Any]:
        """
        Gebe Routing-Informationen für den Orchestrator zurück.
        
        Returns:
            Dict mit Name, Beschreibung und verfügbaren Tools
        """
        return {
            "name": self.name,
            "description": self.description,
            "tools": self.get_tool_names(),
        }
    
    def get_tool_selection(self, message: str, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Ermittle welche Tools für eine Nachricht ausgewählt würden (ohne Ausführung).
        
        Diese Methode ist für Evaluierung gedacht - sie ruft das LLM auf um
        Tool-Auswahl zu prüfen, führt aber die Tools nicht aus.
        
        Args:
            message: Die zu verarbeitende Nachricht
            context: Optionaler Kontext vom Orchestrator
        
        Returns:
            Liste der ausgewählten Tool-Calls (name, args)
        """
        try:
            full_message = message
            if context:
                full_message = f"[Kontext vom Orchestrator: {context}]\n\n{message}"
            
            # LLM mit Tools binden (ohne Ausführung)
            llm_with_tools = self.llm.bind_tools(self.tools)
            
            # Nachricht erstellen
            from langchain_core.messages import HumanMessage
            messages = [self.system_message, HumanMessage(content=full_message)]
            
            # LLM aufrufen
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
            logger.error(f"Fehler bei Tool-Auswahl im {self.name}: {str(e)}")
            return []
