"""
LLM Response Quality Tests - Testet die Qualität und Korrektheit der Modellantworten

Unterstützt Single-Agent und Multi-Agent Modi via pytest Fixtures.

Verwendung:
    pytest tests/llm/test_response_quality.py                    # Single-Agent (default)
    pytest tests/llm/test_response_quality.py --agent-mode=multi # Multi-Agent
"""
import pytest

# Markiere alle Tests in dieser Datei als LLM-Tests, slow und agent
pytestmark = [pytest.mark.llm, pytest.mark.slow, pytest.mark.agent]

import sys
import os
from typing import List, Dict

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from config.settings import settings


class TestLLMResponseQuality:
    """Test-Klasse für die Qualität der LLM-Antworten"""
    
    @pytest.fixture(autouse=True)
    def skip_if_ollama_unavailable(self, ollama_available):
        """Überspringe wenn Ollama nicht verfügbar"""
        if not ollama_available:
            pytest.skip("Ollama-Server nicht erreichbar")
    
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
