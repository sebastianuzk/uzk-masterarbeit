"""
Evaluation Runner für ARES-basierte RAG-Evaluation
=================================================

Orchestriert Evaluationen mit dem Stanford ARES Framework.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .ares_evaluator import ARESEvaluator
from .test_cases import TestCase, load_test_cases, save_test_cases, create_default_test_cases

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """
    Runner für ARES-basierte Evaluationen.
    """
    
    def __init__(self, 
                 agent=None,
                 results_dir: Optional[Path] = None,
                 evaluation_mode: str = "ues_idp"):
        """
        Initialize evaluation runner.
        
        Args:
            agent: Der RAG-Agent für Evaluation
            results_dir: Verzeichnis für Ergebnisse
        """
        self.agent = agent
        # Ergebnisse standardisiert im Modulordner `results/` ablegen
        default_results_dir = Path(__file__).parent / "results"
        self.results_dir = results_dir or default_results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # ARES Evaluator initialisieren
        self.evaluator = ARESEvaluator(mode=evaluation_mode)
        
        logger.info("🚀 EvaluationRunner initialisiert")
    
    def run_complete_evaluation(self, 
                              test_cases: Optional[List[TestCase]] = None,
                              save_results: bool = True) -> Dict[str, Any]:
        """
        Führe vollständige Evaluation durch.
        
        Args:
            test_cases: Testfälle (falls None, werden Standard-Testfälle verwendet)
            save_results: Ob Ergebnisse gespeichert werden sollen
            
        Returns:
            Evaluations-Ergebnisse
        """
        if test_cases is None:
            test_cases = create_default_test_cases()
            logger.info(f"📋 Verwende {len(test_cases)} Standard-Testfälle")
        
        if not self.agent:
            logger.error("❌ Kein Agent für Evaluation verfügbar")
            return {"error": "Kein Agent verfügbar"}
        
        logger.info(f"🔄 Starte Evaluation mit {len(test_cases)} Testfällen...")
        start_time = time.time()
        
        # Sammle Antworten vom Agent
        responses = []
        for i, test_case in enumerate(test_cases, 1):
            try:
                logger.info(f"📝 Verarbeite Testfall {i}/{len(test_cases)}: {test_case.id}")
                
                # Agent-Antwort abrufen
                response = self._get_agent_response(test_case.question)
                
                responses.append({
                    "test_case": test_case,
                    "response": response
                })
                
                # Kurze Pause zwischen Anfragen
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"❌ Fehler bei Testfall {test_case.id}: {e}")
                responses.append({
                    "test_case": test_case,
                    "response": {"error": str(e)}
                })
        
        # ARES Evaluation durchführen (synchroner Evaluator-Wrapper)
        logger.info("🔬 Führe ARES-Evaluation durch...")
        
        # Daten für ARES vorbereiten (Format für evaluate_batch_sync)
        ares_data = []
        for item in responses:
            if "error" not in item["response"]:
                ares_data.append({
                    "query": item["test_case"].question,
                    "response": item["response"].get("answer", ""),
                    "contexts": item["response"].get("source_documents", [])
                })
        
        # ARES Evaluation ausführen
        try:
            if ares_data:
                ares_results = self.evaluator.evaluate_batch_sync(ares_data)
                logger.info("✅ ARES-Evaluation abgeschlossen")
            else:
                ares_results = {"error": "Keine gültigen Antworten für ARES-Evaluation"}
                logger.warning("⚠️ Keine gültigen Antworten für ARES-Evaluation")
                
        except Exception as e:
            logger.error(f"❌ Fehler bei ARES-Evaluation: {e}")
            ares_results = {"error": f"ARES-Evaluation fehlgeschlagen: {e}"}
        
        # Ergebnisse zusammenfassen
        duration = time.time() - start_time
        results = self._compile_results(test_cases, responses, ares_results, duration)
        
        if save_results:
            self._save_results(results)
        
        logger.info(f"✅ Evaluation abgeschlossen in {duration:.2f}s")
        return results
    
    def run_single_evaluation(self, question: str) -> Dict[str, Any]:
        """
        Führe Evaluation für eine einzelne Frage durch.
        
        Args:
            question: Die zu evaluierende Frage
            
        Returns:
            Evaluations-Ergebnisse
        """
        if not self.agent:
            return {"error": "Kein Agent verfügbar"}
        
        try:
            # Agent-Antwort abrufen
            response = self._get_agent_response(question)
            
            if "error" in response:
                return response
            
            # ARES Evaluation (synchroner Wrapper für Einzelabfrage)
            evaluation = self.evaluator.evaluate_single_sync(
                query=question,
                response=response.get("answer", ""),
                contexts=response.get("source_documents", [])
            )
            
            return {
                "question": question,
                "response": response,
                "evaluation": evaluation,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Fehler bei Einzelevaluation: {e}")
            return {"error": str(e)}
    
    def _get_agent_response(self, question: str) -> Dict[str, Any]:
        """
        Hole Antwort vom Agent.
        
        Args:
            question: Die Frage
            
        Returns:
            Agent-Antwort mit Metadaten
        """
        try:
            if hasattr(self.agent, 'invoke'):
                # LangChain Agent
                result = self.agent.invoke({"input": question})
                
                return {
                    "answer": result.get("output", ""),
                    "source_documents": result.get("source_documents", []),
                    "metadata": result.get("metadata", {})
                }
                
            elif hasattr(self.agent, 'query'):
                # Custom Agent Interface
                result = self.agent.query(question)
                
                return {
                    "answer": result.get("answer", ""),
                    "source_documents": result.get("contexts", []),
                    "metadata": result.get("metadata", {})
                }
            else:
                logger.warning("⚠️ Unbekannte Agent-Schnittstelle")
                return {"error": "Unbekannte Agent-Schnittstelle"}
                
        except Exception as e:
            logger.error(f"❌ Fehler beim Abrufen der Agent-Antwort: {e}")
            return {"error": str(e)}
    
    def _compile_results(self, 
                        test_cases: List[TestCase],
                        responses: List[Dict],
                        ares_results: Dict[str, Any],
                        duration: float) -> Dict[str, Any]:
        """
        Kompiliere finale Ergebnisse.
        """
        successful_responses = [r for r in responses if "error" not in r["response"]]
        failed_responses = [r for r in responses if "error" in r["response"]]
        
        # Basis-Statistiken
        stats = {
            "total_test_cases": len(test_cases),
            "successful_responses": len(successful_responses),
            "failed_responses": len(failed_responses),
            "success_rate": len(successful_responses) / len(test_cases) if test_cases else 0,
            "duration_seconds": duration
        }
        
        # ARES Metriken hinzufügen
        if "error" not in ares_results:
            if "average_scores" in ares_results:
                stats["ares_metrics"] = ares_results["average_scores"]
            else:
                stats["ares_metrics"] = ares_results
        
        results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "evaluator": "Stanford_ARES_Framework",
                "version": "1.0.0"
            },
            "statistics": stats,
            "test_cases": [tc.to_dict() for tc in test_cases],
            "responses": responses,
            "ares_evaluation": ares_results
        }
        
        return results
    
    def _save_results(self, results: Dict[str, Any]):
        """
        Speichere Evaluations-Ergebnisse.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_results_{timestamp}.json"
        filepath = self.results_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Auch aktuellste Ergebnisse als "latest" speichern
        latest_path = self.results_dir / "evaluation_results_latest.json"
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Ergebnisse gespeichert: {filepath}")
    
    def load_previous_results(self, filename: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Lade vorherige Evaluations-Ergebnisse.
        
        Args:
            filename: Spezifischer Dateiname (falls None, wird latest verwendet)
            
        Returns:
            Evaluations-Ergebnisse oder None
        """
        if filename is None:
            filepath = self.results_dir / "evaluation_results_latest.json"
        else:
            filepath = self.results_dir / filename
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            logger.info(f"📂 Ergebnisse geladen: {filepath}")
            return results
            
        except FileNotFoundError:
            logger.warning(f"⚠️ Datei nicht gefunden: {filepath}")
            return None
        
        except Exception as e:
            logger.error(f"❌ Fehler beim Laden der Ergebnisse: {e}")
            return None


def quick_evaluation(agent, questions: List[str]) -> Dict[str, Any]:
    """
    Schnelle Evaluation für gegebene Fragen.
    
    Args:
        agent: Der RAG-Agent
        questions: Liste von Fragen
        
    Returns:
        Evaluations-Ergebnisse
    """
    runner = EvaluationRunner(agent=agent)
    
    # Testfälle aus Fragen erstellen
    test_cases = []
    for i, question in enumerate(questions):
        test_case = TestCase(
            id=f"quick_eval_{i+1}",
            question=question,
            category="quick_eval",
            difficulty="medium"
        )
        test_cases.append(test_case)
    
    return runner.run_complete_evaluation(test_cases=test_cases, save_results=False)


if __name__ == "__main__":
    # Beispiel für Standalone-Nutzung
    logger.info("🧪 Starte Standalone-Evaluation...")
    
    # Mock-Agent für Demonstration
    class MockAgent:
        def invoke(self, inputs):
            question = inputs.get("input", "")
            return {
                "output": f"Mock-Antwort für: {question}",
                "source_documents": [f"Mock-Kontext für {question}"],
                "metadata": {"mock": True}
            }
    
    mock_agent = MockAgent()
    runner = EvaluationRunner(agent=mock_agent)
    
    # Teste mit wenigen Fragen
    test_questions = [
        "Welche Master-Programme bietet die WiSo-Fakultät an?",
        "Was sind die Zulassungsvoraussetzungen?"
    ]
    
    results = quick_evaluation(mock_agent, test_questions)
    print("📊 Evaluations-Ergebnisse:")
    print(json.dumps(results["statistics"], indent=2, ensure_ascii=False))