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
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")  # Kleines, schnelles Modell (neigt zu mehrsprachiger Ausgabe)
    
    # LLM Konfiguration
    TEMPERATURE = 0.7
    REQUEST_TIMEOUT = 30  # Sekunden für Ollama-Anfragen
    
    # Agent Konfiguration
    MAX_ITERATIONS = 5  # Balance zwischen Funktionalität und Geschwindigkeit
    MEMORY_SIZE = 100
    
    # Tool Konfiguration
    ENABLE_WEB_SCRAPER = True
    ENABLE_DUCKDUCKGO = True
    
    # E-Mail-Konfiguration
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = int(os.getenv("SMTP_PORT"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    DEFAULT_RECIPIENT = os.getenv("DEFAULT_RECIPIENT")
    
    # Streamlit Konfiguration
    PAGE_TITLE = "🤖 Autonomer Chatbot-Agent"
    PAGE_ICON = "🤖"
    
    # LangSmith Tracing Konfiguration
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")
    LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
    
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
        
        # E-Mail-Konfiguration prüfen
        if not cls.SMTP_USERNAME or not cls.SMTP_PASSWORD:
            print("⚠️ Warnung: E-Mail-Konfiguration unvollständig.")
            print("   Bitte konfigurieren Sie SMTP_USERNAME und SMTP_PASSWORD in der .env Datei.")
            print("   Siehe EMAIL_SETUP.md für Anweisungen.")
        
        if not cls.DEFAULT_RECIPIENT:
            print("⚠️ Warnung: DEFAULT_RECIPIENT nicht konfiguriert.")
            print("   E-Mails können nicht gesendet werden ohne Empfänger-Adresse.")

# Globale Instanz
settings = Settings()

# Module-Level Exports für einfachen Import
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL
OLLAMA_MODEL = settings.OLLAMA_MODEL
TEMPERATURE = settings.TEMPERATURE
MAX_ITERATIONS = settings.MAX_ITERATIONS
MEMORY_SIZE = settings.MEMORY_SIZE
ENABLE_WEB_SCRAPER = settings.ENABLE_WEB_SCRAPER
ENABLE_DUCKDUCKGO = settings.ENABLE_DUCKDUCKGO
PAGE_TITLE = settings.PAGE_TITLE
PAGE_ICON = settings.PAGE_ICON

# LangSmith-Konfiguration Exports
LANGSMITH_API_KEY = settings.LANGSMITH_API_KEY
LANGSMITH_PROJECT = settings.LANGSMITH_PROJECT
LANGSMITH_TRACING = settings.LANGSMITH_TRACING

# E-Mail-Konfiguration Exports
SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
SMTP_USERNAME = settings.SMTP_USERNAME
SMTP_PASSWORD = settings.SMTP_PASSWORD
DEFAULT_RECIPIENT = settings.DEFAULT_RECIPIENT