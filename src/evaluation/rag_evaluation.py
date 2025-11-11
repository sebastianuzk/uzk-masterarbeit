#!/usr/bin/env python3
"""
RAGAS-basierte Evaluation für den RAG-Chatbot

Dieses Modul implementiert eine umfassende Evaluation des RAG-Systems
basierend auf RAGAS (Retrieval-Augmented Generation Assessment).

WICHTIG: Diese Evaluation ist vollständig kompatibel mit dem bestehenden Tech-Stack:
- Verwendet gleiche ChromaDB-Instanz wie RAG-Tool  
- Verwendet gleiche Embedding-Modelle wie Scraper (all-MiniLM-L6-v2)
- Verwendet gleiche Ollama-Konfiguration wie Agent
- Verwendet gleiche Hyperparameter wie Scraper

Bewertete Metriken:
- Context Precision: Präzision der abgerufenen Kontexte
- Context Recall: Vollständigkeit der abgerufenen Kontexte  
- Faithfulness: Treue der generierten Antwort zum Kontext
- Answer Relevancy: Relevanz der Antwort zur Frage
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# RAGAS und Evaluation Dependencies
try:
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
        ContextRelevance
    )
    from datasets import Dataset
except ImportError as e:
    print(f"❌ RAGAS-Dependencies nicht gefunden: {e}")
    print("Installieren Sie mit: pip install ragas datasets")
    sys.exit(1)

# LangChain und lokale Tools - Tech-Stack-konsistent
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
from src.tools.rag_tool import create_university_rag_tool
from src.scraper.hyperparameters import VECTOR_EMBEDDING_MODEL, RAG_SEARCH_RESULTS
from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL, TEMPERATURE

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEvaluator:
    """
    RAGAS-basierte Evaluation für das Universitäts-RAG-System.
    
    Führt umfassende Tests durch und bewertet die Qualität von:
    - Retrieval (Context Precision/Recall)
    - Generation (Faithfulness, Answer Relevancy)
    - Gesamtsystem (Context Relevancy)
    """
    
    def __init__(self, model_name: str = OLLAMA_MODEL):
        """
        Initialisiert den RAG-Evaluator.
        
        Args:
            model_name: Ollama-Modell für die Evaluation
        """
        self.model_name = model_name
        self.rag_tool = create_university_rag_tool()
        
        # LLM für Ground Truth Generation - gleiche Konfiguration wie Agent
        self.llm = ChatOllama(
            model=model_name,
            base_url=OLLAMA_BASE_URL,
            temperature=0.1  # Niedrige Temperatur für konsistente Evaluation
        )
        
        # Lokale Embeddings für RAGAS - exakt gleiche wie Scraper/RAG-Tool
        self.embeddings = HuggingFaceEmbeddings(
            model_name=VECTOR_EMBEDDING_MODEL,  # Konsistent mit Scraper
            model_kwargs={'device': 'cpu'}
        )
        
        # Evaluation-Dataset erstellen
        self.test_questions = self._create_test_dataset()
        
        # Evaluation Results
        self.results = {}
        self.evaluation_details = []  # Für detaillierte Antworten
        
        logger.info(f"RAG-Evaluator initialisiert mit Modell: {model_name}")
    
    def _create_test_dataset(self) -> List[Dict[str, str]]:
        """
        Erstellt ein kompaktes Test-Dataset mit den wichtigsten Universitätsfragen.
        Reduziert für schnellere Evaluation.
        
        Returns:
            Liste von Test-Cases mit question und ground_truth
        """
        return [
            {
                "question": "Was benötige ich für die Bewerbung auf ein höheres Fachsemester im Master Informatik?",
                "ground_truth": "Für eine Bewerbung auf höhere Fachsemester benötigen Sie in der Regel eine Anrechnungsbescheinigung vom Prüfungsamt der WiSo-Fakultät, die bestätigt, welche Leistungen angerechnet werden können.",
                "topic": "bewerbung"
            },
            {
                "question": "Welche Fristen gelten für Bewerbungen an der Universität zu Köln?",
                "ground_truth": "Die Bewerbungsfristen variieren je nach Studiengang und Semester. Für das Wintersemester ist die Frist meist der 15. Juli, für das Sommersemester der 15. Januar.",
                "topic": "fristen"
            },
            {
                "question": "Wie funktioniert die Prüfungsanmeldung an der Universität zu Köln?",
                "ground_truth": "Die Prüfungsanmeldung erfolgt online über KLIPS 2.0 innerhalb der Anmeldefristen. Studierende müssen sich selbständig zu den Prüfungen anmelden.",
                "topic": "pruefung"
            }
        ]
    
    def _get_context_from_rag(self, question: str) -> str:
        """
        Ruft Kontext vom RAG-Tool ab - verwendet die EXAKT gleiche Logik
        wie das produktive System.
        
        Args:
            question: Frage für den Retrieval
            
        Returns:
            Abgerufener Kontext als String
        """
        try:
            # Verwende das RAG-Tool direkt - keine Simulation!
            result = self.rag_tool._run(question)
            
            # Extrahiere nur den reinen Textinhalt ohne UI-Formatierung
            # aber behalte die gleiche Retrieval-Logik bei
            context_parts = []
            lines = result.split('\n')
            
            current_info_block = []
            for line in lines:
                # Überspringe UI-spezifische Zeilen
                if any(marker in line for marker in ['🎓', '📄', '💡', '❌', '**Information']):
                    if current_info_block:
                        # Vorherigen Block hinzufügen
                        clean_block = ' '.join(current_info_block).strip()
                        if clean_block:
                            context_parts.append(clean_block)
                        current_info_block = []
                    continue
                
                # Sammle Textinhalt
                clean_line = line.replace('**', '').replace('*', '').strip()
                if clean_line and not clean_line.startswith('(Quelle:') and not clean_line.startswith('[aus:'):
                    current_info_block.append(clean_line)
            
            # Letzten Block hinzufügen
            if current_info_block:
                clean_block = ' '.join(current_info_block).strip()
                if clean_block:
                    context_parts.append(clean_block)
            
            # Kombiniere alle Kontexte, aber beschränke die Länge
            combined_context = ' '.join(context_parts)
            
            # Wenn kein sauberer Kontext extrahiert werden konnte, verwende Original
            if not combined_context.strip():
                # Fallback: Verwende das originale Ergebnis ohne Formatierung
                combined_context = result.replace('🎓', '').replace('📄', '').replace('💡', '').replace('❌', '')
                combined_context = ' '.join(combined_context.split())  # Normalisiere Whitespace
            
            return combined_context if combined_context.strip() else "Kein relevanter Kontext gefunden."
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen des Kontexts: {e}")
            return f"Fehler beim Kontextabruf: {str(e)}"
    
    def _generate_answer(self, question: str, context: str) -> str:
        """
        Generiert eine Antwort basierend auf Frage und Kontext.
        Verwendet die gleiche Prompt-Struktur wie der produktive Agent.
        
        Args:
            question: Die Benutzerfrage
            context: Abgerufener Kontext
            
        Returns:
            Generierte Antwort
        """
        if not context.strip() or "Kein relevanter Kontext gefunden" in context:
            return "Entschuldigung, ich konnte keine relevanten Informationen in der Wissensdatenbank finden."
        
        # Prompt ähnlich dem produktiven System
        prompt = f"""Du bist ein hilfreicher Assistent für Studierende der Universität zu Köln.
Beantworte die folgende Frage basierend auf den gegebenen Informationen aus der Universitäts-Wissensdatenbank.

Verfügbare Informationen:
{context}

Frage: {question}

Antwort (nur basierend auf den verfügbaren Informationen, präzise und hilfreich):"""
        
        try:
            response = self.llm.invoke(prompt)
            return response.content.strip() if response.content else "Keine Antwort generiert."
        except Exception as e:
            logger.error(f"Fehler bei der Antwortgenerierung: {e}")
            return "Fehler bei der Antwortgenerierung."
    
    def prepare_evaluation_dataset(self) -> Dataset:
        """
        Erstellt das RAGAS-Evaluation-Dataset.
        
        Returns:
            Dataset mit allen erforderlichen Feldern für RAGAS
        """
        logger.info("Erstelle Evaluation-Dataset...")
        
        eval_data = {
            'question': [],
            'answer': [],
            'contexts': [],
            'ground_truth': []
        }
        
        # Speichere auch die Details für später
        self.evaluation_details = []
        
        for test_case in self.test_questions:
            question = test_case['question']
            ground_truth = test_case['ground_truth']
            topic = test_case['topic']
            
            logger.info(f"Verarbeite Frage: {question[:50]}...")
            
            # Kontext abrufen
            context = self._get_context_from_rag(question)
            
            # Antwort generieren
            answer = self._generate_answer(question, context)
            
            # Details speichern für Ergebnisse
            self.evaluation_details.append({
                'question': question,
                'answer': answer,
                'context': context,
                'ground_truth': ground_truth,
                'topic': topic
            })
            
            # Daten zum Dataset hinzufügen
            eval_data['question'].append(question)
            eval_data['answer'].append(answer)
            eval_data['contexts'].append([context])  # RAGAS erwartet Liste von Kontexten
            eval_data['ground_truth'].append(ground_truth)
            
            logger.info(f"✓ Verarbeitet: {len(eval_data['question'])}/{len(self.test_questions)}")
        
        return Dataset.from_dict(eval_data)
    
    async def run_evaluation(self) -> Dict[str, Any]:
        """
        Führt die vollständige RAGAS-Evaluation durch.
        
        Returns:
            Dictionary mit Evaluation-Ergebnissen
        """
        logger.info("🚀 Starte RAG-Evaluation mit RAGAS...")
        
        # Dataset vorbereiten
        dataset = self.prepare_evaluation_dataset()
        
        logger.info("📊 Führe RAGAS-Evaluation durch...")
        
        # RAGAS-Metriken definieren
        metrics = [
            context_precision,
            context_recall,
            faithfulness,
            answer_relevancy,
            ContextRelevance()
        ]
        
        try:
            # RAGAS-Evaluation durchführen
            # Note: RAGAS läuft synchron, daher verwenden wir asyncio.to_thread
            # RAGAS-Evaluation durchführen mit Tech-Stack-kompatiblen Einstellungen
            result = await asyncio.to_thread(
                evaluate,
                dataset=dataset,
                metrics=metrics,
                llm=self.llm,
                embeddings=self.embeddings,  # Gleiche Embeddings wie Scraper
                raise_exceptions=False  # Sanfterer Fehlerbehandlung
            )
            
            # Ergebnisse formatieren - robuste Extraktion
            evaluation_results = {
                'timestamp': datetime.now().isoformat(),
                'model': self.model_name,
                'dataset_size': len(dataset),
                'metrics': {},
                'overall_score': 0,
                'detailed_results': {}
            }
            
            # Robuste Metrik-Extraktion
            try:
                if hasattr(result, 'to_pandas'):
                    # RAGAS DataFrame-Format
                    df = result.to_pandas()
                    for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
                        if metric in df.columns:
                            metric_values = df[metric].dropna()
                            if len(metric_values) > 0:
                                evaluation_results['metrics'][metric] = float(metric_values.mean())
                    
                    # ContextRelevance separat behandeln
                    if 'ContextRelevance' in df.columns:
                        context_rel_values = df['ContextRelevance'].dropna()
                        if len(context_rel_values) > 0:
                            evaluation_results['metrics']['context_relevance'] = float(context_rel_values.mean())
                
                elif isinstance(result, dict):
                    # Dictionary-Format
                    for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
                        if metric in result:
                            value = result[metric]
                            if isinstance(value, (list, tuple)):
                                evaluation_results['metrics'][metric] = float(sum(value) / len(value)) if value else 0.0
                            else:
                                evaluation_results['metrics'][metric] = float(value)
                    
                    # ContextRelevance
                    if 'ContextRelevance' in result:
                        value = result['ContextRelevance']
                        if isinstance(value, (list, tuple)):
                            evaluation_results['metrics']['context_relevance'] = float(sum(value) / len(value)) if value else 0.0
                        else:
                            evaluation_results['metrics']['context_relevance'] = float(value)
                
                else:
                    logger.warning("Unbekanntes RAGAS-Ergebnisformat")
                    evaluation_results['metrics'] = {
                        'context_precision': 0.0,
                        'context_recall': 0.0,
                        'faithfulness': 0.0,
                        'answer_relevancy': 0.0,
                        'context_relevance': 0.0
                    }
                
            except Exception as e:
                logger.error(f"Fehler bei Metrik-Extraktion: {e}")
                evaluation_results['metrics'] = {
                    'context_precision': 0.0,
                    'context_recall': 0.0,
                    'faithfulness': 0.0,
                    'answer_relevancy': 0.0,
                    'context_relevance': 0.0
                }
            
            evaluation_results['overall_score'] = self._calculate_overall_score(evaluation_results['metrics'])
            evaluation_results['detailed_results'] = self._create_detailed_analysis(dataset, result)
            evaluation_results['question_answers'] = self.evaluation_details  # Füge Antworten hinzu
            
            self.results = evaluation_results
            logger.info("✅ RAGAS-Evaluation abgeschlossen!")
            
            return evaluation_results
            
        except Exception as e:
            logger.error(f"❌ Fehler bei der RAGAS-Evaluation: {e}")
            raise
    
    def _calculate_overall_score(self, metrics_dict) -> float:
        """
        Berechnet einen gewichteten Gesamtscore.
        
        Args:
            metrics_dict: Dictionary mit Metrik-Werten
            
        Returns:
            Gewichteter Gesamtscore (0-1)
        """
        weights = {
            'context_precision': 0.25,
            'context_recall': 0.25,
            'faithfulness': 0.25,
            'answer_relevancy': 0.25
        }
        
        total_score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in metrics_dict:
                score = metrics_dict[metric]
                if isinstance(score, (int, float)) and not (isinstance(score, bool)):
                    total_score += float(score) * weight
                    total_weight += weight
        
        return round(total_score / total_weight if total_weight > 0 else 0, 3)
    
    def _create_detailed_analysis(self, dataset: Dataset, ragas_result) -> Dict[str, Any]:
        """
        Erstellt eine detaillierte Analyse der Ergebnisse.
        
        Args:
            dataset: Evaluation-Dataset
            ragas_result: RAGAS-Ergebnisse
            
        Returns:
            Detaillierte Analyse
        """
        analysis = {
            'per_question_analysis': [],
            'topic_analysis': {},
            'strengths': [],
            'weaknesses': [],
            'recommendations': []
        }
        
        # Versuche DataFrame-Extraktion für Per-Question-Analyse
        try:
            if hasattr(ragas_result, 'to_pandas'):
                df = ragas_result.to_pandas()
                for idx, row in df.iterrows():
                    if idx < len(self.test_questions):
                        question_analysis = {
                            'question': dataset[idx]['question'],
                            'topic': self.test_questions[idx]['topic'],
                            'scores': {}
                        }
                        
                        # Extrahiere verfügbare Scores
                        for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
                            if metric in row and row[metric] is not None:
                                try:
                                    question_analysis['scores'][metric] = float(row[metric])
                                except (ValueError, TypeError):
                                    continue
                        
                        analysis['per_question_analysis'].append(question_analysis)
        except Exception as e:
            logger.warning(f"Fehler bei Per-Question-Analyse: {e}")
        
        # Topic-basierte Analyse
        topics = {}
        for i, test_case in enumerate(self.test_questions):
            topic = test_case['topic']
            if topic not in topics:
                topics[topic] = []
            
            if i < len(analysis['per_question_analysis']):
                topics[topic].append(analysis['per_question_analysis'][i]['scores'])
        
        for topic, scores_list in topics.items():
            if scores_list and any(scores_list):  # Überprüfe, ob nicht-leere Scores vorhanden sind
                avg_scores = {}
                for metric in ['context_precision', 'context_recall', 'faithfulness', 'answer_relevancy']:
                    metric_scores = [s.get(metric, 0) for s in scores_list if metric in s]
                    if metric_scores:
                        avg_scores[metric] = sum(metric_scores) / len(metric_scores)
                
                if avg_scores:  # Nur hinzufügen wenn Scores vorhanden
                    analysis['topic_analysis'][topic] = avg_scores
        
        # Generische Empfehlungen basierend auf häufigen Problemen
        analysis['recommendations'].extend([
            "Überprüfen Sie die Qualität der Wissensdatenbank",
            "Experimentieren Sie mit verschiedenen Chunk-Größen",
            "Testen Sie erweiterte Embedding-Modelle",
            "Optimieren Sie die Prompt-Templates"
        ])
        
        return analysis
    
    def save_results(self, output_path: Optional[str] = None) -> str:
        """
        Speichert die Evaluation-Ergebnisse.
        
        Args:
            output_path: Pfad für die Ausgabedatei
            
        Returns:
            Pfad der gespeicherten Datei
        """
        if not self.results:
            raise ValueError("Keine Ergebnisse zum Speichern. Führen Sie zuerst run_evaluation() aus.")
        
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"rag_evaluation_results_{timestamp}.json"
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📁 Ergebnisse gespeichert: {output_file}")
        return str(output_file)
    
    def print_summary(self):
        """Gibt eine Zusammenfassung der Ergebnisse aus."""
        if not self.results:
            print("❌ Keine Ergebnisse verfügbar. Führen Sie zuerst run_evaluation() aus.")
            return
        
        print("\n" + "="*80)
        print("🎯 RAG-EVALUATION ZUSAMMENFASSUNG")
        print("="*80)
        
        metrics = self.results['metrics']
        print(f"📊 **Modell**: {self.results['model']}")
        print(f"📊 **Dataset-Größe**: {self.results['dataset_size']} Fragen")
        print(f"📊 **Timestamp**: {self.results['timestamp']}")
        print("\n📈 **RAGAS-Metriken**:")
        print("-" * 40)
        
        for metric, score in metrics.items():
            status = "🟢" if score >= 0.8 else "🟡" if score >= 0.6 else "🔴"
            print(f"{status} {metric.replace('_', ' ').title()}: {score:.3f}")
        
        print(f"\n🎯 **Gesamtscore**: {self.results['overall_score']:.3f}")
        
        # Stärken und Schwächen
        analysis = self.results['detailed_results']
        
        if analysis['strengths']:
            print(f"\n✅ **Stärken**:")
            for strength in analysis['strengths']:
                print(f"   • {strength}")
        
        if analysis['weaknesses']:
            print(f"\n⚠️ **Schwächen**:")
            for weakness in analysis['weaknesses']:
                print(f"   • {weakness}")
        
        if analysis['recommendations']:
            print(f"\n💡 **Empfehlungen**:")
            for recommendation in analysis['recommendations']:
                print(f"   • {recommendation}")
        
        # Frage-Antwort Details anzeigen
        if 'question_answers' in self.results:
            print(f"\n📝 **Generierte Antworten**:")
            print("-" * 40)
            for i, qa in enumerate(self.results['question_answers'], 1):
                print(f"\n{i}. **Frage**: {qa['question']}")
                print(f"   **Antwort**: {qa['answer']}")
                print(f"   **Thema**: {qa['topic']}")
                if len(qa['answer']) > 100:
                    print(f"   **Länge**: {len(qa['answer'])} Zeichen")
        
        # Topic-Analyse
        if analysis['topic_analysis']:
            print(f"\n📂 **Themen-Analyse**:")
            print("-" * 40)
            for topic, scores in analysis['topic_analysis'].items():
                avg_score = sum(scores.values()) / len(scores) if scores else 0
                status = "🟢" if avg_score >= 0.8 else "🟡" if avg_score >= 0.6 else "🔴"
                print(f"{status} {topic.title()}: {avg_score:.3f}")
        
        print("\n" + "="*80)


async def main():
    """Hauptfunktion für die RAG-Evaluation."""
    print("🚀 Starte RAG-Evaluation mit RAGAS...")
    print("="*60)
    
    try:
        # Evaluator erstellen
        evaluator = RAGEvaluator()
        
        # Evaluation durchführen
        results = await evaluator.run_evaluation()
        
        # Ergebnisse anzeigen
        evaluator.print_summary()
        
        # Ergebnisse speichern
        output_file = evaluator.save_results()
        print(f"\n💾 Detaillierte Ergebnisse gespeichert in: {output_file}")
        
        print("\n✅ RAG-Evaluation erfolgreich abgeschlossen!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Evaluation abgebrochen durch Benutzer.")
    except Exception as e:
        print(f"\n❌ Fehler bei der Evaluation: {e}")
        logger.exception("Detaillierter Fehler:")


if __name__ == "__main__":
    asyncio.run(main())