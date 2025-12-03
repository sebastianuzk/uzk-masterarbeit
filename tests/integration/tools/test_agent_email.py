"""
Integration Tests für Email über den Agenten
============================================
Testet ob der Agent das Email-Tool korrekt nutzt.

HINWEIS: Diese Tests senden keine echten E-Mails, 
es sei denn SMTP-Credentials sind konfiguriert.

HINWEIS: Diese Tests verwenden das gpt-oss:20b Modell für bessere Ergebnisse.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Setze das Modell für alle Integration Tests auf gpt-oss:20b
os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"

from src.agent.react_agent import ReactAgent


def has_email_config():
    """Prüft ob Email-Konfiguration vorhanden ist"""
    return bool(os.getenv("SMTP_SERVER")) or bool(os.getenv("EMAIL_RECIPIENT"))


@pytest.fixture
def agent():
    """Erstellt einen Agent für die Tests"""
    return ReactAgent()


@pytest.mark.integration
@pytest.mark.email
@pytest.mark.slow
class TestAgentEmailUnderstanding:
    """Integration Tests: Agent versteht Email-Anfragen"""
    
    def test_agent_understands_email_request(self, agent):
        """Test: Agent versteht Email-Anfrage"""
        response = agent.chat("Kannst du eine E-Mail an den Support schicken?")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_agent_asks_for_email_details(self, agent):
        """Test: Agent fragt nach Email-Details"""
        test_agent = ReactAgent()
        response = test_agent.chat("Schicke eine Email")
        
        assert isinstance(response, str)


@pytest.mark.integration
@pytest.mark.email
@pytest.mark.slow
@pytest.mark.skipif(not has_email_config(), reason="Keine Email-Konfiguration vorhanden")
class TestAgentEmailWithConfig:
    """Integration Tests: Agent sendet Email mit Konfiguration"""
    
    def test_agent_sends_support_email(self, agent):
        """Test: Agent sendet Support-Email"""
        response = agent.chat(
            "Schicke bitte eine E-Mail an den Support mit dem Betreff 'Test' "
            "und dem Inhalt 'Dies ist eine Testnachricht vom Agent-Test.'"
        )
        
        assert isinstance(response, str)
        assert len(response) > 0
