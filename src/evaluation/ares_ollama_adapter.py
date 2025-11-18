"""
ARES Ollama Adapter - Verbindet ARES mit lokalem Ollama-Modell.

Da ARES standardmäßig OpenAI/vLLM erwartet, erstellen wir einen Custom Scorer,
der direkt mit Ollama kommuniziert.
"""
import logging
from typing import List, Dict, Any
import requests
import json
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


class OllamaARESScorer:
    """
    Custom ARES Scorer für Ollama-Integration.
    
    Implementiert die gleichen Metriken wie ARES:
    - Context Relevance: Ist der abgerufene Kontext relevant für die Frage?
    - Answer Faithfulness: Ist die Antwort treu zum Kontext (keine Halluzinationen)?
    - Answer Relevance: Beantwortet die Antwort die Frage?
    """
    
    def __init__(self, few_shot_examples_path: Path):
        """
        Args:
            few_shot_examples_path: Pfad zur TSV mit Few-Shot Annotationen
        """
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.few_shot_examples = self._load_few_shot_examples(few_shot_examples_path)
        
        logger.info(f"✓ OllamaARESScorer initialisiert")
        logger.info(f"  - Ollama URL: {self.ollama_url}")
        logger.info(f"  - Modell: {self.model}")
        logger.info(f"  - Few-Shot Examples: {len(self.few_shot_examples)}")
    
    def _load_few_shot_examples(self, tsv_path: Path) -> List[Dict[str, Any]]:
        """Lädt Few-Shot Beispiele aus TSV."""
        import csv
        
        examples = []
        with open(tsv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                examples.append({
                    'question': row['Question'],
                    'answer': row['Answer'],
                    'document': row['Document'],
                    'context_relevance': int(row['Context_Relevance_Label']),
                    'answer_faithfulness': int(row['Answer_Faithfulness_Label']),
                    'answer_relevance': int(row['Answer_Relevance_Label'])
                })
        
        return examples
    
    def _build_few_shot_prompt(self, metric: str) -> str:
        """
        Erstellt Few-Shot Prompt für eine spezifische Metrik.
        
        Args:
            metric: 'context_relevance', 'answer_faithfulness', oder 'answer_relevance'
        """
        metric_map = {
            'context_relevance': {
                'label_key': 'context_relevance',
                'instruction': (
                    "Du bist ein RAG-Evaluator. Bewerte, ob der KONTEXT relevant ist, um die FRAGE zu beantworten.\n"
                    "Antworte NUR mit der Zahl '1' (relevant) oder '0' (nicht relevant). KEINE Erklärungen!"
                )
            },
            'answer_faithfulness': {
                'label_key': 'answer_faithfulness',
                'instruction': (
                    "Du bist ein RAG-Evaluator. Bewerte, ob die ANTWORT treu zum KONTEXT ist (keine Halluzinationen).\n"
                    "Antworte NUR mit der Zahl '1' (treu) oder '0' (halluziniert). KEINE Erklärungen!"
                )
            },
            'answer_relevance': {
                'label_key': 'answer_relevance',
                'instruction': (
                    "Du bist ein RAG-Evaluator. Bewerte, ob die ANTWORT die FRAGE adäquat beantwortet.\n"
                    "Antworte NUR mit der Zahl '1' (relevant) oder '0' (nicht relevant). KEINE Erklärungen!"
                )
            }
        }
        
        config = metric_map[metric]
        
        # System-Prompt
        prompt = f"{config['instruction']}\n\n"
        prompt += "BEISPIELE:\n\n"
        
        # Few-Shot Examples (max 3 für Context-Length, jeweils kürzer)
        for i, ex in enumerate(self.few_shot_examples[:3], 1):
            prompt += f"Beispiel {i}:\n"
            prompt += f"FRAGE: {ex['question'][:150]}\n"
            prompt += f"KONTEXT: {ex['document'][:200]}\n"
            prompt += f"ANTWORT: {ex['answer'][:150]}\n"
            prompt += f"→ BEWERTUNG: {ex[config['label_key']]}\n\n"
        
        prompt += "NEUE BEWERTUNG:\n"
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """
        Ruft Ollama API auf (Chat-Format für bessere Responses).
        
        Args:
            prompt: Der vollständige Prompt
            
        Returns:
            Die Antwort des Modells (sollte '0' oder '1' sein)
        """
        try:
            # Verwende Chat API für bessere Prompt-Verarbeitung
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "Du bist ein präziser Evaluator. Antworte NUR mit '1' oder '0', KEINE Erklärungen!"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": False,
                    "options": {
                        "temperature": 0.0  # Deterministisch für Evaluation
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Flexible Extraction: Kombiniere content + thinking (für alle Modelle)
            message = result.get('message', {})
            content = message.get('content', '').strip()
            thinking = message.get('thinking', '').strip()
            
            # Kombiniere beide Felder (thinking kann längere Erklärung enthalten)
            combined_answer = content + " " + thinking
            
            # Extrahiere binäre Antwort (0 oder 1)
            # Suche nach erster Ziffer im kombinierten Text
            for char in combined_answer:
                if char == '1':
                    return '1'
                elif char == '0':
                    return '0'
            
            # Keine Ziffer gefunden - logge Details
            logger.warning(f"Keine 0/1 in Ollama-Antwort gefunden")
            logger.debug(f"Content: '{content[:100]}'")
            logger.debug(f"Thinking: '{thinking[:100]}'")
            return '0'  # Default zu 0
                
        except Exception as e:
            logger.error(f"Ollama API-Fehler: {e}")
            return '0'  # Fallback
    
    def score_single_example(
        self,
        question: str,
        answer: str,
        document: str
    ) -> Dict[str, float]:
        """
        Bewertet ein einzelnes Q/A/D-Tripel für alle drei Metriken.
        
        Args:
            question: Die Frage
            answer: Die generierte Antwort
            document: Der abgerufene Kontext
            
        Returns:
            Dict mit Scores für alle drei Metriken (0.0 oder 1.0)
        """
        scores = {}
        
        for metric in ['context_relevance', 'answer_faithfulness', 'answer_relevance']:
            # Baue Few-Shot Prompt
            few_shot_prompt = self._build_few_shot_prompt(metric)
            
            # Füge aktuelles Beispiel hinzu
            full_prompt = few_shot_prompt
            full_prompt += f"FRAGE: {question[:200]}\n"
            full_prompt += f"KONTEXT: {document[:800]}\n"  # Mehr Context erlauben
            full_prompt += f"ANTWORT: {answer[:400]}\n"
            full_prompt += "→ BEWERTUNG:"
            
            # Rufe Ollama auf
            result = self._call_ollama(full_prompt)
            scores[metric] = float(result)
        
        return scores
    
    def evaluate_dataset(
        self,
        unlabeled_tsv_path: Path
    ) -> Dict[str, List[float]]:
        """
        Evaluiert ein komplettes Dataset.
        
        Args:
            unlabeled_tsv_path: Pfad zur unlabeled TSV mit Q/A/D-Tripeln
            
        Returns:
            Dict mit Listen von Scores für jede Metrik
        """
        import csv
        
        logger.info(f"Starte Ollama-basierte Evaluation von {unlabeled_tsv_path.name}...")
        
        # Lade unlabeled data
        examples = []
        with open(unlabeled_tsv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                examples.append({
                    'question': row['Question'],
                    'answer': row['Answer'],
                    'document': row['Document'],
                    'id': row.get('ID', '')
                })
        
        logger.info(f"✓ {len(examples)} Beispiele geladen")
        
        # Evaluiere jedes Beispiel
        all_scores = {
            'context_relevance': [],
            'answer_faithfulness': [],
            'answer_relevance': []
        }
        
        for i, ex in enumerate(examples, 1):
            logger.info(f"Evaluiere Beispiel {i}/{len(examples)}...")
            
            scores = self.score_single_example(
                question=ex['question'],
                answer=ex['answer'],
                document=ex['document']
            )
            
            for metric, score in scores.items():
                all_scores[metric].append(score)
            
            logger.info(f"  → CR={scores['context_relevance']}, "
                       f"AF={scores['answer_faithfulness']}, "
                       f"AR={scores['answer_relevance']}")
        
        # Berechne Durchschnitte
        logger.info("\n" + "="*80)
        logger.info("EVALUATIONS-ERGEBNISSE (Ollama-basiert)")
        logger.info("="*80)
        
        for metric, scores in all_scores.items():
            avg = sum(scores) / len(scores) if scores else 0.0
            logger.info(f"{metric.upper()}: {avg:.2%} ({sum(scores)}/{len(scores)})")
        
        logger.info("="*80)
        
        return all_scores


def main():
    """Test-Funktion für OllamaARESScorer."""
    from pathlib import Path
    
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "src" / "evaluation" / "data"
    
    scorer = OllamaARESScorer(
        few_shot_examples_path=data_dir / "ares_few_shot_prompt_for_judge_scoring.tsv"
    )
    
    results = scorer.evaluate_dataset(
        unlabeled_tsv_path=data_dir / "ares_unlabeled_evaluation.tsv"
    )
    
    # Speichere Ergebnisse
    import json
    output_path = data_dir / "ollama_ares_results.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n✓ Ergebnisse gespeichert: {output_path}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main()
