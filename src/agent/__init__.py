"""
Agent Package - Enthält Single-Agent, Multi-Agent, Confirmation-Agent und Constrained-Agent.

Verfügbare Agent-Systeme:
- ReactAgent: Einzelner Agent mit allen Tools (Original-Implementierung)
- MultiAgentSystem: Multi-Agent-System mit spezialisierten Agenten
- ConfirmationAgent: Agent mit interner Validierungsschleife vor kritischen Tools
- ConstrainedAgent: Agent mit Schema-beschränkter Generierung (LMQL-inspiriert)

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
    
    # Constrained-Agent (Schema-Validierung)
    from src.agent import create_constrained_agent
    agent = create_constrained_agent()
    
    # Oder direkt über Factory mit Mode-Parameter
    from src.agent import create_agent
    agent = create_agent(mode="single")  # single, multi, confirmation, constrained
"""

from enum import Enum
from typing import Union

from config.logging_config import get_logger

from .react_agent import ReactAgent, create_react_agent
from .multi import MultiAgentSystem, create_multi_agent_system
from .confirmation import ConfirmationAgent, create_confirmation_agent
from .constrained import ConstrainedAgent, create_constrained_agent

logger = get_logger(__name__)


class AgentMode(str, Enum):
    """Verfügbare Agent-Modi."""
    SINGLE = "single"
    MULTI = "multi"
    CONFIRMATION = "confirmation"
    CONSTRAINED = "constrained"


def create_agent(mode: Union[str, AgentMode] = AgentMode.SINGLE):
    """
    Factory-Funktion die den passenden Agenten basierend auf dem Mode erstellt.
    
    Args:
        mode: "single" für ReactAgent, "multi" für MultiAgentSystem,
              "confirmation" für ConfirmationAgent, "constrained" für ConstrainedAgent
        
    Returns:
        Agent-Instanz
        
    Raises:
        ValueError: Bei unbekanntem Mode
    """
    if isinstance(mode, str):
        mode = mode.lower()
    
    if mode in (AgentMode.SINGLE, "single"):
        logger.info("Starting Single-Agent mode")
        return create_react_agent()
    elif mode in (AgentMode.MULTI, "multi"):
        logger.info("Starting Multi-Agent mode")
        return create_multi_agent_system()
    elif mode in (AgentMode.CONFIRMATION, "confirmation"):
        logger.info("Starting Confirmation-Agent mode")
        return create_confirmation_agent()
    elif mode in (AgentMode.CONSTRAINED, "constrained"):
        logger.info("Starting Constrained-Agent mode")
        return create_constrained_agent()
    else:
        raise ValueError(
            f"Unbekannter Agent-Mode: {mode}. "
            "Verwende 'single', 'multi', 'confirmation' oder 'constrained'."
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
    # Constrained Agent
    "ConstrainedAgent",
    "create_constrained_agent",
    # Factory
    "create_agent",
    "AgentMode",
]
