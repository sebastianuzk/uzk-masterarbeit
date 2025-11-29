"""
Unit Tests für das Web Scraper Tool
===================================
Testet die Web-Scraping-Funktionalität mit gemockten HTTP-Requests.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.tools.web_scraper_tool import (
    WebScraperTool,
    WebScraperInput,
    create_web_scraper_tool
)


class TestWebScraperInput:
    """Tests für das Input-Schema"""
    
    def test_valid_input(self):
        """Test: Gültige URL wird akzeptiert"""
        input_data = WebScraperInput(url="https://example.com")
        assert input_data.url == "https://example.com"
    
    def test_url_with_path(self):
        """Test: URL mit Pfad wird akzeptiert"""
        input_data = WebScraperInput(url="https://example.com/path/to/page")
        assert "path/to/page" in input_data.url


class TestWebScraperTool:
    """Tests für das Web Scraper Tool"""
    
    def test_tool_name(self):
        """Test: Tool hat korrekten Namen"""
        tool = WebScraperTool()
        assert tool.name == "web_scraper"
    
    def test_tool_description(self):
        """Test: Tool hat eine Beschreibung"""
        tool = WebScraperTool()
        assert len(tool.description) > 0
        assert "Web" in tool.description or "URL" in tool.description
    
    def test_args_schema(self):
        """Test: Tool verwendet korrektes Args-Schema"""
        tool = WebScraperTool()
        assert tool.args_schema == WebScraperInput
    
    @patch('src.tools.web_scraper_tool.requests.get')
    def test_run_extracts_text(self, mock_get):
        """Test: Tool extrahiert Text aus HTML"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Willkommen</h1>
                <p>Dies ist ein Test-Absatz.</p>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        tool = WebScraperTool()
        result = tool._run("https://example.com")
        
        assert "Willkommen" in result
        assert "Test-Absatz" in result
    
    @patch('src.tools.web_scraper_tool.requests.get')
    def test_run_removes_scripts(self, mock_get):
        """Test: Tool entfernt Script-Tags"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <p>Sichtbarer Text</p>
                <script>console.log('hidden');</script>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        tool = WebScraperTool()
        result = tool._run("https://example.com")
        
        assert "Sichtbarer Text" in result
        assert "console.log" not in result
    
    @patch('src.tools.web_scraper_tool.requests.get')
    def test_run_removes_styles(self, mock_get):
        """Test: Tool entfernt Style-Tags"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"""
        <html>
            <body>
                <style>.hidden { display: none; }</style>
                <p>Sichtbarer Inhalt</p>
            </body>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        tool = WebScraperTool()
        result = tool._run("https://example.com")
        
        assert "Sichtbarer Inhalt" in result
        assert "display: none" not in result
    
    @patch('src.tools.web_scraper_tool.requests.get')
    def test_run_truncates_long_content(self, mock_get):
        """Test: Tool kürzt sehr langen Content"""
        mock_response = Mock()
        mock_response.status_code = 200
        # Erstelle sehr langen Content
        long_text = "A" * 5000
        mock_response.content = f"<html><body><p>{long_text}</p></body></html>".encode()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        tool = WebScraperTool()
        result = tool._run("https://example.com")
        
        # Ergebnis sollte kürzer als der Originaltext sein
        assert len(result) < 5000
    
    @patch('src.tools.web_scraper_tool.requests.get')
    def test_run_handles_timeout(self, mock_get):
        """Test: Tool behandelt Timeout"""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        tool = WebScraperTool()
        result = tool._run("https://slow-website.com")
        
        assert "Fehler" in result or "Error" in result or "timeout" in result.lower()
    
    @patch('src.tools.web_scraper_tool.requests.get')
    def test_run_handles_404(self, mock_get):
        """Test: Tool behandelt 404-Fehler"""
        import requests
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        tool = WebScraperTool()
        result = tool._run("https://example.com/nonexistent")
        
        assert "Fehler" in result or "Error" in result or "404" in result
    
    @patch('src.tools.web_scraper_tool.requests.get')
    def test_run_handles_connection_error(self, mock_get):
        """Test: Tool behandelt Verbindungsfehler"""
        import requests
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        tool = WebScraperTool()
        result = tool._run("https://nonexistent-domain.invalid")
        
        assert "Fehler" in result or "Error" in result


class TestCreateWebScraperTool:
    """Tests für die Factory-Funktion"""
    
    def test_create_tool(self):
        """Test: Factory erstellt Tool korrekt"""
        tool = create_web_scraper_tool()
        assert isinstance(tool, WebScraperTool)
        assert tool.name == "web_scraper"
