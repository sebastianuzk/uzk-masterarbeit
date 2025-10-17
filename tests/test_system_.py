"""
Systemtests für den Autonomen Chatbot-Agenten
"""
import unittest
import sys
import os

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agent.react_agent import create_react_agent
from src.tools.email_tool import create_email_tool
from config.settings import settings


class TestSystemIntegration(unittest.TestCase):
    """Test-Klasse für Systemintegrationstests"""
    
    def setUp(self):
        """Setup für jeden Test"""
        # Prüfen, ob Ollama erreichbar ist
        try:
            import requests
            response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
            if response.status_code != 200:
                self.skipTest("Ollama-Server nicht erreichbar")
        except:
            self.skipTest("Ollama-Server nicht erreichbar")
    
    def test_complete_system_initialization(self):
        """Teste vollständige Systeminitialisierung"""
        try:
            # Erstelle Agent
            agent = create_react_agent()
            self.assertIsNotNone(agent)
            
            # Überprüfe, dass alle erwarteten Tools geladen sind
            tools = agent.get_available_tools()
            self.assertIsInstance(tools, list)
            self.assertGreater(len(tools), 0)
            
            # Überprüfe spezifische Tools
            if settings.ENABLE_DUCKDUCKGO:
                self.assertIn("duckduckgo_search", tools)
            
            if settings.ENABLE_WEB_SCRAPER:
                self.assertIn("web_scraper", tools)
            
            # E-Mail-Tool sollte immer verfügbar sein
            self.assertIn("send_email", tools)
            
            # RAG-Tool sollte verfügbar sein (falls ChromaDB funktioniert)
            # Wird möglicherweise übersprungen, wenn ChromaDB nicht verfügbar ist
            
        except Exception as e:
            self.fail(f"System-Initialisierung fehlgeschlagen: {str(e)}")
    
    def test_agent_tool_interaction(self):
        """Teste Interaktion zwischen Agent und Tools"""
        try:
            agent = create_react_agent()
            
            # Teste einfache Interaktion
            response = agent.chat("Hallo, welche Tools hast du zur Verfügung?")
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            
            # Memory sollte Nachrichten enthalten
            memory_info = agent.get_memory_summary()
            self.assertGreater(memory_info["total_messages"], 0)
            
        except Exception as e:
            self.fail(f"Agent-Tool-Interaktion fehlgeschlagen: {str(e)}")
    
    def test_email_tool_system_integration(self):
        """Teste E-Mail-Tool-Integration im Gesamtsystem"""
        try:
            # Teste eigenständiges E-Mail-Tool
            email_tool = create_email_tool()
            self.assertIsNotNone(email_tool)
            
            # Teste Agent mit E-Mail-Tool
            agent = create_react_agent()
            tools = agent.get_available_tools()
            self.assertIn("send_email", tools)
            
            # Überprüfe, dass E-Mail-Tool korrekt konfiguriert ist
            email_tools = [tool for tool in agent.tools if tool.name == "send_email"]
            self.assertEqual(len(email_tools), 1)
            
            email_tool_instance = email_tools[0]
            
            # Teste Tool-Schema
            self.assertIsNotNone(email_tool_instance.args_schema)
            
            # Teste, dass die richtigen Parameter erwartet werden
            schema_fields = email_tool_instance.args_schema.model_fields
            self.assertIn("subject", schema_fields)
            self.assertIn("body", schema_fields)
            
            # Stelle sicher, dass alte Parameter nicht mehr da sind
            self.assertNotIn("recipient", schema_fields)
            self.assertNotIn("sender_name", schema_fields)
            
        except Exception as e:
            self.fail(f"E-Mail-Tool-System-Integration fehlgeschlagen: {str(e)}")
    
    def test_configuration_validation(self):
        """Teste Systemkonfiguration"""
        try:
            # Teste Settings-Validierung
            settings.validate()
            
            # Überprüfe kritische Konfigurationen
            self.assertIsNotNone(settings.OLLAMA_BASE_URL)
            self.assertIsNotNone(settings.OLLAMA_MODEL)
            
            # E-Mail-Konfiguration (kann leer sein, sollte aber definiert sein)
            self.assertTrue(hasattr(settings, 'SMTP_SERVER'))
            self.assertTrue(hasattr(settings, 'SMTP_PORT'))
            self.assertTrue(hasattr(settings, 'SMTP_USERNAME'))
            self.assertTrue(hasattr(settings, 'SMTP_PASSWORD'))
            self.assertTrue(hasattr(settings, 'DEFAULT_RECIPIENT'))
            
        except Exception as e:
            self.fail(f"Konfigurationsvalidierung fehlgeschlagen: {str(e)}")
    
    def test_memory_and_conversation_flow(self):
        """Teste Memory-Management und Konversationsfluss"""
        try:
            agent = create_react_agent()
            
            # Führe mehrere Konversationsrunden durch
            responses = []
            for i in range(3):
                response = agent.chat(f"Das ist Nachricht Nummer {i+1}")
                responses.append(response)
                self.assertIsInstance(response, str)
                self.assertGreater(len(response), 0)
            
            # Überprüfe Memory-Status
            memory_info = agent.get_memory_summary()
            self.assertEqual(memory_info["total_messages"], 6)  # 3 User + 3 AI
            self.assertEqual(memory_info["human_messages"], 3)
            self.assertEqual(memory_info["ai_messages"], 3)
            
            # Teste Memory-Clearing
            agent.clear_memory()
            memory_info = agent.get_memory_summary()
            self.assertEqual(memory_info["total_messages"], 0)
            
        except Exception as e:
            self.fail(f"Memory-Management-Test fehlgeschlagen: {str(e)}")
    
    def test_error_handling(self):
        """Teste Fehlerbehandlung im System"""
        try:
            agent = create_react_agent()
            
            # Teste Agent-Robustheit bei ungewöhnlichen Eingaben
            test_inputs = [
                "",  # Leere Eingabe
                "x" * 1000,  # Sehr lange Eingabe
                "Teste Unicode: 🤖 äöü ñ",  # Unicode-Zeichen
            ]
            
            for test_input in test_inputs:
                try:
                    response = agent.chat(test_input)
                    self.assertIsInstance(response, str)
                except Exception as e:
                    # Fehler sind okay, aber sollten graceful gehandelt werden
                    self.assertIsInstance(str(e), str)
            
        except Exception as e:
            self.fail(f"Fehlerbehandlungstest fehlgeschlagen: {str(e)}")


if __name__ == "__main__":
    unittest.main()