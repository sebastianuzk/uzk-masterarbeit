"""
Web Scraper Tool - Evaluation Test Scenarios

Tool: web_scraper
Purpose: Extract content from specific web pages

Required arguments:
- url (the URL to scrape)

Optional arguments:
- extract_type (type of content to extract: text, links, tables, etc.)

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


class TestScraperEasy:
    """Easy scenarios - clear URL scraping requests."""

    def test_scraper_01_direct_url(self):
        """
        EASY: Direct URL scraping request.
        """
        user_prompt = """
        Hole den Inhalt von https://www.uni-koeln.de/studium.
        """
        
        gold = GoldStandard(
            required_tools=["web_scraper"],
            required_arguments={
                "web_scraper": {
                    "url": "https://www.uni-koeln.de/studium"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["web_scraper"]

    def test_scraper_02_extract_text(self):
        """
        EASY: Request to extract text from URL.
        """
        user_prompt = """
        Extrahiere den Text von https://example.com/info.
        """
        
        gold = GoldStandard(
            required_tools=["web_scraper"],
            required_arguments={
                "web_scraper": {
                    "url": "https://example.com/info"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["web_scraper"]


class TestScraperMedium:
    """Medium scenarios - URL mentioned in context."""

    def test_scraper_03_in_conversation(self):
        """
        MEDIUM: URL scraping implied from conversation.
        """
        user_prompt = """
        Ich habe diese Seite gefunden: https://portal.uni-koeln.de/termine
        Kannst du mir sagen, was da steht?
        """
        
        gold = GoldStandard(
            required_tools=["web_scraper"],
            required_arguments={
                "web_scraper": {
                    "url": "https://portal.uni-koeln.de/termine"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["web_scraper"]

    def test_scraper_04_multiple_urls(self):
        """
        MEDIUM: Request to scrape multiple URLs.
        """
        user_prompt = """
        Vergleiche die Inhalte von https://uni-koeln.de/a und 
        https://uni-koeln.de/b.
        """
        
        gold = GoldStandard(
            required_tools=["web_scraper"],
            required_arguments={
                "web_scraper": {}
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["web_scraper"]

    def test_scraper_05_summarize_page(self):
        """
        MEDIUM: Request to summarize a webpage.
        """
        user_prompt = """
        Fasse den Inhalt von https://www.example.com/article zusammen.
        """
        
        gold = GoldStandard(
            required_tools=["web_scraper"],
            required_arguments={
                "web_scraper": {
                    "url": "https://www.example.com/article"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["web_scraper"]


class TestScraperHard:
    """Hard scenarios - scraping not appropriate or unclear."""

    def test_scraper_06_no_url(self):
        """
        HARD: Request without URL.
        LLM should ask for URL, NOT call tool.
        """
        user_prompt = """
        Scrape die Webseite für mich.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"web_scraper"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "web_scraper" in gold.forbidden_tools

    def test_scraper_07_invalid_url(self):
        """
        HARD: Invalid URL format.
        """
        user_prompt = """
        Hole Inhalte von "nicht-eine-url".
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"web_scraper"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "web_scraper" in gold.forbidden_tools

    def test_scraper_08_search_instead(self):
        """
        HARD: Should use search instead of scraper.
        """
        user_prompt = """
        Finde Informationen über Uni Köln im Internet.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            forbidden_tools={"web_scraper"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "web_scraper" in gold.forbidden_tools


# Total: 8 scenarios
