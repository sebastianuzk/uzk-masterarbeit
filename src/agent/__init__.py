"""
Agent Package - Enthält Single-Agent, Multi-Agent und Confirmation-Agent Implementierungen.

Verfügbare Agent-Systeme:
- ReactAgent: Einzelner Agent mit allen Tools (Original-Implementierung)
- MultiAgentSystem: Multi-Agent-System mit spezialisierten Agenten
- ConfirmationAgent: Agent mit interner Validierungsschleife vor kritischen Tools

Verwendung:
    # Single-Agent (Original)
    from src.agent import create_react_agent
    agent = create_react_agent()
    
    # Multi-Agent-System
    from src.agent import create_multi_agent_system
    agent = create_multi_agent_system()
    
    # Confirmation-Agent (Self-Critique)
    from src.agent import create_confirmation_agent
    agent = create_confirmation_agent()
    
    # Oder direkt über Factory mit Mode-Parameter
    from src.agent import create_agent
    agent = create_agent(mode="single")  # oder mode="multi" oder mode="confirmation"
"""

from enum import Enum
from typing import Union

from .react_agent import ReactAgent, create_react_agent
from .multi import MultiAgentSystem, create_multi_agent_system
from .confirmation import ConfirmationAgent, create_confirmation_agent


class AgentMode(str, Enum):
    """Verfügbare Agent-Modi."""
    SINGLE = "single"
    MULTI = "multi"
    CONFIRMATION = "confirmation"


def create_agent(mode: Union[str, AgentMode] = AgentMode.SINGLE):
    """
    Factory-Funktion die den passenden Agenten basierend auf dem Mode erstellt.
    
    Args:
        mode: "single" für ReactAgent, "multi" für MultiAgentSystem,
              "confirmation" für ConfirmationAgent
        
    Returns:
        Agent-Instanz (ReactAgent, MultiAgentSystem oder ConfirmationAgent)
        
    Raises:
        ValueError: Bei unbekanntem Mode
    """
    if isinstance(mode, str):
        mode = mode.lower()
    
    if mode in (AgentMode.SINGLE, "single"):
        print("🤖 Starte Single-Agent Modus")
        return create_react_agent()
    elif mode in (AgentMode.MULTI, "multi"):
        print("🎭 Starte Multi-Agent Modus")
        return create_multi_agent_system()
    elif mode in (AgentMode.CONFIRMATION, "confirmation"):
        print("🔒 Starte Confirmation-Agent Modus")
        return create_confirmation_agent()
    else:
        raise ValueError(
            f"Unbekannter Agent-Mode: {mode}. "
            "Verwende 'single', 'multi' oder 'confirmation'."
        )


__all__ = [
    # Single Agent
    "ReactAgent",
    "create_react_agent",
    # Multi Agent
    "MultiAgentSystem",
    "create_multi_agent_system",
    # Confirmation Agent
    "ConfirmationAgent",
    "create_confirmation_agent",
    # Factory
    "create_agent",
    "AgentMode",
]
