"""
ARES-based RAG Evaluation System
================================

Echte ARES Framework Integration für die Evaluation von RAG-Systemen.
Verwendet das Stanford ARES Framework für automatisierte RAG-Bewertung.
"""

from .ares_evaluator import ARESEvaluator
from .test_cases import TestCase, load_test_cases, create_default_test_cases
from .evaluation_runner import EvaluationRunner, quick_evaluation
from .simple_rag_evaluation import evaluate_rag_question, ares_score, quick_rag_evaluation
from .results_manager import EvaluationResultsManager

__all__ = [
    'ARESEvaluator',
    'TestCase',
    'load_test_cases',
    'create_default_test_cases',
    'EvaluationRunner',
    'quick_evaluation',
    'evaluate_rag_question',
    'ares_score', 
    'quick_rag_evaluation',
    'EvaluationResultsManager'
]