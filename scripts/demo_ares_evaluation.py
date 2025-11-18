#!/usr/bin/env python3
"""
Demo Script für Stanford ARES Framework Integration
==================================================

Demonstriert die Nutzung des neuen ARES-basierten Evaluations-Systems.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.evaluation.ares_evaluator import ARESEvaluator
from src.evaluation.evaluation_runner import EvaluationRunner, quick_evaluation
from src.evaluation.test_cases import load_test_cases, create_default_test_cases

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockWiSoAgent:
    """
    Mock-Agent für Demonstration der ARES-Evaluation.
    """
    
    def __init__(self):
        self.knowledge_base = {
            "master": "Die WiSo-Fakultät bietet Master-Programme in Economics, Business Administration, Sociology und weitere spezialisierte Programme an.",
            "zulassung": "Für Master-Programme benötigen Sie einen relevanten Bachelor-Abschluss mit mindestens 2.5 Durchschnitt sowie Sprachkenntnisse.",
            "forschung": "Die WiSo-Fakultät forscht in Bereichen wie empirische Wirtschaftsforschung, Verhaltensökonomie und Soziologie.",
            "career": "Der Career Service bietet Workshops, Networking-Events und Praktikumsvermittlung für WiSo-Studierende.",
            "international": "Es gibt Austauschprogramme mit über 50 Partnerhochschulen weltweit sowie Double-Degree-Programme.",
            "praktikum": "Praktika werden über das Career Center vermittelt, mit Partnern wie McKinsey, Deutsche Bank und lokalen Unternehmen.",
            "software": "Studierende haben Zugang zu STATA, R, Python, SPSS und anderen Analysetools über die Fakultät."
        }
    
    def invoke(self, inputs):
        """LangChain-style invoke method."""
        question = inputs.get("input", "").lower()
        
        # Einfache Keyword-basierte Antwort
        answer = "Entschuldigung, ich habe keine spezifischen Informationen zu Ihrer Frage."
        contexts = []
        
        for keyword, response in self.knowledge_base.items():
            if keyword in question:
                answer = response
                contexts = [f"Kontext aus WiSo-Datenbank: {response[:100]}..."]
                break
        
        return {
            "output": answer,
            "source_documents": contexts,
            "metadata": {
                "confidence": 0.8,
                "sources": ["WiSo-Fakultät Webseite"],
                "query_type": "information_retrieval"
            }
        }


def demo_single_evaluation():
    """Demonstriere Evaluation einer einzelnen Frage."""
    logger.info("🔍 Demo: Einzelne Frage evaluieren")
    
    # Mock Agent erstellen
    agent = MockWiSoAgent()
    
    # ARES Evaluator direkt nutzen
    evaluator = ARESEvaluator()
    
    # Test-Frage
    question = "Welche Master-Programme bietet die WiSo-Fakultät an?"
    
    # Agent-Antwort abrufen
    response = agent.invoke({"input": question})
    answer = response.get("output", "")
    contexts = response.get("source_documents", [])
    
    print(f"📝 Frage: {question}")
    print(f"🤖 Antwort: {answer}")
    print(f"📚 Kontexte: {contexts}")
    
    # ARES Evaluation durchführen
    try:
        evaluation = evaluator.evaluate_single(
            query=question,
            response=answer,
            contexts=contexts
        )
        
        print("📊 ARES Evaluation:")
        for metric, score in evaluation.items():
            print(f"  {metric}: {score}")
            
    except Exception as e:
        logger.error(f"❌ ARES Evaluation fehlgeschlagen: {e}")
        print("⚠️ ARES Framework nicht verfügbar - Mock-Scores werden verwendet")
        
        # Fallback Mock-Evaluation
        evaluation = {
            "context_relevance": 0.85,
            "answer_relevance": 0.78,
            "answer_faithfulness": 0.82
        }
        
        print("📊 Mock Evaluation:")
        for metric, score in evaluation.items():
            print(f"  {metric}: {score:.2f}")


def demo_batch_evaluation():
    """Demonstriere Batch-Evaluation mit mehreren Testfällen."""
    logger.info("📋 Demo: Batch-Evaluation")
    
    # Mock Agent erstellen
    agent = MockWiSoAgent()
    
    # Runner erstellen
    runner = EvaluationRunner(agent=agent)
    
    # Testfälle laden
    test_cases = create_default_test_cases()[:3]  # Nur erste 3 für Demo
    
    print(f"🧪 Evaluiere {len(test_cases)} Testfälle:")
    for tc in test_cases:
        print(f"  - {tc.id}: {tc.question[:50]}...")
    
    # Evaluation durchführen
    try:
        results = runner.run_complete_evaluation(
            test_cases=test_cases,
            save_results=False  # Für Demo nicht speichern
        )
        
        print("\n📊 Ergebnisse:")
        stats = results.get("statistics", {})
        print(f"  Erfolgreich: {stats.get('successful_responses', 0)}/{stats.get('total_test_cases', 0)}")
        print(f"  Erfolgsrate: {stats.get('success_rate', 0):.2%}")
        print(f"  Dauer: {stats.get('duration_seconds', 0):.2f}s")
        
        # ARES Metriken anzeigen
        if "ares_metrics" in stats:
            print("  ARES Metriken:")
            for metric, score in stats["ares_metrics"].items():
                print(f"    {metric}: {score:.2f}")
        
    except Exception as e:
        logger.error(f"❌ Batch-Evaluation fehlgeschlagen: {e}")


def demo_quick_evaluation():
    """Demonstriere Quick-Evaluation."""
    logger.info("⚡ Demo: Quick-Evaluation")
    
    agent = MockWiSoAgent()
    
    test_questions = [
        "Was sind die Zulassungsvoraussetzungen?",
        "Gibt es internationale Programme?",
        "Welche Software steht zur Verfügung?"
    ]
    
    print("🚀 Quick-Evaluation mit 3 Fragen")
    
    try:
        results = quick_evaluation(agent, test_questions)
        
        stats = results.get("statistics", {})
        print(f"✅ Abgeschlossen: {stats.get('success_rate', 0):.2%} Erfolgsrate")
        
    except Exception as e:
        logger.error(f"❌ Quick-Evaluation fehlgeschlagen: {e}")


def demo_test_case_management():
    """Demonstriere Testfall-Verwaltung."""
    logger.info("📝 Demo: Testfall-Verwaltung")
    
    # Standard-Testfälle erstellen
    test_cases = create_default_test_cases()
    
    print(f"📋 {len(test_cases)} Standard-Testfälle erstellt")
    
    # Kategorien anzeigen
    categories = set(tc.category for tc in test_cases)
    print(f"📂 Kategorien: {', '.join(sorted(categories))}")
    
    # Nach Schwierigkeit filtern
    easy_cases = [tc for tc in test_cases if tc.difficulty == "easy"]
    medium_cases = [tc for tc in test_cases if tc.difficulty == "medium"]
    hard_cases = [tc for tc in test_cases if tc.difficulty == "hard"]
    
    print(f"🟢 Einfach: {len(easy_cases)}")
    print(f"🟡 Mittel: {len(medium_cases)}")
    print(f"🔴 Schwer: {len(hard_cases)}")
    
    # Beispiel-Testfall anzeigen
    example = test_cases[0]
    print(f"\n📄 Beispiel-Testfall:")
    print(f"  ID: {example.id}")
    print(f"  Frage: {example.question}")
    print(f"  Kategorie: {example.category}")
    print(f"  Schwierigkeit: {example.difficulty}")


def main():
    """Hauptfunktion für Demo-Script."""
    print("🎯 Stanford ARES Framework Integration Demo")
    print("=" * 50)
    
    try:
        # Demos ausführen
        demo_test_case_management()
        print()
        
        demo_single_evaluation()
        print()
        
        demo_batch_evaluation()
        print()
        
        demo_quick_evaluation()
        print()
        
        print("✅ Alle Demos erfolgreich abgeschlossen!")
        print("\n💡 Nächste Schritte:")
        print("1. Echten RAG-Agent integrieren")
        print("2. ARES Framework konfigurieren")
        print("3. Umfangreichere Testfälle erstellen")
        print("4. Evaluation in CI/CD Pipeline einbinden")
        
    except Exception as e:
        logger.error(f"❌ Demo fehlgeschlagen: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())