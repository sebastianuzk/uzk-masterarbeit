#!/usr/bin/env python3
"""
Echte ARES Evaluation für WiSo-RAG-Chatbot
==========================================

Evaluiert den tatsächlichen ReactAgent mit ARES Framework.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.react_agent import create_react_agent
from src.evaluation import ARESEvaluator, EvaluationRunner, create_default_test_cases

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def evaluate_real_rag_chatbot():
    """
    Hauptfunktion für echte RAG-Chatbot Evaluation.
    """
    print("🎯 Echte WiSo-RAG-Chatbot Evaluation mit ARES")
    print("=" * 50)
    
    try:
        # 1. Echten ReactAgent erstellen
        logger.info("🤖 Initialisiere echten ReactAgent...")
        agent = create_react_agent()
        logger.info("✅ ReactAgent erfolgreich initialisiert")
        
        # 2. ARES Evaluation Runner erstellen
        logger.info("📊 Initialisiere ARES Evaluation Runner...")
        runner = EvaluationRunner(agent=agent)
        logger.info("✅ EvaluationRunner bereit")
        
        # 3. Testfälle laden
        test_cases = create_default_test_cases()
        logger.info(f"📋 {len(test_cases)} WiSo-Testfälle geladen")
        
        print(f"\n📝 Evaluiere folgende Testfälle:")
        for i, tc in enumerate(test_cases, 1):
            print(f"  {i}. [{tc.category}] {tc.question[:60]}...")
        
        # 4. Vollständige Evaluation durchführen
        print(f"\n🚀 Starte echte ARES-Evaluation...")
        results = runner.run_complete_evaluation(
            test_cases=test_cases,
            save_results=True
        )
        
        # 5. Ergebnisse anzeigen
        print_evaluation_results(results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Evaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None


def evaluate_single_question(question: str):
    """
    Evaluiere eine einzelne Frage mit dem echten ReactAgent.
    
    Args:
        question: Die zu evaluierende Frage
    """
    try:
        print(f"\n🔍 Einzelevaluation: {question}")
        
        # ReactAgent erstellen
        agent = create_react_agent()
        runner = EvaluationRunner(agent=agent)
        
        # Evaluation durchführen
        result = runner.run_single_evaluation(question)
        
        print(f"\n📝 Frage: {question}")
        print(f"🤖 Antwort: {result.get('response', {}).get('answer', 'Keine Antwort')}")
        
        evaluation = result.get('evaluation', {})
        if evaluation:
            print(f"\n📊 ARES Bewertung:")
            for metric, score in evaluation.items():
                if isinstance(score, (int, float)):
                    print(f"  {metric}: {score:.3f}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Einzelevaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None


def print_evaluation_results(results):
    """Zeige Evaluations-Ergebnisse übersichtlich an."""
    if not results:
        print("❌ Keine Ergebnisse verfügbar")
        return
    
    stats = results.get("statistics", {})
    
    print(f"\n🎉 Evaluation abgeschlossen!")
    print(f"📊 Ergebnisse:")
    print(f"  Testfälle gesamt: {stats.get('total_test_cases', 0)}")
    print(f"  Erfolgreich: {stats.get('successful_responses', 0)}")
    print(f"  Fehlgeschlagen: {stats.get('failed_responses', 0)}")
    print(f"  Erfolgsrate: {stats.get('success_rate', 0):.1%}")
    print(f"  Dauer: {stats.get('duration_seconds', 0):.1f}s")
    
    # ARES Metriken
    ares_metrics = stats.get('ares_metrics', {})
    if ares_metrics:
        print(f"\n📈 ARES Metriken:")
        for metric, score in ares_metrics.items():
            if isinstance(score, (int, float)):
                # Bewertung hinzufügen
                rating = get_score_rating(score)
                print(f"  {metric}: {score:.3f} {rating}")
    
    print(f"\n💾 Detaillierte Ergebnisse gespeichert")


def get_score_rating(score):
    """Konvertiere numerischen Score zu Bewertung."""
    if score >= 0.8:
        return "🟢 Sehr gut"
    elif score >= 0.6:
        return "🟡 Gut"
    elif score >= 0.4:
        return "🟠 Mäßig"
    else:
        return "🔴 Verbesserungsbedarf"


def interactive_mode():
    """Interaktiver Modus für Fragen."""
    print("\n💬 Interaktiver Modus (Eingabe 'exit' zum Beenden)")
    
    while True:
        try:
            question = input("\n❓ Ihre Frage: ").strip()
            
            if question.lower() in ['exit', 'quit', 'ende']:
                print("👋 Auf Wiedersehen!")
                break
            
            if not question:
                print("⚠️ Bitte geben Sie eine Frage ein")
                continue
            
            evaluate_single_question(question)
            
        except KeyboardInterrupt:
            print("\n👋 Auf Wiedersehen!")
            break
        except Exception as e:
            print(f"❌ Fehler: {e}")


def main():
    """Hauptfunktion."""
    if len(sys.argv) > 1:
        # Kommandozeilen-Argument als Frage
        question = " ".join(sys.argv[1:])
        evaluate_single_question(question)
    else:
        # Menü anzeigen
        print("\n🎯 WiSo-RAG-Chatbot ARES Evaluation")
        print("Wählen Sie eine Option:")
        print("1. Vollständige Evaluation (alle Testfälle)")
        print("2. Einzelne Frage evaluieren")
        print("3. Interaktiver Modus")
        
        try:
            choice = input("\nIhre Wahl (1-3): ").strip()
            
            if choice == "1":
                evaluate_real_rag_chatbot()
            elif choice == "2":
                question = input("Ihre Frage: ").strip()
                if question:
                    evaluate_single_question(question)
            elif choice == "3":
                interactive_mode()
            else:
                print("❌ Ungültige Auswahl")
                
        except KeyboardInterrupt:
            print("\n👋 Auf Wiedersehen!")


if __name__ == "__main__":
    main()