#!/usr/bin/env python3
"""
Minimale RAG-Evaluation mit nur 1 Testfrage

Schnelle Evaluation für Testing und Debugging.
"""

import sys
import asyncio
from pathlib import Path

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.rag_evaluation import RAGEvaluator


class MinimalRAGEvaluator(RAGEvaluator):
    """RAG-Evaluator mit nur einer Testfrage für schnelle Tests."""
    
    def _create_test_dataset(self):
        """Nur eine Testfrage für maximale Geschwindigkeit."""
        return [
            {
                "question": "Bewerbung auf höheres Fachsemester an der Universität zu Köln/WiSo-Fakultät",
                "ground_truth": "Für eine Bewerbung auf höhere Fachsemester benötigen Sie eine Anrechnungsbescheinigung vom Prüfungsamt.",
                "topic": "bewerbung"
            }
        ]


async def main():
    """Minimale Evaluation mit 1 Frage."""
    print("🚀 Minimale RAG-Evaluation (1 Frage)...")
    
    try:
        # Evaluator mit 1 Frage
        evaluator = MinimalRAGEvaluator()
        
        # Evaluation durchführen
        results = await evaluator.run_evaluation()
        
        # Kompakte Ergebnisse
        evaluator.print_summary()
        
        # Zusätzlich: Zeige den gefundenen Kontext
        if hasattr(evaluator, 'evaluation_details') and evaluator.evaluation_details:
            print("\n" + "="*80)
            print("🔍 **GEFUNDENER KONTEXT VOM RAG-TOOL**")
            print("="*80)
            
            for i, detail in enumerate(evaluator.evaluation_details, 1):
                print(f"\n{i}. **Frage**: {detail['question']}")
                print(f"   **RAG-Query**: {detail['question']}")  # Explizit zeigen, dass Query = Frage
                print(f"   **Kontext**: {detail['context']}")
                print(f"   **Antwort**: {detail['answer']}")
                print(f"   **Ground Truth**: {detail['ground_truth']}")
                
                # Kontext-Analyse
                context_length = len(detail['context'])
                if context_length == 0:
                    print(f"   ❌ **Kontext-Status**: Leer (0 Zeichen)")
                elif "❌" in detail['context'] or "nicht gefunden" in detail['context'].lower():
                    print(f"   ⚠️ **Kontext-Status**: Fehler oder nicht gefunden ({context_length} Zeichen)")
                else:
                    print(f"   ✅ **Kontext-Status**: Gefunden ({context_length} Zeichen)")
        
        print("\n✅ Minimale Evaluation abgeschlossen!")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")


if __name__ == "__main__":
    asyncio.run(main())