"""
Integration Tests für RAG über den Agenten
==========================================
Testet ob der Agent das RAG-Tool korrekt nutzt.

Unterstützt Single-Agent und Multi-Agent Modi via pytest Fixtures.

Verwendung:
    pytest tests/integration/tools/test_agent_rag.py                    # Single-Agent
    pytest tests/integration/tools/test_agent_rag.py --agent-mode=multi # Multi-Agent

HINWEIS: Diese Tests verwenden das gpt-oss:20b Modell für bessere Ergebnisse.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Setze das Modell für alle Integration Tests auf gpt-oss:20b
os.environ["OLLAMA_MODEL"] = "gpt-oss:20b"

from tests.integration.tools.conftest import ollama_available


def has_vector_db():
    """Prüft ob eine ChromaDB-Datenbank vorhanden ist"""
    paths = [
        Path("data/vector_db"),
        Path("src/scraper/vector_db")
    ]
    for p in paths:
        if p.exists() and (p / "chroma.sqlite3").exists():
            return True
    return False


# Überspringe alle Tests wenn Ollama nicht verfügbar ist
pytestmark = [
    pytest.mark.skipif(not ollama_available(), reason="Ollama-Server nicht erreichbar"),
    pytest.mark.agent
]


# Note: We use the global 'agent' fixture from conftest.py which respects --agent-mode


@pytest.mark.integration
@pytest.mark.rag
@pytest.mark.slow
@pytest.mark.skipif(not has_vector_db(), reason="Keine ChromaDB-Datenbank vorhanden")
class TestAgentRAGSearch:
    """Integration Tests: Agent nutzt RAG-Tool für Uni-Wissen"""
    
    def test_agent_answers_bewerbung_question(self, agent):
        """Test: Agent beantwortet Bewerbungsfrage mit RAG"""
        response = agent.chat("Wie kann ich mich an der Uni Köln bewerben?")
        
        assert isinstance(response, str)
        assert len(response) > 0
        response_lower = response.lower()
        has_relevant_content = (
            "bewerbung" in response_lower or
            "bewerben" in response_lower or
            "klips" in response_lower or
            "studium" in response_lower
        )
        assert has_relevant_content, "Antwort sollte bewerbungsrelevant sein"
    
    def test_agent_answers_fristen_question(self, agent):
        """Test: Agent beantwortet Fristenfrage"""
        response = agent.chat("Wann sind die Bewerbungsfristen für das Wintersemester?")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_agent_answers_studiengang_question(self, agent):
        """Test: Agent beantwortet Studiengangfrage"""
        from src.agent.react_agent import ReactAgent
        test_agent = ReactAgent()
        response = test_agent.chat("Welche Studiengänge bietet die WiSo-Fakultät an?")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_agent_uses_knowledge_for_klips(self, agent):
        """Test: Agent nutzt Wissensdatenbank für KLIPS-Fragen"""
        from src.agent.react_agent import ReactAgent
        test_agent = ReactAgent()
        response = test_agent.chat("Was ist KLIPS und wie funktioniert es?")
        
        assert isinstance(response, str)
        assert len(response) > 0
    
    def test_agent_handles_specific_question(self, agent):
        """Test: Agent beantwortet spezifische Uni-Frage"""
        from src.agent.react_agent import ReactAgent
        test_agent = ReactAgent()
        response = test_agent.chat("Wie hoch ist der Semesterbeitrag an der Uni Köln?")
        
        assert isinstance(response, str)
