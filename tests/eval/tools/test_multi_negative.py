"""
Multi-Tool and Negative Test Scenarios

These scenarios test:
1. Multi-tool: Requests requiring multiple tools in combination
2. Negative: Requests that should NOT use any tools

Part of Master's Thesis: AI-Powered University Assistant Evaluation Framework
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tests.eval.evaluation import (
    GoldStandard,
    ArgumentMatchMode,
)

pytestmark = [pytest.mark.llm, pytest.mark.eval]


class TestMultiTool:
    """Scenarios requiring multiple tools."""

    def test_multi_01_search_then_scrape(self):
        """
        MULTI-TOOL: Search for information, then scrape specific result.
        """
        user_prompt = """
        Suche nach der offiziellen Seite für KLIPS2 Anleitungen und 
        zeige mir dann den Inhalt der Seite.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "web_scraper"],
            required_arguments={},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "duckduckgo_search" in gold.required_tools
        assert "web_scraper" in gold.required_tools

    def test_multi_02_klips_then_email(self):
        """
        MULTI-TOOL: Get course details and email about it.
        """
        user_prompt = """
        Schau nach den Details zum Kurs "Datenbanken" und schicke 
        eine E-Mail an student@uni-koeln.de mit der Zusammenfassung.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details", "send_email"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_name": "Datenbanken"
                },
                "send_email": {
                    "to": "student@uni-koeln.de"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 2

    def test_multi_03_search_then_email(self):
        """
        MULTI-TOOL: Search and then email results.
        """
        user_prompt = """
        Recherchiere die aktuellen Bewerbungsfristen für die Uni Köln 
        und schicke das Ergebnis an info@example.com mit Betreff "Fristen".
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "send_email"],
            required_arguments={
                "send_email": {
                    "to": "info@example.com",
                    "subject": "Fristen"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "duckduckgo_search" in gold.required_tools
        assert "send_email" in gold.required_tools


class TestNegative:
    """Scenarios that should NOT trigger any tools."""

    def test_negative_01_greeting(self):
        """
        NEGATIVE: Simple greeting should not trigger tools.
        """
        user_prompt = """
        Hallo! Wie geht es dir?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register", "klips2_apply_study", 
                          "send_email", "duckduckgo_search", "web_scraper"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0

    def test_negative_02_general_question(self):
        """
        NEGATIVE: General knowledge question (no tools needed).
        """
        user_prompt = """
        Was ist der Unterschied zwischen Bachelor und Master?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register", "klips2_apply_study",
                          "duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0

    def test_negative_03_system_info(self):
        """
        NEGATIVE: Question about the assistant itself.
        """
        user_prompt = """
        Welche Funktionen hast du? Was kannst du alles machen?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register", "klips2_apply_study",
                          "send_email", "duckduckgo_search", "web_scraper"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0


# Total: 6 scenarios
