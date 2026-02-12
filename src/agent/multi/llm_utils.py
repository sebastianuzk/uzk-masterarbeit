"""
Shared LLM utilities for the multi-agent system.

This module re-exports the centralized LLM factory for backward compatibility.
New code should import directly from src.agent.llm_factory.
"""

from src.agent.llm_factory import create_llm, create_json_llm, get_context_size, MODEL_CTX_SIZES

__all__ = ["create_llm", "create_json_llm", "get_context_size", "MODEL_CTX_SIZES"]
