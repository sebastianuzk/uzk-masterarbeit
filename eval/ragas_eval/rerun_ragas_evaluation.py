#!/usr/bin/env python3
"""
Re-run RAGAS evaluation on existing responses.

Use this when response generation completed but RAGAS evaluation failed
(e.g., due to API quota limits).

Usage:
    python eval/ragas_eval/rerun_ragas_evaluation.py \
        --input data/eval/final/model/timestamp/agent/ragas/ragas_results.csv \
        --judge-provider openai \
        --judge-model gpt-4o-mini \
        --workers 50
"""

import sys
import argparse
import pandas as pd
from pathlib import Path
from typing import List
import json
import os

# Disable RAGAS analytics to prevent network hangs
os.environ["RAGAS_DO_NOT_TRACK"] = "true"

# Import RAGAS library FIRST (before adding project_root to avoid shadowing)
# Using deprecated imports for now as collections metrics have compatibility issues
from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, context_precision
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.run_config import RunConfig

# Add project root to path (AFTER RAGAS imports)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from config.settings import settings


def load_existing_responses(csv_path: Path) -> EvaluationDataset:
    """
    Load existing responses from CSV file.
    
    Args:
        csv_path: Path to ragas_results.csv with responses but missing metrics
        
    Returns:
        EvaluationDataset ready for RAGAS evaluation
    """
    print(f"📂 Loading existing responses from: {csv_path}")

    # ragas_results.csv wird in ragas_evaluation.py mit sep=',' und encoding='utf-8-sig'
    # geschrieben. Beim Lesen explizit dieselben Parameter verwenden, damit ein BOM oder
    # ein anderer Default kein stilles Spaltenshift verursacht.
    df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig')
    print(f"   ✅ Loaded {len(df)} responses")

    # Convert to RAGAS samples
    import ast
    samples = []
    for idx, row in df.iterrows():
        # Parse retrieved_contexts (might be string representation of list)
        contexts = row['retrieved_contexts']
        if isinstance(contexts, str):
            try:
                contexts = ast.literal_eval(contexts)
            except (ValueError, SyntaxError) as e:
                # Echte Parse-Fehler loggen statt still verschlucken; Fallback: Ein-Element-Liste
                print(f"   ⚠️ Row {idx}: konnte retrieved_contexts nicht als Liste parsen ({e}); behandle als single string")
                contexts = [contexts]

        if not isinstance(contexts, list):
            contexts = [str(contexts)]
        
        sample = SingleTurnSample(
            user_input=str(row['user_input']),
            retrieved_contexts=contexts,
            response=str(row['response']),
            reference=str(row['reference'])
        )
        samples.append(sample)
    
    return EvaluationDataset(samples=samples)


def run_ragas_evaluation(
    dataset: EvaluationDataset,
    judge_provider: str,
    judge_model: str,
    max_workers: int
) -> pd.DataFrame:
    """
    Run RAGAS evaluation on existing responses.
    
    Args:
        dataset: Dataset with responses
        judge_provider: 'openai' or 'ollama'
        judge_model: Model name for judge
        max_workers: Number of parallel workers
        
    Returns:
        DataFrame with RAGAS metrics
    """
    print("\n🚀 Running RAGAS evaluation...")
    print("=" * 80)
    print(f"   Judge Provider: {judge_provider}")
    print(f"   Judge Model:    {judge_model}")
    print(f"   Workers:        {max_workers}")
    print(f"   Samples:        {len(dataset.samples)}")
    print()
    
    # Configure LLM judge
    if judge_provider == 'openai':
        llm = ChatOpenAI(
            model=judge_model,
            temperature=settings.TEMPERATURE,
            api_key=settings.OPENAI_API_KEY,
            max_retries=3
        )
    else:
        llm = ChatOllama(
            model=judge_model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=settings.TEMPERATURE
        )
    
    # RAGAS metrics (using deprecated imports until collections API stabilizes)
    metrics = [
        faithfulness,
        context_recall,
        context_precision
    ]
    
    # Run config
    run_config = RunConfig(max_workers=max_workers)
    
    # Evaluate
    print("⏳ Evaluating (this may take several minutes)...\n")
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        run_config=run_config,
        raise_exceptions=False
    )
    
    return results.to_pandas()


def main():
    parser = argparse.ArgumentParser(
        description="Re-run RAGAS evaluation on existing responses"
    )
    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="Path to ragas_results.csv with existing responses"
    )
    parser.add_argument(
        "--judge-provider",
        type=str,
        choices=["openai", "ollama"],
        default="openai",
        help="Judge LLM provider (default: openai)"
    )
    parser.add_argument(
        "--judge-model",
        type=str,
        default="gpt-4o-mini",
        help="Judge model name (default: gpt-4o-mini)"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=50,
        help="Number of parallel workers (default: 50)"
    )
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        sys.exit(1)
    
    # Load existing responses
    dataset = load_existing_responses(input_path)
    
    # Run RAGAS evaluation
    results_df = run_ragas_evaluation(
        dataset=dataset,
        judge_provider=args.judge_provider,
        judge_model=args.judge_model,
        max_workers=args.workers
    )
    
    # Save results (overwrite original CSV)
    print("\n💾 Saving results...")
    results_df.to_csv(input_path, index=False, encoding='utf-8-sig')
    print(f"   ✅ Updated: {input_path}")

    # Generate summary (NaN- und Empty-Context-aware: Zeilen ohne RAG-Kontext
    # werden aus den Mittelwerten ausgeschlossen, damit Vergleiche zwischen
    # Agent-Varianten nicht durch unterschiedliches RAG-Routing verzerrt werden.)
    from eval.ragas_eval.ragas_evaluation import _metric_stats
    summary = {
        "metrics": {}
    }

    for metric in ["faithfulness", "context_recall", "context_precision"]:
        if metric in results_df.columns:
            stats = _metric_stats(results_df, metric)
            summary["metrics"][metric] = {
                "mean": stats["mean"],
                "std": stats["std"],
                "min": float(results_df[metric].min(skipna=True))
                    if results_df[metric].notna().any() else float("nan"),
                "max": float(results_df[metric].max(skipna=True))
                    if results_df[metric].notna().any() else float("nan"),
                "n_valid": stats["n_valid"],
                "n_total": stats["n_total"],
                "n_no_context": stats["n_no_ctx"],
                "n_nan": stats["n_nan"],
            }
    
    # Save summary JSON
    summary_path = input_path.parent / "ragas_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Summary: {summary_path}")
    
    # Print results
    print("\n" + "=" * 80)
    print("📊 RAGAS EVALUATION RESULTS")
    print("=" * 80)
    for metric, values in summary["metrics"].items():
        print(f"   {metric:20s}: {values['mean']:.3f} (±{values['std']:.3f})")
    print("=" * 80)


if __name__ == "__main__":
    main()
