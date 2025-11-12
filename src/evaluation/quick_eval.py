"""
Quick Evaluation Script
======================

Einfaches Skript zum Ausführen der RAG-Evaluation Pipeline.
"""

import logging
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src to path
src_path = Path(__file__).parent.parent
sys.path.append(str(src_path))

from evaluation.pipeline import EvaluationPipeline
from evaluation.test_cases import create_sample_test_cases, save_test_cases


def main():
    """Führe eine Quick-Evaluation durch."""
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Starte RAG Quick-Evaluation...")
    
    # Erstelle Output-Directory
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)
    
    # Erstelle Sample-Testfälle
    test_cases = create_sample_test_cases()
    
    # Speichere Testfälle für Referenz
    test_cases_file = output_dir / "sample_test_cases.json"
    save_test_cases(test_cases, test_cases_file)
    logger.info(f"📋 Sample-Testfälle gespeichert in: {test_cases_file}")
    
    # Initialisiere Pipeline
    pipeline = EvaluationPipeline(output_dir=output_dir)
    
    # Führe Evaluation durch
    results = pipeline.run_batch_evaluation(test_cases, save_results=True)
    
    # Zeige Zusammenfassung
    summary = results['aggregated_metrics']['summary_statistics']
    ares_metrics = summary['ares_metrics']
    
    logger.info("\n" + "="*50)
    logger.info("📊 EVALUATION ZUSAMMENFASSUNG")
    logger.info("="*50)
    logger.info(f"Testfälle evaluiert: {summary['total_evaluations']}")
    logger.info(f"Ø ARES Score: {ares_metrics['avg_overall_score']:.3f}")
    logger.info(f"Ø Context Relevance: {ares_metrics['avg_context_relevance']:.3f}")
    logger.info(f"Ø Answer Faithfulness: {ares_metrics['avg_answer_faithfulness']:.3f}")
    logger.info(f"Ø Answer Relevance: {ares_metrics['avg_answer_relevance']:.3f}")
    logger.info("="*50)
    logger.info(f"📁 Vollständige Ergebnisse in: {output_dir}")
    logger.info("✅ Quick-Evaluation abgeschlossen!")


if __name__ == "__main__":
    main()