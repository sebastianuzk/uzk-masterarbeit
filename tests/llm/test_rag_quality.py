"""
LLM RAG Quality Tests - Testet die Qualität der RAG-basierten Antworten
"""
import pytest
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
    def agent(self):
        """Agent-Fixture für alle Tests"""
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
            if response.status_code != 200:
                pytest.skip("Ollama-Server nicht erreichbar")
        except:
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
    
    def test_uses_rag_for_university_questions(self, agent):
        """Testet ob der Agent RAG für Universitätsfragen verwendet"""
        agent.clear_memory()
        response = agent.chat("Welche Master-Programme gibt es an der WiSo-Fakultät?")
        
        # Sollte spezifische Informationen enthalten (nur möglich mit RAG)
        # Allgemeine Antworten wie "Es gibt BWL und VWL" sind zu unspezifisch
        assert len(response) > 100, \
            f"Antwort sollte detailliert sein (RAG-basiert): {len(response)} Zeichen"
    
    def test_rag_provides_source_urls(self, agent):
        """Testet ob RAG-basierte Antworten Quellen-URLs enthalten"""
        agent.clear_memory()
        response = agent.chat("Wie bewerbe ich mich für einen Master an der WiSo?")
        
        # Sollte URL-Hinweise enthalten
        url_indicators = ["http", "www", "uni-koeln.de", "wiso.uni"]
        
        has_url = any(indicator in response.lower() for indicator in url_indicators)
        
        # Warnung wenn keine URL (sollte normalerweise vorhanden sein)
        if not has_url:
            print(f"⚠️  Warnung: Keine Quellen-URL in RAG-Antwort gefunden")
            print(f"   Antwort: {response[:200]}...")
    
    # ========================================================================
    # RAG DATEN-QUALITÄT TESTS
    # ========================================================================
    
    def test_rag_returns_relevant_documents(self, rag_tool):
        """Testet ob RAG Tool relevante Dokumente zurückgibt"""
        result = rag_tool._run("Master-Programme WiSo-Fakultät")
        
        # Sollte nicht leer sein und Inhalt haben
        assert result is not None and len(result) > 0, \
            "RAG sollte nicht-leere Ergebnisse liefern"
        
        # Sollte mindestens 50 Zeichen haben (sinnvoller Content)
        assert len(result) > 50, \
            f"RAG-Ergebnis zu kurz ({len(result)} Zeichen): {result}"
    
    def test_rag_returns_multiple_sources(self, rag_tool):
        """Testet ob RAG Tool mehrere Quellen zurückgibt"""
        result = rag_tool._run("Bewerbung Master WiSo")
        
        # Sollte mehrere URLs enthalten (= mehrere Quellen)
        url_count = result.lower().count("http") + result.lower().count("www")
        
        # Erwarte mindestens 2 Quellen
        assert url_count >= 2, \
            f"RAG sollte mehrere Quellen liefern (gefunden: {url_count})"
    
    def test_rag_empty_query_handling(self, rag_tool):
        """Testet wie RAG mit leeren Queries umgeht"""
        result = rag_tool._run("")
        
        # Sollte nicht crashen und eine sinnvolle Antwort geben
        assert result is not None and len(result) > 0, \
            "RAG sollte bei leerer Query nicht crashen"
    
    # ========================================================================
    # KATEGORIE-SPEZIFISCHE TESTS
    # ========================================================================
    
    def test_rag_studium_category_accuracy(self, agent):
        """Testet ob Studiums-Fragen korrekt beantwortet werden"""
        agent.clear_memory()
        response = agent.chat("Welche Bachelor-Studiengänge gibt es?")
        
        # Sollte Studiengangs-relevante Begriffe enthalten
        study_terms = ["bachelor", "studiengang", "programm", "bwl", "vwl", "sozial"]
        
        found_terms = sum(1 for term in study_terms if term in response.lower())
        assert found_terms >= 2, \
            f"Antwort sollte studiengangsbezogen sein: {response[:200]}..."
    
    def test_rag_bewerbung_category_accuracy(self, agent):
        """Testet ob Bewerbungsfragen korrekt beantwortet werden"""
        agent.clear_memory()
        response = agent.chat("Wie bewerbe ich mich für das Wintersemester?")
        
        # Sollte Bewerbungs-relevante Begriffe enthalten
        application_terms = ["bewerbung", "frist", "semester", "bewerben", "zulassung", "antrag"]
        
        found_terms = sum(1 for term in application_terms if term in response.lower())
        assert found_terms >= 2, \
            f"Antwort sollte bewerbungsbezogen sein: {response[:200]}..."
    
    def test_rag_services_category_accuracy(self, agent):
        """Testet ob Service-Fragen korrekt beantwortet werden"""
        agent.clear_memory()
        response = agent.chat("Wo finde ich IT-Support?")
        
        # Sollte Service-relevante Begriffe enthalten
        service_terms = ["support", "service", "hilfe", "beratung", "kontakt", "it"]
        
        found_terms = sum(1 for term in service_terms if term in response.lower())
        assert found_terms >= 2, \
            f"Antwort sollte service-bezogen sein: {response[:200]}..."
    
    # ========================================================================
    # ANTWORT-INTEGRATION TESTS
    # ========================================================================
    
    def test_agent_integrates_rag_naturally(self, agent):
        """Testet ob der Agent RAG-Informationen natürlich integriert"""
        agent.clear_memory()
        response = agent.chat("Erzähl mir über die Forschung an der WiSo")
        
        # Sollte nicht nur RAG-Daten kopieren, sondern natürlich antworten
        # Kein "Hier ist die Information:" oder "Laut Datenbank:"
        unnatural_phrases = [
            "hier ist die information",
            "laut datenbank",
            "die daten zeigen",
            "aus der datenbank"
        ]
        
        has_unnatural = any(phrase in response.lower() for phrase in unnatural_phrases)
        
        if has_unnatural:
            print(f"⚠️  Warnung: Antwort klingt unnatürlich formuliert")
    
    def test_agent_combines_rag_with_reasoning(self, agent):
        """Testet ob der Agent RAG mit eigenem Reasoning kombiniert"""
        agent.clear_memory()
        response = agent.chat("Was muss ich beachten, wenn ich mich für einen Master bewerben will?")
        
        # Sollte nicht nur Fakten auflisten, sondern auch strukturieren
        # Erwarte Strukturierungshinweise wie Aufzählungen oder Schritte
        structure_indicators = ["1", "2", "erstens", "zweitens", "zunächst", "außerdem", "wichtig"]
        
        has_structure = any(indicator in response.lower() for indicator in structure_indicators)
        
        if not has_structure:
            print(f"ℹ️  Info: Antwort könnte strukturierter sein")
    
    # ========================================================================
    # FEHLERBEHANDLUNG TESTS
    # ========================================================================
    
    def test_handles_no_rag_results_gracefully(self, agent):
        """Testet wie der Agent reagiert, wenn RAG keine Ergebnisse hat"""
        agent.clear_memory()
        # Frage zu etwas, das nicht in der Datenbank ist
        response = agent.chat("Wie ist das Mensa-Essen an der WiSo?")
        
        # Sollte nicht behaupten, etwas zu wissen, wenn keine RAG-Daten da sind
        # Sollte aber trotzdem hilfreich sein
        assert len(response) > 20, \
            "Agent sollte auch ohne RAG-Treffer eine Antwort geben"
    
    def test_doesnt_confuse_categories(self, agent):
        """Testet ob der Agent Kategorien nicht verwechselt"""
        agent.clear_memory()
        response = agent.chat("Wo finde ich Informationen zur Forschung?")
        
        # Sollte nicht über Bewerbungsfristen oder Studiengänge reden
        irrelevant_terms = ["bewerbungsfrist", "bachelor", "master-bewerbung"]
        
        found_irrelevant = sum(1 for term in irrelevant_terms if term in response.lower())
        
        assert found_irrelevant == 0, \
            f"Agent sollte bei Forschungsfrage nicht über Bewerbung reden: {response}"
    
    # ========================================================================
    # PERFORMANCE TESTS
    # ========================================================================
    
    @pytest.mark.slow
    def test_rag_response_time_reasonable(self, agent):
        """Testet ob RAG-Antworten in vernünftiger Zeit kommen"""
        import time
        
        agent.clear_memory()
        start_time = time.time()
        response = agent.chat("Welche Master-Programme gibt es?")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Sollte unter 30 Sekunden sein (mit LLM kann es länger dauern)
        assert response_time < 30, \
            f"RAG-Antwort zu langsam: {response_time:.2f} Sekunden"
        
        print(f"ℹ️  Response Zeit: {response_time:.2f} Sekunden")
    
    @pytest.mark.slow
    def test_multiple_rag_queries_stable(self, agent):
        """Testet ob mehrere RAG-Queries stabil laufen"""
        agent.clear_memory()
        
        questions = [
            "Welche Studiengänge gibt es?",
            "Wie bewerbe ich mich?",
            "Wo finde ich Support?",
            "Was wird erforscht?",
            "Wie ist die Fakultät strukturiert?"
        ]
        
        for question in questions:
            response = agent.chat(question)
            assert response and len(response) > 20, \
                f"Frage '{question}' lieferte keine gute Antwort"
        
        print(f"✅ Alle {len(questions)} Fragen erfolgreich beantwortet")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
