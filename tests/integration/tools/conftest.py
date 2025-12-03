"""
Pytest Configuration für Integration Tests
==========================================
Setzt das Modell für alle Integration Tests auf gpt-oss:20b.

WICHTIG: Diese Datei wird VOR allen Tests geladen!
"""
import os
import sys

# Setze das Modell BEVOR irgendwelche Imports passieren
os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Jetzt erst Settings importieren und patchen
from config.settings import Settings
Settings.OLLAMA_MODEL = "gpt-oss:20b"

import pytest


def pytest_configure(config):
    """Wird ganz am Anfang von pytest aufgerufen"""
    os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"
    Settings.OLLAMA_MODEL = "gpt-oss:20b"
    print(f"\n🔧 Integration Tests konfiguriert mit Modell: gpt-oss:20b")
