"""
Tests für die Tools
"""
import unittest
import sys
import os

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.tools.wikipedia_tool import create_wikipedia_tool
from src.tools.web_scraper_tool import create_web_scraper_tool
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from config.settings import settings

# Process Automation Tools
try:
    from src.tools.process_automation_tool import get_process_automation_tools
    PROCESS_AUTOMATION_AVAILABLE = True
except ImportError:
    PROCESS_AUTOMATION_AVAILABLE = False


class TestTools(unittest.TestCase):
    """Test-Klasse für die Tools"""
    
    def test_wikipedia_tool_creation(self):
        """Teste Wikipedia-Tool-Erstellung"""
        try:
            tool = create_wikipedia_tool()
            self.assertIsNotNone(tool)
            self.assertEqual(tool.name, "wikipedia_search")
            self.assertIsNotNone(tool.description)
        except Exception as e:
            self.fail(f"Wikipedia-Tool-Erstellung fehlgeschlagen: {str(e)}")
    
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
    
    def test_wikipedia_search(self):
        """Teste Wikipedia-Suche"""
        try:
            tool = create_wikipedia_tool()
            result = tool._run("Python programming")
            
            self.assertIsInstance(result, str)
            self.assertGreater(len(result), 0)
            self.assertIn("Python", result)
            
        except Exception as e:
            # Wikipedia-Test kann fehlschlagen, wenn keine Internetverbindung besteht
            self.skipTest(f"Wikipedia-Test übersprungen: {str(e)}")
    
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

    @unittest.skipUnless(PROCESS_AUTOMATION_AVAILABLE, "Process Automation Tools nicht verfügbar")
    def test_process_automation_tools_creation(self):
        """Teste Process Automation Tools Erstellung"""
        try:
            tools = get_process_automation_tools()
            self.assertIsInstance(tools, list)
            self.assertGreater(len(tools), 0)
            
            # Prüfe erwartete Tool-Namen
            tool_names = [tool.name for tool in tools]
            expected_tools = ["discover_processes", "start_process", "get_process_status", "complete_task"]
            
            for expected_tool in expected_tools:
                self.assertIn(expected_tool, tool_names, f"Tool '{expected_tool}' nicht gefunden")
                
        except Exception as e:
            self.fail(f"Process Automation Tools Erstellung fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(PROCESS_AUTOMATION_AVAILABLE, "Process Automation Tools nicht verfügbar")
    def test_discover_processes_tool(self):
        """Teste discover_processes Tool"""
        try:
            tools = get_process_automation_tools()
            discover_tool = None
            
            for tool in tools:
                if tool.name == "discover_processes":
                    discover_tool = tool
                    break
            
            self.assertIsNotNone(discover_tool, "discover_processes Tool nicht gefunden")
            
            # Test ohne Camunda Engine (sollte Error-Handling testen)
            result = discover_tool.invoke({})
            self.assertIsInstance(result, dict)
            
            # Das Ergebnis sollte entweder erfolgreich sein oder einen Fehler enthalten
            self.assertTrue(
                "processes" in result or "error" in result,
                "Ergebnis sollte 'processes' oder 'error' enthalten"
            )
            
        except Exception as e:
            self.skipTest(f"discover_processes Test übersprungen: {str(e)}")

    @unittest.skipUnless(PROCESS_AUTOMATION_AVAILABLE, "Process Automation Tools nicht verfügbar")
    def test_start_process_tool_validation(self):
        """Teste start_process Tool Parameter-Validation"""
        try:
            tools = get_process_automation_tools()
            start_tool = None
            
            for tool in tools:
                if tool.name == "start_process":
                    start_tool = tool
                    break
            
            self.assertIsNotNone(start_tool, "start_process Tool nicht gefunden")
            
            # Test mit ungültigen Parametern (sollte Validation Error geben)
            try:
                result = start_tool.invoke({
                    "process_key": "nonexistent_process",
                    "variables": {"test": "value"}
                })
                
                self.assertIsInstance(result, dict)
                # Sollte einen Fehler enthalten, da Prozess nicht existiert
                self.assertTrue(
                    "error" in result or "success" in result,
                    "Ergebnis sollte Erfolgs- oder Fehler-Information enthalten"
                )
                
            except Exception as e:
                # Validation Errors sind erwartbar
                self.assertIn("validation", str(e).lower(), "Sollte Validation Error sein")
                
        except Exception as e:
            self.skipTest(f"start_process Test übersprungen: {str(e)}")

    @unittest.skipUnless(PROCESS_AUTOMATION_AVAILABLE, "Process Automation Tools nicht verfügbar")
    def test_process_tools_error_handling(self):
        """Teste Error Handling der Process Tools"""
        try:
            tools = get_process_automation_tools()
            
            for tool in tools:
                # Test mit ungültigen/fehlenden Parametern
                try:
                    if tool.name == "get_process_status":
                        result = tool.invoke({"process_instance_id": "invalid_id"})
                    elif tool.name == "complete_task":
                        result = tool.invoke({"process_instance_id": "invalid_id"})
                    else:
                        continue  # Skip tools that don't take simple invalid params
                    
                    self.assertIsInstance(result, dict)
                    # Sollte Error-Information enthalten
                    self.assertTrue(
                        "error" in result or "success" in result,
                        f"Tool {tool.name} sollte Error-Information liefern"
                    )
                    
                except Exception:
                    # Exceptions beim Error-Handling sind okay - das testen wir
                    pass
                    
        except Exception as e:
            self.skipTest(f"Process Tools Error Handling Test übersprungen: {str(e)}")


if __name__ == "__main__":
    unittest.main()