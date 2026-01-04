"""
Confirmation Agent Package - Agent mit interner Validierungsschleife.

Der Confirmation Agent führt vor kritischen Tool-Aufrufen eine
interne Selbstvalidierung durch, um sicherzustellen, dass:
1. Alle erforderlichen Parameter vorhanden sind
2. Die Parameter im korrekten Format vorliegen
3. Der Tool-Aufruf sinnvoll ist

Dies implementiert ein "Self-Critique" Pattern, bei dem der Agent
seine eigenen Entscheidungen vor der Ausführung überprüft.
"""

from .confirmation_agent import ConfirmationAgent, create_confirmation_agent

__all__ = [
    "ConfirmationAgent",
    "create_confirmation_agent",
]
