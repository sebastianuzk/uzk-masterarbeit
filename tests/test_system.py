"""
Vollständige System-Integrationstests für die gesamte Anwendung
"""
import unittest
import sys
import os
import time
import subprocess
import threading
import requests
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from config.settings import settings


class TestSystemIntegration(unittest.TestCase):
    """Test-Klasse für vollständige System-Integration"""
    
    @classmethod
    def setUpClass(cls):
        """Setup für alle Tests"""
        cls.project_root = Path(project_root)
        cls.python_executable = cls.project_root / "Masterarbeit" / "Scripts" / "python.exe"
        
        # Überprüfe Python-Umgebung
        if not cls.python_executable.exists():
            raise unittest.SkipTest("Python-Umgebung nicht verfügbar")
    
    def test_project_structure(self):
        """Teste die Projektstruktur"""
        # Überprüfe wichtige Verzeichnisse
        required_dirs = [
            "src/agent",
            "src/tools", 
            "src/scraper",
            "src/ui",
            "tests",
            "config"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            self.assertTrue(full_path.exists(), f"Verzeichnis {dir_path} nicht gefunden")
    
    def test_configuration_validation(self):
        """Teste Konfigurationsvalidierung"""
        try:
            settings.validate()
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Konfigurationsvalidierung fehlgeschlagen: {str(e)}")
    
    def test_agent_initialization(self):
        """Teste Agent-Initialisierung"""
        try:
            from src.agent.react_agent import ReactAgent
            
            # Prüfen, ob Ollama erreichbar ist
            try:
                response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code != 200:
                    self.skipTest("Ollama-Server nicht erreichbar")
            except:
                self.skipTest("Ollama-Server nicht erreichbar")
            
            agent = ReactAgent()
            self.assertIsNotNone(agent)
            self.assertIsNotNone(agent.tools)
            
        except Exception as e:
            self.fail(f"Agent-Initialisierung fehlgeschlagen: {str(e)}")
    
    def test_tools_integration(self):
        """Teste Tool-Integration (ohne Wikipedia, mit E-Mail)"""
        try:
            from src.tools.web_scraper_tool import create_web_scraper_tool
            from src.tools.duckduckgo_tool import create_duckduckgo_tool
            from src.tools.rag_tool import create_university_rag_tool
            from src.tools.email_tool import create_email_tool
            
            # Teste Tool-Erstellung (ohne Wikipedia, mit E-Mail)
            tools = [
                create_web_scraper_tool(),
                create_duckduckgo_tool(),
                create_university_rag_tool(),
                create_email_tool()
            ]
            
            for tool in tools:
                self.assertIsNotNone(tool)
                self.assertIsNotNone(tool.name)
                self.assertIsNotNone(tool.description)
            
            # Überprüfe spezifische Tool-Namen
            tool_names = [tool.name for tool in tools]
            expected_names = ["web_scraper", "duckduckgo_search", "university_knowledge_search", "send_email"]
            
            for expected_name in expected_names:
                self.assertIn(expected_name, tool_names, f"Tool {expected_name} nicht gefunden")
                
        except Exception as e:
            self.fail(f"Tool-Integration fehlgeschlagen: {str(e)}")
    
    def test_scraper_system_integration(self):
        """Teste Scraper-System-Integration"""
        try:
            from src.scraper.batch_scraper import BatchScraper
            from src.scraper.vector_store import VectorStore
            
            # Teste Scraper-Komponenten
            scraper = BatchScraper()
            vector_store = VectorStore()
            
            self.assertIsNotNone(scraper)
            self.assertIsNotNone(vector_store)
            
        except ImportError:
            self.skipTest("Scraper-System nicht verfügbar")
        except Exception as e:
            self.fail(f"Scraper-System-Integration fehlgeschlagen: {str(e)}")
    
    def test_complete_system_initialization(self):
        """Teste vollständige System-Initialisierung (ohne Wikipedia, mit E-Mail)"""
        try:
            # Prüfen, ob Ollama erreichbar ist
            try:
                response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code != 200:
                    self.skipTest("Ollama-Server nicht erreichbar für Volltest")
            except:
                self.skipTest("Ollama-Server nicht erreichbar für Volltest")
            
            # Importiere und initialisiere alle Hauptkomponenten (ohne Wikipedia, mit E-Mail)
            from src.agent.react_agent import ReactAgent
            from src.tools.web_scraper_tool import create_web_scraper_tool
            from src.tools.duckduckgo_tool import create_duckduckgo_tool
            from src.tools.rag_tool import create_university_rag_tool
            from src.tools.email_tool import create_email_tool
            
            # Teste vollständige Initialisierung
            agent = ReactAgent()
            tools = [
                create_web_scraper_tool(),
                create_duckduckgo_tool(), 
                create_university_rag_tool(),
                create_email_tool()
            ]
            
            # Überprüfe, dass alles funktioniert
            self.assertIsNotNone(agent)
            self.assertEqual(len(tools), 4)  # 4 Tools ohne Wikipedia
            
            # Teste Agent-Tools-Integration
            available_tools = agent.get_available_tools()
            self.assertGreater(len(available_tools), 0)
            
            # Überprüfe, dass E-Mail-Tool verfügbar ist
            self.assertIn("send_email", available_tools)
            
        except Exception as e:
            self.fail(f"Vollständige System-Initialisierung fehlgeschlagen: {str(e)}")
    
    def test_email_system_integration(self):
        """Teste E-Mail-System-Integration"""
        try:
            from src.tools.email_tool import create_email_tool
            
            # Teste E-Mail-Tool-Erstellung
            email_tool = create_email_tool()
            self.assertIsNotNone(email_tool)
            self.assertEqual(email_tool.name, "send_email")
            
            # Teste E-Mail-Tool-Integration im System
            from src.agent.react_agent import ReactAgent
            agent = ReactAgent()
            available_tools = agent.get_available_tools()
            
            self.assertIn("send_email", available_tools)
            
        except Exception as e:
            self.fail(f"E-Mail-System-Integration fehlgeschlagen: {str(e)}")


class TestStreamlitAppIntegration(unittest.TestCase):
    """Test-Klasse für Streamlit-App-Integration"""
    
    def setUp(self):
        """Setup für Streamlit-Tests"""
        self.project_root = Path(project_root)
        self.python_executable = self.project_root / "Masterarbeit" / "Scripts" / "python.exe"
        
        if not self.python_executable.exists():
            self.skipTest("Python-Umgebung nicht verfügbar")
    
    def test_streamlit_app_import(self):
        """Teste Streamlit-App-Import"""
        try:
            # Importiere Streamlit-App-Module
            import streamlit as st
            from src.ui.streamlit_app import initialize_session_state, display_chat_interface, display_sidebar, main
            
            self.assertTrue(True)  # Wenn Import erfolgreich, ist Test bestanden
            
        except ImportError as e:
            self.fail(f"Streamlit-App-Import fehlgeschlagen: {str(e)}")
    
    def test_streamlit_app_structure(self):
        """Teste Streamlit-App-Struktur"""
        app_file = self.project_root / "src" / "ui" / "streamlit_app.py"
        self.assertTrue(app_file.exists(), "Streamlit-App-Datei nicht gefunden")
        
        # Überprüfe App-Inhalt
        with open(app_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Überprüfe wichtige Funktionen
        required_functions = [
            "initialize_session_state",
            "display_chat_interface", 
            "display_sidebar",
            "main"
        ]
        
        for func in required_functions:
            self.assertIn(f"def {func}", content, f"Funktion {func} nicht gefunden")


class TestSystemPerformance(unittest.TestCase):
    """Test-Klasse für System-Performance"""
    
    def test_agent_initialization_performance(self):
        """Teste Agent-Initialisierungsperformance"""
        try:
            # Prüfen, ob Ollama erreichbar ist
            try:
                response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code != 200:
                    self.skipTest("Ollama-Server nicht erreichbar für Performance-Test")
            except:
                self.skipTest("Ollama-Server nicht erreichbar für Performance-Test")
            
            from src.agent.react_agent import ReactAgent
            
            start_time = time.time()
            agent = ReactAgent()
            end_time = time.time()
            
            initialization_time = end_time - start_time
            
            # Agent sollte in weniger als 30 Sekunden initialisiert werden
            self.assertLess(initialization_time, 30.0, 
                          f"Agent-Initialisierung zu langsam: {initialization_time:.2f}s")
            
            self.assertIsNotNone(agent)
            
        except Exception as e:
            self.fail(f"Performance-Test fehlgeschlagen: {str(e)}")
    
    def test_tools_loading_performance(self):
        """Teste Tool-Ladeperformance"""
        try:
            start_time = time.time()
            
            from src.tools.web_scraper_tool import create_web_scraper_tool
            from src.tools.duckduckgo_tool import create_duckduckgo_tool
            from src.tools.rag_tool import create_university_rag_tool
            
            tools = [
                create_web_scraper_tool(),
                create_duckduckgo_tool(),
                create_university_rag_tool()
            ]
            
            end_time = time.time()
            loading_time = end_time - start_time
            
            # Tools sollten in weniger als 10 Sekunden geladen werden
            self.assertLess(loading_time, 10.0, 
                          f"Tool-Laden zu langsam: {loading_time:.2f}s")
            
            self.assertEqual(len(tools), 3)
            
        except Exception as e:
            self.fail(f"Tool-Performance-Test fehlgeschlagen: {str(e)}")


class TestSystemHealthCheck(unittest.TestCase):
    """Test-Klasse für System-Health-Checks"""
    
    def test_python_version(self):
        """Teste Python-Version"""
        import sys
        version_info = sys.version_info
        
        # Mindestens Python 3.8 erforderlich
        self.assertGreaterEqual(version_info.major, 3)
        self.assertGreaterEqual(version_info.minor, 8)
    
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
        """Teste verfügbarer Festplattenspeicher"""
        import shutil
        
        # Überprüfe verfügbaren Speicher im Projektverzeichnis
        total, used, free = shutil.disk_usage(project_root)
        
        free_gb = free / (1024**3)
        
        # Mindestens 1GB freier Speicher erforderlich
        self.assertGreater(
            free_gb,
            1.0,
            f"Zu wenig freier Festplattenspeicher: {free_gb:.2f}GB"
        )


if __name__ == "__main__":
    # Führe alle Tests aus
    unittest.main(verbosity=2)