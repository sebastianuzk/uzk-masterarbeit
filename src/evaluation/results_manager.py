"""
Evaluation Results Manager
=========================

Speichert und verwaltet ARES-Evaluation Ergebnisse in verschiedenen Formaten.
"""

import json
import csv
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class EvaluationResultsManager:
    """Manager für Speicherung und Verwaltung von Evaluation-Ergebnissen."""
    
    def __init__(self, results_dir: Optional[Path] = None):
        """
        Args:
            results_dir: Verzeichnis für Ergebnisse (default: src/evaluation/results)
        """
        if results_dir is None:
            # Standard: results-Ordner neben diesem Script
            self.results_dir = Path(__file__).parent / "results"
        else:
            self.results_dir = results_dir
            
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"📂 Results Manager initialisiert: {self.results_dir}")
    
    def save_evaluation_results(
        self, 
        results: Dict[str, Any], 
        evaluation_type: str = "ares",
        model_name: str = "unknown",
        test_source: str = "default"
    ) -> Dict[str, Path]:
        """
        Speichere Evaluation-Ergebnisse in mehreren Formaten.
        
        Args:
            results: ARES Evaluation Ergebnisse
            evaluation_type: Art der Evaluation (ares, ollama, etc.)
            model_name: Verwendetes LLM Model
            test_source: Quelle der Test-Cases (csv, default, etc.)
            
        Returns:
            Dict mit Pfaden zu gespeicherten Dateien
        """
        try:
            # Anreichere Ergebnisse mit Metadaten
            enriched_results = self._enrich_results(results, evaluation_type, model_name, test_source)
            
            # Generiere eindeutigen Dateinamen
            base_filename = self._generate_filename(evaluation_type, model_name, test_source)
            
            # Speichere in verschiedenen Formaten
            saved_files = {
                'json': self._save_json_results(enriched_results, base_filename),
                'csv': self._save_csv_results(enriched_results, base_filename),
                'summary': self._save_summary_report(enriched_results, base_filename)
            }
            
            logger.info(f"✅ Evaluation results saved successfully:")
            for format_type, file_path in saved_files.items():
                logger.info(f"   {format_type.upper()}: {file_path.name}")
            
            return saved_files
            
        except Exception as e:
            logger.error(f"❌ Error saving evaluation results: {e}")
            raise
    
    def _generate_filename(self, evaluation_type: str, model_name: str, test_source: str) -> str:
        """Generiere eindeutigen Dateinamen."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Säubere Namen für Windows-Kompatibilität
        clean_model = self._sanitize_filename(model_name)
        clean_source = self._sanitize_filename(test_source)
        
        return f"{evaluation_type}_{clean_model}_{clean_source}_{timestamp}"
    
    def _sanitize_filename(self, name: str) -> str:
        """Säubere String für Dateinamen."""
        # Entferne problematische Zeichen für Windows
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Kürze wenn nötig
        return name[:50] if len(name) > 50 else name
    
    def _enrich_results(
        self, 
        results: Dict[str, Any], 
        evaluation_type: str, 
        model_name: str, 
        test_source: str
    ) -> Dict[str, Any]:
        """Reichere Ergebnisse mit Metadaten an."""
        enriched = results.copy()
        
        # Berechne tatsächliche Evaluation-Dauer
        duration_minutes = self._calculate_actual_duration(results)
        
        # Bestimme Anzahl der Fragen aus verschiedenen Quellen
        total_questions = 0
        if 'individual_results' in results:
            total_questions = len(results['individual_results'])
        elif 'questions' in results:
            total_questions = len(results['questions'])
        elif 'total_samples' in results:
            total_questions = results['total_samples']
        
        # Metadaten hinzufügen
        enriched['metadata'] = {
            'timestamp': datetime.now().isoformat(),
            'evaluation_type': evaluation_type,
            'model_name': model_name,
            'test_source': test_source,
            'total_questions': total_questions,
            'evaluation_duration_minutes': duration_minutes,
            'system_info': {
                'python_version': f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}",
                'platform': __import__('platform').system()
            }
        }
        
        # Fragen und Antworten sicherstellen
        if 'questions' in results and 'responses' in results:
            enriched['questions'] = results['questions']
            enriched['responses'] = results['responses']
            
        # Kategorie-Analyse hinzufügen (falls verfügbar)
        if 'questions' in results and 'responses' in results:
            enriched['category_analysis'] = self._analyze_by_category(results)
            
        # Performance-Klassifikation
        if 'scores' in results:
            enriched['performance_classification'] = self._classify_performance(results['scores'])
        elif 'average_scores' in results:
            enriched['performance_classification'] = self._classify_performance(results['average_scores'])
        
        return enriched
    
    def _save_json_results(self, results: Dict[str, Any], base_filename: str) -> Path:
        """Speichere vollständige Ergebnisse als strukturiertes JSON."""
        json_path = self.results_dir / f"{base_filename}_detailed.json"
        
        # Sicherstellen dass alle Daten verfügbar sind
        json_data = {
            'run_id': base_filename,
            'timestamp': results.get('metadata', {}).get('timestamp', datetime.now().isoformat()),
            'evaluation_config': results.get('metadata', {}),
            'questions': [],
            'responses': [],
            'detailed_results': []
        }
        
        # Daten aus verschiedenen Strukturen extrahieren
        if 'individual_results' in results:
            # ARES-Format: individual_results mit query/response
            for i, result in enumerate(results['individual_results']):
                question = result.get('query', f'Question {i+1}')
                response = result.get('response', 'No response recorded')
                
                json_data['questions'].append(question)
                json_data['responses'].append(response)
                json_data['detailed_results'].append({
                    'question': question,
                    'response': response,
                    'scores': {
                        'context_relevance': result.get('context_relevance', None),
                        'answer_relevance': result.get('answer_relevance', None),
                        'answer_faithfulness': result.get('answer_faithfulness', None),
                        'overall_score': result.get('overall_score', None)
                    },
                    'metadata': {
                        'question_index': i,
                        'evaluation_source': 'ARES'
                    }
                })
                
        elif 'questions' in results and 'responses' in results:
            # Standard-Format mit separaten Listen
            questions = results['questions']
            responses = results.get('responses', ['No response'] * len(questions))
            scores_data = results.get('scores', {})
            
            json_data['questions'] = questions
            json_data['responses'] = responses
            
            for i, (q, r) in enumerate(zip(questions, responses)):
                json_data['detailed_results'].append({
                    'question': q,
                    'response': r,
                    'scores': scores_data.get(i, {}),
                    'metadata': {
                        'question_index': i,
                        'evaluation_source': 'Standard'
                    }
                })
        
        # Durchschnittswerte und Zusammenfassung
        if 'average_scores' in results:
            json_data['summary'] = {
                'average_scores': results['average_scores'],
                'total_questions': len(json_data['questions']),
                'evaluation_metadata': results.get('metadata', {})
            }
        elif 'scores' in results:
            json_data['summary'] = {
                'scores': results['scores'],
                'total_questions': len(json_data['questions']),
                'evaluation_metadata': results.get('metadata', {})
            }
        
        # Metadaten hinzufügen
        json_data['metadata'] = results.get('metadata', {})
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON results saved to {json_path}")
        return json_path
    
    def _save_csv_results(self, results: Dict[str, Any], base_filename: str) -> Path:
        """Speichere Ergebnisse als CSV für Excel/Analyse."""
        csv_path = self.results_dir / f"{base_filename}_data.csv"
        
        csv_data = []
        metadata = results.get('metadata', {})
        
        # Extrahiere Daten aus ARES individual_results Struktur
        if 'individual_results' in results:
            for i, result in enumerate(results['individual_results']):
                csv_data.append({
                    'question_id': i + 1,
                    'question': result.get('query', f'Question {i+1}'),
                    'answer': result.get('response', 'N/A'),
                    'context_relevance': result.get('context_relevance', 'N/A'),
                    'answer_relevance': result.get('answer_relevance', 'N/A'),
                    'answer_faithfulness': result.get('answer_faithfulness', 'N/A'),
                    'overall_score': result.get('overall_score', 'N/A'),
                    'evaluation_duration_seconds': result.get('evaluation_duration_seconds', 'N/A'),
                    'timestamp': metadata.get('timestamp', ''),
                    'model': metadata.get('model_name', ''),
                    'test_source': metadata.get('test_source', '')
                })
        elif 'questions' in results and 'responses' in results:
            # Standard Struktur mit separaten Listen
            questions = results['questions']
            responses = results['responses']
            individual_results = results.get('individual_results', [])
            
            for i, (question, response) in enumerate(zip(questions, responses)):
                individual_scores = individual_results[i] if i < len(individual_results) else {}
                
                csv_data.append({
                    'question_id': i + 1,
                    'question': question,
                    'answer': response,
                    'context_relevance': individual_scores.get('context_relevance', 'N/A'),
                    'answer_relevance': individual_scores.get('answer_relevance', 'N/A'),
                    'answer_faithfulness': individual_scores.get('answer_faithfulness', 'N/A'),
                    'overall_score': individual_scores.get('overall_score', 'N/A'),
                    'evaluation_duration_seconds': individual_scores.get('evaluation_duration_seconds', 'N/A'),
                    'timestamp': metadata.get('timestamp', ''),
                    'model': metadata.get('model_name', ''),
                    'test_source': metadata.get('test_source', '')
                })
        else:
            # Fallback: nur Scores ohne Fragen/Antworten
            logger.warning("⚠️ No individual question data found - creating summary row")
            csv_data.append({
                'question_id': 'Summary',
                'question': 'Overall Results',
                'answer': 'N/A',
                'context_relevance': results.get('average_scores', {}).get('context_relevance', 'N/A'),
                'answer_relevance': results.get('average_scores', {}).get('answer_relevance', 'N/A'),
                'answer_faithfulness': results.get('average_scores', {}).get('answer_faithfulness', 'N/A'),
                'overall_score': results.get('average_scores', {}).get('overall_score', 'N/A'),
                'evaluation_duration_seconds': 'N/A',
                'timestamp': metadata.get('timestamp', ''),
                'model': metadata.get('model_name', ''),
                'test_source': metadata.get('test_source', '')
            })
        
        # Speichere als CSV
        if csv_data:
            df = pd.DataFrame(csv_data)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"CSV results saved to {csv_path} ({len(csv_data)} rows)")
        else:
            logger.warning("⚠️ No data to save in CSV format")
            
        return csv_path
    
    def _save_summary_report(self, results: Dict[str, Any], base_filename: str) -> Path:
        """Speichere lesbare Zusammenfassung."""
        summary_path = self.results_dir / f"{base_filename}_summary.txt"
        
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("ARES EVALUATION SUMMARY REPORT\n")
            f.write("="*60 + "\n\n")
            
            # Metadaten mit besserer Anzahl-Bestimmung
            metadata = results.get('metadata', {})
            total_questions = metadata.get('total_questions', 0)
            
            # Fallback: Bestimme Anzahl aus verfügbaren Daten
            if total_questions == 0:
                if 'individual_results' in results:
                    total_questions = len(results['individual_results'])
                elif 'questions' in results:
                    total_questions = len(results['questions'])
                elif 'responses' in results:
                    total_questions = len(results['responses'])
            
            f.write(f"Timestamp: {metadata.get('timestamp', 'N/A')}\n")
            f.write(f"Evaluation Type: {metadata.get('evaluation_type', 'N/A')}\n")
            f.write(f"Model: {metadata.get('model_name', 'N/A')}\n")
            f.write(f"Test Source: {metadata.get('test_source', 'N/A')}\n")
            f.write(f"Total Questions: {total_questions}\n")
            
            # Verbesserte Dauer-Berechnung
            duration = metadata.get('evaluation_duration_minutes')
            if duration and duration > 0:
                f.write(f"Duration: {duration:.1f} minutes\n")
            elif 'start_time' in results and 'end_time' in results:
                # Berechne Dauer aus Start- und Endzeit
                try:
                    start_dt = datetime.fromisoformat(results['start_time'].replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(results['end_time'].replace('Z', '+00:00'))
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    duration_minutes = duration_seconds / 60
                    f.write(f"Duration: {duration_minutes:.1f} minutes\n")
                except:
                    f.write("Duration: Unable to calculate\n")
            else:
                f.write("Duration: N/A\n")
            f.write("\n")
            
            # Scores - versuche verschiedene Score-Strukturen
            scores_dict = None
            if 'scores' in results:
                scores_dict = results['scores']
            elif 'average_scores' in results:
                scores_dict = results['average_scores']
            
            if scores_dict:
                f.write("PERFORMANCE SCORES:\n")
                f.write("-" * 20 + "\n")
                f.write(f"Context Relevance:    {scores_dict.get('context_relevance', 'N/A'):.3f} ({self._score_to_classification(scores_dict.get('context_relevance', 0))})\n")
                f.write(f"Answer Relevance:     {scores_dict.get('answer_relevance', 'N/A'):.3f} ({self._score_to_classification(scores_dict.get('answer_relevance', 0))})\n") 
                f.write(f"Answer Faithfulness:  {scores_dict.get('answer_faithfulness', 'N/A'):.3f} ({self._score_to_classification(scores_dict.get('answer_faithfulness', 0))})\n")
                f.write(f"Overall Score:        {scores_dict.get('overall_score', 'N/A'):.3f} ({self._score_to_classification(scores_dict.get('overall_score', 0))})\n\n")
            
            # Detaillierte Frage-Antwort-Auswertung aus verschiedenen Strukturen
            if 'individual_results' in results:
                # ARES-Format
                f.write("DETAILED QUESTION-ANSWER ANALYSIS:\n")
                f.write("-" * 37 + "\n")
                
                for i, result in enumerate(results['individual_results']):
                    question = result.get('query', f'Question {i+1}')
                    response = result.get('response', 'No response recorded')
                    
                    f.write(f"\nQuestion {i+1}:\n")
                    f.write(f"Q: {question}\n")
                    f.write(f"A: {response}\n")
                    f.write(f"Scores: CR={result.get('context_relevance', 'N/A'):.3f}, ")
                    f.write(f"AR={result.get('answer_relevance', 'N/A'):.3f}, ")
                    f.write(f"AF={result.get('answer_faithfulness', 'N/A'):.3f}, ")
                    f.write(f"Overall={result.get('overall_score', 'N/A'):.3f}\n")
                    eval_time = result.get('evaluation_duration_seconds', 0)
                    if eval_time and eval_time != 'N/A':
                        f.write(f"Evaluation Time: {eval_time:.1f}s\n")
                    
            elif 'questions' in results and 'responses' in results:
                # Standard-Format
                questions = results['questions']
                responses = results['responses']
                individual_results = results.get('individual_results', [])
                
                f.write("DETAILED QUESTION-ANSWER ANALYSIS:\n")
                f.write("-" * 37 + "\n")
                
                for i, (question, response) in enumerate(zip(questions, responses)):
                    individual_scores = individual_results[i] if i < len(individual_results) else {}
                    
                    f.write(f"\nQuestion {i+1}:\n")
                    f.write(f"Q: {question}\n")
                    f.write(f"A: {response}\n")
                    if individual_scores:
                        f.write(f"Scores: CR={individual_scores.get('context_relevance', 'N/A'):.3f}, ")
                        f.write(f"AR={individual_scores.get('answer_relevance', 'N/A'):.3f}, ")
                        f.write(f"AF={individual_scores.get('answer_faithfulness', 'N/A'):.3f}, ")
                        f.write(f"Overall={individual_scores.get('overall_score', 'N/A'):.3f}\n")
                        eval_time = individual_scores.get('evaluation_duration_seconds', 0)
                        if eval_time and eval_time != 'N/A':
                            f.write(f"Evaluation Time: {eval_time:.1f}s\n")
            
            # Performance-Klassifikation
            if 'performance_classification' in results:
                classification = results['performance_classification']
                f.write(f"\n\nPERFORMANCE CLASSIFICATION:\n")
                f.write("-" * 25 + "\n")
                f.write(f"Overall Rating: {classification.get('overall', 'N/A')}\n")
                f.write(f"Strengths: {', '.join(classification.get('strengths', []))}\n")
                f.write(f"Improvement Areas: {', '.join(classification.get('weaknesses', []))}\n")
        
        return summary_path
    
    def _calculate_actual_duration(self, results: Dict[str, Any]) -> float:
        """Berechne tatsächliche Evaluation-Dauer in Minuten."""
        try:
            if 'start_time' in results and 'end_time' in results:
                start_dt = datetime.fromisoformat(results['start_time'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(results['end_time'].replace('Z', '+00:00'))
                duration_seconds = (end_dt - start_dt).total_seconds()
                return duration_seconds / 60
            elif 'duration' in results:
                # Duration könnte in verschiedenen Einheiten sein
                duration = results['duration']
                if isinstance(duration, (int, float)):
                    return duration  # Assume minutes
                else:
                    return 0.0
            else:
                return 0.0
        except Exception:
            return 0.0
    
    def _analyze_by_category(self, results: Dict[str, Any]) -> Dict[str, Dict]:
        """Analysiere Ergebnisse nach Kategorien (falls verfügbar)."""
        analysis = {}
        
        questions = results.get('questions', [])
        if not questions:
            return analysis
        
        # Simple Kategorie-Erkennung basierend auf Keywords
        categories = {
            'Economics': ['wirtschaft', 'economic', 'ökonomie', 'markt', 'market'],
            'Business': ['business', 'unternehmen', 'company', 'firma'],
            'Finance': ['finance', 'finanz', 'geld', 'money', 'banking'],
            'Management': ['management', 'führung', 'strategic', 'organization'],
            'Other': []
        }
        
        for category in categories:
            analysis[category] = {'count': 0, 'avg_score': 0.0}
        
        # Kategorisiere Fragen basierend auf Keywords
        for i, question in enumerate(questions):
            question_lower = question.lower()
            categorized = False
            
            for category, keywords in categories.items():
                if category == 'Other':
                    continue
                if any(keyword in question_lower for keyword in keywords):
                    analysis[category]['count'] += 1
                    categorized = True
                    break
            
            if not categorized:
                analysis['Other']['count'] += 1
        
        return analysis
    
    def _classify_performance(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """Klassifiziere Performance basierend auf Scores."""
        overall_score = scores.get('overall_score', 0)
        
        if overall_score >= 0.8:
            rating = "Excellent"
        elif overall_score >= 0.6:
            rating = "Good"
        elif overall_score >= 0.4:
            rating = "Fair"
        else:
            rating = "Poor"
        
        # Identifiziere Stärken und Schwächen
        strengths = []
        weaknesses = []
        
        metrics = {
            'Context Relevance': scores.get('context_relevance', 0),
            'Answer Relevance': scores.get('answer_relevance', 0),
            'Answer Faithfulness': scores.get('answer_faithfulness', 0)
        }
        
        for metric, score in metrics.items():
            if score >= 0.7:
                strengths.append(metric)
            elif score < 0.5:
                weaknesses.append(metric)
        
        return {
            'overall': rating,
            'overall_score': overall_score,
            'strengths': strengths,
            'weaknesses': weaknesses
        }
    
    def _score_to_classification(self, score: float) -> str:
        """Konvertiere numerischen Score zu Text-Klassifikation."""
        if score >= 0.8:
            return "Excellent"
        elif score >= 0.6:
            return "Good"
        elif score >= 0.4:
            return "Fair"
        else:
            return "Poor"
    
    def list_saved_results(self) -> List[Path]:
        """Liste alle gespeicherten Ergebnisse."""
        json_files = list(self.results_dir.glob("*_detailed.json"))
        return sorted(json_files, key=lambda f: f.stat().st_mtime, reverse=True)
    
    def load_results(self, json_file: Path) -> Dict[str, Any]:
        """Lade gespeicherte Ergebnisse."""
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)


# Convenience functions
def save_ares_results(
    results: Dict[str, Any],
    model_name: str = "llama3.1:8b",
    test_source: str = "CSV"
) -> Dict[str, Path]:
    """
    Convenience-Funktion zum Speichern von ARES-Ergebnissen.
    
    Args:
        results: ARES Evaluation Ergebnisse
        model_name: LLM Model Name
        test_source: Test-Datenquelle
        
    Returns:
        Dictionary mit Pfaden zu gespeicherten Dateien
    """
    manager = EvaluationResultsManager()
    return manager.save_evaluation_results(results, "ares", model_name, test_source)


def get_latest_results() -> Optional[Dict[str, Any]]:
    """Lade die neuesten gespeicherten Ergebnisse."""
    manager = EvaluationResultsManager()
    saved_files = manager.list_saved_results()
    
    if saved_files:
        return manager.load_results(saved_files[0])
    else:
        return None