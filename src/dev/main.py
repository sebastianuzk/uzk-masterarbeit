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

# Einfache E-Mail senden
recipient = "test@example.com"
subject = "Test E-Mail vom Chatbot"
body = "Dies ist eine Test-E-Mail vom autonomen Chatbot-System."
sender_name = "Experimenteller Chatbot"

result = email_tool._run(
    recipient=recipient,
    subject=subject,
    body=body,
    sender_name=sender_name
)

print(f"E-Mail Test")
print("-" * 40)
print(f"Empfänger: {recipient}")
print(f"Betreff: {subject}")
print(f"Absender: {sender_name}")
print("-" * 40)
print("Ergebnis:")
print(result)
