#!/usr/bin/env python3
"""
Leichtgewichtiger Test für E-Mail Tool
"""

import sys
from pathlib import Path

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.email_tool import create_email_tool

# Tool erstellen und testen
email_tool = create_email_tool()

# Einfache E-Mail senden (nur subject und body erforderlich)
subject = "Test E-Mail vom Chatbot"
body = "Dies ist eine Test-E-Mail vom autonomen Chatbot-System."

result = email_tool._run(
    subject=subject,
    body=body
)

print(f"E-Mail Test")
print("-" * 40)
print(f"Betreff: {subject}")
print("-" * 40)
print("Ergebnis:")
print(result)
