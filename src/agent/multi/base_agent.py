"""
Base Agent Klasse für spezialisierte Agenten im Multi-Agent-System.

Bietet gemeinsame Funktionalität für alle spezialisierten Agenten:
- LLM-Initialisierung
- Tool-Management
- Memory-Handling
- Agent-Erstellung mit LangGraph
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent as create_langgraph_agent

from config.settings import settings


class BaseSpecializedAgent(ABC):
    """
    Abstrakte Basisklasse für spezialisierte Agenten.
    
    Jeder spezialisierte Agent:
    - Hat einen eindeutigen Namen und Beschreibung
    - Verfügt über eine Menge von Tools für seinen Aufgabenbereich
    - Kann Anfragen in seinem Bereich bearbeiten
    """
    
    def __init__(self, share_llm: Optional[ChatOllama] = None):
        """
        Initialisiere den spezialisierten Agenten.
        
        Args:
            share_llm: Optional geteilte LLM-Instanz für Ressourceneffizienz
        """
        # LLM initialisieren oder teilen
        self.llm = share_llm if share_llm else self._create_llm()
        
        # Tools für diesen Agenten erstellen
        self.tools = self._create_tools()
        
        # System-Prompt erstellen
        self.system_message = SystemMessage(content=self._get_system_prompt())
        
        # Agent mit LangGraph erstellen
        self.agent = create_langgraph_agent(self.llm, self.tools)
        
        # Memory für Konversationshistorie (begrenzt)
        self.memory: List[Any] = []
        self._max_memory_size = 20  # Kleinere Memory für spezialisierte Agenten
        
        # Track last agent response for evaluation/debugging
        self.last_agent_response: Optional[Dict[str, Any]] = None
    
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
    
    def _create_llm(self) -> ChatOllama:
        """
        Erstelle eine LLM-Instanz mit optimierten Einstellungen.
        
        Returns:
            Konfigurierte ChatOllama-Instanz
        """
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
        ctx_size = 8192  # Standard
        for size_key, ctx_value in MODEL_CTX_SIZES.items():
            if size_key in model_lower:
                ctx_size = ctx_value
                break
        
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE,
            num_ctx=ctx_size,
            timeout=settings.REQUEST_TIMEOUT,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
    
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
            
            response = self.agent.invoke(agent_input)
            
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
            return error_msg
    
    def get_tool_names(self) -> List[str]:
        """Gebe Liste der verfügbaren Tool-Namen zurück."""
        return [tool.name for tool in self.tools]
    
    def clear_memory(self) -> None:
        """Lösche die Konversationshistorie."""
        self.memory = []
    
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
            print(f"Fehler bei Tool-Auswahl im {self.name}: {str(e)}")
            return []
