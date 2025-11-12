"""
Complete Chatbot Evaluation Runner
==================================

Vollständiger Workflow für die Chatbot-Evaluation:
1. Optional: Testfälle generieren aus gescrapten Dokumenten
2. Chatbot mit ARES-ähnlichen Metriken evaluieren
3. Ergebnisse analysieren und berichten
"""

import logging
import argparse
from pathlib import Path

# Imports für die Evaluation-Module
from src.evaluation.test_real_chatbot import SimpleChatbotEvaluator, create_sample_test_cases, SimpleTestCase
from src.evaluation.generate_test_cases import TestCaseGenerator


def load_test_cases_from_file(file_path: Path) -> list:
    """Lade Testfälle aus einer JSON-Datei."""
    import json
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    test_cases = []
    for tc_data in data['test_cases']:
        test_case = SimpleTestCase(
            id=tc_data['id'],
            question=tc_data['question'],
            category=tc_data['category'],
            expected_keywords=tc_data['expected_keywords']
        )
        test_cases.append(test_case)
    
    return test_cases


def main():
    """Hauptfunktion für die komplette Chatbot-Evaluation."""
    parser = argparse.ArgumentParser(description='Chatbot Evaluation mit ARES')
    parser.add_argument('--generate', action='store_true', 
                       help='Generiere neue Testfälle aus gescrapten Dokumenten')
    parser.add_argument('--test-file', type=str, 
                       help='Pfad zu custom Testfälle-Datei (JSON)')
    parser.add_argument('--output-dir', type=str, default='evaluation_results',
                       help='Ausgabeverzeichnis für Ergebnisse')
    parser.add_argument('--num-generated', type=int, default=8,
                       help='Anzahl zu generierender Testfälle (falls --generate)')
    
    args = parser.parse_args()
    
    # Logging setup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    print("🚀 COMPLETE CHATBOT EVALUATION")
    print("=" * 50)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # Schritt 1: Testfälle vorbereiten
    test_cases = []
    
    if args.generate:
        print("\n🎯 SCHRITT 1: Generiere neue Testfälle")
        print("-" * 30)
        
        generator = TestCaseGenerator()
        
        # Analysiere Dokumente und generiere Testfälle
        analysis = generator.analyze_scraped_documents()
        
        if analysis['topics_by_category']:
            logger.info("📊 Generiere Testfälle aus gescrapten Dokumenten...")
            doc_cases = generator.generate_test_cases_from_analysis(analysis, 2)
        else:
            logger.warning("⚠️ Keine Dokumente gefunden, verwende nur Templates")
            doc_cases = []
        
        # Template-basierte Testfälle
        template_cases = generator.generate_test_cases_from_templates(args.num_generated)
        
        # Kombiniere
        test_cases = doc_cases + template_cases
        
        # Speichere generierte Testfälle
        generated_file = output_dir / "evaluation_test_cases.json"
        generator.save_generated_test_cases(test_cases, generated_file)
        logger.info(f"💾 {len(test_cases)} Testfälle gespeichert in: {generated_file}")
        
    elif args.test_file:
        print(f"\n📋 SCHRITT 1: Lade Testfälle aus {args.test_file}")
        print("-" * 30)
        
        test_file = Path(args.test_file)
        if test_file.exists():
            test_cases = load_test_cases_from_file(test_file)
            logger.info(f"📋 {len(test_cases)} Testfälle geladen aus {test_file}")
        else:
            logger.error(f"❌ Testfälle-Datei nicht gefunden: {test_file}")
            print("💡 Verwende Standard-Testfälle stattdessen...")
            test_cases = create_sample_test_cases()
    
    else:
        print("\n📋 SCHRITT 1: Verwende Standard-Testfälle")
        print("-" * 30)
        test_cases = create_sample_test_cases()
        logger.info(f"📋 {len(test_cases)} Standard-Testfälle geladen")
    
    if not test_cases:
        logger.error("❌ Keine Testfälle verfügbar!")
        return
    
    # Schritt 2: Chatbot-Evaluation durchführen
    print(f"\n🤖 SCHRITT 2: Evaluiere Chatbot mit {len(test_cases)} Testfällen")
    print("-" * 30)
    
    evaluator = SimpleChatbotEvaluator()
    results_file = output_dir / "chatbot_evaluation_results.json"
    
    try:
        results = evaluator.evaluate_batch(test_cases, results_file)
        
        # Schritt 3: Erweiterte Analyse
        print(f"\n📊 SCHRITT 3: Erweiterte Ergebnisanalyse")
        print("-" * 30)
        
        # Kategorien-basierte Analyse
        category_stats = {}
        for result in results['detailed_results']:
            category = None
            # Finde Kategorie aus Testfall
            for tc in test_cases:
                if tc.id == result['test_id']:
                    category = tc.category
                    break
            
            if category:
                if category not in category_stats:
                    category_stats[category] = []
                category_stats[category].append(result['overall_score'])
        
        print("\n📈 Performance pro Kategorie:")
        for category, scores in category_stats.items():
            avg_score = sum(scores) / len(scores)
            print(f"   {category:12}: {avg_score:.3f} ({len(scores)} Tests)")
        
        # Performance-Analyse
        response_times = [r['response_time_ms'] for r in results['detailed_results']]
        if response_times:
            print(f"\n⚡ Response-Zeit Analyse:")
            print(f"   Schnellste:  {min(response_times)}ms")
            print(f"   Langsamste:  {max(response_times)}ms")
            print(f"   Median:      {sorted(response_times)[len(response_times)//2]}ms")
        
        # Top/Bottom Performer
        sorted_results = sorted(results['detailed_results'], 
                              key=lambda x: x['overall_score'], reverse=True)
        
        print(f"\n🏆 Beste Antwort (Score: {sorted_results[0]['overall_score']:.3f}):")
        print(f"   Frage: {sorted_results[0]['question']}")
        
        if len(sorted_results) > 1:
            print(f"\n🔻 Schwächste Antwort (Score: {sorted_results[-1]['overall_score']:.3f}):")
            print(f"   Frage: {sorted_results[-1]['question']}")
        
        print(f"\n✅ EVALUATION ABGESCHLOSSEN!")
        print(f"📁 Alle Ergebnisse gespeichert in: {output_dir}")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Evaluation fehlgeschlagen: {e}")
        return None


if __name__ == "__main__":
    main()