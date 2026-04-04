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
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")  # Kleineres Modell für begrenzte RAM-Systeme
    
    # SentenceTransformer Embedding-Modell (für Vektordatenbank & Semantic Chunking)
    # BAAI/bge-m3: Multilingual, 1024 Dimensionen, max 8192 Tokens (wir nutzen 1024) --> max Tokens nur für bge-m3 zu setzen, ansonsten auskommentieren!
    SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "BAAI/bge-m3")
    EMBEDDING_MAX_SEQ_LENGTH = int(os.getenv("EMBEDDING_MAX_SEQ_LENGTH", "1024"))
    
    # LLM Konfiguration (Chatbot UND Evaluation)
    # Temperature 0.0 für deterministische Antworten, CONTEXT_WINDOW als Fallback
    # (ReactAgent verwendet dynamische ctx-Berechnung basierend auf Modellgröße)
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
    CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", "14500"))
    
    # RAGAS Evaluation: Separates Modell für Metrik-Berechnung
    # (nutzt gleiche LLM-Parameter: TEMPERATURE, CONTEXT_WINDOW, RANDOM_SEED)
    RAGAS_EVAL_MODEL = os.getenv("RAGAS_EVAL_MODEL", "phi4-mini:3.8b")
    
    # OpenAI Konfiguration (für RAGAS-Evaluation mit Cloud-LLM als Judge)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_EVAL_MODEL = os.getenv("OPENAI_EVAL_MODEL", "gpt-4.1-mini")  # Günstiges GPT-4 Modell für Evaluation
    
    # RAGAS Evaluation Mode: True = lokales Ollama-LLM, False = OpenAI-LLM als Judge
    # Hinweis: Embeddings werden IMMER lokal mit Ollama (embeddinggemma) berechnet
    RUN_EVALUATION_LOCAL = os.getenv("RUN_EVALUATION_LOCAL", "false").lower() == "true"
    
    # Reproduzierbarkeit
    RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
    
    # Agent Konfiguration
    MAX_ITERATIONS = 10
    MEMORY_SIZE = 100
    
    # RAG Konfiguration
    # Anzahl der finalen Dokumente, die an den Agent übergeben werden (gilt für alle Retrieval-Ansätze)
    TOP_K = int(os.getenv("TOP_K", "5"))
    
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

# Exportiere Settings-Instanz
settings = Settings()

# Exportiere wichtige Variablen auch direkt
OLLAMA_MODEL = settings.OLLAMA_MODEL
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL
SENTENCE_TRANSFORMER_MODEL = settings.SENTENCE_TRANSFORMER_MODEL
EMBEDDING_MAX_SEQ_LENGTH = settings.EMBEDDING_MAX_SEQ_LENGTH
LANGSMITH_API_KEY = settings.LANGSMITH_API_KEY
LANGSMITH_PROJECT = settings.LANGSMITH_PROJECT
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

# RAGAS Evaluation Export (nutzt gemeinsame LLM-Parameter)
RAGAS_EVAL_MODEL = settings.RAGAS_EVAL_MODEL
CONTEXT_WINDOW = settings.CONTEXT_WINDOW
RANDOM_SEED = settings.RANDOM_SEED

# OpenAI Konfiguration Exports
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_EVAL_MODEL = settings.OPENAI_EVAL_MODEL
RUN_EVALUATION_LOCAL = settings.RUN_EVALUATION_LOCAL