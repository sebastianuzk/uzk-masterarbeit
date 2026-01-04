"""
Constrained Agent Package - Agent mit Schema-beschränkter Generierung.

Der Constrained Agent erzwingt gültige Tool-Call-Strukturen während der Generierung,
um JSON-Parse-Fehler und falsche Feldnamen zu verhindern.

Basierend auf dem Konzept von "Constrained Decoding" (LMQL, Beurer-Kellner et al., 2022).
"""

from .constrained_agent import ConstrainedAgent, create_constrained_agent

__all__ = [
    "ConstrainedAgent",
    "create_constrained_agent",
]
