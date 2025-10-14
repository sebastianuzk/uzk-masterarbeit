"""
Konfigurationseinstellungen für den Autonomen Chatbot-Agenten
"""
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

class Settings:
    """Zentrale Konfigurationsklasse"""
    
    # Ollama Konfiguration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
    
    # Camunda Konfiguration
    CAMUNDA_BASE_URL = os.getenv("CAMUNDA_BASE_URL", "http://localhost:8080/engine-rest")
    
    # LLM Konfiguration
    TEMPERATURE = 0.7
    
    # Agent Konfiguration
    MAX_ITERATIONS = 10
    MEMORY_SIZE = 100
    
    # Tool Konfiguration
    ENABLE_WIKIPEDIA = True
    ENABLE_WEB_SCRAPER = True
    ENABLE_DUCKDUCKGO = True
    
    # Streamlit Konfiguration
    PAGE_TITLE = "Autonomer Chatbot Agent"
    PAGE_ICON = "🤖"
    
    # Process Engine Konfiguration
    ENABLE_PROCESS_ENGINE = os.getenv("ENABLE_PROCESS_ENGINE", "false").lower() == "true"
    CAMUNDA_ZEEBE_ADDRESS = os.getenv("CAMUNDA_ZEEBE_ADDRESS", "localhost:26500")
    CAMUNDA_OPERATE_URL = os.getenv("CAMUNDA_OPERATE_URL", "http://localhost:8081")
    CAMUNDA_TASKLIST_URL = os.getenv("CAMUNDA_TASKLIST_URL", "http://localhost:8082")
    CAMUNDA_TENANT_ID = os.getenv("CAMUNDA_TENANT_ID", "university")
    
    @classmethod
    def validate(cls):
        """Validiere erforderliche Konfigurationen"""
        # Für Ollama sind keine API-Schlüssel erforderlich
        # Nur prüfen, ob Ollama-Server erreichbar ist
        import requests
        try:
            response = requests.get(f"{cls.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if response.status_code != 200:
                print("⚠️ Warnung: Ollama-Server nicht erreichbar. Stellen Sie sicher, dass Ollama läuft.")
        except requests.RequestException:
            print("⚠️ Warnung: Ollama-Server nicht erreichbar. Starten Sie Ollama mit: ollama serve")

# Globale Instanz
settings = Settings()