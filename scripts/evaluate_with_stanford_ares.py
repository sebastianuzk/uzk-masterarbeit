#!/usr/bin/env python3
"""
Echte Stanford ARES Evaluation für ReactAgent
============================================

Verwendet das authentische Stanford ARES Framework gemäß offizieller Dokumentation.
"""

import sys
import logging
import os
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from src.agent.react_agent import create_react_agent
from src.evaluation.stanford_ares_integration import (
    StanfordARESEvaluator, 
    stanford_ares_evaluate,
    evaluate_react_agent_with_stanford_ares
)
from src.evaluation.test_cases import create_default_test_cases, auto_load_test_cases
from src.evaluation.results_manager import EvaluationResultsManager

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_ares_setup():
    """Prüfe ARES Setup und lokales/Cloud LLM Setup."""
    print("🔍 Prüfe Evaluation Setup...")
    
    # Lokales Ollama LLM prüfen
    print("\n🏠 Lokales Ollama LLM:")
    from config.settings import settings
    import requests
    
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            print(f"✅ Ollama Server erreichbar: {settings.OLLAMA_BASE_URL}")
            
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            if any(model.startswith(settings.OLLAMA_MODEL) for model in model_names):
                print(f"✅ Ollama Modell verfügbar: {settings.OLLAMA_MODEL}")
                print("💡 Empfehlung: Verwenden Sie lokales Ollama für Evaluation")
                return True
            else:
                print(f"⚠️ Ollama Modell '{settings.OLLAMA_MODEL}' nicht gefunden")
                print(f"💡 Installieren Sie mit: ollama pull {settings.OLLAMA_MODEL}")
        else:
            print(f"❌ Ollama Server nicht erreichbar: {settings.OLLAMA_BASE_URL}")
    except Exception as e:
        print(f"❌ Ollama Verbindung fehlgeschlagen: {e}")
        print("💡 Starten Sie Ollama mit: ollama serve")
    
    # Stanford ARES Package prüfen (optional)
    print("\n☁️ Stanford ARES Framework:")
    try:
        from ares import ARES
        print("✅ Stanford ARES Framework installiert")
    except ImportError as e:
        print(f"⚠️ Stanford ARES Framework NICHT installiert: {e}")
        print("💡 Installieren Sie mit: pip install ares-ai")
    
    # API Keys prüfen (optional für Cloud LLM)
    print("\n🔑 Cloud API Keys:")
    api_keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "TOGETHER_API_KEY": os.getenv("TOGETHER_API_KEY"), 
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    }
    
    available_keys = [k for k, v in api_keys.items() if v]
    missing_keys = [k for k, v in api_keys.items() if not v]
    
    if available_keys:
        print(f"✅ Verfügbare API Keys: {available_keys}")
    if missing_keys:
        print(f"⚠️ Fehlende API Keys: {missing_keys}")
        print("💡 Nur für Cloud LLM benötigt: export OPENAI_API_KEY=<your-key>")
    
    return True  # Lokales Ollama ist primäre Option


def evaluate_with_csv_testcases():
    """Evaluiere ReactAgent mit CSV-basierten Testfällen (alle 40 Fragen)."""
    print("\n📊 CSV-basierte ARES Evaluation (Vollständiges Testset)")
    print("=" * 60)
    
    try:
        # ReactAgent erstellen
        logger.info("🤖 Initialisiere ReactAgent...")
        agent = create_react_agent()
        logger.info("✅ ReactAgent bereit")
        
        # CSV-Testfälle laden
        print("\n📄 Lade CSV-Testfälle...")
        test_cases = auto_load_test_cases()
        questions = [tc.question for tc in test_cases]
        
        print(f"📝 Gefunden: {len(questions)} Testfragen aus CSV")
        print("\n🎯 Kategorien:")
        
        # Kategorie-Statistik
        categories = {}
        for tc in test_cases:
            categories[tc.category] = categories.get(tc.category, 0) + 1
        
        for cat, count in categories.items():
            print(f"  • {cat}: {count} Fragen")
        
        # Nutzer fragen nach Anzahl
        print(f"\n🔢 Möchten Sie alle {len(questions)} Fragen evaluieren?")
        print("   1. Alle Fragen (vollständige Evaluation)")
        print("   2. Erste 10 Fragen (Demo)")
        print("   3. Erste 5 Fragen (Quick-Test)")
        print("   4. Eigene Anzahl wählen")
        
        choice = input("\nIhre Wahl (1-4): ").strip()
        
        if choice == "1":
            eval_questions = questions
            print(f"🚀 Evaluiere alle {len(questions)} Fragen...")
        elif choice == "2":
            eval_questions = questions[:10]
            print(f"🚀 Evaluiere erste 10 Fragen...")
        elif choice == "3":
            eval_questions = questions[:5]
            print(f"🚀 Evaluiere erste 5 Fragen...")
        elif choice == "4":
            try:
                num = int(input(f"Anzahl Fragen (1-{len(questions)}): "))
                num = max(1, min(num, len(questions)))
                eval_questions = questions[:num]
                print(f"🚀 Evaluiere erste {num} Fragen...")
            except ValueError:
                eval_questions = questions[:5]
                print("🚀 Ungültige Eingabe, evaluiere erste 5 Fragen...")
        else:
            eval_questions = questions[:5]
            print("🚀 Standard: Evaluiere erste 5 Fragen...")
        
        print(f"\n📋 Evaluierte Fragen:")
        for i, q in enumerate(eval_questions[:5], 1):
            print(f"  {i}. {q[:80]}{'...' if len(q) > 80 else ''}")
        if len(eval_questions) > 5:
            print(f"  ... und {len(eval_questions) - 5} weitere Fragen")
        
        # Lokale Ollama ARES-style Evaluation
        print(f"\n🚀 Starte CSV-basierte Ollama ARES Evaluation...")
        results = evaluate_react_agent_with_stanford_ares(
            agent=agent,
            questions=eval_questions,
            method="ollama"
        )
        
        # Ergebnisse anzeigen
        print_stanford_ares_results(results)
        
        # Automatische Speicherung
        if results:
            print("\n💾 Speichere Evaluation-Ergebnisse...")
            results_manager = EvaluationResultsManager()
            saved_files = results_manager.save_evaluation_results(
                results=results,
                evaluation_type="csv_ollama_ares",
                model_name="llama3.1:8b",
                test_source=f"csv_{len(eval_questions)}_questions"
            )
            
            if saved_files:
                print(f"✅ Ergebnisse gespeichert in {len(saved_files)} Formaten:")
                for format_type, path in saved_files.items():
                    print(f"  📄 {format_type.upper()}: {path.name}")
            else:
                print("⚠️ Speicherung fehlgeschlagen")
        
        # Zusätzliche CSV-spezifische Statistiken
        if results and 'scores' in results:
            print(f"\n📊 CSV-Testset Analyse:")
            print(f"  📄 Quelle: CSV-Datei (ARES-Testset.CSV)")
            print(f"  🎯 Evaluierte Fragen: {len(eval_questions)}/{len(questions)}")
            print(f"  📈 Durchschnittliche Performance: {results.get('overall_score', 'N/A')}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ CSV-basierte Evaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None

def evaluate_with_ollama():
    """Evaluiere ReactAgent mit lokalem Ollama LLM (ARES-style)."""
    print("\n🏠 Lokales Ollama ARES-style Evaluation")
    print("=" * 50)
    
    try:
        # ReactAgent erstellen
        logger.info("🤖 Initialisiere ReactAgent...")
        agent = create_react_agent()
        logger.info("✅ ReactAgent bereit")
        
        # Test-Fragen (weniger für Demo)
        test_cases = create_default_test_cases()[:3]  # Nur erste 3 für Demo
        questions = [tc.question for tc in test_cases]
        
        print(f"📝 Evaluiere {len(questions)} Fragen mit lokalem Ollama:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q[:60]}...")
        
        # Lokale Ollama ARES-style Evaluation
        print(f"\n🚀 Starte lokale Ollama ARES-style Evaluation...")
        results = evaluate_react_agent_with_stanford_ares(
            agent=agent,
            questions=questions,
            method="ollama"
        )
        
        # Ergebnisse anzeigen
        print_stanford_ares_results(results)
        
        # Automatische Speicherung  
        if results:
            print("\n💾 Speichere Evaluation-Ergebnisse...")
            results_manager = EvaluationResultsManager()
            saved_files = results_manager.save_evaluation_results(
                results=results,
                evaluation_type="ollama_ares",
                model_name="llama3.1:8b", 
                test_source="default_3_questions"
            )
            
            if saved_files:
                print(f"✅ Ergebnisse gespeichert in {len(saved_files)} Formaten:")
                for format_type, path in saved_files.items():
                    print(f"  📄 {format_type.upper()}: {path.name}")
            else:
                print("⚠️ Speicherung fehlgeschlagen")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Ollama Evaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None

def evaluate_with_ues_idp():
    """Evaluiere ReactAgent mit Stanford ARES UES/IDP (Cloud LLM)."""
    print("\n☁️ Stanford ARES UES/IDP Evaluation (Cloud)")
    print("=" * 50)
    
    try:
        # ReactAgent erstellen
        logger.info("🤖 Initialisiere ReactAgent...")
        agent = create_react_agent()
        logger.info("✅ ReactAgent bereit")
        
        # Test-Fragen (weniger für Demo)
        test_cases = create_default_test_cases()[:3]  # Nur erste 3 für Demo
        questions = [tc.question for tc in test_cases]
        
        print(f"📝 Evaluiere {len(questions)} Fragen mit echtem Stanford ARES:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q[:60]}...")
        
        # Stanford ARES UES/IDP Evaluation
        print(f"\n🚀 Starte echte Stanford ARES UES/IDP Evaluation...")
        results = evaluate_react_agent_with_stanford_ares(
            agent=agent,
            questions=questions,
            method="ues_idp"
        )
        
        # Ergebnisse anzeigen
        print_stanford_ares_results(results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ UES/IDP Evaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None

def evaluate_with_ppi():
    """Evaluiere ReactAgent mit Stanford ARES PPI (Cloud LLM)."""
    print("\n☁️ Stanford ARES PPI Evaluation (Cloud)")
    print("=" * 50)
    
    try:
        # ReactAgent erstellen
        logger.info("🤖 Initialisiere ReactAgent...")
        agent = create_react_agent()
        logger.info("✅ ReactAgent bereit")
        
        # Test-Fragen (weniger für Demo)
        test_cases = create_default_test_cases()[:3]  # Nur erste 3 für Demo
        questions = [tc.question for tc in test_cases]
        
        print(f"📝 Evaluiere {len(questions)} Fragen mit PPI Methode:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q[:60]}...")
        
        # Stanford ARES PPI Evaluation
        print(f"\n🚀 Starte Stanford ARES PPI Evaluation...")
        results = evaluate_react_agent_with_stanford_ares(
            agent=agent,
            questions=questions,
            method="ppi"
        )
        
        # Ergebnisse anzeigen
        print_stanford_ares_results(results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ PPI Evaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None


def evaluate_with_ppi():
    """Evaluiere ReactAgent mit Stanford ARES PPI.""" 
    print("\n🎯 Stanford ARES PPI Evaluation")
    print("=" * 50)
    
    try:
        # ReactAgent erstellen
        agent = create_react_agent()
        
        # Test-Fragen
        test_cases = create_default_test_cases()[:2]  # Nur 2 für PPI Demo
        questions = [tc.question for tc in test_cases]
        
        print(f"📝 Evaluiere {len(questions)} Fragen mit Stanford ARES PPI:")
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q[:60]}...")
        
        # Stanford ARES PPI Evaluation
        print(f"\n🚀 Starte echte Stanford ARES PPI Evaluation...")
        results = evaluate_react_agent_with_stanford_ares(
            agent=agent,
            questions=questions, 
            method="ppi"
        )
        
        # Ergebnisse anzeigen
        print_stanford_ares_results(results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ PPI Evaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None


def evaluate_single_question_stanford_ares(question: str):
    """Evaluiere eine einzelne Frage mit Stanford ARES."""
    print(f"\n🔍 Stanford ARES Einzelevaluation")
    print(f"📝 Frage: {question}")
    
    try:
        # ReactAgent erstellen
        agent = create_react_agent()
        
        # Agent ausführen
        result = agent.invoke({"input": question})
        answer = result.get("output", "")
        context = " ".join(result.get("source_documents", []))
        
        print(f"🤖 Antwort: {answer}")
        print(f"📚 Kontext: {context[:100]}...")
        
        # Stanford ARES UES/IDP 
        print(f"\n🚀 Stanford ARES Evaluation...")
        results = stanford_ares_evaluate(
            queries=[question],
            responses=[answer], 
            contexts=[context],
            method="ues_idp"
        )
        
        print_stanford_ares_results(results)
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Einzelevaluation fehlgeschlagen: {e}")
        print(f"❌ Fehler: {e}")
        return None


def print_stanford_ares_results(results):
    """Zeige Stanford ARES Ergebnisse an."""
    if not results:
        print("❌ Keine Ergebnisse verfügbar")
        return
    
    if "error" in results:
        print(f"❌ Fehler: {results['error']}")
        return
    
    print(f"\n📊 Stanford ARES Ergebnisse:")
    print(f"  Evaluation Typ: {results.get('evaluation_type', 'unknown')}")
    print(f"  Model: {results.get('model_used', 'unknown')}")
    print(f"  Samples: {results.get('total_samples', 0)}")
    
    # Average Scores
    avg_scores = results.get('average_scores', {})
    if avg_scores:
        print(f"\n📈 Durchschnittliche ARES Scores:")
        for metric, score in avg_scores.items():
            if isinstance(score, (int, float)):
                rating = get_stanford_ares_rating(score)
                print(f"  {metric}: {score:.3f} {rating}")
    
    # Individual Scores
    individual_scores = results.get('individual_scores', {})
    if individual_scores:
        print(f"\n📋 Individuelle Scores:")
        for metric, scores in individual_scores.items():
            if scores:
                print(f"  {metric}: {scores}")


def get_stanford_ares_rating(score):
    """Bewerte Stanford ARES Score."""
    if score >= 0.8:
        return "🟢 Exzellent"
    elif score >= 0.6:
        return "🟡 Gut" 
    elif score >= 0.4:
        return "🟠 Mäßig"
    else:
        return "🔴 Schlecht"


def interactive_stanford_ares():
    """Interaktive Stanford ARES Evaluation."""
    print("\n💬 Interaktive Stanford ARES Evaluation")
    
    while True:
        try:
            question = input("\n❓ Ihre Frage (oder 'exit'): ").strip()
            
            if question.lower() in ['exit', 'quit', 'ende']:
                print("👋 Auf Wiedersehen!")
                break
            
            if not question:
                print("⚠️ Bitte geben Sie eine Frage ein")
                continue
            
            evaluate_single_question_stanford_ares(question)
            
        except KeyboardInterrupt:
            print("\n👋 Auf Wiedersehen!")
            break
        except Exception as e:
            print(f"❌ Fehler: {e}")


def main():
    """Hauptfunktion."""
    print("🎯 Echte Stanford ARES Framework Evaluation")
    print("=" * 55)
    
    # Setup prüfen
    if not check_ares_setup():
        print("\n❌ Stanford ARES Setup unvollständig!")
        print("📖 Siehe: https://ares-ai.vercel.app/installation.html")
        return 1
    
    if len(sys.argv) > 1:
        # Kommandozeilen-Argument als Frage
        question = " ".join(sys.argv[1:])
        evaluate_single_question_stanford_ares(question)
    else:
        # Menü anzeigen
        print("\nWählen Sie eine Option:")
        print("1. CSV-basierte Evaluation (40 WiSo-Fragen) 📊")
        print("2. Lokale Ollama Evaluation (3 Demo-Fragen) 🏠")
        print("3. Cloud UES/IDP Evaluation (benötigt API Key) ☁️")
        print("4. Cloud PPI Evaluation (benötigt API Key) ☁️")
        print("5. Einzelne Frage evaluieren")
        print("6. Interaktiver Modus")
        
        try:
            choice = input("\nIhre Wahl (1-6): ").strip()
            
            if choice == "1":
                evaluate_with_csv_testcases()
            elif choice == "2":
                evaluate_with_ollama()
            elif choice == "3":
                evaluate_with_ues_idp()
            elif choice == "4":
                evaluate_with_ppi() 
            elif choice == "5":
                question = input("Ihre Frage: ").strip()
                if question:
                    evaluate_single_question_stanford_ares(question)
            elif choice == "6":
                interactive_stanford_ares()
            else:
                print("❌ Ungültige Auswahl")
                
        except KeyboardInterrupt:
            print("\n👋 Auf Wiedersehen!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())