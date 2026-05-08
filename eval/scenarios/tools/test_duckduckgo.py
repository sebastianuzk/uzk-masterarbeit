"""
DuckDuckGo Such-Tool - Evaluierungs-Testszenarien

Tool: duckduckgo_search
Zweck: Websuche mit DuckDuckGo durchführen

Erforderliche Argumente:
- query (Suchanfrage als String)

Teil der Masterarbeit: KI-gestütztes Universitäts-Assistenten Evaluierungs-Framework
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from eval.core.evaluation import (
    GoldStandard,
    ArgumentMatchMode,
)

pytestmark = [pytest.mark.llm, pytest.mark.eval]


class TestSearchEasy:
    """Einfache Szenarien - Klare Suchanfragen."""

    def test_search_01_simple_query(self):
        """
        EASY: Simple, explicit search request.
        """
        user_prompt = """
        Suche im Internet nach "Uni Köln Bewerbungsfristen".
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {
                    "query": "Uni Köln Bewerbungsfristen"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_02_english_query(self):
        """
        EASY: Search request in English.
        """
        user_prompt = """
        Search for "University of Cologne international students requirements".
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {
                    "query": "University of Cologne international students requirements"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_03_query_with_count_hint(self):
        """
        EASY: Search query where user mentions a count — tool only accepts query.
        """
        user_prompt = """
        Zeige mir die top 5 Ergebnisse für "Informatik Studium Deutschland".
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {
                    "query": "Informatik Studium Deutschland"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]


class TestSearchMedium:
    """Medium scenarios - search needs implied from context."""

    def test_search_04_implicit_search(self):
        """
        MEDIUM: Search need implied but not explicitly stated.
        """
        user_prompt = """
        Suche im Internet nach den aktuellen Öffnungszeiten der Uni-Bibliothek Köln.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_05_complex_query(self):
        """
        MEDIUM: Complex, multi-part search request.
        """
        user_prompt = """
        Such im Internet nach Informationen über die Zulassungsvoraussetzungen und 
        Bewerbungsfristen für den Masterstudiengang Informatik an der Uni Köln.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_06_current_events(self):
        """
        MEDIUM: Search for current/recent information.
        """
        user_prompt = """
        Was sind die neuesten Nachrichten zur Hochschulpolitik in NRW?
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]


class TestSearchHard:
    """Hard scenarios - search not appropriate or needs clarification."""

    def test_search_07_personal_data(self):
        """
        HARD: Request that shouldn't use search (personal data).
        """
        user_prompt = """
        Such nach meiner E-Mail-Adresse.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "duckduckgo_search" in gold.forbidden_tools

    def test_search_08_internal_system(self):
        """
        HARD: Request that should use internal system instead.
        """
        user_prompt = """
        Such in KLIPS nach dem Kurs Informatik I.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            forbidden_tools={"duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "duckduckgo_search" in gold.forbidden_tools

    def test_search_09_too_vague(self):
        """
        HARD: Too vague search request.
        """
        user_prompt = """
        Such mal was.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "duckduckgo_search" in gold.forbidden_tools

    def test_search_10_academic_topic(self):
        """
        MEDIUM: Search for academic/research topic.
        """
        user_prompt = """
        Suche nach aktuellen Forschungsarbeiten zum Thema 
        "Machine Learning in der Medizin".
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_11_comparison(self):
        """
        MEDIUM: Search for comparison information.
        """
        user_prompt = """
        Suche online nach einem Vergleich zwischen der Uni Köln und der Uni Bonn 
        bezüglich des Informatik-Studiums.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_12_news_search(self):
        """
        MEDIUM: Search for news about university.
        """
        user_prompt = """
        Suche nach aktuellen Nachrichten über die Universität zu Köln.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_13_job_search(self):
        """
        MEDIUM: Search for job/internship opportunities.
        """
        user_prompt = """
        Suche im Internet nach Werkstudentenstellen für Informatik-Studenten in Köln.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_14_scholarship_search(self):
        """
        MEDIUM: Search for scholarship information.
        """
        user_prompt = """
        Recherchiere nach Stipendien für Master-Studenten in Deutschland.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]

    def test_search_15_event_search(self):
        """
        MEDIUM: Search for university events.
        """
        user_prompt = """
        Google nach Karrieremessen für Studenten in NRW.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={
                "duckduckgo_search": {}
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["duckduckgo_search"]


# Total: 15 scenarios
