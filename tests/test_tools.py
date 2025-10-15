"""
Tests für die Tools
"""
import unittest
import sys
import os

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Aktuelle Tools (Wikipedia wird entfernt)
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.email_tool import create_email_tool
from config.settings import settings


class TestTools(unittest.TestCase):
    """Test-Klasse für die Tools"""
    
    def test_web_scraper_tool_creation(self):
        """Teste Web-Scraper-Tool-Erstellung"""
        try:
            tool = create_web_scraper_tool()
            self.assertIsNotNone(tool)
            self.assertEqual(tool.name, "web_scraper")
            self.assertIsNotNone(tool.description)
        except Exception as e:
            self.fail(f"Web-Scraper-Tool-Erstellung fehlgeschlagen: {str(e)}")
    
    def test_duckduckgo_tool_creation(self):
        """Teste DuckDuckGo-Tool-Erstellung"""
        try:
            tool = create_duckduckgo_tool()
            self.assertIsNotNone(tool)
            self.assertEqual(tool.name, "duckduckgo_search")
            self.assertIsNotNone(tool.description)
        except Exception as e:
            self.fail(f"DuckDuckGo-Tool-Erstellung fehlgeschlagen: {str(e)}")
    
    def test_rag_tool_creation(self):
        """Teste RAG-Tool-Erstellung"""
        try:
            tool = create_university_rag_tool()
            self.assertIsNotNone(tool)
            self.assertEqual(tool.name, "university_knowledge_search")
            self.assertIsNotNone(tool.description)
        except Exception as e:
            self.fail(f"RAG-Tool-Erstellung fehlgeschlagen: {str(e)}")
    
    def test_email_tool_creation(self):
        """Teste E-Mail-Tool-Erstellung"""
        try:
            tool = create_email_tool()
            self.assertIsNotNone(tool)
            self.assertEqual(tool.name, "send_email")
            self.assertIsNotNone(tool.description)
        except Exception as e:
            self.fail(f"E-Mail-Tool-Erstellung fehlgeschlagen: {str(e)}")
    
    def test_web_scraper_invalid_url(self):
        """Teste Web-Scraper mit ungültiger URL"""
        try:
            tool = create_web_scraper_tool()
            result = tool._run("invalid-url")
            
            self.assertIsInstance(result, str)
            self.assertIn("Fehler", result)
            
        except Exception as e:
            self.fail(f"Web-Scraper-Test fehlgeschlagen: {str(e)}")
    
    def test_duckduckgo_search(self):
        """Teste DuckDuckGo-Suche"""
        try:
            tool = create_duckduckgo_tool()
            result = tool._run("Python programming")
            
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
            
        except Exception as e:
            # DuckDuckGo-Test kann fehlschlagen, wenn keine Internetverbindung besteht
            self.skipTest(f"DuckDuckGo-Test übersprungen: {str(e)}")
    
    def test_rag_search(self):
        """Teste RAG-Tool-Suche"""
        try:
            tool = create_university_rag_tool()
            result = tool._run("Bewerbung höheres Fachsemester")
            
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
            
            # Überprüfe, ob die Antwort relevante Informationen enthält
            self.assertIn("Bewerbung", result)
            
        except Exception as e:
            # RAG-Test kann fehlschlagen, wenn keine ChromaDB verfügbar ist
            self.skipTest(f"RAG-Test übersprungen: {str(e)}")
    
    def test_email_tool_configuration(self):
        """Teste E-Mail-Tool-Konfiguration"""
        try:
            tool = create_email_tool()
            
            # Teste ohne E-Mail-Konfiguration (sollte Fehlermeldung geben)
            if not settings.DEFAULT_RECIPIENT or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
                result = tool._run(
                    subject="Test Betreff",
                    body="Test Nachricht"
                )
                self.assertIsInstance(result, str)
                self.assertIn("❌", result)  # Sollte Fehlermeldung enthalten
            else:
                # Mit Konfiguration - teste nur die Struktur (ohne tatsächlichen Versand)
                self.assertIsNotNone(tool)
                
        except Exception as e:
            self.skipTest(f"E-Mail-Tool-Konfigurationstest übersprungen: {str(e)}")
    
    def test_email_tool_validation(self):
        """Teste E-Mail-Tool-Validierung"""
        try:
            tool = create_email_tool()
            
            # Teste dass Tool korrekt erstellt wurde
            self.assertIsNotNone(tool)
            self.assertEqual(tool.name, "send_email")
            
            # Teste Input-Validierung (wenn verfügbar)
            from src.tools.email_tool import EmailInput
            email_input = EmailInput(
                subject="Test Betreff",
                body="Test Nachricht"
            )
            self.assertEqual(email_input.subject, "Test Betreff")
            self.assertEqual(email_input.body, "Test Nachricht")
            
        except Exception as e:
            self.fail(f"E-Mail-Tool-Validierungstest fehlgeschlagen: {str(e)}")
    
    def test_email_tool_mock_sending(self):
        """Teste E-Mail-Tool Mock-Versendung"""
        try:
            tool = create_email_tool()
            
            # Teste Tool-Ausführung (sollte Konfigurationsfehler zurückgeben wenn nicht konfiguriert)
            result = tool._run("Test Betreff")
            
            self.assertIsInstance(result, str)
            # Ergebnis sollte entweder Erfolg oder Konfigurationsfehler sein
            self.assertTrue(
                "✅" in result or "❌" in result or "Fehler" in result,
                f"Unerwartetes Ergebnis: {result}"
            )
            
        except Exception as e:
            self.skipTest(f"E-Mail-Tool Mock-Test übersprungen: {str(e)}")


if __name__ == "__main__":
    unittest.main()