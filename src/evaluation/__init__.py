"""
RAG Evaluation Pipeline
======================

Einfache und erweiterte ARES-basierte Evaluation für den RAG-Chatbot.

SIMPLE API (empfohlen für Einsteiger):
- test_real_chatbot: Direkte Integration mit vorhandenem Chatbot
- generate_test_cases: Automatische Testfall-Generierung
- run_complete_evaluation: Vollständiger Evaluation-Workflow

ADVANCED API (für erweiterte Anwendungen):
- ares_evaluator: Detaillierte ARES-Implementation
- metrics: Umfangreiche Metriken-Sammlung
- pipeline: Konfigurierbare Evaluation-Pipeline
"""

# Simple API (empfohlen)
from .test_real_chatbot import SimpleChatbotEvaluator, SimpleTestCase, create_sample_test_cases
from .generate_test_cases import TestCaseGenerator

# Advanced API - ARESEvaluator temporarily commented out until implementation is complete
# from .ares_evaluator import ARESEvaluator
# from .metrics import RAGMetrics
# from .test_cases import load_test_cases, TestCase
# from .pipeline import EvaluationPipeline

__all__ = [
    # Simple API
    'SimpleChatbotEvaluator', 'SimpleTestCase', 'create_sample_test_cases', 'TestCaseGenerator',
    # Advanced API - temporarily commented out
    # 'ARESEvaluator', 'RAGMetrics', 'load_test_cases', 'TestCase', 'EvaluationPipeline'
]