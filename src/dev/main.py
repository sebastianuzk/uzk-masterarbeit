#!/usr/bin/env python3
"""
Leichtgewichtiger Test für DuckDuckGo Tool
"""

import sys
from pathlib import Path

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.duckduckgo_tool import DuckDuckGoTool

# Tool erstellen und testen
tool = DuckDuckGoTool()

# Einfache Suche
query = "Wie bewerbe ich mich auf die Universität Köln?"
result = tool._run(query)

print(f"Suche: {query}")
print("-" * 40)
print(result)
