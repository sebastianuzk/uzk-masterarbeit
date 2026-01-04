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
    
    def __init__(self):
        """Initialisiere das Multi-Agent-System."""
        self.orchestrator = OrchestratorAgent()
    
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
    
    def get_tool_selection(self, message: str) -> List[Dict[str, Any]]:
        """
        Ermittle Tool-Auswahl ohne Ausführung (für Evaluierung).
        
        Diese Methode führt das Routing durch und fragt den spezialisierten
        Agenten welche Tools er auswählen würde, ohne sie auszuführen.
        
        Args:
            message: Die Nutzeranfrage
            
        Returns:
            Liste der ausgewählten Tool-Calls
        """
        agent_name, tool_calls = self.orchestrator.get_tool_selection(message)
        return tool_calls


def create_multi_agent_system() -> MultiAgentSystem:
    """
    Factory-Funktion für das Multi-Agent-System.
    
    Returns:
        Initialisiertes MultiAgentSystem
    """
    return MultiAgentSystem()
