"""
Centralized LLM Factory for all agent types.

Provides unified LLM creation supporting both Ollama and OpenAI providers.
Eliminates code duplication across agent implementations.
"""
from __future__ import annotations

from typing import Optional, Union

from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger(__name__)


# Context-Size mapping based on model size (used for Ollama models)
MODEL_CTX_SIZES = {
    "0.5b": 2048,
    "1b": 4096,
    "3b": 8192,
    "8b": 16384,
    "20b": 16384,
    "70b": 16384,
}


def get_context_size(model_name: str) -> int:
    """
    Determine appropriate context size based on model name.
    
    Args:
        model_name: Name of the model (e.g., "llama3.1:8b")
        
    Returns:
        Context size in tokens
    """
    model_lower = model_name.lower()
    for size_key, ctx_value in MODEL_CTX_SIZES.items():
        if size_key in model_lower:
            return ctx_value
    return 8192  # Default


def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    timeout: Optional[int] = None,
    json_mode: bool = False,
) -> Union[ChatOllama, ChatOpenAI, ChatAnthropic]:
    """
    Create an LLM instance based on the provider.
    
    Supports Ollama (local), OpenAI and Anthropic providers with
    consistent configuration handling.
    
    Args:
        provider: 'ollama' or 'openai' (default from settings.LLM_PROVIDER)
        model: Model name (default from settings based on provider)
        temperature: Temperature for generation (default from settings)
        timeout: Request timeout in seconds (default from settings)
        json_mode: If True, configure LLM for JSON output (Ollama only)
        
    Returns:
        Configured LangChain Chat model (ChatOllama, ChatOpenAI or ChatAnthropic)
        
    Raises:
        ValueError: If provider is unknown or required API key is missing
    """
    _provider = provider or getattr(settings, 'LLM_PROVIDER', 'ollama')
    _temperature = temperature if temperature is not None else settings.TEMPERATURE
    _timeout = timeout or settings.REQUEST_TIMEOUT
    
    if _provider == "openai":
        _model = model or settings.OPENAI_MODEL
        
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
        
        openai_kwargs = {
            "model": _model,
            "timeout": _timeout,
            "api_key": settings.OPENAI_API_KEY,
        }

        if settings.OPENAI_BASE_URL:
            openai_kwargs["base_url"] = settings.OPENAI_BASE_URL

        if json_mode:
            openai_kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}

        llm = ChatOpenAI(**openai_kwargs)
        llm.model_kwargs["temperature"] = _temperature
        logger.info(f"Creating ChatOpenAI with model: {_model} (temperature={_temperature}, json_mode={json_mode})")
        return llm
    
    elif _provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is required for Anthropic provider")
        
        anthropic_kwargs = {
            "model": model or getattr(settings, 'ANTHROPIC_MODEL', 'claude-sonnet-4-6'),
            "temperature": _temperature,
            "timeout": _timeout,
            "api_key": settings.ANTHROPIC_API_KEY,
        }
        
        logger.info(f"Creating ChatAnthropic with model: {anthropic_kwargs['model']} (temperature={_temperature})")
        return ChatAnthropic(**anthropic_kwargs)
    
    else:  # Ollama (default)
        _model = model or settings.OLLAMA_MODEL
        ctx_size = get_context_size(_model)
        
        ollama_kwargs = {
            "model": _model,
            "base_url": settings.OLLAMA_BASE_URL,
            "temperature": _temperature,
            "num_ctx": ctx_size,
            "timeout": _timeout,
            "keep_alive": settings.OLLAMA_KEEP_ALIVE,
            "seed": 42,
        }
        
        # JSON mode for structured output
        if json_mode:
            ollama_kwargs["format"] = "json"
        
        logger.info(f"Creating ChatOllama with model: {_model} (ctx_size={ctx_size}, temperature={_temperature}, seed=42)")
        return ChatOllama(**ollama_kwargs)


def create_json_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> Union[ChatOllama, ChatOpenAI]:
    """
    Create an LLM configured for JSON output.
    
    Convenience wrapper for create_llm with json_mode=True.
    
    Args:
        provider: 'ollama' or 'openai'
        model: Model name
        
    Returns:
        LLM configured for JSON output
    """
    return create_llm(provider=provider, model=model, json_mode=True)
