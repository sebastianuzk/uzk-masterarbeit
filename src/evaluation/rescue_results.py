"""
RESCUE SCRIPT: Lädt Checkpoint und speichert Ergebnisse

Dieses Script lädt die gespeicherten Antworten aus dem Checkpoint,
führt die RAGAS-Evaluation durch und speichert die Ergebnisse.
"""

import sys
import pickle
import pandas as pd
from pathlib import Path

# Projekt-Root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, context_precision
from ragas.run_config import RunConfig
from langchain_ollama import ChatOllama
from config.settings import (
    OLLAMA_BASE_URL,
    RAGAS_EVAL_MODEL,
    TEMPERATURE,
    CONTEXT_WINDOW,
    RANDOM_SEED
)

# Import der display_and_save_results Funktion
from src.evaluation.ragas_evaluation import display_and_save_results, load_testset


def main():
    print("\n" + "=" * 80)
    print("🔧 RESCUE SCRIPT - Lade Checkpoint und speichere Ergebnisse")
    print("=" * 80 + "\n")
    
    # Checkpoint laden
    checkpoint_path = Path(__file__).parent / "data" / "responses_checkpoint.pkl"
    
    if not checkpoint_path.exists():
        print("❌ Kein Checkpoint gefunden!")
        return
    
    print(f"📂 Lade Checkpoint: {checkpoint_path}")
    with open(checkpoint_path, 'rb') as f:
        checkpoint_data = pickle.load(f)
    
    # Daten extrahieren
    dataset = checkpoint_data.get('dataset')
    test_df = checkpoint_data.get('test_df')
    response_times = checkpoint_data.get('response_times', [])
    urls_list = checkpoint_data.get('urls_list', [])
    content_types_list = checkpoint_data.get('content_types_list', [])
    
    print(f"   ✅ {len(dataset.samples)} Samples geladen")
    print(f"   ✅ {len(response_times)} Response-Zeiten")
    print(f"   ✅ {len(urls_list)} URL-Listen")
    
    # RAGAS-Evaluation
    print("\n🚀 Starte RAGAS-Evaluation...")
    print("=" * 80)
    
    llm = ChatOllama(
        model=RAGAS_EVAL_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE,
        seed=RANDOM_SEED,
        num_ctx=CONTEXT_WINDOW
    )
    print(f"   RAGAS-LLM: {RAGAS_EVAL_MODEL} @ {OLLAMA_BASE_URL}")
    
    metrics = [faithfulness, context_recall, context_precision]
    run_config = RunConfig(max_workers=4)
    
    import time
    eval_start = time.time()
    
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        run_config=run_config,
        raise_exceptions=False
    )
    
    evaluation_time = time.time() - eval_start
    print(f"\n   ✅ Evaluation abgeschlossen in {evaluation_time:.2f}s")
    
    results_df = results.to_pandas()
    
    # Ergebnisse speichern (mit gefixter Funktion)
    display_and_save_results(
        results_df, 
        test_df, 
        response_times, 
        urls_list, 
        content_types_list, 
        evaluation_time
    )
    
    print("\n✅ Rescue erfolgreich!")


if __name__ == "__main__":
    main()
