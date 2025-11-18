"""
ARES Evaluation Runner
======================

Vollautomatisierte ARES-Evaluation Pipeline:
1. Konvertiert Few-Shot CSV → TSV (ARES-Format)
2. Installiert/prüft ARES-Framework
3. Führt UES/IDP Evaluation aus
4. Generiert Ergebnisreport
"""

import csv
import sys
from pathlib import Path
import logging
import subprocess
import json

# Projekt-Root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ARESEvaluationRunner:
    """Automatisierte ARES-Evaluation Pipeline."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.few_shot_csv = data_dir / "ares_few_shot_examples.csv"
        self.few_shot_tsv = data_dir / "ares_few_shot_prompt_for_judge_scoring.tsv"
        self.unlabeled_tsv = data_dir / "ares_unlabeled_evaluation.tsv"
        self.results_json = data_dir / "ares_evaluation_results.json"
        self.results_csv = data_dir / "ares_evaluation_scores.csv"
        
    def step1_convert_fewshot_to_tsv(self):
        """Konvertiert Few-Shot CSV → ARES-TSV Format."""
        logger.info("\n" + "="*80)
        logger.info("SCHRITT 1: Few-Shot CSV → ARES TSV")
        logger.info("="*80)
        
        if not self.few_shot_csv.exists():
            logger.error(f"❌ Few-Shot CSV nicht gefunden: {self.few_shot_csv}")
            return False
        
        logger.info(f"✓ Lese Few-Shot Examples aus: {self.few_shot_csv.name}")
        
        # CSV lesen
        examples = []
        with open(self.few_shot_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                examples.append({
                    'Question': row['question'],
                    'Answer': row['rag_answer'],
                    'Document': row['full_context'],
                    'Context_Relevance_Label': row['Context_Relevance_Label'],
                    'Answer_Faithfulness_Label': row['Answer_Faithfulness_Label'],
                    'Answer_Relevance_Label': row['Answer_Relevance_Label']
                })
        
        logger.info(f"✓ {len(examples)} Few-Shot Examples geladen")
        
        # TSV schreiben (ARES-Format)
        with open(self.few_shot_tsv, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, 
                fieldnames=['Question', 'Answer', 'Document', 
                           'Context_Relevance_Label', 'Answer_Faithfulness_Label', 
                           'Answer_Relevance_Label'],
                delimiter='\t',
                quoting=csv.QUOTE_MINIMAL
            )
            writer.writeheader()
            writer.writerows(examples)
        
        logger.info(f"✓ Few-Shot TSV erstellt: {self.few_shot_tsv.name}")
        logger.info(f"  → Format: Question | Answer | Context | 3 Labels (0/1)")
        return True
    
    def step2_check_ares_installation(self):
        """Prüft ARES-Installation, installiert falls nötig."""
        logger.info("\n" + "="*80)
        logger.info("SCHRITT 2: ARES-Framework Installation")
        logger.info("="*80)
        
        try:
            import ares
            logger.info("✓ ARES bereits installiert")
            return True
        except ImportError:
            logger.warning("⚠️  ARES nicht gefunden, starte Installation...")
            
            try:
                # ARES installieren
                subprocess.check_call([
                    sys.executable, '-m', 'pip', 'install', 
                    'ares-ai', '--upgrade'
                ])
                logger.info("✓ ARES erfolgreich installiert")
                return True
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ ARES Installation fehlgeschlagen: {e}")
                return False
    
    def step3_configure_ares(self):
        """Konfiguriert ARES für LLM-Judge."""
        logger.info("\n" + "="*80)
        logger.info("SCHRITT 3: ARES-Konfiguration")
        logger.info("="*80)
        
        # ARES Config
        config = {
            "model_choice": "gpt-4",  # Oder "gpt-3.5-turbo" für schnellere/günstigere Evaluation
            "api_key": settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None,
            "evaluation_datasets": {
                "unlabeled": str(self.unlabeled_tsv),
                "few_shot": str(self.few_shot_tsv)
            },
            "metrics": ["context_relevance", "answer_faithfulness", "answer_relevance"]
        }
        
        if not config["api_key"]:
            logger.warning("⚠️  OPENAI_API_KEY nicht in settings.py konfiguriert")
            logger.warning("    → Alternative: Verwende lokales LLM (z.B. Ollama)")
            config["model_choice"] = "local"  # Placeholder für lokales Modell
        
        logger.info(f"✓ Konfiguration:")
        logger.info(f"  - LLM Judge: {config['model_choice']}")
        logger.info(f"  - Unlabeled Set: {self.unlabeled_tsv.name}")
        logger.info(f"  - Few-Shot Set: {self.few_shot_tsv.name}")
        logger.info(f"  - Metriken: {', '.join(config['metrics'])}")
        
        return config
    
    def step4_run_ares_evaluation(self, config: dict):
        """Führt ARES Evaluation mit lokalem Ollama-Modell aus."""
        logger.info("\n" + "="*80)
        logger.info("SCHRITT 4: ARES Evaluation (Lokales Ollama)")
        logger.info("="*80)
        
        # Prüfe, ob OpenAI API Key vorhanden
        has_openai_key = hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY
        
        if has_openai_key:
            # Verwende ARES mit OpenAI (falls Key konfiguriert)
            logger.info("OpenAI API Key gefunden - verwende ARES mit GPT")
            return self._run_ares_with_openai()
        else:
            # Standardmäßig: Custom Ollama Adapter (zuverlässiger als vLLM-Modus)
            logger.info("Kein OpenAI Key - verwende lokales Ollama-Modell")
            logger.info("ℹ️  Nutze Custom Ollama Adapter (optimiert für lokale Modelle)")
            return self._run_custom_ollama_adapter()
    
    def _run_ares_with_openai(self):
        """Führt ARES mit OpenAI API aus (optional)."""
        try:
            from ares import ARES
            
            logger.info("Initialisiere ARES mit OpenAI/GPT...")
            
            ues_idp_config = {
                "in_domain_prompts_dataset": str(self.few_shot_tsv),
                "unlabeled_evaluation_set": str(self.unlabeled_tsv),
                "model_choice": "gpt-3.5-turbo-0125"
            }
            
            evaluator = ARES(ues_idp=ues_idp_config)
            
            logger.info("Starte Evaluation mit GPT-3.5...")
            results = evaluator.ues_idp()
            
            logger.info("\n✓ ARES (OpenAI) Evaluation abgeschlossen!")
            self._save_results(results)
            return results
            
        except Exception as e:
            logger.error(f"❌ OpenAI-Evaluation fehlgeschlagen: {e}")
            logger.warning("→ Falle zurück auf lokales Ollama-Modell")
            return self._run_ares_with_ollama()
    
    def _run_ares_with_ollama(self):
        """Führt ARES mit lokalem Ollama via vLLM-Interface aus (EXAKT nach Doku)."""
        try:
            from ares import ARES
            
            logger.info("Initialisiere ARES mit lokalem Ollama (vLLM-Modus)...")
            
            # EXAKT wie in ARES-Dokumentation:
            # https://ares-ai.vercel.app/local_model_execution.html
            ues_idp_config = {
                "in_domain_prompts_dataset": str(self.few_shot_tsv),
                "unlabeled_evaluation_set": str(self.unlabeled_tsv),
                "model_choice": settings.OLLAMA_MODEL,  # z.B. "qwen3:8b"
                "vllm": True,  # Toggle vLLM to True
                "host_url": f"{settings.OLLAMA_BASE_URL}/v1"  # Host URL followed by "/v1"
            }
            
            logger.info("✓ ARES Config (vLLM-Mode):")
            logger.info(f"  - Model: {settings.OLLAMA_MODEL}")
            logger.info(f"  - Host: {settings.OLLAMA_BASE_URL}/v1")
            logger.info(f"  - vLLM: True")
            
            evaluator = ARES(ues_idp=ues_idp_config)
            
            logger.info("\nStarte Evaluation mit lokalem Ollama...")
            results = evaluator.ues_idp()
            
            logger.info("\n✓ ARES (Ollama) Evaluation abgeschlossen!")
            self._save_results(results)
            return results
            
        except Exception as e:
            logger.error(f"❌ ARES-Evaluation fehlgeschlagen: {e}")
            logger.error(f"    Typ: {type(e).__name__}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Letzter Fallback: Custom Ollama Adapter
            logger.warning("\n→ Letzter Fallback: Custom Ollama Adapter")
            return self._run_custom_ollama_adapter()
    
    def _run_custom_ollama_adapter(self):
        """Fallback: Custom Ollama Adapter (wenn ARES vLLM nicht funktioniert)."""
        try:
            from src.evaluation.ares_ollama_adapter import OllamaARESScorer
            
            logger.info("Initialisiere Custom Ollama Scorer...")
            
            scorer = OllamaARESScorer(
                few_shot_examples_path=self.few_shot_tsv
            )
            
            logger.info("✓ Custom Scorer initialisiert")
            logger.info(f"  - Modell: {settings.OLLAMA_MODEL}")
            
            results = scorer.evaluate_dataset(
                unlabeled_tsv_path=self.unlabeled_tsv
            )
            
            logger.info("\n✓ Custom Ollama-Evaluation abgeschlossen!")
            self._save_results(results)
            return results
            
        except Exception as e:
            logger.error(f"❌ Alle Evaluation-Methoden fehlgeschlagen: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _save_results(self, results: dict):
        """Speichert Ollama-ARES-Ergebnisse."""
        logger.info("\n" + "="*80)
        logger.info("SCHRITT 5: Ergebnisse speichern")
        logger.info("="*80)
        
        # JSON
        with open(self.results_json, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ JSON gespeichert: {self.results_json.name}")
        
        # CSV für Excel-Analyse
        # Ollama-Format: {'context_relevance': [scores], 'answer_faithfulness': [scores], ...}
        if all(k in results for k in ['context_relevance', 'answer_faithfulness', 'answer_relevance']):
            with open(self.results_csv, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow([
                    'Question_ID', 
                    'Context_Relevance_Score', 
                    'Answer_Faithfulness_Score', 
                    'Answer_Relevance_Score',
                    'Overall_Score'
                ])
                
                num_examples = len(results['context_relevance'])
                for i in range(num_examples):
                    ctx_rel = results['context_relevance'][i]
                    ans_faith = results['answer_faithfulness'][i]
                    ans_rel = results['answer_relevance'][i]
                    overall = (ctx_rel + ans_faith + ans_rel) / 3
                    
                    writer.writerow([i+1, ctx_rel, ans_faith, ans_rel, overall])
            
            logger.info(f"✓ CSV gespeichert: {self.results_csv.name}")
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("EVALUATIONSERGEBNISSE")
        logger.info("="*80)
        
        if 'summary' in results:
            summary = results['summary']
            logger.info(f"Context Relevance:    {summary.get('context_relevance_avg', 0):.2%}")
            logger.info(f"Answer Faithfulness:  {summary.get('answer_faithfulness_avg', 0):.2%}")
            logger.info(f"Answer Relevance:     {summary.get('answer_relevance_avg', 0):.2%}")
            logger.info(f"Overall RAG Quality:  {summary.get('overall_avg', 0):.2%}")
        
        logger.info("="*80)
    
    def run(self):
        """Führt komplette ARES-Evaluation Pipeline aus."""
        logger.info("\n" + "="*80)
        logger.info("ARES EVALUATION PIPELINE - WISO RAG SYSTEM")
        logger.info("="*80)
        
        # Schritt 1: Few-Shot TSV erstellen
        if not self.step1_convert_fewshot_to_tsv():
            logger.error("❌ Pipeline abgebrochen (Schritt 1)")
            return False
        
        # Schritt 2: ARES Installation prüfen
        if not self.step2_check_ares_installation():
            logger.error("❌ Pipeline abgebrochen (Schritt 2)")
            return False
        
        # Schritt 3: ARES konfigurieren
        config = self.step3_configure_ares()
        
        # Schritt 4: Evaluation durchführen
        results = self.step4_run_ares_evaluation(config)
        
        if results is None:
            logger.error("❌ Evaluation fehlgeschlagen")
            logger.info("\n📋 ALTERNATIVE WORKFLOW:")
            logger.info("1. Installiere ARES manuell: pip install ares-ai")
            logger.info("2. Konfiguriere OpenAI API Key in config/settings.py")
            logger.info("3. Führe dieses Script erneut aus")
            return False
        
        logger.info("\n✅ ARES-Evaluation erfolgreich abgeschlossen!")
        logger.info(f"📊 Ergebnisse gespeichert in: {self.data_dir}")
        logger.info(f"   - {self.results_json.name}")
        logger.info(f"   - {self.results_csv.name}")
        
        return True


def main():
    """Main Execution."""
    data_dir = project_root / "src" / "evaluation" / "data"
    
    runner = ARESEvaluationRunner(data_dir)
    success = runner.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
