#!/usr/bin/env python3
"""
Batch-Ausführung aller RAG-Evaluationen

Führt sowohl RAGAS-basierte als auch erweiterte Evaluationen durch
und erstellt einen kombinierten Report.
"""

import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime
import logging

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.rag_evaluation import RAGEvaluator
from src.evaluation.extended_rag_evaluation import ExtendedRAGEvaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BatchEvaluator:
    """
    Führt alle RAG-Evaluationen in einem Batch aus.
    """
    
    def __init__(self):
        """Initialisiert den Batch-Evaluator."""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results = {}
    
    async def run_all_evaluations(self) -> dict:
        """
        Führt alle verfügbaren Evaluationen durch.
        
        Returns:
            Kombinierte Ergebnisse aller Evaluationen
        """
        logger.info("🚀 Starte Batch-Evaluation aller RAG-Tests...")
        
        combined_results = {
            'batch_timestamp': self.timestamp,
            'evaluations': {}
        }
        
        # 1. RAGAS-Evaluation
        logger.info("📊 1/2 RAGAS-basierte Evaluation...")
        try:
            ragas_evaluator = RAGEvaluator()
            ragas_results = await ragas_evaluator.run_evaluation()
            combined_results['evaluations']['ragas'] = ragas_results
            logger.info("✅ RAGAS-Evaluation abgeschlossen")
        except Exception as e:
            logger.error(f"❌ RAGAS-Evaluation fehlgeschlagen: {e}")
            combined_results['evaluations']['ragas'] = {
                'error': str(e),
                'status': 'failed'
            }
        
        # 2. Erweiterte Evaluation
        logger.info("📈 2/2 Erweiterte RAG-Evaluation...")
        try:
            extended_evaluator = ExtendedRAGEvaluator()
            extended_results = extended_evaluator.run_full_evaluation()
            combined_results['evaluations']['extended'] = extended_results
            logger.info("✅ Erweiterte Evaluation abgeschlossen")
        except Exception as e:
            logger.error(f"❌ Erweiterte Evaluation fehlgeschlagen: {e}")
            combined_results['evaluations']['extended'] = {
                'error': str(e),
                'status': 'failed'
            }
        
        self.results = combined_results
        return combined_results
    
    def create_combined_report(self) -> str:
        """
        Erstellt einen kombinierten Evaluation-Report.
        
        Returns:
            Formatierter Report als String
        """
        if not self.results:
            return "❌ Keine Ergebnisse verfügbar. Führen Sie zuerst run_all_evaluations() aus."
        
        report = []
        report.append("="*80)
        report.append("🎯 UMFASSENDER RAG-EVALUATION REPORT")
        report.append("="*80)
        report.append(f"📅 Timestamp: {self.results['batch_timestamp']}")
        report.append("")
        
        # RAGAS-Sektion
        if 'ragas' in self.results['evaluations']:
            ragas_data = self.results['evaluations']['ragas']
            
            if 'error' in ragas_data:
                report.append("❌ RAGAS-EVALUATION: FEHLGESCHLAGEN")
                report.append(f"   Fehler: {ragas_data['error']}")
            else:
                report.append("📊 RAGAS-EVALUATION ERGEBNISSE")
                report.append("-" * 40)
                
                if 'metrics' in ragas_data:
                    metrics = ragas_data['metrics']
                    for metric, score in metrics.items():
                        status = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🔴"
                        metric_name = metric.replace('_', ' ').title()
                        report.append(f"   {status} {metric_name}: {score:.3f}")
                
                if 'overall_score' in ragas_data:
                    overall = ragas_data['overall_score']
                    status = "🟢" if overall >= 0.8 else "🟡" if overall >= 0.6 else "🔴"
                    report.append(f"   {status} Gesamtscore: {overall:.3f}")
        
        report.append("")
        
        # Erweiterte Evaluation Sektion
        if 'extended' in self.results['evaluations']:
            extended_data = self.results['evaluations']['extended']
            
            if 'error' in extended_data:
                report.append("❌ ERWEITERTE EVALUATION: FEHLGESCHLAGEN")
                report.append(f"   Fehler: {extended_data['error']}")
            else:
                report.append("📈 ERWEITERTE EVALUATION ERGEBNISSE")
                report.append("-" * 40)
                
                evals = extended_data.get('evaluations', {})
                
                # Response Time
                if 'response_time' in evals:
                    rt = evals['response_time']
                    if rt:
                        avg_time = rt.get('overall_avg', 0)
                        status = "🟢" if avg_time <= 2.0 else "🟡" if avg_time <= 5.0 else "🔴"
                        report.append(f"   {status} Durchschnittliche Response Time: {avg_time:.2f}s")
                
                # Domain Coverage
                if 'domain_coverage' in evals:
                    dc = evals['domain_coverage']
                    report.append("   📚 Domain Coverage:")
                    for domain, data in dc.items():
                        score = data.get('coverage_score', 0)
                        status = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🔴"
                        report.append(f"      {status} {domain.title()}: {score:.1%}")
                
                # Consistency
                if 'consistency' in evals:
                    cons = evals['consistency']
                    score = cons.get('overall_consistency', 0)
                    status = "🟢" if score >= 0.7 else "🟡" if score >= 0.5 else "🔴"
                    report.append(f"   {status} Konsistenz: {score:.1%}")
                
                # Source Quality
                if 'source_quality' in evals:
                    sq = evals['source_quality']
                    if sq.get('total_responses', 0) > 0:
                        coverage_rate = sq.get('source_coverage_rate', 0)
                        status = "🟢" if coverage_rate >= 0.8 else "🟡" if coverage_rate >= 0.6 else "🔴"
                        report.append(f"   {status} Quellenabdeckung: {coverage_rate:.1%}")
        
        # Empfehlungen
        report.append("")
        report.append("💡 GESAMTEMPFEHLUNGEN")
        report.append("-" * 40)
        
        recommendations = self._generate_combined_recommendations()
        for rec in recommendations:
            report.append(f"   • {rec}")
        
        report.append("")
        report.append("="*80)
        
        return "\n".join(report)
    
    def _generate_combined_recommendations(self) -> list:
        """
        Generiert kombinierte Empfehlungen basierend auf allen Evaluationen.
        
        Returns:
            Liste von Empfehlungen
        """
        recommendations = []
        
        if not self.results or 'evaluations' not in self.results:
            return ["Führen Sie zuerst eine vollständige Evaluation durch."]
        
        evals = self.results['evaluations']
        
        # RAGAS-basierte Empfehlungen
        if 'ragas' in evals and 'metrics' in evals['ragas']:
            metrics = evals['ragas']['metrics']
            
            if metrics.get('context_precision', 0) < 0.6:
                recommendations.append("Verbesserung der Retrieval-Präzision durch optimierte Embedding-Modelle")
            
            if metrics.get('context_recall', 0) < 0.6:
                recommendations.append("Erhöhung der Anzahl abgerufener Dokumente für bessere Vollständigkeit")
            
            if metrics.get('faithfulness', 0) < 0.6:
                recommendations.append("Optimierung der Prompt-Templates zur Reduktion von Halluzinationen")
            
            if metrics.get('answer_relevancy', 0) < 0.6:
                recommendations.append("Verbesserung der Antwortgenerierung durch bessere Kontextintegration")
        
        # Erweiterte Evaluations-Empfehlungen
        if 'extended' in evals and 'evaluations' in evals['extended']:
            ext_evals = evals['extended']['evaluations']
            
            # Response Time
            if 'response_time' in ext_evals:
                rt = ext_evals['response_time']
                if rt and rt.get('overall_avg', 0) > 5.0:
                    recommendations.append("Optimierung der Response Time durch Caching oder kleinere Modelle")
            
            # Domain Coverage
            if 'domain_coverage' in ext_evals:
                dc = ext_evals['domain_coverage']
                low_coverage_domains = [
                    domain for domain, data in dc.items()
                    if data.get('coverage_score', 0) < 0.6
                ]
                if low_coverage_domains:
                    recommendations.append(f"Verbesserung der Wissensdatenbank für: {', '.join(low_coverage_domains)}")
            
            # Consistency
            if 'consistency' in ext_evals:
                cons = ext_evals['consistency']
                if cons.get('overall_consistency', 0) < 0.5:
                    recommendations.append("Verbesserung der Antwort-Konsistenz durch Prompt-Standardisierung")
            
            # Source Quality
            if 'source_quality' in ext_evals:
                sq = ext_evals['source_quality']
                if sq.get('source_coverage_rate', 0) < 0.6:
                    recommendations.append("Verbesserung der Quellenangaben für bessere Nachvollziehbarkeit")
        
        if not recommendations:
            recommendations.append("Excellent! Alle Metriken zeigen gute Ergebnisse. Weiter so!")
        
        return recommendations
    
    def save_combined_results(self, output_path: str = None) -> str:
        """
        Speichert die kombinierten Ergebnisse.
        
        Args:
            output_path: Pfad für die Ausgabedatei
            
        Returns:
            Pfad der gespeicherten Datei
        """
        if not self.results:
            raise ValueError("Keine Ergebnisse zum Speichern.")
        
        if output_path is None:
            output_path = f"batch_rag_evaluation_{self.timestamp}.json"
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📁 Kombinierte Ergebnisse gespeichert: {output_file}")
        return str(output_file)


async def main():
    """Hauptfunktion für die Batch-Evaluation."""
    print("🚀 Starte umfassende RAG-Evaluation...")
    print("="*60)
    
    try:
        # Batch-Evaluator erstellen
        batch_evaluator = BatchEvaluator()
        
        # Alle Evaluationen durchführen
        results = await batch_evaluator.run_all_evaluations()
        
        # Kombinierten Report erstellen und anzeigen
        report = batch_evaluator.create_combined_report()
        print(report)
        
        # Ergebnisse speichern
        output_file = batch_evaluator.save_combined_results()
        
        # Einzelne Reports speichern
        report_file = f"combined_rag_report_{batch_evaluator.timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n💾 Dateien gespeichert:")
        print(f"   📊 JSON-Daten: {output_file}")
        print(f"   📋 Report: {report_file}")
        print("\n✅ Umfassende RAG-Evaluation erfolgreich abgeschlossen!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Evaluation abgebrochen durch Benutzer.")
    except Exception as e:
        print(f"\n❌ Fehler bei der Batch-Evaluation: {e}")
        logger.exception("Detaillierter Fehler:")


if __name__ == "__main__":
    asyncio.run(main())