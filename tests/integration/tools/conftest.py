"""
Pytest Configuration für Integration Tests
==========================================
Setzt das Modell für alle Integration Tests auf gpt-oss:20b.

WICHTIG: Diese Datei wird VOR allen Tests geladen!
"""
import os
import sys

import pytest
import requests

# Setze das Modell BEVOR irgendwelche Imports passieren
os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"

# Füge Projekt-Root zum Path hinzu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Jetzt erst Settings importieren und patchen
from config.settings import Settings, settings
Settings.OLLAMA_MODEL = "gpt-oss:20b"


def is_ollama_available() -> bool:
    """Prüft ob Ollama erreichbar ist"""
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


# Cache den Ollama-Status für die gesamte Test-Session
_OLLAMA_AVAILABLE = None


def ollama_available() -> bool:
    """Cached Check ob Ollama verfügbar ist"""
    global _OLLAMA_AVAILABLE
    if _OLLAMA_AVAILABLE is None:
        _OLLAMA_AVAILABLE = is_ollama_available()
    return _OLLAMA_AVAILABLE


def pytest_configure(config):
    """Wird ganz am Anfang von pytest aufgerufen"""
    os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"
    Settings.OLLAMA_MODEL = "gpt-oss:20b"
    print(f"\n🔧 Integration Tests konfiguriert mit Modell: gpt-oss:20b")
    if not ollama_available():
        print("⚠️  Ollama-Server nicht erreichbar - Ollama-abhängige Tests werden übersprungen")


@pytest.fixture(scope="session")
def ollama_check():
    """Fixture das Ollama-abhängige Tests überspringt wenn Ollama nicht läuft"""
    if not ollama_available():
        pytest.skip("Ollama-Server nicht erreichbar")

