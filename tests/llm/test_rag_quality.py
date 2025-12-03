"""
LLM RAG Quality Tests - Testet die Qualität der RAG-basierten Antworten
"""
import pytest

pytestmark = [pytest.mark.llm, pytest.mark.slow]  # Markiere alle Tests in dieser Datei als LLM-Tests und slow
import sys
import os
from typing import List, Dict

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from src.agent.react_agent import ReactAgent
from src.tools.rag_tool import create_university_rag_tool
from config.settings import settings


class TestLLMRAGQuality:
    """Test-Klasse für RAG-spezifische Antwort-Qualität"""
    
    @pytest.fixture(scope="class")
    def agent(self, ollama_available):
        """Agent-Fixture für alle Tests (verwendet automatisch schnelles Modell)"""
        if not ollama_available:
            pytest.skip("Ollama-Server nicht erreichbar")
        return ReactAgent()
    
    @pytest.fixture(scope="class")
    def rag_tool(self):
        """RAG Tool Fixture"""
        try:
            return create_university_rag_tool()
        except:
            pytest.skip("RAG Tool nicht verfügbar")
    
    # ========================================================================
    # RAG NUTZUNG TESTS
    # ========================================================================
    
    @pytest.mark.slow
    def test_rag_quality_comprehensive(self, agent):
        """Kombinierter Test für RAG-Qualität (schneller als einzelne Tests)"""
        # Test 1: RAG für Universitätsfragen
        agent.clear_memory()
        response = agent.chat("Bachelor-Studiengänge?")
        assert len(response) > 20, "Antwort sollte detailliert sein"
        
        # Test 2: Relevante Begriffe
        expected_terms = ["bachelor", "studiengang", "programm", "wirtschaft", "master", "fakultät"]
        found = sum(1 for term in expected_terms if term in response.lower())
        assert found >= 1, f"Antwort sollte relevante Begriffe enthalten"
    
    # ========================================================================
    # RAG DATEN-QUALITÄT TESTS
    # ========================================================================
    
    def test_rag_returns_relevant_documents(self, rag_tool):
        """Testet ob RAG Tool relevante Dokumente zurückgibt"""
        result = rag_tool._run("Master-Programme WiSo-Fakultät")
        
        # Sollte nicht leer sein und Inhalt haben
        assert result is not None and len(result) > 50, \
            f"RAG sollte nicht-leere, sinnvolle Ergebnisse liefern ({len(result)} Zeichen)"
    



if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
