#!/usr/bin/env python3
"""
Erweiterte RAG-Evaluation mit benutzerdefinierten Metriken

Zusätzlich zu RAGAS werden hier spezifische Metriken für das
Universitäts-RAG-System implementiert:

- Universitätsspezifische Accuracy
- Response Time Analyse  
- Coverage-Analyse der Wissensdatenbank
- Konsistenz-Tests
"""

import sys
import time
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict
import json

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.tools.rag_tool import create_university_rag_tool
import logging

logger = logging.getLogger(__name__)


class ExtendedRAGEvaluator:
    """
    Erweiterte Evaluation für universitätsspezifische RAG-Metriken.
    
    Evaluiert:
    - Response Time Performance
    - Fachbereichs-Coverage
    - Konsistenz bei ähnlichen Fragen
    - Qualität der Quellenangaben
    """
    
    def __init__(self):
        """Initialisiert den erweiterten Evaluator."""
        self.rag_tool = create_university_rag_tool()
        self.response_times = []
        self.coverage_results = {}
        self.consistency_results = {}
        
    def evaluate_response_time(self, questions: List[str], runs: int = 3) -> Dict[str, float]:
        """
        Evaluiert die Response Time des RAG-Systems.
        
        Args:
            questions: Liste von Testfragen
            runs: Anzahl der Wiederholungen pro Frage
            
        Returns:
            Response Time Statistiken
        """
        logger.info(f"⏱️ Evaluiere Response Time mit {len(questions)} Fragen...")
        
        all_times = []
        question_times = {}
        
        for question in questions:
            times = []
            
            for run in range(runs):
                start_time = time.time()
                
                try:
                    _ = self.rag_tool._run(question)
                    end_time = time.time()
                    response_time = end_time - start_time
                    times.append(response_time)
                    all_times.append(response_time)
                    
                except Exception as e:
                    logger.warning(f"Fehler bei Frage '{question[:30]}...': {e}")
                    continue
            
            if times:
                question_times[question] = {
                    'avg': statistics.mean(times),
                    'min': min(times),
                    'max': max(times),
                    'std': statistics.stdev(times) if len(times) > 1 else 0
                }
        
        if all_times:
            return {
                'overall_avg': statistics.mean(all_times),
                'overall_min': min(all_times),
                'overall_max': max(all_times),
                'overall_std': statistics.stdev(all_times) if len(all_times) > 1 else 0,
                'per_question': question_times
            }
        
        return {}
    
    def evaluate_domain_coverage(self) -> Dict[str, Any]:
        """
        Evaluiert die Abdeckung verschiedener Universitätsbereiche.
        
        Returns:
            Coverage-Analyse nach Fachbereichen
        """
        logger.info("📚 Evaluiere Domain Coverage...")
        
        domain_questions = {
            'bewerbung': [
                "Wie bewerbe ich mich für einen Masterstudiengang?",
                "Was sind die Bewerbungsfristen?"
            ],
            'pruefungen': [
                "Wie melde ich mich zu Prüfungen an?",
                "Wo finde ich meine Prüfungsergebnisse?"
            ],
            'international': [
                "Welche Sprachkenntnisse brauche ich?",
                "Wie bewerbe ich mich als internationaler Student?"
            ]
        }
        
        coverage_results = {}
        
        for domain, questions in domain_questions.items():
            domain_results = {
                'total_questions': len(questions),
                'successful_responses': 0,
                'failed_responses': 0,
                'empty_responses': 0,
                'avg_content_length': 0,
                'response_details': []
            }
            
            content_lengths = []
            
            for question in questions:
                try:
                    response = self.rag_tool._run(question)
                    
                    if not response or response.strip() == "":
                        domain_results['empty_responses'] += 1
                    elif "❌" in response or "nicht gefunden" in response.lower():
                        domain_results['failed_responses'] += 1
                    else:
                        domain_results['successful_responses'] += 1
                        content_lengths.append(len(response))
                    
                    domain_results['response_details'].append({
                        'question': question,
                        'response_length': len(response),
                        'has_content': bool(response and "❌" not in response)
                    })
                    
                except Exception as e:
                    domain_results['failed_responses'] += 1
                    logger.warning(f"Fehler bei Domain-Frage '{question[:30]}...': {e}")
            
            if content_lengths:
                domain_results['avg_content_length'] = statistics.mean(content_lengths)
            
            # Coverage Score berechnen
            success_rate = domain_results['successful_responses'] / domain_results['total_questions']
            domain_results['coverage_score'] = success_rate
            
            coverage_results[domain] = domain_results
        
        return coverage_results
    
    def evaluate_consistency(self) -> Dict[str, Any]:
        """
        Evaluiert die Konsistenz bei ähnlichen oder umformulierten Fragen.
        
        Returns:
            Konsistenz-Analyse
        """
        logger.info("🔄 Evaluiere Antwort-Konsistenz...")
        
        # Ähnliche Fragenpaare definieren - reduziert
        similar_questions = [
            [
                "Was brauche ich für die Bewerbung auf ein höheres Fachsemester?",
                "Welche Unterlagen sind für die Bewerbung auf höhere Fachsemester erforderlich?"
            ],
            [
                "Welche Fristen gelten für Bewerbungen?",
                "Bis wann muss ich mich bewerben?"
            ]
        ]
        
        consistency_results = {
            'question_groups': [],
            'overall_consistency': 0,
            'avg_response_similarity': 0
        }
        
        total_consistency_scores = []
        
        for group_idx, question_group in enumerate(similar_questions):
            group_results = {
                'questions': question_group,
                'responses': [],
                'consistency_score': 0,
                'content_overlap': 0
            }
            
            # Antworten für alle Fragen in der Gruppe sammeln
            responses = []
            for question in question_group:
                try:
                    response = self.rag_tool._run(question)
                    responses.append(response)
                    group_results['responses'].append({
                        'question': question,
                        'response': response,
                        'response_length': len(response)
                    })
                except Exception as e:
                    logger.warning(f"Fehler bei Konsistenz-Frage '{question[:30]}...': {e}")
                    responses.append("")
            
            # Konsistenz bewerten (vereinfachte Wort-Überlappung)
            if len(responses) >= 2:
                overlap_scores = []
                
                for i in range(len(responses)):
                    for j in range(i + 1, len(responses)):
                        if responses[i] and responses[j]:
                            # Einfache Wort-Überlappung berechnen
                            words_i = set(responses[i].lower().split())
                            words_j = set(responses[j].lower().split())
                            
                            if words_i and words_j:
                                overlap = len(words_i.intersection(words_j))
                                total_words = len(words_i.union(words_j))
                                overlap_score = overlap / total_words if total_words > 0 else 0
                                overlap_scores.append(overlap_score)
                
                if overlap_scores:
                    group_results['consistency_score'] = statistics.mean(overlap_scores)
                    group_results['content_overlap'] = statistics.mean(overlap_scores)
                    total_consistency_scores.append(group_results['consistency_score'])
            
            consistency_results['question_groups'].append(group_results)
        
        if total_consistency_scores:
            consistency_results['overall_consistency'] = statistics.mean(total_consistency_scores)
            consistency_results['avg_response_similarity'] = statistics.mean(total_consistency_scores)
        
        return consistency_results
    
    def evaluate_source_quality(self, questions: List[str]) -> Dict[str, Any]:
        """
        Evaluiert die Qualität der Quellenangaben.
        
        Args:
            questions: Liste von Testfragen
            
        Returns:
            Quellenqualität-Analyse
        """
        logger.info("📖 Evaluiere Quellenqualität...")
        
        source_results = {
            'total_responses': 0,
            'responses_with_sources': 0,
            'responses_with_multiple_sources': 0,
            'avg_sources_per_response': 0,
            'source_types': defaultdict(int),
            'response_details': []
        }
        
        total_sources = []
        
        for question in questions:
            try:
                response = self.rag_tool._run(question)
                source_results['total_responses'] += 1
                
                # Quellenangaben zählen
                source_count = 0
                has_title_source = False
                has_url_source = False
                has_collection_info = False
                
                # Nach verschiedenen Quellenformaten suchen
                if "(Quelle:" in response:
                    source_count += response.count("(Quelle:")
                    has_title_source = True
                
                if "http" in response:
                    has_url_source = True
                
                if "[aus:" in response:
                    source_count += response.count("[aus:")
                    has_collection_info = True
                
                if source_count > 0:
                    source_results['responses_with_sources'] += 1
                    total_sources.append(source_count)
                    
                    if source_count > 1:
                        source_results['responses_with_multiple_sources'] += 1
                
                # Quellentypen kategorisieren
                if has_title_source:
                    source_results['source_types']['title_reference'] += 1
                if has_url_source:
                    source_results['source_types']['url_reference'] += 1
                if has_collection_info:
                    source_results['source_types']['collection_reference'] += 1
                
                source_results['response_details'].append({
                    'question': question,
                    'source_count': source_count,
                    'has_sources': source_count > 0,
                    'source_types': {
                        'title': has_title_source,
                        'url': has_url_source,
                        'collection': has_collection_info
                    }
                })
                
            except Exception as e:
                logger.warning(f"Fehler bei Quellenanalyse '{question[:30]}...': {e}")
        
        # Durchschnittliche Anzahl Quellen
        if total_sources:
            source_results['avg_sources_per_response'] = statistics.mean(total_sources)
        
        # Prozentuale Metriken berechnen
        if source_results['total_responses'] > 0:
            source_results['source_coverage_rate'] = (
                source_results['responses_with_sources'] / source_results['total_responses']
            )
            source_results['multiple_source_rate'] = (
                source_results['responses_with_multiple_sources'] / source_results['total_responses']
            )
        
        return source_results
    
    def run_full_evaluation(self) -> Dict[str, Any]:
        """
        Führt die vollständige erweiterte Evaluation durch.
        
        Returns:
            Alle Evaluation-Ergebnisse
        """
        logger.info("🚀 Starte erweiterte RAG-Evaluation...")
        
        # Test-Fragen für verschiedene Evaluationen - reduziert
        general_questions = [
            "Was brauche ich für die Bewerbung?",
            "Wie funktioniert die Prüfungsanmeldung?",
            "Welche Fristen muss ich beachten?"
        ]
        
        results = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'evaluations': {}
        }
        
        # Response Time Evaluation
        logger.info("1/4 Response Time Evaluation...")
        results['evaluations']['response_time'] = self.evaluate_response_time(general_questions)
        
        # Domain Coverage Evaluation  
        logger.info("2/4 Domain Coverage Evaluation...")
        results['evaluations']['domain_coverage'] = self.evaluate_domain_coverage()
        
        # Consistency Evaluation
        logger.info("3/4 Consistency Evaluation...")
        results['evaluations']['consistency'] = self.evaluate_consistency()
        
        # Source Quality Evaluation
        logger.info("4/4 Source Quality Evaluation...")
        results['evaluations']['source_quality'] = self.evaluate_source_quality(general_questions)
        
        logger.info("✅ Erweiterte Evaluation abgeschlossen!")
        
        return results
    
    def print_extended_summary(self, results: Dict[str, Any]):
        """
        Gibt eine Zusammenfassung der erweiterten Evaluation aus.
        
        Args:
            results: Evaluation-Ergebnisse
        """
        print("\n" + "="*80)
        print("📊 ERWEITERTE RAG-EVALUATION ZUSAMMENFASSUNG")
        print("="*80)
        
        print(f"🕒 **Timestamp**: {results['timestamp']}")
        
        # Response Time Analyse
        if 'response_time' in results['evaluations']:
            rt = results['evaluations']['response_time']
            print(f"\n⏱️ **Response Time Analyse**:")
            print("-" * 40)
            if rt:
                print(f"   Durchschnitt: {rt['overall_avg']:.2f}s")
                print(f"   Minimum: {rt['overall_min']:.2f}s")
                print(f"   Maximum: {rt['overall_max']:.2f}s")
                print(f"   Standardabweichung: {rt['overall_std']:.2f}s")
        
        # Domain Coverage
        if 'domain_coverage' in results['evaluations']:
            dc = results['evaluations']['domain_coverage']
            print(f"\n📚 **Domain Coverage**:")
            print("-" * 40)
            for domain, data in dc.items():
                score = data.get('coverage_score', 0)
                status = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🔴"
                print(f"   {status} {domain.title()}: {score:.1%} "
                      f"({data['successful_responses']}/{data['total_questions']} erfolgreich)")
        
        # Consistency
        if 'consistency' in results['evaluations']:
            cons = results['evaluations']['consistency']
            print(f"\n🔄 **Konsistenz-Analyse**:")
            print("-" * 40)
            score = cons.get('overall_consistency', 0)
            status = "🟢" if score >= 0.7 else "🟡" if score >= 0.5 else "🔴"
            print(f"   {status} Gesamtkonsistenz: {score:.1%}")
            print(f"   Durchschnittliche Ähnlichkeit: {cons.get('avg_response_similarity', 0):.1%}")
        
        # Source Quality
        if 'source_quality' in results['evaluations']:
            sq = results['evaluations']['source_quality']
            print(f"\n📖 **Quellenqualität**:")
            print("-" * 40)
            if sq['total_responses'] > 0:
                coverage_rate = sq.get('source_coverage_rate', 0)
                status = "🟢" if coverage_rate >= 0.8 else "🟡" if coverage_rate >= 0.6 else "🔴"
                print(f"   {status} Antworten mit Quellen: {coverage_rate:.1%}")
                print(f"   Durchschnittliche Quellen pro Antwort: {sq.get('avg_sources_per_response', 0):.1f}")
                print(f"   Antworten mit mehreren Quellen: {sq.get('multiple_source_rate', 0):.1%}")
        
        print("\n" + "="*80)


def main():
    """Hauptfunktion für die erweiterte RAG-Evaluation."""
    print("🚀 Starte erweiterte RAG-Evaluation...")
    
    try:
        evaluator = ExtendedRAGEvaluator()
        results = evaluator.run_full_evaluation()
        
        # Ergebnisse anzeigen
        evaluator.print_extended_summary(results)
        
        # Ergebnisse speichern
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = f"extended_rag_evaluation_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Erweiterte Ergebnisse gespeichert in: {output_file}")
        print("✅ Erweiterte RAG-Evaluation erfolgreich abgeschlossen!")
        
    except Exception as e:
        print(f"❌ Fehler bei der erweiterten Evaluation: {e}")
        logger.exception("Detaillierter Fehler:")


if __name__ == "__main__":
    main()