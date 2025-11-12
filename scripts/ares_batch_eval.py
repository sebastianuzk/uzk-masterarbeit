#!/usr/bin/env python3
"""
ARES Batch-Evaluation mit LangSmith
===================================
"""

from src.evaluation.test_real_chatbot import SimpleChatbotEvaluator, create_sample_test_cases
from pathlib import Path

def main():
    print('🚀 VOLLSTÄNDIGE ARES-BATCH-EVALUATION MIT LANGSMITH:')
    print()

    # Setup
    evaluator = SimpleChatbotEvaluator()
    test_cases = create_sample_test_cases()
    output_file = Path('evaluation_results/ares_langsmith_batch.json')

    print(f'📝 Führe Batch-Evaluation mit {len(test_cases)} Testfällen durch:')
    for i, tc in enumerate(test_cases, 1):
        print(f'   {i}. {tc.id}: {tc.question[:60]}...')

    print()
    print('🔄 Starte Evaluation...')

    try:
        # Batch-Evaluation mit LangSmith-Tracking
        results = evaluator.evaluate_batch(test_cases, output_file)
        
        print()
        print('📊 BATCH-EVALUATION ABGESCHLOSSEN!')
        print(f'💾 Ergebnisse gespeichert in: {output_file}')
        print()
        print('🎯 SCHNELL-STATISTIKEN:')
        metrics = results['performance_metrics']
        print(f'   📈 Ø Overall Score:      {metrics["avg_overall_score"]:.3f}')
        print(f'   ⚡ Ø Response Zeit:       {metrics["avg_response_time_ms"]:.0f}ms')
        print(f'   🔑 Keywords Coverage:     {metrics["keywords_coverage"]:.3f}')
        print()
        print('🔍 LangSmith: Alle Testfälle vollständig getrackt!')
        
        return results
        
    except Exception as e:
        print(f'❌ Evaluation fehlgeschlagen: {e}')
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()