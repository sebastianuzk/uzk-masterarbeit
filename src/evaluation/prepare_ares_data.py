"""
ARES-Datenaufbereitung: CSV → TSV-Konvertierung
=================================================

Dieses Skript generiert ARES-kompatible TSV-Dateien aus dem ARES-Testset.CSV:
1. Liest die 40 Testfragen
2. Ruft Dokumente direkt aus der Vector-DB ab
3. Generiert RAG-Antworten mit dem WiSo-Agent
4. Erzeugt unlabeled_evaluation.tsv für ARES
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
import logging

# Projekt-Root zum Path hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.react_agent import create_react_agent
from src.tools.rag_tool import create_university_rag_tool

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ARESDataPreparer:
    """Konvertiert ARES-Testset.CSV in ARES-kompatible TSV-Dateien."""
    
    def __init__(self, csv_path: Path, output_dir: Path):
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.agent = None
        self.rag_tool = None
    
    def load_questions(self) -> List[Dict[str, str]]:
        """Liest Fragen aus der CSV-Datei."""
        questions = []
        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig entfernt BOM
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                questions.append({
                    'id': row['id'],
                    'question': row['question'],
                    'expected_answer': row['expected_answer'],
                    'context_hint': row['context_hint'],
                    'category': row['category'],
                    'difficulty': row['difficulty']
                })
        logger.info(f"✓ {len(questions)} Fragen aus CSV geladen")
        return questions
    
    def initialize_agent(self):
        """Initialisiert den WiSo RAG-Agent und das RAG-Tool."""
        logger.info("Initialisiere WiSo RAG-Agent und RAG-Tool...")
        try:
            # Agent für Antwortgenerierung
            self.agent = create_react_agent()
            
            # RAG-Tool direkt für Dokumenten-Retrieval
            self.rag_tool = create_university_rag_tool()
            
            logger.info("✓ Agent und RAG-Tool erfolgreich initialisiert")
        except Exception as e:
            logger.error(f"✗ Fehler bei Initialisierung: {e}")
            raise
    
    def generate_rag_response(self, question: str) -> Dict[str, Any]:
        """
        Generiert RAG-Antwort für eine Frage.
        
        Returns:
            Dict mit 'answer' und 'contexts' (Liste von Dokumenten)
        """
        try:
            # Schritt 1: Dokumente direkt über RAG-Tool abrufen
            rag_result = self.rag_tool.invoke({"query": question})
            
            # Extrahiere Dokumente aus dem Result
            retrieved_docs = []
            if isinstance(rag_result, str):
                # Falls String zurückkommt, ist es bereits formatiert
                retrieved_docs = [rag_result]
            elif isinstance(rag_result, dict) and "documents" in rag_result:
                retrieved_docs = rag_result["documents"]
            elif isinstance(rag_result, list):
                retrieved_docs = [str(doc) for doc in rag_result]
            else:
                # Fallback: Konvertiere zu String
                retrieved_docs = [str(rag_result)]
            
            # Schritt 2: Agent-Antwort generieren
            answer = self.agent.chat(message=question, session_id=f"ares_eval_{hash(question)}")
            
            # Kontexte zusammenfügen
            contexts = retrieved_docs if retrieved_docs else ["[Keine Dokumente abgerufen]"]
            
            return {
                'answer': answer,
                'contexts': contexts
            }
        
        except Exception as e:
            logger.error(f"Fehler bei RAG-Generierung für Frage '{question[:50]}...': {e}")
            logger.exception("Vollständiger Traceback:")
            return {
                'answer': f"[Fehler: {str(e)}]",
                'contexts': ["[Fehler bei Kontext-Abruf]"]
            }
    
    def process_all_questions(self, questions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Verarbeitet alle Fragen und generiert RAG-Antworten."""
        results = []
        
        logger.info(f"Starte RAG-Generierung für {len(questions)} Fragen...")
        
        for q_data in tqdm(questions, desc="Generiere RAG-Antworten"):
            question = q_data['question']
            
            # RAG-Antwort generieren
            rag_result = self.generate_rag_response(question)
            
            # Kontexte zusammenfügen (ARES erwartet einen einzigen Context-String)
            context_combined = "\n---\n".join(rag_result['contexts'])
            
            results.append({
                'id': q_data['id'],
                'question': question,
                'rag_answer': rag_result['answer'],
                'context': context_combined,
                'expected_answer': q_data['expected_answer'],
                'category': q_data['category'],
                'difficulty': q_data['difficulty'],
                'context_hint': q_data['context_hint']
            })
        
        logger.info(f"✓ {len(results)} RAG-Antworten erfolgreich generiert")
        return results
    
    def write_unlabeled_tsv(self, results: List[Dict[str, Any]], filename: str = "ares_unlabeled_evaluation.tsv"):
        """
        Schreibt unlabeled TSV für ARES (Format: Question | Answer | Context | ID).
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter='\t')
            # Header
            writer.writerow(['Question', 'Answer', 'Context', 'ID'])
            
            # Daten
            for r in results:
                writer.writerow([
                    r['question'],
                    r['rag_answer'],
                    r['context'],
                    f"eval_{r['id']}"
                ])
        
        logger.info(f"✓ Unlabeled TSV gespeichert: {output_path}")
        return output_path
    
    def write_reference_csv(self, results: List[Dict[str, Any]], filename: str = "ares_results_with_reference.csv"):
        """
        Speichert vollständige Ergebnisse inkl. expected_answer für spätere Analyse.
        """
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                'id', 'question', 'rag_answer', 'expected_answer', 
                'context_preview', 'category', 'difficulty'
            ])
            
            for r in results:
                # Context-Preview (erste 200 Zeichen)
                context_preview = r['context'][:200] + "..." if len(r['context']) > 200 else r['context']
                
                writer.writerow([
                    r['id'],
                    r['question'],
                    r['rag_answer'],
                    r['expected_answer'],
                    context_preview,
                    r['category'],
                    r['difficulty']
                ])
        
        logger.info(f"✓ Referenz-CSV gespeichert: {output_path}")
        return output_path
    
    def run(self):
        """Hauptprozess: CSV → TSV-Konvertierung."""
        logger.info("=" * 80)
        logger.info("ARES-Datenaufbereitung - Schritt 1: RAG-Antworten generieren")
        logger.info("=" * 80)
        
        # 1. Fragen laden
        questions = self.load_questions()
        
        # 2. Agent initialisieren
        self.initialize_agent()
        
        # 3. RAG-Antworten generieren
        results = self.process_all_questions(questions)
        
        # 4. TSV-Dateien schreiben
        unlabeled_path = self.write_unlabeled_tsv(results)
        reference_path = self.write_reference_csv(results)
        
        # 5. Zusammenfassung
        logger.info("\n" + "=" * 80)
        logger.info("✓ SCHRITT 1 ABGESCHLOSSEN")
        logger.info("=" * 80)
        logger.info(f"Generierte Dateien:")
        logger.info(f"  1. {unlabeled_path}")
        logger.info(f"     → ARES Unlabeled Evaluation Set (40 Q/A/Context-Tripel)")
        logger.info(f"  2. {reference_path}")
        logger.info(f"     → Referenz-CSV mit RAG- und Expected-Antworten")
        logger.info("\nNächster Schritt:")
        logger.info("  → Few-Shot-Beispiele manuell erstellen (3-5 Beispiele annotieren)")
        logger.info("=" * 80)


def main():
    """Entry-Point für die Datenaufbereitung."""
    csv_path = project_root / "ARES-Testset.CSV"
    output_dir = project_root / "src" / "evaluation" / "data"
    
    if not csv_path.exists():
        logger.error(f"✗ CSV-Datei nicht gefunden: {csv_path}")
        sys.exit(1)
    
    preparer = ARESDataPreparer(csv_path, output_dir)
    preparer.run()


if __name__ == "__main__":
    main()
