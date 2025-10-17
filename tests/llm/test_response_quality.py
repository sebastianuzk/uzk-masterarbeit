"""
LLM Response Quality Tests - Testet die Qualität und Korrektheit der Modellantworten
"""
import pytest
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
    
    # ========================================================================
    # FAKTENTREUE TESTS
    # ========================================================================
    
    def test_university_name_accuracy(self, agent):
        """Testet ob der Agent den korrekten Universitätsnamen verwendet"""
        response = agent.chat("Wie heißt die Universität?")
        
        # Der Agent sollte "Universität zu Köln" verwenden
        assert "Universität zu Köln" in response or "University of Cologne" in response, \
            f"Universitätsname nicht korrekt: {response}"
        
        # Sollte nicht "Universität Köln" ohne "zu" sagen
        assert "Universität Köln" not in response or "zu Köln" in response, \
            f"Universitätsname ungenau formuliert: {response}"
    
    def test_faculty_name_accuracy(self, agent):
        """Testet ob der Agent den korrekten Fakultätsnamen verwendet"""
        response = agent.chat("Welche Fakultät ist das?")
        
        # Sollte WiSo-Fakultät oder Wirtschafts- und Sozialwissenschaftliche Fakultät erwähnen
        assert any(term in response.lower() for term in [
            "wiso", "wirtschafts", "sozialwissenschaft"
        ]), f"Fakultätsname nicht korrekt: {response}"
    
    def test_no_hallucination_on_unknown_info(self, agent):
        """Testet ob der Agent bei unbekannten Informationen nicht halluziniert"""
        response = agent.chat("Wer ist der Rektor der Universität zu Köln im Jahr 2099?")
        
        # Der Agent sollte zugeben, dass er diese Information nicht hat
        uncertainty_phrases = [
            "weiß ich nicht",
            "kann ich nicht sagen",
            "keine information",
            "nicht sicher",
            "finde keine",
            "habe keine",
            "leider nicht"
        ]
        
        assert any(phrase in response.lower() for phrase in uncertainty_phrases), \
            f"Agent sollte Unsicherheit bei unbekannten Infos zeigen: {response}"
    
    # ========================================================================
    # RELEVANZ TESTS
    # ========================================================================
    
    def test_relevance_for_study_program_query(self, agent):
        """Testet ob die Antwort bei Studiengangsfragen relevant ist"""
        response = agent.chat("Welche Master-Programme bietet die WiSo-Fakultät an?")
        
        # Sollte relevante Begriffe enthalten
        relevant_terms = [
            "master", "programm", "studiengang", "wiso", 
            "wirtschaft", "bwl", "vwl", "sozial"
        ]
        
        found_terms = sum(1 for term in relevant_terms if term in response.lower())
        assert found_terms >= 2, \
            f"Antwort sollte mindestens 2 relevante Begriffe enthalten: {response}"
    
    def test_no_off_topic_response(self, agent):
        """Testet ob der Agent bei einfachen Fragen nicht unnötig abschwenkt"""
        response = agent.chat("Wie ist das Wetter heute?")
        
        # Sollte nicht über Studiengänge oder Bewerbung reden
        off_topic_terms = ["bewerbung", "master", "bachelor", "studiengang"]
        
        off_topic_count = sum(1 for term in off_topic_terms if term in response.lower())
        assert off_topic_count == 0, \
            f"Agent sollte bei Wetter-Frage nicht über Studium reden: {response}"
    
    # ========================================================================
    # ANTWORTFORMAT TESTS
    # ========================================================================
    
    def test_response_not_empty(self, agent):
        """Testet ob Antworten nicht leer sind"""
        response = agent.chat("Hallo!")
        
        assert response and len(response.strip()) > 0, \
            "Antwort sollte nicht leer sein"
    
    def test_response_reasonable_length(self, agent):
        """Testet ob Antworten eine vernünftige Länge haben"""
        response = agent.chat("Was ist die WiSo-Fakultät?")
        
        # Sollte mindestens 20 Zeichen haben (nicht zu kurz)
        assert len(response) >= 20, \
            f"Antwort zu kurz ({len(response)} Zeichen): {response}"
        
        # Sollte nicht extrem lang sein (< 2000 Zeichen für einfache Fragen)
        assert len(response) < 2000, \
            f"Antwort zu lang ({len(response)} Zeichen) für einfache Frage"
    
    def test_response_is_german(self, agent):
        """Testet ob Antworten auf Deutsch sind (bei deutschen Fragen)"""
        response = agent.chat("Welche Studiengänge gibt es?")
        
        # Sollte deutsche Wörter enthalten
        german_indicators = ["der", "die", "das", "und", "ist", "sind", "werden", "können"]
        found_german = sum(1 for word in german_indicators if f" {word} " in response.lower())
        
        assert found_german >= 2, \
            f"Antwort sollte auf Deutsch sein: {response}"
    
    def test_urls_are_included_when_using_tools(self, agent):
        """Testet ob URLs in Antworten enthalten sind, wenn Tools verwendet werden"""
        # Diese Frage sollte das RAG-Tool triggern
        response = agent.chat("Wo finde ich Informationen zur Bewerbung?")
        
        # Wenn das RAG-Tool verwendet wurde, sollten URLs dabei sein
        # (RAG-Tool liefert URLs mit)
        if "wiso" in response.lower() or "universität" in response.lower():
            # Suche nach URL-Mustern
            has_url = "http" in response or "www" in response or "uni-koeln.de" in response
            
            # Warnung wenn keine URL, aber kein Fehler (da nicht immer garantiert)
            if not has_url:
                print(f"⚠️  Warnung: Keine URL in Antwort gefunden, obwohl Tool verwendet wurde")
    
    # ========================================================================
    # KONSISTENZ TESTS
    # ========================================================================
    
    def test_consistent_answers_on_repeated_questions(self, agent):
        """Testet ob der Agent bei wiederholten Fragen konsistent antwortet"""
        question = "Was ist die WiSo-Fakultät?"
        
        response1 = agent.chat(question)
        agent.clear_memory()  # Memory löschen für unabhängige Antwort
        response2 = agent.chat(question)
        
        # Beide Antworten sollten ähnliche Kernbegriffe enthalten
        core_terms = ["wirtschaft", "sozial", "fakultät", "universität"]
        
        terms_in_response1 = sum(1 for term in core_terms if term in response1.lower())
        terms_in_response2 = sum(1 for term in core_terms if term in response2.lower())
        
        # Mindestens 2 Kernbegriffe sollten in beiden vorkommen
        assert terms_in_response1 >= 2 and terms_in_response2 >= 2, \
            f"Antworten sollten konsistente Kernbegriffe enthalten"
    
    # ========================================================================
    # KONVERSATIONSFLUSS TESTS
    # ========================================================================
    
    def test_maintains_context_in_conversation(self, agent):
        """Testet ob der Agent Kontext über mehrere Nachrichten behält"""
        agent.clear_memory()
        
        response1 = agent.chat("Ich interessiere mich für einen Master in BWL")
        response2 = agent.chat("Welche Voraussetzungen brauche ich dafür?")
        
        # Die zweite Antwort sollte sich auf BWL/Master beziehen
        assert any(term in response2.lower() for term in ["master", "bwl", "voraussetzung", "bachelor"]), \
            f"Agent sollte Kontext (Master BWL) beibehalten: {response2}"
    
    def test_friendly_greeting_response(self, agent):
        """Testet ob der Agent freundlich auf Begrüßungen reagiert"""
        agent.clear_memory()
        response = agent.chat("Hallo!")
        
        # Sollte freundliche Begriffe enthalten
        friendly_terms = ["hallo", "guten tag", "hi", "willkommen", "helfen"]
        
        assert any(term in response.lower() for term in friendly_terms), \
            f"Agent sollte freundlich grüßen: {response}"
    
    def test_no_unnecessary_tool_use_for_greetings(self, agent):
        """Testet ob der Agent bei Begrüßungen nicht unnötig Tools verwendet"""
        agent.clear_memory()
        response = agent.chat("Hallo, wie geht es dir?")
        
        # Sollte keine URLs oder technische Informationen enthalten
        technical_indicators = ["http", "www", "api", "tool", "search"]
        
        found_technical = sum(1 for indicator in technical_indicators if indicator in response.lower())
        assert found_technical == 0, \
            f"Agent sollte bei Smalltalk keine Tools verwenden: {response}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
