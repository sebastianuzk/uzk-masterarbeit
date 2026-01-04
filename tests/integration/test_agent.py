"""
Tests für den Agent (Single-Agent und Multi-Agent)

Diese Tests sind agnostisch gegenüber dem Agent-Mode und nutzen
die pytest Fixtures aus conftest.py.

Verwendung:
    pytest tests/integration/test_agent.py                    # Single-Agent (default)
    pytest tests/integration/test_agent.py --agent-mode=multi # Multi-Agent
"""
import os
import sys
import pytest

# Markiere alle Tests in dieser Datei als slow, integration und agent
pytestmark = [pytest.mark.slow, pytest.mark.integration, pytest.mark.agent]

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.settings import settings


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

class TestAgentInitialization:
    """Tests für Agent-Initialisierung"""
    
    def test_agent_initialization(self, agent):
        """Teste Agent-Initialisierung"""
        assert agent is not None
        assert hasattr(agent, 'chat')
        assert hasattr(agent, 'get_available_tools')
        assert hasattr(agent, 'clear_memory')
        assert hasattr(agent, 'get_memory_summary')
    
    def test_available_tools(self, agent):
        """Teste verfügbare Tools"""
        tools = agent.get_available_tools()
        
        assert isinstance(tools, list)
        assert len(tools) > 0
        
        # Diese Tools sollten immer verfügbar sein
        if settings.ENABLE_WEB_SCRAPER:
            assert "web_scraper" in tools
        
        if settings.ENABLE_DUCKDUCKGO:
            assert "duckduckgo_search" in tools
        
        # E-Mail-Tool sollte immer verfügbar sein
        assert "send_email" in tools


class TestAgentMemory:
    """Tests für Memory-Management"""
    
    def test_initial_memory_empty(self, agent):
        """Teste, dass initiales Memory leer ist"""
        memory_info = agent.get_memory_summary()
        assert memory_info["total_messages"] == 0
    
    def test_clear_memory(self, agent):
        """Teste Memory löschen nach Konversation"""
        # Füge erst etwas zum Memory hinzu
        agent.chat("Hallo, wie geht es dir?")
        
        # Überprüfe, dass Memory nicht leer ist
        memory_info_before = agent.get_memory_summary()
        assert memory_info_before["total_messages"] > 0
        
        # Lösche Memory
        agent.clear_memory()
        
        # Überprüfe, dass Memory jetzt leer ist
        memory_info_after = agent.get_memory_summary()
        assert memory_info_after["total_messages"] == 0
    
    def test_memory_after_chat(self, agent):
        """Teste Memory nach Chat"""
        agent.chat("Hallo")
        
        memory_info = agent.get_memory_summary()
        assert memory_info["total_messages"] > 0


class TestAgentChat:
    """Tests für Chat-Funktionalität"""
    
    def test_simple_chat(self, agent):
        """Teste einfache Chat-Funktionalität"""
        response = agent.chat("Hallo, wie geht es dir?")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_chat_response_not_empty(self, agent):
        """Teste, dass Chat-Antworten nicht leer sind"""
        response = agent.chat("Was ist KLIPS?")
        
        assert response is not None
        assert len(response.strip()) > 0


class TestAgentTools:
    """Tests für Tool-Integration"""
    
    def test_email_tool_available(self, agent):
        """Teste E-Mail-Tool-Verfügbarkeit"""
        tools = agent.get_available_tools()
        assert "send_email" in tools
    
    def test_klips_tools_available(self, agent):
        """Teste KLIPS-Tools-Verfügbarkeit"""
        tools = agent.get_available_tools()
        
        # Mindestens ein KLIPS-Tool sollte verfügbar sein
        klips_tools = [t for t in tools if "klips" in t.lower()]
        assert len(klips_tools) > 0


class TestMultiAgentSpecific:
    """Tests spezifisch für Multi-Agent-System"""
    
    def test_multi_agent_has_agents_method(self, agent, agent_mode):
        """Teste ob Multi-Agent get_available_agents hat"""
        if agent_mode == "multi":
            assert hasattr(agent, 'get_available_agents')
            agents = agent.get_available_agents()
            assert isinstance(agents, list)
            assert len(agents) > 0
        else:
            # Single-Agent hat diese Methode nicht
            pytest.skip("Nur für Multi-Agent relevant")
    
    def test_multi_agent_routing(self, agent, agent_mode):
        """Teste ob Multi-Agent korrekt routet"""
        if agent_mode == "multi":
            # KLIPS-bezogene Frage sollte funktionieren
            response = agent.chat("Wie kann ich mich bei KLIPS registrieren?")
            assert isinstance(response, str)
            assert len(response) > 0
        else:
            pytest.skip("Nur für Multi-Agent relevant")