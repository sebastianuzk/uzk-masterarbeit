"""
Konfigurationseinstellungen für den Autonomen Chatbot-Agenten
"""
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

# Ollama Server-Optimierungen (werden beim Import automatisch gesetzt)
# Diese Variablen müssen VOR dem Ollama-Server-Start gesetzt sein
# OLLAMA_MODELS muss manuell gesetzt werden (systemabhängig)
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")  # ~20% schneller, weniger VRAM
os.environ.setdefault("OLLAMA_KEEP_ALIVE", "30m")  # Modell 30 Min im RAM halten
os.environ.setdefault("OLLAMA_NUM_GPU", "99")  # Alle Layer auf GPU

class Settings:
    """Zentrale Konfigurationsklasse"""
    
    # Ollama Konfiguration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:3b")  # Kleineres Modell für begrenzte RAM-Systeme
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:8b")
    OLLAMA_EVALUATION_TIMEOUT = int(os.getenv("OLLAMA_EVALUATION_TIMEOUT", "300"))  # 5 Minuten für RAGAS-Evaluationen
    
    # OpenAI Konfiguration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")  # Default OpenAI Modell
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # Optional: für Custom OpenAI-kompatible APIs
    
    # LLM Provider (ollama oder openai)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    
    # RAGAS-Evaluation: Fester Judge für faire Vergleiche zwischen Modellen
    RAGAS_JUDGE_MODEL = os.getenv("RAGAS_JUDGE_MODEL", "qwen2.5:7b")
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))  # 2 Minuten Timeout für LLM-Requests
    
    # Ollama Server-Optimierungen (aus Umgebungsvariablen)
    OLLAMA_FLASH_ATTENTION = os.getenv("OLLAMA_FLASH_ATTENTION", "1") == "1"
    OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "99"))
    
    # SentenceTransformer Embedding-Modell (für Vektordatenbank & Semantic Chunking)
    # BAAI/bge-m3 für DE+EN Texte (1024 Dimensionen) - passend zur Vektordatenbank
    SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "BAAI/bge-m3")
    
    # LLM Konfiguration
    TEMPERATURE = 0.0
    
    # Agent Konfiguration
    MAX_ITERATIONS = 10
    MEMORY_SIZE = 100
    
    # Recursion Limits für verschiedene Agent-Typen
    AGENT_RECURSION_LIMIT = int(os.getenv("AGENT_RECURSION_LIMIT", "25"))  # Limit für Standard ReactAgent
    CONFIRMATION_AGENT_RECURSION_LIMIT = int(os.getenv("CONFIRMATION_AGENT_RECURSION_LIMIT", "25"))  # Limit für Confirmation Agent
    CONSTRAINED_AGENT_RECURSION_LIMIT = int(os.getenv("CONSTRAINED_AGENT_RECURSION_LIMIT", "25"))  # Limit für Constrained Agent
    MULTI_AGENT_RECURSION_LIMIT = int(os.getenv("MULTI_AGENT_RECURSION_LIMIT", "25"))  # Limit für Multi-Agent System
    
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
        import requests
        
        # Provider-spezifische Validierung
        if cls.LLM_PROVIDER == "openai":
            # OpenAI: API-Key erforderlich
            if not cls.OPENAI_API_KEY:
                print("⚠️ Warnung: OPENAI_API_KEY nicht gesetzt.")
                print("   Bitte konfigurieren Sie OPENAI_API_KEY in der .env Datei.")
        else:
            # Ollama: Prüfen, ob Server erreichbar ist
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

# Exportiere Settings-Instanz
settings = Settings()

# Exportiere wichtige Variablen auch direkt
OLLAMA_MODEL = settings.OLLAMA_MODEL
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL
OLLAMA_EMBEDDING_MODEL = settings.OLLAMA_EMBEDDING_MODEL
OLLAMA_EVALUATION_TIMEOUT = settings.OLLAMA_EVALUATION_TIMEOUT
RAGAS_JUDGE_MODEL = settings.RAGAS_JUDGE_MODEL
SENTENCE_TRANSFORMER_MODEL = settings.SENTENCE_TRANSFORMER_MODEL
LANGSMITH_API_KEY = settings.LANGSMITH_API_KEY
LANGSMITH_PROJECT = settings.LANGSMITH_PROJECT
TEMPERATURE = settings.TEMPERATURE
MAX_ITERATIONS = settings.MAX_ITERATIONS
MEMORY_SIZE = settings.MEMORY_SIZE
AGENT_RECURSION_LIMIT = settings.AGENT_RECURSION_LIMIT
CONFIRMATION_AGENT_RECURSION_LIMIT = settings.CONFIRMATION_AGENT_RECURSION_LIMIT
CONSTRAINED_AGENT_RECURSION_LIMIT = settings.CONSTRAINED_AGENT_RECURSION_LIMIT
MULTI_AGENT_RECURSION_LIMIT = settings.MULTI_AGENT_RECURSION_LIMIT
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