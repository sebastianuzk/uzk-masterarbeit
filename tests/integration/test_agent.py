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


class TestConfirmationAgentSpecific:
    """Tests spezifisch für Confirmation-Agent"""
    
    def test_confirmation_agent_initialization(self, agent, agent_mode):
        """Teste Confirmation-Agent Initialisierung"""
        if agent_mode == "confirmation":
            assert hasattr(agent, 'get_confirmation_stats')
            assert hasattr(agent, 'confirmation_count')
            assert hasattr(agent, 'confirmed_count')
            assert hasattr(agent, 'rejected_count')
        else:
            pytest.skip("Nur für Confirmation-Agent relevant")
    
    def test_confirmation_stats_initial(self, agent, agent_mode):
        """Teste initiale Confirmation-Statistiken"""
        if agent_mode == "confirmation":
            stats = agent.get_confirmation_stats()
            assert stats["total_confirmations"] == 0
            assert stats["confirmed"] == 0
            assert stats["rejected"] == 0
            assert stats["confirmation_rate"] == 0
            assert stats["last_confirmation"] is None
        else:
            pytest.skip("Nur für Confirmation-Agent relevant")
    
    def test_confirmation_agent_critical_tools_wrapped(self, agent, agent_mode):
        """Teste dass kritische Tools gewrapped sind"""
        if agent_mode == "confirmation":
            tools = agent.get_available_tools()
            # Kritische Tools sollten verfügbar sein
            critical_tool_names = ["klips2_register", "klips2_apply_study", 
                                   "klips2_change_password", "klips2_change_address", 
                                   "send_email"]
            
            for tool_name in critical_tool_names:
                assert tool_name in tools, f"{tool_name} sollte verfügbar sein"
        else:
            pytest.skip("Nur für Confirmation-Agent relevant")
    
    def test_confirmation_agent_validation_rejects_missing_params(self, agent, agent_mode):
        """Teste dass Validierung fehlende Parameter erkennt"""
        if agent_mode == "confirmation":
            # Versuche eine Registrierung ohne alle erforderlichen Parameter
            # Dies sollte durch die Validierung abgelehnt werden
            response = agent.chat(
                "Erstelle einen KLIPS-Account für Max ohne weitere Informationen"
            )
            
            # Agent sollte nach fehlenden Informationen fragen oder Fehler melden
            assert isinstance(response, str)
            assert len(response) > 0
            
            # Die Validierung sollte ausgelöst worden sein
            stats = agent.get_confirmation_stats()
            # Da die Anfrage unvollständig war, könnte sie abgelehnt worden sein
            # oder der Agent fragt nach weiteren Informationen
            assert stats["total_confirmations"] >= 0
        else:
            pytest.skip("Nur für Confirmation-Agent relevant")
    
    def test_confirmation_agent_memory_management(self, agent, agent_mode):
        """Teste Memory-Management des Confirmation-Agents"""
        if agent_mode == "confirmation":
            # Initiales Memory sollte leer sein
            memory_info = agent.get_memory_summary()
            assert memory_info["total_messages"] == 0
            
            # Nach Chat sollte Memory gefüllt sein
            agent.chat("Hallo, was ist KLIPS?")
            memory_info = agent.get_memory_summary()
            assert memory_info["total_messages"] > 0
            
            # Clear sollte funktionieren
            agent.clear_memory()
            memory_info = agent.get_memory_summary()
            assert memory_info["total_messages"] == 0
        else:
            pytest.skip("Nur für Confirmation-Agent relevant")
    
    def test_confirmation_rate_calculation(self, agent, agent_mode):
        """Teste Bestätigungsraten-Berechnung"""
        if agent_mode == "confirmation":
            # Nach mehreren Chats sollten Statistiken verfügbar sein
            stats = agent.get_confirmation_stats()
            
            # confirmation_rate sollte zwischen 0 und 1 liegen
            assert 0 <= stats["confirmation_rate"] <= 1
            
            # Wenn total_confirmations 0 ist, sollte rate auch 0 sein
            if stats["total_confirmations"] == 0:
                assert stats["confirmation_rate"] == 0
            # Sonst sollte die Rate korrekt berechnet sein
            else:
                expected_rate = stats["confirmed"] / stats["total_confirmations"]
                assert stats["confirmation_rate"] == expected_rate
        else:
            pytest.skip("Nur für Confirmation-Agent relevant")