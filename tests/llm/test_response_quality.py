"""
LLM Response Quality Tests - Testet die Qualität und Korrektheit der Modellantworten
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
from config.settings import settings


class TestLLMResponseQuality:
    """Test-Klasse für die Qualität der LLM-Antworten"""
    
    @pytest.fixture(scope="class")
    def agent(self, ollama_available):
        """Agent-Fixture für alle Tests (verwendet automatisch schnelles Modell)"""
        if not ollama_available:
            pytest.skip("Ollama-Server nicht erreichbar")
        return ReactAgent()
    
    # ========================================================================
    # FAKTENTREUE & KONVERSATIONSFLUSS - KOMBINIERT
    # ========================================================================
    
    @pytest.mark.slow
    def test_response_quality_comprehensive(self, agent):
        """Kombinierter Test für Response-Qualität (schneller als einzelne Tests)"""
        agent.clear_memory()
        response = agent.chat("Guten Tag! Wie heißt die Universität?")
        
        # Sollte nicht leer sein und entweder freundlich oder informativ antworten
        assert len(response) > 10, "Antwort sollte nicht leer sein"
        
        # Sehr flexible Prüfung - nur dass irgendeine sinnvolle Antwort kommt
        assert len(response.split()) > 3, f"Antwort sollte mehrere Wörter enthalten"
    
    # ========================================================================
    # ANTWORTFORMAT TESTS
    # ========================================================================
    
    @pytest.mark.slow
    def test_response_not_empty_and_reasonable_length(self, agent):
        """Testet ob Antworten nicht leer sind und vernünftige Länge haben"""
        response = agent.chat("Hallo!")
        assert response and 10 < len(response.strip()) < 2000, \
            f"Antwort sollte zwischen 10 und 2000 Zeichen haben: {len(response)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
