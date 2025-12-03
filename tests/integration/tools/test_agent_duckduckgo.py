"""
Integration Tests für DuckDuckGo über den Agenten
=================================================
Testet ob der Agent das DuckDuckGo-Tool korrekt nutzt.

HINWEIS: Diese Tests verwenden das gpt-oss:20b Modell für bessere Ergebnisse.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Setze das Modell für alle Integration Tests auf gpt-oss:20b
os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"

from src.agent.react_agent import ReactAgent


@pytest.fixture(scope="module")
def agent():
    """Erstellt einen Agent für die Tests"""
    return ReactAgent()


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.network
class TestAgentDuckDuckGoSearch:
    """Integration Tests: Agent nutzt DuckDuckGo-Tool"""
    
    def test_agent_searches_for_university(self, agent):
        """Test: Agent sucht nach Universität Köln"""
        response = agent.chat("Suche im Internet nach der Universität zu Köln")
        
        assert isinstance(response, str)
        assert len(response) > 0
        response_lower = response.lower()
        assert "köln" in response_lower or "uni" in response_lower or "universität" in response_lower
    
    def test_agent_searches_for_klips(self, agent):
        """Test: Agent sucht nach KLIPS"""
        test_agent = ReactAgent()
        response = test_agent.chat("Was findest du im Internet über KLIPS an der Uni Köln?")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_agent_searches_bewerbungsfristen(self, agent):
        """Test: Agent sucht nach Bewerbungsfristen"""
        test_agent = ReactAgent()
        response = test_agent.chat("Suche online nach den aktuellen Bewerbungsfristen für die Uni Köln")
        
        assert isinstance(response, str)
        assert len(response) > 0


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.network
class TestAgentWebScraper:
    """Integration Tests: Agent nutzt Web-Scraper-Tool"""
    
    def test_agent_scrapes_uni_homepage(self, agent):
        """Test: Agent scraped Uni-Homepage"""
        test_agent = ReactAgent()
        response = test_agent.chat("Hole mir den Inhalt von der Webseite https://www.uni-koeln.de")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_agent_scrapes_wiso_page(self, agent):
        """Test: Agent scraped WiSo-Seite"""
        test_agent = ReactAgent()
        response = test_agent.chat("Was steht auf der Webseite https://wiso.uni-koeln.de?")
        
        assert isinstance(response, str)
        assert len(response) > 0
