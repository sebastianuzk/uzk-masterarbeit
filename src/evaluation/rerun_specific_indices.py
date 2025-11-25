"""
Führe produktive RAGAS-Evaluation nur für spezifische Indizes aus.

Nutzt das komplette Setup von ragas_evaluation_with_retry.py,
aber evaluiert nur ausgewählte Fragen (z.B. die ohne validen Context).
"""

import sys
from pathlib import Path

# Füge project root zum Path hinzu
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Direkter Import ohne __init__.py
import importlib.util
spec = importlib.util.spec_from_file_location(
    "ragas_eval",
    project_root / "src" / "evaluation" / "ragas_evaluation_with_retry.py"
)
ragas_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ragas_eval)

# Nutze die Funktionen
load_testset = ragas_eval.load_testset
generate_chatbot_responses = ragas_eval.generate_chatbot_responses
run_ragas_evaluation = ragas_eval.run_ragas_evaluation
display_and_save_results = ragas_eval.display_and_save_results

import pandas as pd
import json


def find_empty_context_indices() -> list:
    """Findet alle Indizes ohne validen Context in den existierenden Ergebnissen."""
    results_file = Path(__file__).parent / "data" / "ragas_results.xlsx"
    
    if not results_file.exists():
        print(f"❌ Ergebnisdatei nicht gefunden: {results_file}")
        return []
    
    print(f"📂 Lade existierende Ergebnisse: {results_file}")
    df = pd.read_excel(results_file, engine='openpyxl')
    
    empty_indices = []
    for idx, row in df.iterrows():
        contexts_raw = row['retrieved_contexts']
        
        # Parse Context
        try:
            if pd.isna(contexts_raw):
                contexts = []
            elif isinstance(contexts_raw, str):
                contexts = json.loads(contexts_raw)
            else:
                contexts = contexts_raw
        except:
            contexts = []
        
        # Prüfe auf leere/invalide Contexts
        is_empty = (
            len(contexts) == 0 or
            (len(contexts) == 1 and contexts[0] == "Kein Kontext gefunden")
        )
        
        if is_empty:
            empty_indices.append(idx)
            question = row.get('user_input', 'N/A')
            print(f"   Index {idx}: {question[:60]}...")
    
    return empty_indices


def main():
    print("\n" + "=" * 80)
    print("🔄 RAGAS NEU-EVALUATION FÜR SPEZIFISCHE INDIZES")
    print("=" * 80)
    
    # 1. Finde Indizes ohne Context
    empty_indices = find_empty_context_indices()
    
    if not empty_indices:
        print("\n✅ Keine Indizes ohne Context gefunden")
        return 0
    
    print(f"\n📋 {len(empty_indices)} Indizes gefunden: {empty_indices}")
    print("\n⚠️  Diese Indizes werden komplett neu evaluiert:")
    print("   - Neue Chatbot-Responses werden generiert")
    print("   - Neue RAG-Contexts werden abgerufen")  
    print("   - Neue RAGAS-Metriken werden berechnet")
    
    # 2. Lade Testset
    print("\n" + "="*80)
    testset_df = load_testset()
    
    # 3. Filtere Testset auf gewünschte Indizes
    # Konvertiere DataFrame-Index zu question_id (Index + 1)
    selected_ids = [idx + 1 for idx in empty_indices]
    filtered_testset = testset_df[testset_df['id'].isin(selected_ids)].copy()
    
    print(f"\n📝 Gefiltert: {len(filtered_testset)} von {len(testset_df)} Fragen")
    
    # 4. Initialisiere Agent und LangSmith
    from src.agent.react_agent import create_react_agent
    from langsmith import Client
    import os
    
    agent = create_react_agent()
    langsmith_client = None
    if os.getenv("LANGSMITH_API_KEY"):
        langsmith_client = Client()
    
    # 5. Generiere Chatbot-Responses
    dataset = generate_chatbot_responses(filtered_testset, agent, langsmith_client)
    
    # 6. Führe RAGAS-Evaluation durch
    results_df = run_ragas_evaluation(dataset)
    
    # 7. Speichere mit speziellem Suffix
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    display_and_save_results(results_df, output_suffix=f"_rerun_{timestamp}")
    
    # 7. Merge zurück in Original
    print("\n" + "=" * 80)
    print("🔄 MERGE ZURÜCK IN ORIGINAL-DATEI")
    print("=" * 80)
    
    results_file = Path(__file__).parent / "data" / "ragas_results.xlsx"
    original_df = pd.read_excel(results_file, engine='openpyxl')
    
    updates_count = 0
    metric_columns = ['faithfulness', 'context_recall', 'context_precision']
    update_columns = ['retrieved_contexts', 'response'] + metric_columns
    
    # Map results zurück via question_id
    for _, new_row in results_df.iterrows():
        question_id = new_row.get('question_id')
        if pd.notna(question_id):
            # Finde Original-Index (ID - 1)
            orig_idx = int(question_id) - 1
            if orig_idx < len(original_df):
                for col in update_columns:
                    if col in results_df.columns:
                        new_value = new_row[col]
                        # Update nur valide Werte
                        if col in metric_columns:
                            if pd.notna(new_value):
                                original_df.at[orig_idx, col] = new_value
                                updates_count += 1
                        else:
                            original_df.at[orig_idx, col] = new_value
    
    if updates_count > 0:
        original_df.to_excel(results_file, index=False, engine='openpyxl')
        print(f"✅ {updates_count} Werte in Original-Datei aktualisiert")
        print(f"   Datei: {results_file}")
    else:
        print("ℹ️  Keine Updates - Original-Datei unverändert")
    
    print("\n" + "=" * 80)
    print("✅ NEU-EVALUATION ABGESCHLOSSEN!")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    exit(main())
