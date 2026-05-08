"""
Configuration settings for the Autonomous Chatbot Agent
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Disable ChromaDB telemetry
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# Ollama server optimizations (applied automatically on import)
# These variables must be set BEFORE starting the Ollama server
# OLLAMA_MODELS must be set manually (system-dependent)
os.environ.setdefault("OLLAMA_FLASH_ATTENTION", "1")  # ~20% faster, less VRAM
os.environ.setdefault("OLLAMA_KEEP_ALIVE", "30m")  # Keep model in RAM for 30 min
os.environ.setdefault("OLLAMA_NUM_GPU", "99")  # All layers on GPU


def _str_to_bool(value: str, default: bool = False) -> bool:
    """Convert a string environment variable to a boolean."""
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _safe_int(value: str, default: int) -> int:
    """Safely convert an environment variable to int with a fallback default."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Available LLM models for evaluation and agent configuration
AVAILABLE_MODELS: Dict[str, Dict[str, Any]] = {
    # Ollama models
    "llama3.1:8b": {
        "name": "LLaMA 3.1 8B",
        "ctx_size": 8192,
        "description": "Meta's LLaMA 3.1 with 8B parameters",
        "provider": "ollama",
    },
    "gpt-oss:20b": {
        "name": "GPT-OSS 20B",
        "ctx_size": 16384,
        "description": "Open-source GPT variant with 20B parameters",
        "provider": "ollama",
    },
    # OpenAI models
    "gpt-4o": {
        "name": "GPT-4o",
        "ctx_size": 128000,
        "description": "OpenAI GPT-4o (multimodal, fast)",
        "provider": "openai",
    },
    "gpt-4o-mini": {
        "name": "GPT-4o Mini",
        "ctx_size": 128000,
        "description": "OpenAI GPT-4o Mini (cost-efficient)",
        "provider": "openai",
    },
        "gpt-4.1-mini": {
        "name": "GPT-4o Mini",
        "ctx_size": 128000,
        "description": "OpenAI GPT-4o Mini (cost-efficient)",
        "provider": "openai",
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo",
        "ctx_size": 128000,
        "description": "OpenAI GPT-4 Turbo",
        "provider": "openai",
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "ctx_size": 16385,
        "description": "OpenAI GPT-3.5 Turbo (budget)",
        "provider": "openai",
    },
    "gpt-5": {
        "name": "GPT-5",
        "ctx_size": 200000,
        "description": "OpenAI GPT-5 (latest)",
        "provider": "openai",
    },
    "gpt-5.2": {
        "name": "GPT-5.2",
        "ctx_size": 200000,
        "description": "OpenAI GPT-5.2",
        "provider": "openai",
    },
    # Anthropic models
    "claude-opus-4-5": {
        "name": "Claude Opus 4.5",
        "ctx_size": 200000,
        "description": "Anthropic Claude Opus 4.5",
        "provider": "anthropic",
    },
    "claude-sonnet-4-5": {
        "name": "Claude Sonnet 4.5",
        "ctx_size": 200000,
        "description": "Anthropic Claude Sonnet 4.5",
        "provider": "anthropic",
    },
    "claude-sonnet-4-6": {
        "name": "Claude Sonnet 4.6",
        "ctx_size": 200000,
        "description": "Anthropic Claude Sonnet 4.6",
        "provider": "anthropic",
    },
    "claude-haiku-3-5": {
        "name": "Claude Haiku 3.5",
        "ctx_size": 200000,
        "description": "Anthropic Claude Haiku 3.5 (cost-efficient)",
        "provider": "anthropic",
    },
}


class Settings:
    """Central configuration class"""
    
    # Ollama configuration
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:3b")  # Smaller model for RAM-limited systems
    OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "qwen3-embedding:8b")
    OLLAMA_EVALUATION_TIMEOUT = _safe_int(os.getenv("OLLAMA_EVALUATION_TIMEOUT"), 600)  # 10 minutes for RAGAS evaluations
    
    # OpenAI configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.2")  # Default OpenAI model
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # Optional: for custom OpenAI-compatible APIs
    
    # Anthropic configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")  # Default Anthropic model
    
    # LLM provider (ollama, openai or anthropic)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
    
    # RAGAS evaluation: fixed judge for fair cross-model comparisons
    RAGAS_JUDGE_MODEL = os.getenv("RAGAS_JUDGE_MODEL", "qwen2.5:7b")
    REQUEST_TIMEOUT = _safe_int(os.getenv("REQUEST_TIMEOUT"), 600)  # 10 minute timeout for LLM requests
    
    # Ollama server optimizations (from environment variables)
    OLLAMA_FLASH_ATTENTION = _str_to_bool(os.getenv("OLLAMA_FLASH_ATTENTION", "1"))
    OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    OLLAMA_NUM_GPU = _safe_int(os.getenv("OLLAMA_NUM_GPU"), 99)
    
    # SentenceTransformer Embedding-Modell (für Vektordatenbank & Semantic Chunking)
    # BAAI/bge-m3 für DE+EN Texte (1024 Dimensionen) - passend zur Vektordatenbank
    SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "BAAI/bge-m3")
    
    # LLM Konfiguration
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
    
    # Agent Konfiguration
    MAX_ITERATIONS = 10
    MEMORY_SIZE = 100
    
    # Recursion Limits für verschiedene Agent-Typen
    # Alle Agenten nutzen ein gemeinsames Standard-Limit mit optionalen Overrides
    DEFAULT_RECURSION_LIMIT = _safe_int(os.getenv("DEFAULT_RECURSION_LIMIT"), 25)
    
    RECURSION_LIMITS = {
        "single": _safe_int(os.getenv("AGENT_RECURSION_LIMIT"), DEFAULT_RECURSION_LIMIT),
        "multi": _safe_int(os.getenv("MULTI_AGENT_RECURSION_LIMIT"), DEFAULT_RECURSION_LIMIT),
        "confirmation": _safe_int(os.getenv("CONFIRMATION_AGENT_RECURSION_LIMIT"), DEFAULT_RECURSION_LIMIT),
        "constrained": _safe_int(os.getenv("CONSTRAINED_AGENT_RECURSION_LIMIT"), DEFAULT_RECURSION_LIMIT),
    }
    
    # Backward compatibility - deprecated, use RECURSION_LIMITS instead
    AGENT_RECURSION_LIMIT = RECURSION_LIMITS["single"]
    CONFIRMATION_AGENT_RECURSION_LIMIT = RECURSION_LIMITS["confirmation"]
    CONSTRAINED_AGENT_RECURSION_LIMIT = RECURSION_LIMITS["constrained"]
    MULTI_AGENT_RECURSION_LIMIT = RECURSION_LIMITS["multi"]
    
    # Tool Konfiguration
    ENABLE_WEB_SCRAPER = True
    ENABLE_DUCKDUCKGO = True
    ENABLE_EMAIL = True
    ENABLE_KLIPS = True
    ENABLE_RAG_TOOL = True  # university_knowledge_search; disable for tool-routing evaluation
    
    # E-Mail-Konfiguration
    SMTP_SERVER = os.getenv("SMTP_SERVER")
    SMTP_PORT = _safe_int(os.getenv("SMTP_PORT"), 587)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    DEFAULT_RECIPIENT = os.getenv("DEFAULT_RECIPIENT")
    
    # Streamlit Konfiguration
    PAGE_TITLE = "🤖 Autonomer Chatbot-Agent"
    PAGE_ICON = "🤖"
    
    # LangSmith Tracing Konfiguration
    LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
    LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT")
    LANGSMITH_TRACING = _str_to_bool(os.getenv("LANGSMITH_TRACING", "false"))
    
    @classmethod
    def validate(cls):
        """Validate required configurations"""
        import requests
        from config.logging_config import get_logger
        
        logger = get_logger(__name__)
        
        # Provider-specific validation
        if cls.LLM_PROVIDER == "openai":
            # OpenAI: API key required
            if not cls.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY not set. Please configure OPENAI_API_KEY in the .env file.")
        else:
            # Ollama: check if server is reachable
            try:
                response = requests.get(f"{cls.OLLAMA_BASE_URL}/api/tags", timeout=5)
                if response.status_code != 200:
                    logger.warning("Ollama server not reachable. Make sure Ollama is running.")
            except requests.RequestException:
                logger.warning("Ollama server not reachable. Start Ollama with: ollama serve")
        
        # Email configuration check
        if not cls.SMTP_USERNAME or not cls.SMTP_PASSWORD:
            logger.warning("Email configuration incomplete. Please configure SMTP_USERNAME and SMTP_PASSWORD in the .env file. See EMAIL_SETUP.md for instructions.")
        
        if not cls.DEFAULT_RECIPIENT:
            logger.warning("DEFAULT_RECIPIENT not configured. Emails cannot be sent without a recipient address.")

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
ENABLE_EMAIL = settings.ENABLE_EMAIL
ENABLE_KLIPS = settings.ENABLE_KLIPS
PAGE_TITLE = settings.PAGE_TITLE
PAGE_ICON = settings.PAGE_ICON

# OpenAI-Konfiguration Exports
OPENAI_API_KEY = settings.OPENAI_API_KEY
OPENAI_MODEL = settings.OPENAI_MODEL
OPENAI_BASE_URL = settings.OPENAI_BASE_URL
LLM_PROVIDER = settings.LLM_PROVIDER

# Anthropic-Konfiguration Exports
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
ANTHROPIC_MODEL = settings.ANTHROPIC_MODEL

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

# Modell-Konfiguration Export (bereits auf Modul-Ebene definiert)
# AVAILABLE_MODELS ist direkt importierbar: from config.settings import AVAILABLE_MODELS