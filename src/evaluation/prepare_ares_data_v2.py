"""
ARES-Datenaufbereitung via LangSmith Tracing
=============================================

Nutzt LangSmith Tracing, um Retrieved Documents aus RAG-Tool zu extrahieren.
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
import logging
import os

# Projekt-Root zum Path hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.react_agent import create_react_agent
from config.settings import settings

# LangSmith Client für Trace-Abruf
try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False
    print("⚠️  LangSmith nicht verfügbar - Bitte installieren mit: pip install langsmith")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ARESDataPreparerWithTracing:
    """Konvertiert ARES-Testset.CSV in ARES-kompatible TSV-Dateien via LangSmith Tracing."""
    
    def __init__(self, csv_path: Path, output_dir: Path):
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.agent = None
        self.langsmith_client = None
        self.trace_map = {}  # Maps session_id -> trace_info
    
    @staticmethod
    def clean_agent_answer(answer: str) -> str:
        """Entfernt Agent-Selbstbewertung aus der Antwort."""
        import re
        # Entferne alles ab "**Bewertung**:" oder "**Erfüllt die Frage"
        patterns = [
            r'\*\*Bewertung\*\*:.*$',
            r'\*\*Erfüllt die Frage.*$',
            r'\*\*War meine Antwort.*$',
            r'\*\*Hat der Benutzer.*$',
            r'\*\*Sollte diese Anfrage.*$'
        ]
        
        cleaned = answer
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.MULTILINE)
        
        # Entferne trailing whitespace und mehrfache Newlines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        return cleaned.strip()
    
    @staticmethod
    def clean_context(context: str) -> str:
        """Bereinigt Kontext-Text von Markdown-Artefakten."""
        import re
        # Entferne "--- Page X ---" Marker
        cleaned = re.sub(r'^---\s*Page\s+\d+\s*---\s*$', '', context, flags=re.MULTILINE)
        # Entferne führende/trailing Leerzeilen
        cleaned = '\n'.join(line for line in cleaned.split('\n') if line.strip())
        return cleaned.strip()
    
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
        
        # DEBUG: Nur erste 10 Fragen für Tests
        questions = questions[:10]
        logger.info(f"✓ {len(questions)} Fragen aus CSV geladen (limitiert auf 10 für Debugging)")
        return questions
    
    def initialize_agent(self):
        """Initialisiert den WiSo RAG-Agent und LangSmith Client."""
        logger.info("Initialisiere WiSo RAG-Agent und LangSmith Client...")
        try:
            # Agent für Antwortgenerierung
            self.agent = create_react_agent()
            
            # LangSmith Client für Trace-Abruf
            if LANGSMITH_AVAILABLE and settings.LANGSMITH_TRACING:
                self.langsmith_client = Client(
                    api_key=settings.LANGSMITH_API_KEY,
                    api_url="https://api.smith.langchain.com"
                )
                logger.info("✓ LangSmith Client initialisiert")
            else:
                logger.warning("⚠️  LangSmith Tracing nicht aktiviert - Kontexte werden nicht extrahiert")
            
            logger.info("✓ Agent erfolgreich initialisiert")
        except Exception as e:
            logger.error(f"✗ Fehler bei Initialisierung: {e}")
            raise
    
    def generate_rag_response(self, question: str, question_id: str) -> Dict[str, Any]:
        """
        Generiert RAG-Antwort für eine Frage.
        
        Returns:
            Dict mit 'answer' und 'session_id'
        """
        try:
            # Eindeutige Session-ID für Tracing
            session_id = f"ares_eval_{question_id}_{hash(question)}"
            
            # WICHTIG: Lösche Agent-Memory für isolierte Evaluation
            self.agent.memory.clear()
            
            # Agent-Antwort generieren (mit automatischem LangSmith Tracing)
            answer = self.agent.chat(message=question, session_id=session_id)
            
            return {
                'answer': answer,
                'session_id': session_id
            }
        
        except Exception as e:
            logger.error(f"Fehler bei RAG-Generierung für Frage '{question[:50]}...': {e}")
            logger.exception("Vollständiger Traceback:")
            return {
                'answer': f"[Fehler: {str(e)}]",
                'session_id': None
            }
    
    def extract_contexts_from_traces(self, session_id: str) -> List[str]:
        """
        Extrahiert Retrieved Documents aus LangSmith Traces.
        
        Args:
            session_id: Die Session-ID des Traces
            
        Returns:
            Liste von Dokument-Texten
        """
        if not self.langsmith_client or not session_id:
            return ["[Kontext nicht verfügbar - LangSmith Tracing deaktiviert]"]
        
        try:
            import time
            # Kurz warten, damit Trace in LangSmith verfügbar ist
            time.sleep(2)
            
            # SCHRITT 1: Finde den Root-Run mit der session_id in den Metadaten
            # Filter-Syntax: has(metadata, "key") prüft ob Metadata-Key existiert
            root_runs = list(self.langsmith_client.list_runs(
                project_name=settings.LANGSMITH_PROJECT,
                is_root=True,
                limit=20  # Nur die letzten 20 Root-Runs
            ))
            
            # Clientseitig nach session_id filtern
            matching_root = None
            for run in root_runs:
                if hasattr(run, 'metadata') and run.metadata and run.metadata.get('session_id') == session_id:
                    matching_root = run
                    break
            
            if not matching_root:
                logger.warning(f"Kein Root-Run mit session_id '{session_id}' gefunden")
                return ["[Kein Trace mit dieser Session-ID gefunden]"]
            
            logger.info(f"✓ Root-Run gefunden: {matching_root.id}")
            
            # SCHRITT 2: Hole alle Child-Runs dieses Traces (via trace_id)
            trace_id = matching_root.trace_id if hasattr(matching_root, 'trace_id') else matching_root.id
            all_runs_in_trace = list(self.langsmith_client.list_runs(
                project_name=settings.LANGSMITH_PROJECT,
                trace_id=trace_id
            ))
            
            logger.info(f"✓ {len(all_runs_in_trace)} Runs in diesem Trace gefunden")
            
            contexts = []
            
            # SCHRITT 3: Durchsuche alle Runs nach Retriever-Outputs
            for run in all_runs_in_trace:
                logger.debug(f"Prüfe Run: {run.name if hasattr(run, 'name') else 'Unknown'}, Type: {run.run_type if hasattr(run, 'run_type') else 'Unknown'}")
                
                # Prüfe ob Run ein Retriever ist
                if hasattr(run, 'run_type') and run.run_type == 'retriever':
                    # Extrahiere Outputs
                    if hasattr(run, 'outputs') and run.outputs:
                        outputs = run.outputs
                        logger.debug(f"Retriever-Output gefunden: {type(outputs)}")
                        
                        # LangSmith speichert Retrieved Documents in outputs["output"] als Liste
                        if isinstance(outputs, dict) and 'output' in outputs:
                            documents = outputs['output']
                            if isinstance(documents, list):
                                for doc in documents:
                                    if isinstance(doc, dict) and 'page_content' in doc:
                                        contexts.append(doc['page_content'])
                                        logger.debug(f"✓ Context extrahiert: {doc['page_content'][:100]}...")
                        
                        # Fallback: documents key (falls andere Implementierung)
                        elif isinstance(outputs, dict) and 'documents' in outputs:
                            for doc in outputs['documents']:
                                if isinstance(doc, dict) and 'page_content' in doc:
                                    contexts.append(doc['page_content'])
                                    logger.debug(f"✓ Context extrahiert: {doc['page_content'][:100]}...")
                        
                        # Fallback: Outputs ist direkt eine Liste
                        elif isinstance(outputs, list):
                            for doc in outputs:
                                if isinstance(doc, dict):
                                    if 'page_content' in doc:
                                        contexts.append(doc['page_content'])
                                        logger.debug(f"✓ Context extrahiert: {doc['page_content'][:100]}...")
                                    elif 'text' in doc:
                                        contexts.append(doc['text'])
                                        logger.debug(f"✓ Context extrahiert: {doc['text'][:100]}...")
            
            if not contexts:
                logger.warning(f"Keine Retriever-Kontexte in Trace gefunden für session_id: {session_id}")
                logger.warning(f"Gefundene Run-Typen: {[run.run_type for run in all_runs_in_trace if hasattr(run, 'run_type')]}")
                return ["[Keine Dokumente im Trace gefunden]"]
            
            logger.info(f"✓ {len(contexts)} Kontexte erfolgreich extrahiert")
            return contexts
        
        except Exception as e:
            logger.error(f"Fehler beim Extrahieren von Kontexten aus Trace: {e}")
            logger.exception("Vollständiger Traceback:")
            return [f"[Fehler beim Trace-Abruf: {str(e)}]"]
    
    def process_all_questions(self, questions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Verarbeitet alle Fragen und generiert RAG-Antworten."""
        results = []
        
        logger.info(f"Starte RAG-Generierung für {len(questions)} Fragen...")
        
        for q_data in tqdm(questions, desc="Generiere RAG-Antworten"):
            question = q_data['question']
            question_id = q_data['id']
            
            # RAG-Antwort generieren
            rag_result = self.generate_rag_response(question, question_id)
            
            results.append({
                'id': question_id,
                'question': question,
                'rag_answer': rag_result['answer'],
                'session_id': rag_result['session_id'],
                'expected_answer': q_data['expected_answer'],
                'category': q_data['category'],
                'difficulty': q_data['difficulty'],
                'context_hint': q_data['context_hint']
            })
        
        logger.info(f"✓ {len(results)} RAG-Antworten erfolgreich generiert")
        
        # WICHTIG: Jetzt Kontexte aus Traces extrahieren
        if self.langsmith_client:
            logger.info("Extrahiere Kontexte aus LangSmith Traces...")
            for result in tqdm(results, desc="Extrahiere Kontexte"):
                contexts = self.extract_contexts_from_traces(result['session_id'])
                result['contexts'] = contexts
            logger.info("✓ Kontexte aus Traces extrahiert")
        else:
            # Fallback wenn LangSmith nicht verfügbar
            for result in results:
                result['contexts'] = ["[LangSmith Tracing nicht verfügbar]"]
        
        return results
    
    def write_unlabeled_tsv(self, results: List[Dict[str, Any]], filename: str = "ares_unlabeled_evaluation.tsv"):
        """
        Schreibt unlabeled TSV für ARES (Format: Question | Answer | Context | ID).
        """
        output_path = self.output_dir / filename
        
        # UTF-8 mit BOM für Excel-Kompatibilität
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
            # Header (ARES erwartet "Document" statt "Context")
            writer.writerow(['Question', 'Answer', 'Document', 'ID'])
            
            # Daten
            for r in results:
                # Bereinige Antwort von Selbstbewertung
                cleaned_answer = self.clean_agent_answer(r['rag_answer'])
                
                # Bereinige und kombiniere Kontexte
                contexts = r.get('contexts', [])
                cleaned_contexts = [self.clean_context(ctx) for ctx in contexts]
                context_combined = "\n---\n".join(cleaned_contexts)
                
                writer.writerow([
                    r['question'],
                    cleaned_answer,
                    context_combined,
                    f"eval_{r['id']}"
                ])
        
        logger.info(f"✓ Unlabeled TSV gespeichert: {output_path}")
        return output_path
    
    def write_reference_csv(self, results: List[Dict[str, Any]], filename: str = "ares_results_with_reference.csv"):
        """
        Speichert vollständige Ergebnisse inkl. expected_answer für spätere Analyse.
        """
        output_path = self.output_dir / filename
        
        # UTF-8 mit BOM für Excel-Kompatibilität
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow([
                'id', 'question', 'rag_answer', 'expected_answer', 
                'full_context', 'category', 'difficulty'
            ])
            
            for r in results:
                # Vollständiger Kontext (alle retrieved Documents)
                contexts = r.get('contexts', [])
                cleaned_contexts = [self.clean_context(ctx) for ctx in contexts]
                full_context = "\n---\n".join(cleaned_contexts)
                
                writer.writerow([
                    r['id'],
                    r['question'],
                    r['rag_answer'],
                    r['expected_answer'],
                    full_context,
                    r['category'],
                    r['difficulty']
                ])
        
        logger.info(f"✓ Referenz-CSV gespeichert: {output_path}")
        return output_path
    
    def run(self):
        """Hauptprozess: CSV → TSV-Konvertierung."""
        logger.info("=" * 80)
        logger.info("ARES-Datenaufbereitung - Schritt 1: RAG-Antworten + Kontexte via LangSmith")
        logger.info("=" * 80)
        
        # 1. Fragen laden
        questions = self.load_questions()
        
        # 2. Agent initialisieren
        self.initialize_agent()
        
        # 3. RAG-Antworten generieren + Kontexte aus Traces extrahieren
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
    
    preparer = ARESDataPreparerWithTracing(csv_path, output_dir)
    preparer.run()


if __name__ == "__main__":
    main()
