"""
Systemtests für den Autonomen Chatbot-Agenten
"""
import unittest
import sys
import os
import pytest

# Markiere alle Tests in dieser Datei als slow und integration
pytestmark = [pytest.mark.slow, pytest.mark.integration]

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
        """Teste vollständige Systeminitialisierung und Interaktion"""
        try:
            # Erstelle Agent
            agent = create_react_agent()
            self.assertIsNotNone(agent)
            
            # Überprüfe Tools
            tools = agent.get_available_tools()
            self.assertIsInstance(tools, list)
            self.assertGreater(len(tools), 0)
            self.assertIn("send_email", tools)
            
            # Teste einfache Interaktion
            response = agent.chat("Hallo")
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 10)
        except Exception as e:
            self.fail(f"System-Initialisierung fehlgeschlagen: {str(e)}")
    
    def test_email_tool_system_integration(self):
        """Teste E-Mail-Tool-Integration im Gesamtsystem"""
        try:
            # Teste eigenständiges E-Mail-Tool
            email_tool = create_email_tool()
            self.assertIsNotNone(email_tool)
            self.assertEqual(email_tool.name, "send_email")
            
            # Erstelle einen Agent, um Tool-Integration zu testen
            agent = create_react_agent()
            
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
        """Teste Memory-Management"""
        try:
            agent = create_react_agent()
            
            # Teste Memory-Clearing
            agent.clear_memory()
            memory_info = agent.get_memory_summary()
            self.assertEqual(memory_info["total_messages"], 0)
        except Exception as e:
            self.fail(f"Memory-Management-Test fehlgeschlagen: {str(e)}")
    



if __name__ == "__main__":
    unittest.main()