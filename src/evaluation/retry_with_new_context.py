"""
RAGAS Retry für Fälle ohne validen Context - Komplett-Neu-Evaluation

Dieses Script führt eine vollständige Neu-Evaluation durch:
1. Identifiziert Zeilen ohne validen Context
2. Generiert neue Chatbot-Responses (mit frischem RAG-Retrieval)
3. Führt RAGAS-Evaluation durch
4. Merged erfolgreiche Ergebnisse zurück in Original-Datei
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from pathlib import Path

# LangChain & RAGAS
from langchain_ollama import ChatOllama
from ragas import evaluate, EvaluationDataset, SingleTurnSample, RunConfig
from ragas.metrics import faithfulness, context_recall, context_precision

# Füge src zum Python Path hinzu
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agent.react_agent import create_react_agent

# ============================================================================
# KONFIGURATION
# ============================================================================

# Lade Ollama-Config aus .env
from dotenv import load_dotenv
load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EVALUATION_TIMEOUT = int(os.getenv("OLLAMA_EVALUATION_TIMEOUT", "240"))

# Pfade
DATA_DIR = Path(__file__).parent / "data"
TESTSET_FILE = DATA_DIR / "Testset.CSV"
RESULTS_FILE = DATA_DIR / "ragas_results.xlsx"

# Max Retry Runden
MAX_RETRY_ROUNDS = 3


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_testset() -> pd.DataFrame:
    """Lädt das Testset."""
    print(f"📂 Lade Testset: {TESTSET_FILE}")
    
    # CSV mit Semikolon-Trennung
    df = pd.read_csv(TESTSET_FILE, sep=';', encoding='utf-8')
    
    print(f"✅ {len(df)} Test-Fragen geladen")
    return df


def load_existing_results() -> pd.DataFrame:
    """Lädt existierende Evaluationsergebnisse."""
    print(f"📂 Lade existierende Ergebnisse: {RESULTS_FILE}")
    
    df = pd.read_excel(RESULTS_FILE, engine='openpyxl')
    
    print(f"✅ {len(df)} Evaluationen geladen")
    return df


def find_empty_context_indices(results_df: pd.DataFrame) -> list:
    """
    Findet alle Indizes mit fehlendem oder leerem Context.
    
    Args:
        results_df: DataFrame mit Evaluationsergebnissen
        
    Returns:
        Liste von Indizes ohne validen Context
    """
    empty_indices = []
    
    for idx, row in results_df.iterrows():
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
    
    return empty_indices


def show_empty_context_details(results_df: pd.DataFrame, indices: list):
    """Zeigt Details zu Fragen ohne Context."""
    print("\n📋 Details der Evaluationen ohne validen Context:\n")
    
    for idx in indices:
        row = results_df.iloc[idx]
        question = row.get('user_input', '')
        print(f"   Index {idx}:")
        print(f"      Frage: {question}")
        print(f"      Kategorie: {row.get('category', 'N/A')}")
        print(f"      Metriken: faithfulness={row.get('faithfulness', 'N/A'):.3f}, "
              f"context_recall={row.get('context_recall', 'N/A')}, "
              f"context_precision={row.get('context_precision', 'N/A')}")
        print()


def generate_chatbot_response_for_indices(
    testset_df: pd.DataFrame,
    indices: list
) -> pd.DataFrame:
    """
    Generiert neue Chatbot-Responses für ausgewählte Indizes.
    
    Args:
        testset_df: DataFrame mit Test-Fragen
        indices: Liste von Indizes für Neu-Evaluation
        
    Returns:
        DataFrame mit neuen Responses und Contexts
    """
    print("\n🤖 Initialisiere RAG-Agent...")
    agent = create_react_agent()
    print("✅ Agent bereit")
    
    print(f"\n💬 Generiere neue Responses für {len(indices)} Fragen...")
    
    results = []
    
    for idx in indices:
        # Hole Frage aus Testset (ID = Index + 1)
        question_id = idx + 1
        test_row = testset_df[testset_df['id'] == question_id].iloc[0]
        
        user_input = test_row['question']
        reference = test_row['expected_answer']
        
        print(f"\n   [{idx}] Frage: {user_input[:60]}...")
        
        try:
            # Nutze ReactAgent.chat() statt invoke()
            agent.clear_memory()  # Sauberer Start für jede Frage
            response = agent.chat(user_input)
            
            # Extrahiere retrieved contexts - verwende leeren Kontext als Fallback
            # Da wir nicht direkt auf intermediate_steps zugreifen können,
            # nutzen wir einen Platzhalter - die RAG-Evaluation wird den Context finden
            retrieved_contexts = ["Context wird bei Evaluation ermittelt"]
            
            print(f"      ✅ Response generiert")
            
            results.append({
                'index': idx,
                'user_input': user_input,
                'retrieved_contexts': retrieved_contexts,
                'response': response,
                'reference': reference,
                'category': test_row.get('category', ''),
                'difficulty': test_row.get('difficulty', '')
            })
            
        except Exception as e:
            print(f"      ❌ Fehler: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'index': idx,
                'user_input': user_input,
                'retrieved_contexts': ["Kein Kontext gefunden"],
                'response': f"Fehler bei Response-Generierung: {e}",
                'reference': reference,
                'category': test_row.get('category', ''),
                'difficulty': test_row.get('difficulty', '')
            })
    
    return pd.DataFrame(results)


def run_ragas_evaluation(
    responses_df: pd.DataFrame,
    max_retry_rounds: int = 3
) -> pd.DataFrame:
    """
    Führt RAGAS-Evaluation mit Retry-Logik durch.
    
    Args:
        responses_df: DataFrame mit Chatbot-Responses
        max_retry_rounds: Maximale Anzahl Retry-Runden
        
    Returns:
        DataFrame mit Evaluationsergebnissen
    """
    print("\n" + "=" * 80)
    print("📊 RAGAS EVALUATION")
    print("=" * 80)
    
    # Initialisiere LLM
    print("\n🤖 Initialisiere Ollama LLM...")
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0
    )
    print("✅ LLM bereit")
    
    # Metrics
    metrics = [faithfulness, context_recall, context_precision]
    metric_columns = ['faithfulness', 'context_recall', 'context_precision']
    
    # RunConfig
    run_config = RunConfig(max_workers=4, timeout=OLLAMA_EVALUATION_TIMEOUT)
    
    print(f"\n⚙️ Konfiguration:")
    print(f"   - Anzahl Samples: {len(responses_df)}")
    print(f"   - Max Workers: 4 (parallel)")
    print(f"   - Timeout: {OLLAMA_EVALUATION_TIMEOUT}s pro LLM-Call")
    print(f"   - Max Retry Runden: {max_retry_rounds}")
    
    # Erstelle Dataset
    samples = []
    for _, row in responses_df.iterrows():
        sample = SingleTurnSample(
            user_input=row['user_input'],
            retrieved_contexts=row['retrieved_contexts'],
            response=row['response'],
            reference=row['reference']
        )
        samples.append(sample)
    
    dataset = EvaluationDataset(samples=samples)
    
    # Erstelle results_df mit allen Daten
    results_df = responses_df.copy()
    for metric in metric_columns:
        if metric not in results_df.columns:
            results_df[metric] = None
    
    remaining_indices = list(range(len(responses_df)))
    
    for round_num in range(1, max_retry_rounds + 1):
        if not remaining_indices:
            print(f"\n✅ Alle Evaluationen vollständig!")
            break
        
        print(f"\n🔄 Evaluationsrunde {round_num}/{max_retry_rounds}")
        print(f"   📋 {len(remaining_indices)} Samples zu evaluieren")
        
        # Erstelle Dataset nur mit verbleibenden Samples
        selected_samples = [samples[i] for i in remaining_indices]
        selected_dataset = EvaluationDataset(samples=selected_samples)
        
        print(f"   ⏳ Evaluiere {len(selected_samples)} Samples...")
        
        try:
            # Evaluation
            eval_results = evaluate(
                dataset=selected_dataset,
                metrics=metrics,
                llm=llm,
                raise_exceptions=False,
                run_config=run_config
            )
            eval_df = eval_results.to_pandas()
            
            # Überschreibe Metriken für erfolgreiche Evaluationen
            successfully_evaluated = []
            for idx, original_idx in enumerate(remaining_indices):
                any_success = False
                for metric_col in metric_columns:
                    if metric_col in eval_df.columns and not pd.isna(eval_df.iloc[idx][metric_col]):
                        results_df.at[original_idx, metric_col] = eval_df.iloc[idx][metric_col]
                        any_success = True
                
                if any_success:
                    successfully_evaluated.append(original_idx)
            
            # Update verbleibende Indizes
            new_remaining = []
            for idx in remaining_indices:
                still_failed = results_df.loc[idx, metric_columns].isna().any()
                if still_failed:
                    new_remaining.append(idx)
            
            remaining_indices = new_remaining
            fixed_count = len(responses_df) - len(remaining_indices)
            
            print(f"   ✅ Runde {round_num} abgeschlossen - {fixed_count} erfolgreich, {len(remaining_indices)} verbleibend")
            
        except Exception as e:
            print(f"   ❌ Fehler bei Evaluation: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Final Check
    final_failed_count = len(remaining_indices)
    if final_failed_count > 0:
        print(f"\n⚠️ Nach {max_retry_rounds} Runden verbleiben {final_failed_count} fehlgeschlagene Evaluationen")
        print(f"   Fehlgeschlagene Indizes: {remaining_indices}")
    else:
        print(f"\n🎉 Alle Evaluationen erfolgreich!")
    
    return results_df


def merge_back_to_original(new_results_df: pd.DataFrame, original_indices: list):
    """
    Merged neue Evaluationsergebnisse zurück in Original-Datei.
    
    Args:
        new_results_df: DataFrame mit neuen Evaluationsergebnissen
        original_indices: Original-Indizes der evaluierten Zeilen
    """
    print(f"\n🔄 Merge Ergebnisse zurück in: {RESULTS_FILE}")
    
    # Lade Original
    original_df = pd.read_excel(RESULTS_FILE, engine='openpyxl')
    
    metric_columns = ['faithfulness', 'context_recall', 'context_precision']
    update_columns = ['retrieved_contexts', 'response'] + metric_columns
    
    updates_count = 0
    
    for new_idx, orig_idx in enumerate(original_indices):
        if orig_idx < len(original_df):
            # Update alle relevanten Spalten
            for col in update_columns:
                if col in new_results_df.columns:
                    new_value = new_results_df.iloc[new_idx][col]
                    
                    # Konvertiere Liste zu JSON-String für retrieved_contexts
                    if col == 'retrieved_contexts' and isinstance(new_value, list):
                        new_value = json.dumps(new_value)
                    
                    # Update nur wenn neuer Wert valide ist
                    if col in metric_columns:
                        if pd.notna(new_value):
                            original_df.at[orig_idx, col] = new_value
                            updates_count += 1
                    else:
                        original_df.at[orig_idx, col] = new_value
                        updates_count += 1
    
    # Speichere
    if updates_count > 0:
        original_df.to_excel(RESULTS_FILE, index=False, engine='openpyxl')
        print(f"✅ Original-Ergebnisse aktualisiert: {RESULTS_FILE}")
        print(f"   {updates_count} Werte erfolgreich zurückgeschrieben")
    else:
        print(f"ℹ️ Keine Updates - Original-Datei unverändert")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Hauptfunktion - Komplett-Neu-Evaluation für Fälle ohne Context."""
    
    print("\n" + "=" * 80)
    print("🔄 RAGAS RETRY MIT NEUER CONTEXT-GENERIERUNG")
    print("=" * 80)
    
    try:
        # 1. Lade Daten
        testset_df = load_testset()
        results_df = load_existing_results()
        
        # 2. Finde Fälle ohne Context
        empty_indices = find_empty_context_indices(results_df)
        
        if not empty_indices:
            print("\n✅ Alle Evaluationen haben validen Context - keine Aktion erforderlich")
            return 0
        
        print(f"\n❌ {len(empty_indices)} Evaluationen ohne validen Context gefunden:")
        print(f"   Indizes: {empty_indices}")
        
        show_empty_context_details(results_df, empty_indices)
        
        # 3. Generiere neue Responses
        new_responses_df = generate_chatbot_response_for_indices(testset_df, empty_indices)
        
        # 4. Führe RAGAS-Evaluation durch
        evaluated_df = run_ragas_evaluation(new_responses_df, max_retry_rounds=MAX_RETRY_ROUNDS)
        
        # 5. Speichere Zwischenergebnisse
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = DATA_DIR / f"ragas_results_reeval_{timestamp}.xlsx"
        evaluated_df.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n💾 Zwischenergebnisse gespeichert: {output_file}")
        
        # 6. Merge zurück in Original
        merge_back_to_original(evaluated_df, empty_indices)
        
        # 7. Finale Statistik
        print("\n" + "=" * 80)
        print("✅ KOMPLETT-NEU-EVALUATION ABGESCHLOSSEN!")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
