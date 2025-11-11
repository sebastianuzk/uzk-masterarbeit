#!/usr/bin/env python3
"""
Leichtgewichtiger Test für RAG Tool - Eine Query
"""

import sys
from pathlib import Path

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.rag_tool import create_university_rag_tool

# Tool erstellen und testen
rag_tool = create_university_rag_tool()

# Test-Query
query = "Was benötige ich für die Bewerbung auf ein höheres Fachsemester?"

print(f"RAG Tool Test")
print("=" * 60)
print(f"Query: {query}")
print("=" * 60)

# RAG-Tool ausführen
result = rag_tool._run(query=query)

print("Ergebnis:")
print(result)