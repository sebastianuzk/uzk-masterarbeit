"""
Shared LLM utilities for the multi-agent system.

This module provides common functionality for creating and configuring
LLM instances to avoid code duplication.
"""

from langchain_ollama import ChatOllama
from config.settings import settings


def create_llm(verbose: bool = False) -> ChatOllama:
    """
    Erstelle eine LLM-Instanz mit optimierten Einstellungen.
    
    Diese Funktion wird sowohl vom Orchestrator als auch von den
    spezialisierten Agenten verwendet, um eine konsistente LLM-Konfiguration
    zu gewährleisten.
    
    Args:
        verbose: Ob zusätzliche Ausgaben geloggt werden sollen
        
    Returns:
        Konfigurierte ChatOllama-Instanz
    """
    # Context-Size nach Modellgröße
    MODEL_CTX_SIZES = {
        "0.5b": 2048,
        "1b": 4096,
        "3b": 8192,
        "8b": 8192,
        "20b": 16384,
        "70b": 16384,
    }
    
    model_lower = settings.OLLAMA_MODEL.lower()
    ctx_size = 8192  # Standard
    for size_key, ctx_value in MODEL_CTX_SIZES.items():
        if size_key in model_lower:
            ctx_size = ctx_value
            break
    
    if verbose:
        print(f"🤖 Initialisiere ChatOllama mit Modell: {settings.OLLAMA_MODEL} (ctx_size={ctx_size})")
    
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.TEMPERATURE,
        num_ctx=ctx_size,
        timeout=settings.REQUEST_TIMEOUT,
        keep_alive=settings.OLLAMA_KEEP_ALIVE,
    )
