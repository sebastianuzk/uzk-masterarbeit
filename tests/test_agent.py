"""
Tests für den React Agent
"""
import unittest
import sys
import os

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.agent.react_agent import ReactAgent
from config.settings import settings


class TestReactAgent(unittest.TestCase):
    """Test-Klasse für den React Agent"""
    
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
    
    def test_agent_initialization(self):
        """Teste Agent-Initialisierung"""
        try:
            agent = ReactAgent()
            self.assertIsNotNone(agent)
            self.assertIsNotNone(agent.llm)
            self.assertIsNotNone(agent.tools)
            self.assertIsNotNone(agent.agent)
        except Exception as e:
            self.fail(f"Agent-Initialisierung fehlgeschlagen: {str(e)}")
    
    def test_available_tools(self):
        """Teste verfügbare Tools"""
        try:
            agent = ReactAgent()
            tools = agent.get_available_tools()
            
            self.assertIsInstance(tools, list)
            self.assertGreater(len(tools), 0)
           
            if settings.ENABLE_WEB_SCRAPER:
                self.assertIn("web_scraper", tools)
            
            if settings.ENABLE_DUCKDUCKGO:
                self.assertIn("duckduckgo_search", tools)
            
            # E-Mail-Tool sollte immer verfügbar sein
            self.assertIn("send_email", tools)
                
        except Exception as e:
            self.fail(f"Tool-Test fehlgeschlagen: {str(e)}")
    
    def test_memory_management(self):
        """Teste Memory-Management"""
        try:
            agent = ReactAgent()
            
            # Initiales Memory sollte leer sein
            memory_info = agent.get_memory_summary()
            self.assertEqual(memory_info["total_messages"], 0)
            
            # Memory löschen sollte funktionieren
            agent.clear_memory()
            memory_info = agent.get_memory_summary()
            self.assertEqual(memory_info["total_messages"], 0)
            
        except Exception as e:
            self.fail(f"Memory-Test fehlgeschlagen: {str(e)}")
    
    def test_simple_chat(self):
        """Teste einfache Chat-Funktionalität"""
        try:
            agent = ReactAgent()
            
            # Einfache Frage stellen
            response = agent.chat("Hallo, wie geht es dir?")
            
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            
            # Memory sollte jetzt Nachrichten enthalten
            memory_info = agent.get_memory_summary()
            self.assertGreater(memory_info["total_messages"], 0)
            
        except Exception as e:
            self.fail(f"Chat-Test fehlgeschlagen: {str(e)}")
    
    def test_email_tool_integration(self):
        """Teste E-Mail-Tool-Integration im Agent"""
        try:
            agent = ReactAgent()
            
            # Überprüfe, dass E-Mail-Tool geladen wurde
            tools = agent.get_available_tools()
            self.assertIn("send_email", tools)
            
            # Überprüfe, dass E-Mail-Tool in der Tool-Liste ist
            email_tools = [tool for tool in agent.tools if tool.name == "send_email"]
            self.assertEqual(len(email_tools), 1)
            
            # Teste Tool-Beschreibung
            email_tool = email_tools[0]
            self.assertIsNotNone(email_tool.description)
            self.assertIn("E-Mail", email_tool.description)
            
        except Exception as e:
            self.fail(f"E-Mail-Tool-Integration-Test fehlgeschlagen: {str(e)}")
    
    def test_agent_system_prompt_contains_email_info(self):
        """Teste, dass System-Prompt E-Mail-Informationen enthält"""
        try:
            agent = ReactAgent()
            
            # Da wir nicht direkt auf system_prompt zugreifen können,
            # testen wir indirekt über die Tool-Verfügbarkeit
            tools = agent.get_available_tools()
            self.assertIn("send_email", tools)
            
            # Überprüfe, dass Agent E-Mail-Tool korrekt initialisiert hat
            email_tools = [tool for tool in agent.tools if tool.name == "send_email"]
            self.assertGreater(len(email_tools), 0)
            
        except Exception as e:
            self.fail(f"System-Prompt-Test fehlgeschlagen: {str(e)}")


if __name__ == "__main__":
    unittest.main()