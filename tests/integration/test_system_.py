"""
Systemtests für den Autonomen Chatbot-Agenten

Unterstützt Single-Agent und Multi-Agent Modi via pytest Fixtures.

Verwendung:
    pytest tests/integration/test_system_.py                    # Single-Agent (default)
    pytest tests/integration/test_system_.py --agent-mode=multi # Multi-Agent
"""
import os
import pytest

# Markiere alle Tests in dieser Datei als slow, integration und agent
pytestmark = [pytest.mark.slow, pytest.mark.integration, pytest.mark.agent]

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.settings import settings
from src.tools.email_tool import create_email_tool


# ============================================================================
# HELPER: Skip wenn Ollama nicht verfügbar
# ============================================================================

@pytest.fixture(autouse=True)
def skip_if_ollama_unavailable():
    """Überspringe Tests wenn Ollama nicht erreichbar ist"""
    try:
        import requests
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
        if response.status_code != 200:
            pytest.skip("Ollama-Server nicht erreichbar")
    except Exception:
        pytest.skip("Ollama-Server nicht erreichbar")


# ============================================================================
# TESTS
# ============================================================================

class TestSystemIntegration:
    """Test-Klasse für Systemintegrationstests"""
    
    def test_complete_system_initialization(self, agent):
        """Teste vollständige Systeminitialisierung und Interaktion"""
        # Agent ist bereits initialisiert durch Fixture
        assert agent is not None
        
        # Überprüfe Tools
        tools = agent.get_available_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        assert "send_email" in tools
        
        # Teste einfache Interaktion
        response = agent.chat("Hallo")
        assert isinstance(response, str)
        assert len(response) > 10
    
    def test_email_tool_standalone(self):
        """Teste eigenständiges E-Mail-Tool"""
        email_tool = create_email_tool()
        assert email_tool is not None
        assert email_tool.name == "send_email"
        
        # Teste Tool-Schema
        assert email_tool.args_schema is not None
        
        # Teste, dass die richtigen Parameter erwartet werden
        schema_fields = email_tool.args_schema.model_fields
        assert "subject" in schema_fields
        assert "body" in schema_fields
        
        # Stelle sicher, dass alte Parameter nicht mehr da sind
        assert "recipient" not in schema_fields
        assert "sender_name" not in schema_fields
    
    def test_email_tool_in_agent(self, agent):
        """Teste E-Mail-Tool-Integration im Agent"""
        # Überprüfe, dass E-Mail-Tool korrekt konfiguriert ist
        tools = agent.get_available_tools()
        assert "send_email" in tools
    
    def test_configuration_validation(self):
        """Teste Systemkonfiguration"""
        # Teste Settings-Validierung
        settings.validate()
        
        # Überprüfe kritische Konfigurationen
        assert settings.OLLAMA_BASE_URL is not None
        assert settings.OLLAMA_MODEL is not None
        
        # E-Mail-Konfiguration (kann leer sein, sollte aber definiert sein)
        assert hasattr(settings, 'SMTP_SERVER')
        assert hasattr(settings, 'SMTP_PORT')
        assert hasattr(settings, 'SMTP_USERNAME')
        assert hasattr(settings, 'SMTP_PASSWORD')
        assert hasattr(settings, 'DEFAULT_RECIPIENT')
    
    def test_memory_and_conversation_flow(self, agent):
        """Teste Memory-Management"""
        # Teste Memory-Clearing
        agent.clear_memory()
        memory_info = agent.get_memory_summary()
        assert memory_info["total_messages"] == 0