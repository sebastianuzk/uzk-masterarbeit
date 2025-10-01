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
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    
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