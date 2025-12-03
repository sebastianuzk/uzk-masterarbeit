"""
Evaluation Module for Tool Usage Testing

This module provides the core evaluation logic for assessing AI agent tool usage.
It defines data structures for representing tool calls and gold standards,
as well as evaluation functions that determine task success.

Part of Master's Thesis: AI-Powered University Assistant Evaluation Framework
"""

from .evaluation import (
    ToolCall,
    GoldStandard,
    EvaluationResult,
    evaluate_tool_run,
    ArgumentMatchMode,
)

__all__ = [
    "ToolCall",
    "GoldStandard", 
    "EvaluationResult",
    "evaluate_tool_run",
    "ArgumentMatchMode",
]
