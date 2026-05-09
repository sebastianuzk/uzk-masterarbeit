"""
Multi-Agent System Facade - Einheitliche Schnittstelle für das Multi-Agent-System.

Diese Klasse bietet die gleiche Schnittstelle wie der ursprüngliche ReactAgent,
um nahtlose Integration und einfaches Umschalten zu ermöglichen.
"""

import uuid
from typing import Any, Dict, List

from .orchestrator import OrchestratorAgent


class MultiAgentSystem:
    """
    Facade für das Multi-Agent-System.
    
    Bietet die gleiche Schnittstelle wie ReactAgent für einfache
    Integration in bestehende Systeme (Streamlit, CLI).
    """
    
    def __init__(self, force_llm_routing: bool = False):
        """
        Initialisiere das Multi-Agent-System.
        
        Args:
            force_llm_routing: Wenn True, keine Keyword-Vorfilterung (für Evaluation-Konsistenz)
        """
        self.orchestrator = OrchestratorAgent(force_llm_routing=force_llm_routing)
        self.conversation_trace: List[Dict[str, Any]] = []
    
    def chat(self, message: str, session_id: str = None) -> str:
        """
        Führe eine Unterhaltung mit dem Multi-Agent-System.
        
        Args:
            message: Die Nachricht des Nutzers
            session_id: Optionale Session-ID für Tracing
            
        Returns:
            Die Antwort des Systems
            
        Raises:
            ValueError: Wenn die Nachricht leer oder None ist
        """
        if not message or not message.strip():
            raise ValueError("Die Nachricht darf nicht leer sein")
        
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        return self.orchestrator.process(message, session_id=session_id)
    
    def get_available_tools(self) -> List[str]:
        """
        Gebe Liste der verfügbaren Tools zurück.
        
        Returns:
            Liste aller Tool-Namen über alle Agenten
        """
        return self.orchestrator.get_all_tools()
    
    def get_available_agents(self) -> List[str]:
        """
        Gebe Liste der verfügbaren Agenten zurück.
        
        Returns:
            Liste der Agenten-Namen
        """
        return self.orchestrator.get_available_agents()
    
    def clear_memory(self) -> None:
        """Lösche Konversationshistorie aller Agenten."""
        self.orchestrator.clear_memory()
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """
        Gebe Zusammenfassung des Memory zurück.
        
        Returns:
            Dict mit Memory-Statistiken
        """
        return self.orchestrator.get_memory_summary()
    
    def get_agent_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Gebe detaillierte Informationen über alle Agenten zurück.
        
        Returns:
            Dict mit Agenten-Informationen
        """
        return self.orchestrator.get_agent_info()
    
    def get_tool_selection(self, message: str, enable_trace: bool = False) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl ohne Ausführung (für Evaluierung).

        Diese Methode führt das Routing durch und fragt den spezialisierten
        Agenten welche Tools er auswählen würde, ohne sie auszuführen.

        Args:
            message: Die Nutzeranfrage
            enable_trace: Wenn True, wird Routing-Trace in conversation_trace gespeichert

        Returns:
            Liste der ausgewählten Tool-Calls
        """
        from datetime import datetime
        if enable_trace:
            self.conversation_trace = []

        agent_name, tool_calls, step_details = self.orchestrator.get_tool_selection(message)

        if enable_trace:
            if step_details:
                # Multi-step: one trace entry per decomposed step
                for i, step in enumerate(step_details, 1):
                    self.conversation_trace.append({
                        "step": f"routing_step_{i}",
                        "step_query": step["step_query"],
                        "routed_to": step["routed_to"],
                        "tool_calls_proposed": [{"name": tc.get("name", ""), "args": tc.get("args", {})} for tc in step["tools"]],
                        "timestamp": datetime.now().isoformat(),
                    })
            else:
                # Single-step: one trace entry
                self.conversation_trace.append({
                    "step": "routing",
                    "routed_to": agent_name,
                    "tool_calls_proposed": [{"name": tc.get("name", ""), "args": tc.get("args", {})} for tc in tool_calls],
                    "timestamp": datetime.now().isoformat(),
                })

        return tool_calls  # Nur Tool-Calls zurückgeben, nicht das Tuple!

    def clear_conversation_trace(self):
        """Lösche den Conversation-Trace."""
        self.conversation_trace = []


def create_multi_agent_system() -> MultiAgentSystem:
    """
    Factory-Funktion für das Multi-Agent-System.
    
    Returns:
        Initialisiertes MultiAgentSystem
    """
    return MultiAgentSystem()
