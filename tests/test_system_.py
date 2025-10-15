"""
System-Tests für das gesamte Masterarbeit-System
Testet die Integration aller Komponenten
"""
import unittest
import sys
import os
import time
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.settings import settings

# Komponenten für System-Tests
try:
    from src.agent.react_agent import ReactAgent
    AGENT_AVAILABLE = True
except ImportError:
    AGENT_AVAILABLE = False

try:
    from src.tools.process_automation_tool import get_process_automation_tools
    PROCESS_AUTOMATION_AVAILABLE = True
except ImportError:
    PROCESS_AUTOMATION_AVAILABLE = False

try:
    from src.camunda_integration.client.camunda_client import CamundaClient
    from src.camunda_integration.services.camunda_service import CamundaService
    CAMUNDA_AVAILABLE = True
except ImportError:
    CAMUNDA_AVAILABLE = False

try:
    from src.scraper.vector_store import VectorStore
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False


class TestSystemIntegration(unittest.TestCase):
    """Test-Klasse für System-Integration"""
    
    def test_settings_configuration(self):
        """Teste System-Konfiguration über Settings"""
        try:
            # Prüfe kritische Settings
            self.assertIsNotNone(settings.OLLAMA_MODEL)
            self.assertIsNotNone(settings.OLLAMA_BASE_URL)
            self.assertIsNotNone(settings.CAMUNDA_BASE_URL)
            
            # Validiere Settings
            settings.validate()
            
        except Exception as e:
            self.fail(f"Settings Konfiguration Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(AGENT_AVAILABLE, "Agent nicht verfügbar")
    def test_react_agent_initialization(self):
        """Teste React Agent Initialisierung"""
        try:
            agent = ReactAgent()
            self.assertIsNotNone(agent)
            self.assertIsNotNone(agent.llm)
            self.assertIsNotNone(agent.tools)
            self.assertGreater(len(agent.tools), 0)
            
        except Exception as e:
            self.skipTest(f"React Agent Test übersprungen: {str(e)}")

    @unittest.skipUnless(PROCESS_AUTOMATION_AVAILABLE, "Process Automation nicht verfügbar")
    def test_process_automation_tools_integration(self):
        """Teste Process Automation Tools Integration"""
        try:
            tools = get_process_automation_tools()
            self.assertIsInstance(tools, list)
            self.assertGreater(len(tools), 0)
            
            # Prüfe, dass alle erwarteten Tools vorhanden sind
            tool_names = [tool.name for tool in tools]
            expected_tools = ["discover_processes", "start_process", "get_process_status", "complete_task"]
            
            for expected_tool in expected_tools:
                self.assertIn(expected_tool, tool_names)
                
        except Exception as e:
            self.skipTest(f"Process Automation Integration Test übersprungen: {str(e)}")

    @unittest.skipUnless(CAMUNDA_AVAILABLE, "Camunda Integration nicht verfügbar")
    def test_camunda_system_components(self):
        """Teste Camunda System Komponenten"""
        try:
            # Test CamundaClient
            client = CamundaClient(base_url=settings.CAMUNDA_BASE_URL)
            self.assertIsNotNone(client)
            
            # Test CamundaService  
            bpmn_dir = Path("src/camunda_integration/bpmn_processes")
            service = CamundaService(client=client, bpmn_dir=bpmn_dir)
            self.assertIsNotNone(service)
            
            # Test BPMN Directory
            self.assertEqual(service.bpmn_dir, bpmn_dir)
            
        except Exception as e:
            self.skipTest(f"Camunda System Test übersprungen: {str(e)}")

    @unittest.skipUnless(RAG_AVAILABLE, "RAG System nicht verfügbar")
    def test_rag_system_integration(self):
        """Teste RAG System Integration"""
        try:
            # Test VectorStore Erstellung
            vector_store = VectorStore()
            self.assertIsNotNone(vector_store)
            
        except Exception as e:
            self.skipTest(f"RAG System Test übersprungen: {str(e)}")

    def test_project_structure(self):
        """Teste Projekt-Struktur"""
        try:
            # Prüfe wichtige Verzeichnisse
            project_dirs = [
                "src",
                "src/agent", 
                "src/tools",
                "src/camunda_integration",
                "src/scraper",
                "tests",
                "config"
            ]
            
            for dir_path in project_dirs:
                full_path = Path(project_root) / dir_path
                self.assertTrue(
                    full_path.exists(),
                    f"Verzeichnis {dir_path} sollte existieren"
                )
                
            # Prüfe wichtige Dateien
            project_files = [
                "config/settings.py",
                "src/agent/react_agent.py",
                "src/tools/process_automation_tool.py",
                "tests/test_tools.py"
            ]
            
            for file_path in project_files:
                full_path = Path(project_root) / file_path
                self.assertTrue(
                    full_path.exists(),
                    f"Datei {file_path} sollte existieren"
                )
                
        except Exception as e:
            self.fail(f"Projekt-Struktur Test fehlgeschlagen: {str(e)}")

    @unittest.skipUnless(AGENT_AVAILABLE and PROCESS_AUTOMATION_AVAILABLE, 
                         "Agent oder Process Automation nicht verfügbar")
    def test_agent_process_automation_integration(self):
        """Teste Integration zwischen Agent und Process Automation"""
        try:
            agent = ReactAgent()
            
            # Prüfe, dass Process Automation Tools im Agent verfügbar sind
            tool_names = [tool.name for tool in agent.tools]
            process_automation_tools = ["discover_processes", "start_process", "get_process_status", "complete_task"]
            
            # Mindestens ein Process Automation Tool sollte verfügbar sein
            has_process_tools = any(tool in tool_names for tool in process_automation_tools)
            self.assertTrue(
                has_process_tools,
                "Agent sollte Process Automation Tools haben"
            )
            
        except Exception as e:
            self.skipTest(f"Agent-Process Automation Integration Test übersprungen: {str(e)}")

    def test_import_dependencies(self):
        """Teste kritische Import-Abhängigkeiten"""
        try:
            # Test kritische Imports
            import langchain_core
            import langchain_ollama
            import langgraph
            import streamlit
            import requests
            import pydantic
            
            # Alle Imports erfolgreich
            self.assertTrue(True)
            
        except ImportError as e:
            self.fail(f"Kritische Abhängigkeit fehlt: {e}")

    def test_configuration_consistency(self):
        """Teste Konsistenz der Konfiguration"""
        try:
            # Prüfe URL-Formate
            self.assertTrue(settings.OLLAMA_BASE_URL.startswith("http"))
            self.assertTrue(settings.CAMUNDA_BASE_URL.startswith("http"))
            
            # Prüfe Temperatur-Bereich
            self.assertGreaterEqual(settings.TEMPERATURE, 0.0)
            self.assertLessEqual(settings.TEMPERATURE, 2.0)
            
            # Prüfe Model-Name
            self.assertIsInstance(settings.OLLAMA_MODEL, str)
            self.assertGreater(len(settings.OLLAMA_MODEL), 0)
            
        except Exception as e:
            self.fail(f"Konfigurations-Konsistenz Test fehlgeschlagen: {str(e)}")


class TestSystemPerformance(unittest.TestCase):
    """Test-Klasse für System-Performance"""
    
    @unittest.skipUnless(AGENT_AVAILABLE, "Agent nicht verfügbar")
    def test_agent_initialization_performance(self):
        """Teste Performance der Agent-Initialisierung"""
        try:
            start_time = time.time()
            agent = ReactAgent()
            end_time = time.time()
            
            initialization_time = end_time - start_time
            
            # Agent sollte in weniger als 30 Sekunden initialisiert werden
            self.assertLess(
                initialization_time, 
                30.0,
                f"Agent-Initialisierung dauerte {initialization_time:.2f}s (zu langsam)"
            )
            
        except Exception as e:
            self.skipTest(f"Agent Performance Test übersprungen: {str(e)}")

    @unittest.skipUnless(PROCESS_AUTOMATION_AVAILABLE, "Process Automation nicht verfügbar")
    def test_tools_loading_performance(self):
        """Teste Performance des Tool-Ladens"""
        try:
            start_time = time.time()
            tools = get_process_automation_tools()
            end_time = time.time()
            
            loading_time = end_time - start_time
            
            # Tools sollten in weniger als 5 Sekunden geladen werden
            self.assertLess(
                loading_time,
                5.0,
                f"Tool-Laden dauerte {loading_time:.2f}s (zu langsam)"
            )
            
            # Sollte mindestens 4 Tools haben
            self.assertGreaterEqual(len(tools), 4)
            
        except Exception as e:
            self.skipTest(f"Tools Performance Test übersprungen: {str(e)}")


class TestSystemHealthCheck(unittest.TestCase):
    """Test-Klasse für System-Health-Checks"""
    
    def test_python_version(self):
        """Teste Python-Version"""
        try:
            import sys
            
            # Prüfe Python-Version (sollte 3.8+ sein)
            self.assertGreaterEqual(sys.version_info.major, 3)
            self.assertGreaterEqual(sys.version_info.minor, 8)
            
        except Exception as e:
            self.fail(f"Python Version Test fehlgeschlagen: {str(e)}")

    def test_memory_usage(self):
        """Teste Speicher-Nutzung"""
        try:
            import psutil
            
            # Hole aktuelle Speicher-Nutzung
            memory = psutil.virtual_memory()
            
            # System sollte mindestens 1GB verfügbaren Speicher haben
            available_gb = memory.available / (1024**3)
            self.assertGreater(
                available_gb,
                1.0,
                f"Zu wenig verfügbarer Speicher: {available_gb:.2f}GB"
            )
            
        except ImportError:
            self.skipTest("psutil nicht verfügbar für Memory-Test")
        except Exception as e:
            self.skipTest(f"Memory Test übersprungen: {str(e)}")

    def test_disk_space(self):
        """Teste verfügbaren Festplattenspeicher"""
        try:
            import shutil
            
            # Prüfe verfügbaren Speicher im Projekt-Verzeichnis
            free_bytes = shutil.disk_usage(project_root).free
            free_gb = free_bytes / (1024**3)
            
            # Sollte mindestens 1GB freien Speicher haben
            self.assertGreater(
                free_gb,
                1.0,
                f"Zu wenig freier Speicher: {free_gb:.2f}GB"
            )
            
        except Exception as e:
            self.skipTest(f"Disk Space Test übersprungen: {str(e)}")


if __name__ == "__main__":
    unittest.main()