"""
Vereinfachtes ARES Interface für direkte RAG-Evaluation
======================================================

Eine einfache Funktion für die Evaluation Ihres ReactAgent.
"""

import logging
from typing import Dict, Any, List, Optional

from src.agent.react_agent import create_react_agent
from src.evaluation import EvaluationRunner, create_default_test_cases

logger = logging.getLogger(__name__)


def quick_rag_evaluation(questions: Optional[List[str]] = None, 
                        save_results: bool = True) -> Dict[str, Any]:
    """
    Schnelle ARES-Evaluation Ihres RAG-Chatbots.
    
    Args:
        questions: Optional Liste von Fragen
        save_results: Ob Ergebnisse gespeichert werden sollen
        
    Returns:
        Dictionary mit Evaluations-Ergebnissen
    """
    try:
        logger.info("🎯 Starte schnelle RAG-Evaluation...")
        
        # ReactAgent erstellen
        agent = create_react_agent()
        logger.info("✅ ReactAgent initialisiert")
        
        # Evaluation Runner
        runner = EvaluationRunner(agent=agent)
        
        if questions:
            # Eigene Fragen verwenden
            from src.evaluation.test_cases import TestCase
            test_cases = []
            for i, question in enumerate(questions):
                test_case = TestCase(
                    id=f"custom_{i+1}",
                    question=question,
                    category="custom",
                    difficulty="medium"
                )
                test_cases.append(test_case)
        else:
            # Standard WiSo-Testfälle
            test_cases = create_default_test_cases()
        
        # Evaluation durchführen
        results = runner.run_complete_evaluation(
            test_cases=test_cases,
            save_results=save_results
        )
        
        # Zusammenfassung loggen
        stats = results.get("statistics", {})
        logger.info(f"📊 Evaluation abgeschlossen: {stats.get('success_rate', 0):.1%} Erfolgsrate")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ RAG-Evaluation fehlgeschlagen: {e}")
        return {"error": str(e)}


def evaluate_rag_question(question: str) -> Dict[str, Any]:
    """
    Evaluiere eine einzelne Frage mit ARES.
    
    Args:
        question: Die zu evaluierende Frage
        
    Returns:
        Dictionary mit Antwort und ARES-Bewertung
        
    Example:
        result = evaluate_rag_question("Welche Master-Programme bietet die WiSo-Fakultät?")
        print(f"Antwort: {result['answer']}")
        print(f"ARES-Score: {result['ares_score']}")
    """
    try:
        logger.info(f"🔍 Evaluiere: {question}")
        
        # ReactAgent erstellen
        agent = create_react_agent()
        runner = EvaluationRunner(agent=agent)
        
        # Evaluation durchführen
        result = runner.run_single_evaluation(question)
        
        # Vereinfachte Antwort
        response = result.get('response', {})
        evaluation = result.get('evaluation', {})
        
        simplified_result = {
            "question": question,
            "answer": response.get('answer', 'Keine Antwort'),
            "sources": response.get('source_documents', []),
            "ares_score": evaluation.get('overall_score', 0.0),
            "context_relevance": evaluation.get('context_relevance', 0.0),
            "answer_relevance": evaluation.get('answer_relevance', 0.0),
            "answer_faithfulness": evaluation.get('answer_faithfulness', 0.0),
            "timestamp": result.get('timestamp')
        }
        
        logger.info(f"✅ Evaluation abgeschlossen (Score: {simplified_result['ares_score']:.3f})")
        return simplified_result
        
    except Exception as e:
        logger.error(f"❌ Frage-Evaluation fehlgeschlagen: {e}")
        return {
            "question": question,
            "error": str(e),
            "answer": None,
            "ares_score": 0.0
        }


def batch_evaluate_rag(questions_and_expected: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Evaluiere mehrere Fragen mit erwarteten Antworten.
    
    Args:
        questions_and_expected: Liste von Dicts mit 'question' und optional 'expected_answer'
        
    Returns:
        Batch-Evaluations-Ergebnisse
        
    Example:
        questions = [
            {"question": "Welche Master-Programme gibt es?", "expected_answer": "Economics, Business..."},
            {"question": "Wie bewerbe ich mich?"}
        ]
        results = batch_evaluate_rag(questions)
    """
    try:
        logger.info(f"📋 Starte Batch-Evaluation mit {len(questions_and_expected)} Fragen...")
        
        # ReactAgent erstellen  
        agent = create_react_agent()
        runner = EvaluationRunner(agent=agent)
        
        # TestCases erstellen
        from src.evaluation.test_cases import TestCase
        test_cases = []
        
        for i, item in enumerate(questions_and_expected):
            test_case = TestCase(
                id=f"batch_{i+1}",
                question=item["question"],
                category="batch_evaluation",
                expected_answer=item.get("expected_answer"),
                difficulty="medium"
            )
            test_cases.append(test_case)
        
        # Evaluation durchführen
        results = runner.run_complete_evaluation(
            test_cases=test_cases,
            save_results=True
        )
        
        logger.info("✅ Batch-Evaluation abgeschlossen")
        return results
        
    except Exception as e:
        logger.error(f"❌ Batch-Evaluation fehlgeschlagen: {e}")
        return {"error": str(e)}


# Convenience-Funktionen für häufige Use Cases
def evaluate_wiso_chatbot() -> Dict[str, Any]:
    """Evaluiere mit Standard WiSo-Testfällen."""
    return quick_rag_evaluation()


def evaluate_custom_questions(*questions) -> Dict[str, Any]:
    """Evaluiere mit eigenen Fragen."""
    return quick_rag_evaluation(list(questions))


# Für einfachste Nutzung
def ares_score(question: str) -> float:
    """
    Bekomme nur den ARES-Score für eine Frage.
    
    Returns:
        Float zwischen 0.0 und 1.0
    """
    result = evaluate_rag_question(question)
    return result.get('ares_score', 0.0)