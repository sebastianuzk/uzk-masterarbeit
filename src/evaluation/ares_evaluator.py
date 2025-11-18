"""
ARES-based RAG Evaluator (official API)
======================================

Korrekte Integration der Stanford ARES Framework APIs (UES/IDP und PPI).

Unterstützte Flows (siehe ARES README):
- UES/IDP: ARES(ues_idp=...).ues_idp()
- PPI:    ARES(ppi=...).evaluate_RAG()
"""

import csv
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

from ares import ARES

logger = logging.getLogger(__name__)


class ARESEvaluator:
    """
    Offizieller ARES Evaluator-Wrapper.

    Kernprinzipien:
    - Bereitet aus Q/A/Context ein unlabeled TSV im erwarteten ARES-Format vor
    - Bietet UES/IDP (LLM-Judge) und PPI (LLM-Judge oder Checkpoints) Aufrufe
    - Aggregiert die ARES-Ergebnisse in ein praktisches Strukturformat
    """

    def __init__(self,
                 mode: str = "ues_idp",  # "ues_idp" oder "ppi"
                 work_dir: Optional[Path] = None,
                 few_shot_path: Optional[Path] = None,
                 llm_model_ues: str = "gpt-3.5-turbo-0125",
                 llm_judge_ppi: str = "gpt-3.5-turbo-1106",
                 checkpoints: Optional[List[str]] = None,
                 gold_label_path: Optional[Path] = None,
                 vllm: bool = False,
                 vllm_host_url: Optional[str] = None):
        self.mode = mode
        self.work_dir = Path(work_dir or (Path(__file__).parent / "tmp_ares"))
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.few_shot_path = Path(few_shot_path) if few_shot_path else (Path(__file__).parent / "data" / "ares_few_shot_prompt_for_judge_scoring.tsv")
        self.llm_model_ues = llm_model_ues
        self.llm_judge_ppi = llm_judge_ppi
        self.checkpoints = checkpoints or []
        self.gold_label_path = Path(gold_label_path) if gold_label_path else None
        self.vllm = vllm
        self.vllm_host_url = vllm_host_url

    # ---------- Public API ----------
    def evaluate_batch_sync(self, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluierung eines Batches von Q/A/Context-Paaren über ARES (offizielle APIs).

        Args:
            data_list: Liste von Dicts mit Keys: 'query', 'response', 'contexts' (list[str] oder str)

        Returns:
            Dict mit average_scores, individual_results und Roh-ARES-Ergebnis
        """
        unlabeled_path = self._write_unlabeled_tsv(data_list)

        if self.mode == "ues_idp":
            ares_result = self._run_ues_idp(unlabeled_path)
        elif self.mode == "ppi":
            ares_result = self._run_ppi(unlabeled_path)
        else:
            raise ValueError("Unbekannter ARES Modus. Erlaubt: 'ues_idp' oder 'ppi'")

        aggregated = self._aggregate_scores(ares_result, data_list)
        return {
            "timestamp": datetime.now().isoformat(),
            "evaluation_type": f"stanford_ares_{self.mode}",
            "average_scores": aggregated["average_scores"],
            "individual_results": aggregated["individual_results"],
            "raw": ares_result
        }

    def evaluate_single_sync(self, query: str, response: str, contexts: List[str]) -> Dict[str, Any]:
        data = [{"query": query, "response": response, "contexts": contexts}]
        res = self.evaluate_batch_sync(data)
        # einzelnes Resultat zurückgeben
        single = res["individual_results"][0] if res.get("individual_results") else {}
        single.update({
            "evaluation_type": res.get("evaluation_type"),
            "timestamp": res.get("timestamp")
        })
        return single

    # ---------- ARES calls ----------
    def _run_ues_idp(self, unlabeled_path: Path) -> Dict[str, Any]:
        """
        ARES UES/IDP: ARES(ues_idp=...).ues_idp()
        Benötigt: few_shot TSV und unlabeled TSV, plus LLM model_choice.
        Optional: vLLM host.
        """
        config = {
            "in_domain_prompts_dataset": str(self.few_shot_path),
            "unlabeled_evaluation_set": str(unlabeled_path),
            "model_choice": self.llm_model_ues
        }
        if self.vllm:
            config.update({"vllm": True, "host_url": self.vllm_host_url})

        logger.info("Running ARES UES/IDP evaluation...")
        ares = ARES(ues_idp=config)
        return ares.ues_idp()

    def _run_ppi(self, unlabeled_path: Path) -> Dict[str, Any]:
        """
        ARES PPI: ARES(ppi=...).evaluate_RAG()
        Zwei Varianten:
        - LLM Judge: requires few_shot_examples_filepath + llm_judge
        - Checkpoints: requires 'checkpoints' (pfade zu .pt) und optional gold_label_path
        """
        ppi_config: Dict[str, Any] = {
            "evaluation_datasets": [str(unlabeled_path)],
            # Standard-Labels (du kannst subsetten):
            "labels": [
                "Context_Relevance_Label",
                "Answer_Faithfulness_Label",
                "Answer_Relevance_Label"
            ]
        }

        if self.checkpoints:
            ppi_config["checkpoints"] = self.checkpoints
        else:
            # LLM Judge Modus
            ppi_config.update({
                "few_shot_examples_filepath": str(self.few_shot_path),
                "llm_judge": self.llm_judge_ppi
            })
            if self.vllm:
                ppi_config.update({"vllm": True, "host_url": self.vllm_host_url})

        if self.gold_label_path:
            ppi_config["gold_label_path"] = str(self.gold_label_path)

        logger.info("Running ARES PPI evaluation...")
        ares = ARES(ppi=ppi_config)
        return ares.evaluate_RAG()

    # ---------- Helpers ----------
    def _write_unlabeled_tsv(self, data_list: List[Dict[str, Any]]) -> Path:
        """
        Erzeuge ein ARES-kompatibles unlabeled TSV mit Spalten: Question, Answer, Context, ID
        """
        out_path = self.work_dir / f"unlabeled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tsv"
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow(["Question", "Answer", "Context", "ID"])  # Header
            for i, item in enumerate(data_list):
                q = item.get("query", "").strip()
                a = item.get("response", "").strip()
                ctxs = item.get("contexts", [])
                if isinstance(ctxs, list):
                    ctx = " \n---\n ".join(str(c) for c in ctxs)
                else:
                    ctx = str(ctxs)
                writer.writerow([q, a, ctx, f"eval_{i}"])
        logger.info(f"Wrote unlabeled TSV: {out_path}")
        return out_path

    def _aggregate_scores(self, ares_result: Dict[str, Any], data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Vereinheitliche ARES-Ergebnis-Format in average_scores + individual_results.
        Erwartete Keys: 'Context Relevance Scores', 'Answer Faithfulness Scores', 'Answer Relevance Scores'
        """
        def list_or_empty(obj, key):
            val = obj.get(key, [])
            return val if isinstance(val, list) else []

        cr = list_or_empty(ares_result, "Context Relevance Scores")
        af = list_or_empty(ares_result, "Answer Faithfulness Scores")
        ar = list_or_empty(ares_result, "Answer Relevance Scores")

        n = max(len(cr), len(af), len(ar), len(data_list))
        # pad lists to same length
        def at(lst, i):
            return float(lst[i]) if i < len(lst) else None

        individual = []
        for i in range(n):
            item = data_list[i] if i < len(data_list) else {}
            q = item.get("query", "")
            a = item.get("response", "")
            entry = {
                "query": q,
                "response": a,
                "context_relevance": at(cr, i),
                "answer_faithfulness": at(af, i),
                "answer_relevance": at(ar, i)
            }
            # overall als Mittel der verfügbaren
            scores = [s for s in [entry["context_relevance"], entry["answer_faithfulness"], entry["answer_relevance"]] if isinstance(s, (int, float, float))]
            entry["overall_score"] = sum(scores) / len(scores) if scores else None
            individual.append(entry)

        def avg(lst):
            vals = [x for x in lst if isinstance(x, (int, float, float))]
            return sum(vals) / len(vals) if vals else None

        avg_scores = {
            "context_relevance": avg([it["context_relevance"] for it in individual]),
            "answer_faithfulness": avg([it["answer_faithfulness"] for it in individual]),
            "answer_relevance": avg([it["answer_relevance"] for it in individual]),
            "overall_score": avg([it["overall_score"] for it in individual])
        }

        return {"average_scores": avg_scores, "individual_results": individual}