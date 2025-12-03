"""
Unit Tests für das DuckDuckGo Search Tool
==========================================
Testet die Suchfunktionalität ohne echte API-Aufrufe (mocked).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.tools.duckduckgo_tool import (
    DuckDuckGoTool,
    DuckDuckGoSearchInput,
    WebSearchResult,
    create_duckduckgo_tool
)


class TestWebSearchResult:
    """Tests für die WebSearchResult Klasse"""
    
    def test_create_result(self):
        """Test: WebSearchResult kann erstellt werden"""
        result = WebSearchResult(
            titel="Test Titel",
            snippet="Test Snippet",
            domain="example.com",
            url="https://example.com/test"
        )
        assert result.titel == "Test Titel"
        assert result.snippet == "Test Snippet"
        assert result.domain == "example.com"
        assert result.url == "https://example.com/test"
    
    def test_str_representation(self):
        """Test: String-Repräsentation enthält alle Felder"""
        result = WebSearchResult(
            titel="Test",
            snippet="Beschreibung",
            domain="test.de",
            url="https://test.de"
        )
        str_repr = str(result)
        assert "Test" in str_repr
        assert "Beschreibung" in str_repr
        assert "test.de" in str_repr


class TestDuckDuckGoSearchInput:
    """Tests für das Input-Schema"""
    
    def test_valid_input(self):
        """Test: Gültiges Input wird akzeptiert"""
        input_data = DuckDuckGoSearchInput(query="Universität Köln")
        assert input_data.query == "Universität Köln"
    
    def test_empty_query(self):
        """Test: Leere Query wird akzeptiert (Validierung im Tool)"""
        input_data = DuckDuckGoSearchInput(query="")
        assert input_data.query == ""


class TestDuckDuckGoTool:
    """Tests für das DuckDuckGo Tool"""
    
    def test_tool_name(self):
        """Test: Tool hat korrekten Namen"""
        tool = DuckDuckGoTool()
        assert tool.name == "duckduckgo_search"
    
    def test_tool_description(self):
        """Test: Tool hat eine Beschreibung"""
        tool = DuckDuckGoTool()
        assert len(tool.description) > 0
        assert "Web" in tool.description or "suchen" in tool.description.lower()
    
    def test_args_schema(self):
        """Test: Tool verwendet korrektes Args-Schema"""
        tool = DuckDuckGoTool()
        assert tool.args_schema == DuckDuckGoSearchInput
    
    @patch('src.tools.duckduckgo_tool.DDGS')
    def test_run_with_results(self, mock_ddgs_class):
        """Test: Tool verarbeitet Suchergebnisse korrekt"""
        # Mock DDGS als Context Manager
        mock_instance = MagicMock()
        mock_instance.text.return_value = [
            {
                'title': 'Uni Köln - Startseite',
                'body': 'Willkommen an der Universität zu Köln',
                'href': 'https://www.uni-koeln.de/'
            },
            {
                'title': 'Studium - Uni Köln',
                'body': 'Informationen zum Studium',
                'href': 'https://www.uni-koeln.de/studium'
            }
        ]
        mock_ddgs_class.return_value.__enter__ = Mock(return_value=mock_instance)
        mock_ddgs_class.return_value.__exit__ = Mock(return_value=False)
        
        tool = DuckDuckGoTool()
        result = tool._run("Universität Köln")
        
        assert "Uni Köln" in result or "uni-koeln" in result.lower()
    
    @patch('src.tools.duckduckgo_tool.DDGS')
    def test_run_no_results(self, mock_ddgs_class):
        """Test: Tool behandelt leere Ergebnisse"""
        mock_instance = MagicMock()
        mock_instance.text.return_value = []
        mock_ddgs_class.return_value.__enter__ = Mock(return_value=mock_instance)
        mock_ddgs_class.return_value.__exit__ = Mock(return_value=False)
        
        tool = DuckDuckGoTool()
        result = tool._run("xyznonexistent12345")
        
        assert "keine" in result.lower() or "Ergebnis" in result or result == ""
    
    @patch('src.tools.duckduckgo_tool.DDGS')
    def test_run_handles_exception(self, mock_ddgs_class):
        """Test: Tool behandelt Fehler graceful"""
        mock_ddgs_class.return_value.__enter__ = Mock(side_effect=Exception("Network error"))
        mock_ddgs_class.return_value.__exit__ = Mock(return_value=False)
        
        tool = DuckDuckGoTool()
        result = tool._run("test query")
        
        # Tool sollte Fehler abfangen und Fehlermeldung zurückgeben
        assert "Fehler" in result or "error" in result.lower() or "Error" in result


class TestCreateDuckDuckGoTool:
    """Tests für die Factory-Funktion"""
    
    def test_create_tool(self):
        """Test: Factory erstellt Tool korrekt"""
        tool = create_duckduckgo_tool()
        assert isinstance(tool, DuckDuckGoTool)
        assert tool.name == "duckduckgo_search"
