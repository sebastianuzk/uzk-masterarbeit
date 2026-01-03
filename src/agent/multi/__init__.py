"""
Multi-Agent System Package

Implementiert ein Supervisor-Pattern basiertes Multi-Agent-System
mit spezialisierten Agenten für verschiedene Aufgabenbereiche.

Hauptkomponenten:
- OrchestratorAgent: Routing-Agent, der Anfragen an spezialisierte Agenten weiterleitet
- KlipsAgent: Spezialisiert auf KLIPS2-Funktionalität
- EmailAgent: Spezialisiert auf E-Mail-Versand
- KnowledgeAgent: Spezialisiert auf Wissensabfragen (RAG, Web-Suche)
"""

from .orchestrator import OrchestratorAgent
from .multi_agent_system import MultiAgentSystem, create_multi_agent_system
from .klips_agent import KlipsAgent
from .email_agent import EmailAgent
from .knowledge_agent import KnowledgeAgent

__all__ = [
    "OrchestratorAgent",
    "MultiAgentSystem",
    "create_multi_agent_system",
    "KlipsAgent",
    "EmailAgent",
    "KnowledgeAgent",
]
