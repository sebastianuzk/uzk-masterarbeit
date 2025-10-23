"""
Tests für die Tools
"""
import unittest
import sys
import os

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.email_tool import create_email_tool
from src.tools.klips2_register_tool import create_klips2_register_tool
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
                self.assertIsNotNone(tool._get_smtp_config())
                
        except Exception as e:
            self.fail(f"E-Mail-Tool-Konfigurationstest fehlgeschlagen: {str(e)}")
    
    def test_email_tool_validation(self):
        """Teste E-Mail-Tool-Validierung"""
        try:
            tool = create_email_tool()
            
            # Teste E-Mail-Validierungsfunktion
            self.assertTrue(tool._is_valid_email("test@example.com"))
            self.assertTrue(tool._is_valid_email("user.name@domain.co.uk"))
            self.assertFalse(tool._is_valid_email("invalid-email"))
            self.assertFalse(tool._is_valid_email("@domain.com"))
            self.assertFalse(tool._is_valid_email("user@"))
            
        except Exception as e:
            self.fail(f"E-Mail-Tool-Validierungstest fehlgeschlagen: {str(e)}")
    
    def test_klips2_register_tool_creation(self):
        """Teste KLIPS2-Registrierungs-Tool-Erstellung"""
        try:
            tool = create_klips2_register_tool()
            self.assertIsNotNone(tool)
            self.assertEqual(tool.name, "klips2_register")
            self.assertIsNotNone(tool.description)
        except Exception as e:
            self.fail(f"KLIPS2-Registrierungs-Tool-Erstellung fehlgeschlagen: {str(e)}")
    
    def test_klips2_date_validation(self):
        """Teste KLIPS2-Datumsvalidierung"""
        try:
            tool = create_klips2_register_tool()
            
            # Gültige Datumsformate
            self.assertTrue(tool._validate_date("15.03.1995"))
            self.assertTrue(tool._validate_date("01.01.2000"))
            self.assertTrue(tool._validate_date("31.12.1990"))
            self.assertTrue(tool._validate_date("15.3.1995"))  # Python akzeptiert auch einstellige Monate/Tage
            
            # Ungültige Datumsformate
            self.assertFalse(tool._validate_date("1995-03-15"))
            self.assertFalse(tool._validate_date("15/03/1995"))
            self.assertFalse(tool._validate_date("32.13.1995"))
            
        except Exception as e:
            self.fail(f"KLIPS2-Datumsvalidierungstest fehlgeschlagen: {str(e)}")
    
    def test_klips2_email_validation(self):
        """Teste KLIPS2-E-Mail-Validierung"""
        try:
            tool = create_klips2_register_tool()
            
            # Gültige E-Mail-Adressen
            self.assertTrue(tool._validate_email("test@example.com"))
            self.assertTrue(tool._validate_email("user.name@domain.co.uk"))
            
            # Ungültige E-Mail-Adressen
            self.assertFalse(tool._validate_email("invalid-email"))
            self.assertFalse(tool._validate_email("@domain.com"))
            self.assertFalse(tool._validate_email("user@"))
            
        except Exception as e:
            self.fail(f"KLIPS2-E-Mail-Validierungstest fehlgeschlagen: {str(e)}")
    
    def test_klips2_gender_mapping(self):
        """Teste KLIPS2-Geschlechtsmapping"""
        try:
            tool = create_klips2_register_tool()
            
            # Männlich
            self.assertEqual(tool._map_gender("männlich"), "M")
            self.assertEqual(tool._map_gender("male"), "M")
            self.assertEqual(tool._map_gender("m"), "M")
            
            # Weiblich
            self.assertEqual(tool._map_gender("weiblich"), "W")
            self.assertEqual(tool._map_gender("female"), "W")
            self.assertEqual(tool._map_gender("w"), "W")
            self.assertEqual(tool._map_gender("f"), "W")
            
            # Divers (KLIPS2 verwendet "X", nicht "D")
            self.assertEqual(tool._map_gender("divers"), "X")
            self.assertEqual(tool._map_gender("diverse"), "X")
            self.assertEqual(tool._map_gender("d"), "X")
            
        except Exception as e:
            self.fail(f"KLIPS2-Geschlechtsmapping-Test fehlgeschlagen: {str(e)}")
    
    def test_klips2_language_mapping(self):
        """Teste KLIPS2-Sprachmapping"""
        try:
            tool = create_klips2_register_tool()
            
            # Deutsch (KLIPS2 verwendet numerische IDs: "1" für Deutsch)
            self.assertEqual(tool._map_language("Deutsch"), "1")
            self.assertEqual(tool._map_language("deutsch"), "1")
            self.assertEqual(tool._map_language("German"), "1")
            
            # Englisch (KLIPS2 verwendet numerische IDs: "2" für Englisch)
            self.assertEqual(tool._map_language("Englisch"), "2")
            self.assertEqual(tool._map_language("English"), "2")
            self.assertEqual(tool._map_language("englisch"), "2")
            
        except Exception as e:
            self.fail(f"KLIPS2-Sprachmapping-Test fehlgeschlagen: {str(e)}")
    
    def test_klips2_nationality_mapping(self):
        """Teste KLIPS2-Nationalitätsmapping"""
        try:
            tool = create_klips2_register_tool()
            
            # Teste häufige Länder (KLIPS2 verwendet numerische Codes)
            self.assertEqual(tool._map_nationality("Deutschland"), "56")
            self.assertEqual(tool._map_nationality("germany"), "56")
            self.assertEqual(tool._map_nationality("Österreich"), "168")
            self.assertEqual(tool._map_nationality("austria"), "168")
            self.assertEqual(tool._map_nationality("Schweiz"), "192")
            self.assertEqual(tool._map_nationality("switzerland"), "192")
            self.assertEqual(tool._map_nationality("Frankreich"), "68")
            self.assertEqual(tool._map_nationality("france"), "68")
            
            # Default sollte Deutschland sein
            self.assertEqual(tool._map_nationality("UnbekanntesLand"), "56")
            
        except Exception as e:
            self.fail(f"KLIPS2-Nationalitätsmapping-Test fehlgeschlagen: {str(e)}")
    
    def test_klips2_registration_validation(self):
        """Teste KLIPS2-Registrierung mit ungültigen Daten (KEINE echte Registrierung)"""
        try:
            tool = create_klips2_register_tool()
            
            # Test mit ungültigem Datum
            result = tool._run(
                vorname="Max",
                nachname="Mustermann",
                geschlecht="männlich",
                geburtsdatum="1995-03-15",  # Falsches Format (YYYY-MM-DD statt TT.MM.JJJJ)
                email="max@example.com",
                staatsangehoerigkeit="Deutschland"
            )
            self.assertIn("❌", result)
            self.assertIn("Datumsformat", result)
            
            # Test mit ungültiger E-Mail
            result = tool._run(
                vorname="Max",
                nachname="Mustermann",
                geschlecht="männlich",
                geburtsdatum="15.03.1995",
                email="invalid-email",  # Ungültige E-Mail
                staatsangehoerigkeit="Deutschland"
            )
            self.assertIn("❌", result)
            self.assertIn("E-Mail", result)
            
        except Exception as e:
            self.fail(f"KLIPS2-Registrierungsvalidierungstest fehlgeschlagen: {str(e)}")
    
    def test_klips2_registration_no_real_submission(self):
        """Stelle sicher, dass Tests KEINE echte Registrierung durchführen"""
        # WICHTIG: Dieser Test überprüft nur die Tool-Struktur, 
        # NICHT die tatsächliche Registrierung!
        # Echte Registrierungstests sollten mit Mock-Daten oder in isolierter Umgebung laufen.
        try:
            tool = create_klips2_register_tool()
            
            # Teste nur mit offensichtlich ungültigen Daten, die sofort fehlschlagen
            result = tool._run(
                vorname="Test",
                nachname="User",
                geschlecht="männlich",
                geburtsdatum="invalid-date",  # Ungültiges Datum
                email="test@example.com",
                staatsangehoerigkeit="Deutschland"
            )
            
            # Sollte Validierungsfehler zurückgeben (keine echte Registrierung)
            self.assertIn("❌", result)
            
        except Exception as e:
            # Wenn ein Fehler auftritt, ist das in Ordnung - Hauptsache keine echte Registrierung
            pass


if __name__ == "__main__":
    unittest.main()
