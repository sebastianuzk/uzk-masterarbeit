"""
Retry-Script mit manueller Index-Auswahl für fehlgeschlagene RAGAS-Evaluationen

Erlaubt das Auswählen spezifischer Indizes für Retry.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    context_recall,
    context_precision
)
from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
from ragas.run_config import RunConfig
from langchain_ollama import ChatOllama
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()

# Configuration aus .env (globale Ollama-Settings)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EVALUATION_TIMEOUT = int(os.getenv("OLLAMA_EVALUATION_TIMEOUT", "240"))

# Selective Mode: Wenn True, wird nach spezifischen Indizes gefragt
# Wenn False (Standard), werden automatisch ALLE fehlgeschlagenen Indizes retried
SELECTIVE_MODE = False  # Setze auf True für manuelle Index-Auswahl

# Paths - suche in src/evaluation/data/
RESULTS_DIR = Path(__file__).parent / "data"
RESULTS_FILE = RESULTS_DIR / "ragas_results.xlsx"


def find_results_file() -> Path:
    """Findet die neueste RAGAS-Ergebnisdatei."""
    possible_files = [
        RESULTS_DIR / "ragas_results.xlsx",
        RESULTS_DIR / "ragas_results_with_retry.xlsx",
        Path("data/ragas_results.xlsx"),
        Path("data/ragas_results_with_retry.xlsx")
    ]
    
    for file_path in possible_files:
        if file_path.exists():
            return file_path
    
    raise FileNotFoundError(
        f"Keine RAGAS-Ergebnisdatei gefunden. Gesucht in:\n" +
        "\n".join(f"  - {f}" for f in possible_files)
    )


def load_existing_results() -> tuple[pd.DataFrame, EvaluationDataset]:
    """
    Lädt existierende RAGAS-Ergebnisse und rekonstruiert Dataset.
    
    Returns:
        Tuple of (results_df, evaluation_dataset)
    """
    results_file = find_results_file()
    print(f"📂 Lade existierende Ergebnisse: {results_file}")
    
    results_df = pd.read_excel(results_file, engine='openpyxl')
    print(f"✅ {len(results_df)} Evaluationen geladen")
    
    # Rekonstruiere EvaluationDataset aus DataFrame
    import json
    samples = []
    for _, row in results_df.iterrows():
        # Handle retrieved_contexts - JSON-String → Liste
        contexts = []
        if pd.notna(row.get('retrieved_contexts')):
            ctx_value = row['retrieved_contexts']
            if isinstance(ctx_value, str):
                try:
                    # Parse JSON-String zurück zu Liste
                    contexts = json.loads(ctx_value)
                    if not isinstance(contexts, list):
                        contexts = [str(contexts)]
                except json.JSONDecodeError:
                    # Fallback: String als einzelner Context
                    contexts = [ctx_value]
            elif isinstance(ctx_value, list):
                contexts = ctx_value
            else:
                contexts = [str(ctx_value)]
        
        sample = SingleTurnSample(
            user_input=row['user_input'],
            response=row['response'],
            retrieved_contexts=contexts,  # MUSS Liste sein für context_precision!
            reference=row.get('reference', '') if pd.notna(row.get('reference')) else ''
        )
        
        # Füge question_id hinzu falls vorhanden
        if 'question_id' in row and pd.notna(row['question_id']):
            sample._question_id = int(row['question_id'])
        
        samples.append(sample)
    
    dataset = EvaluationDataset(samples=samples)
    print(f"✅ Dataset mit {len(samples)} Samples rekonstruiert")
    
    return results_df, dataset


def show_failed_indices(results_df: pd.DataFrame) -> list[int]:
    """
    Zeigt fehlgeschlagene Indizes an.
    
    Args:
        results_df: DataFrame mit Evaluationsergebnissen
        
    Returns:
        Liste der fehlgeschlagenen Indizes
    """
    # Identifiziere verfügbare Metrik-Spalten (gleiche wie produktive Evaluation)
    all_metrics = ['faithfulness', 'context_recall', 'context_precision']
    metric_columns = [col for col in all_metrics if col in results_df.columns]
    
    if not metric_columns:
        print(f"\n⚠️ Keine Metrik-Spalten gefunden. Verfügbare Spalten: {results_df.columns.tolist()}")
        return list(range(len(results_df)))  # Alle Indizes als fehlgeschlagen markieren
    
    # Finde fehlgeschlagene Evaluationen
    failed_mask = results_df[metric_columns].isna().any(axis=1)
    failed_indices = results_df[failed_mask].index.tolist()
    
    if not failed_indices:
        print("\n✅ Alle Evaluationen sind vollständig - keine fehlgeschlagenen Indizes!")
        return []
    
    print(f"\n❌ {len(failed_indices)} fehlgeschlagene Evaluationen gefunden:")
    print(f"   Indizes: {failed_indices}")
    
    # Zeige Details
    print("\n📋 Details der fehlgeschlagenen Evaluationen:")
    for idx in failed_indices:
        row = results_df.iloc[idx]
        question = row['user_input'][:60] + "..." if len(row['user_input']) > 60 else row['user_input']
        missing_metrics = [col for col in metric_columns if pd.isna(row[col])]
        question_id = row.get('question_id', 'N/A')
        print(f"\n   Index {idx} (ID: {question_id}):")
        print(f"      Frage: {question}")
        print(f"      Fehlende Metriken: {', '.join(missing_metrics)}")
    
    return failed_indices


def get_user_selection(failed_indices: list[int]) -> list[int]:
    """
    Lässt Benutzer Indizes auswählen.
    
    Args:
        failed_indices: Liste der verfügbaren fehlgeschlagenen Indizes
        
    Returns:
        Liste der ausgewählten Indizes
    """
    print("\n" + "=" * 80)
    print("🎯 INDEX-AUSWAHL")
    print("=" * 80)
    print("\nOptionen:")
    print("  1. Alle fehlgeschlagenen Indizes (default)")
    print("  2. Spezifische Indizes auswählen (z.B. '0,5,12' oder '0-5')")
    print("  3. Abbrechen")
    
    choice = input("\nIhre Wahl (Enter für alle): ").strip()
    
    if not choice or choice == "1":
        print(f"✅ Alle {len(failed_indices)} Indizes ausgewählt")
        return failed_indices
    
    if choice == "3":
        print("❌ Abgebrochen")
        return []
    
    # Parse Eingabe
    selected = []
    try:
        parts = choice.split(',')
        for part in parts:
            part = part.strip()
            if '-' in part:
                # Range: 0-5
                start, end = map(int, part.split('-'))
                selected.extend(range(start, end + 1))
            else:
                # Einzelner Index
                selected.append(int(part))
        
        # Filter nur gültige fehlgeschlagene Indizes
        valid_selected = [idx for idx in selected if idx in failed_indices]
        
        if not valid_selected:
            print("❌ Keine gültigen Indizes ausgewählt")
            return []
        
        print(f"✅ {len(valid_selected)} Indizes ausgewählt: {valid_selected}")
        return valid_selected
        
    except Exception as e:
        print(f"❌ Fehler beim Parsen der Eingabe: {e}")
        return []


def retry_selected_evaluations(
    results_df: pd.DataFrame,
    dataset: EvaluationDataset,
    selected_indices: list[int],
    llm: ChatOllama,
    max_retry_rounds: int = 3
) -> pd.DataFrame:
    """
    Retry für ausgewählte Indizes.
    
    Args:
        results_df: DataFrame mit existierenden Ergebnissen
        dataset: Original EvaluationDataset
        selected_indices: Liste der zu wiederholenden Indizes
        llm: Ollama LLM für Evaluation
        max_retry_rounds: Maximale Anzahl Wiederholungsrunden
        
    Returns:
        Aktualisierter DataFrame mit Retry-Ergebnissen
    """
    if not selected_indices:
        print("⚠️ Keine Indizes zum Retry ausgewählt")
        return results_df
    
    # Metriken (gleiche wie produktive Evaluation)
    metrics = [
        faithfulness,
        context_recall,
        context_precision
    ]
    
    metric_columns = ['faithfulness', 'context_recall', 'context_precision']
    
    # RunConfig mit reduziertem max_workers
    run_config = RunConfig(max_workers=4, timeout=OLLAMA_EVALUATION_TIMEOUT)
    
    print("\n" + "=" * 80)
    print("🔄 RETRY AUSGEWÄHLTER EVALUATIONEN")
    print("=" * 80)
    print(f"⚙️ Konfiguration:")
    print(f"   - Ausgewählte Indizes: {selected_indices}")
    print(f"   - Anzahl: {len(selected_indices)}")
    print(f"   - Max Workers: 4 (parallel)")
    print(f"   - Timeout: {OLLAMA_EVALUATION_TIMEOUT}s pro LLM-Call")
    print(f"   - Max Retry Runden: {max_retry_rounds}")
    
    remaining_indices = selected_indices.copy()
    
    for round_num in range(1, max_retry_rounds + 1):
        if not remaining_indices:
            print(f"\n✅ Alle ausgewählten Evaluationen vollständig!")
            break
        
        print(f"\n🔄 Wiederholungsrunde {round_num}/{max_retry_rounds}")
        print(f"   📋 {len(remaining_indices)} Indizes zu evaluieren")
        print(f"   🎯 Indizes: {remaining_indices}")
        
        # Erstelle Dataset nur mit ausgewählten Samples
        selected_samples = [dataset.samples[i] for i in remaining_indices]
        selected_dataset = EvaluationDataset(samples=selected_samples)
        
        print(f"   ⏳ Evaluiere {len(selected_samples)} Samples...")
        
        try:
            # Evaluation mit RunConfig
            retry_results = evaluate(
                dataset=selected_dataset,
                metrics=metrics,
                llm=llm,
                raise_exceptions=False,
                run_config=run_config
            )
            retry_df = retry_results.to_pandas()
            
            # Überschreibe Metrik-Spalten für erfolgreiche Evaluationen
            successfully_evaluated = []
            for idx, original_idx in enumerate(remaining_indices):
                any_success = False
                for metric_col in metric_columns:
                    if metric_col in retry_df.columns and not pd.isna(retry_df.iloc[idx][metric_col]):
                        results_df.at[original_idx, metric_col] = retry_df.iloc[idx][metric_col]
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
            fixed_count = len(selected_indices) - len(remaining_indices)
            
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
        print(f"\n🎉 Alle ausgewählten Evaluationen erfolgreich!")
    
    return results_df


def display_and_save_results(results_df: pd.DataFrame, output_suffix: str = ""):
    """
    Zeigt Ergebnisse an und speichert sie.
    
    Args:
        results_df: DataFrame mit Evaluationsergebnissen
        output_suffix: Suffix für Output-Datei
    """
    print("\n" + "=" * 80)
    print("📊 FINALE ERGEBNISSE")
    print("=" * 80)
    
    metric_columns = ['faithfulness', 'context_recall', 'context_precision']
    
    # Statistiken
    print("\n📈 Metriken (Durchschnitt über alle erfolgreichen Evaluationen):")
    for metric in metric_columns:
        if metric in results_df.columns:
            valid_values = results_df[metric].dropna()
            if len(valid_values) > 0:
                mean_val = valid_values.mean()
                print(f"   {metric.replace('_', ' ').title():<20}: {mean_val:.4f}")
    
    # Erfolgsrate
    total_samples = len(results_df)
    failed_count = results_df[metric_columns].isna().any(axis=1).sum()
    success_count = total_samples - failed_count
    success_rate = (success_count / total_samples) * 100 if total_samples > 0 else 0
    
    print(f"\n✅ Erfolgsrate: {success_count}/{total_samples} ({success_rate:.1f}%)")
    
    if failed_count > 0:
        print(f"❌ Fehlgeschlagen: {failed_count}/{total_samples} ({100-success_rate:.1f}%)")
        failed_indices = results_df[results_df[metric_columns].isna().any(axis=1)].index.tolist()
        print(f"   Fehlgeschlagene Indizes: {failed_indices}")
    
    # Speichern
    output_name = f"ragas_results_retry{output_suffix}.xlsx" if output_suffix else "ragas_results_retry.xlsx"
    output_file = RESULTS_DIR / output_name
    
    print(f"\n💾 Speichere Retry-Ergebnisse: {output_file}")
    results_df.to_excel(output_file, index=False, engine='openpyxl')
    print(f"✅ Ergebnisse gespeichert: {output_file}")
    
    # Merge erfolgreich retried results zurück in original file
    original_file = find_results_file()
    print(f"\n🔄 Merge Retry-Ergebnisse zurück in: {original_file}")
    
    # Lade original results
    original_df = pd.read_excel(original_file, engine='openpyxl')
    
    metric_columns = ['faithfulness', 'context_recall', 'context_precision']
    available_metrics = [col for col in metric_columns if col in results_df.columns]
    
    # Zähle erfolgreiche Updates
    updates_count = 0
    
    # Merge via question_id falls vorhanden, sonst via index
    if 'question_id' in results_df.columns and 'question_id' in original_df.columns:
        print("   Merge via question_id...")
        for _, retry_row in results_df.iterrows():
            qid = retry_row.get('question_id')
            if pd.notna(qid):
                # Finde matching row in original
                mask = original_df['question_id'] == qid
                if mask.any():
                    # Update nur non-NaN Metriken (nur erfolgreich evaluierte)
                    for metric in available_metrics:
                        if pd.notna(retry_row[metric]):
                            # Prüfe ob Original NaN war (d.h. wirklich ein Update)
                            original_value = original_df.loc[mask, metric].values[0]
                            if pd.isna(original_value):
                                original_df.loc[mask, metric] = retry_row[metric]
                                updates_count += 1
    else:
        print("   Merge via index (fallback)...")
        for idx in results_df.index:
            if idx < len(original_df):
                for metric in available_metrics:
                    if pd.notna(results_df.loc[idx, metric]):
                        # Prüfe ob Original NaN war (d.h. wirklich ein Update)
                        if pd.isna(original_df.loc[idx, metric]):
                            original_df.loc[idx, metric] = results_df.loc[idx, metric]
                            updates_count += 1
    
    # Speichere updated original file nur wenn Updates vorhanden
    if updates_count > 0:
        original_df.to_excel(original_file, index=False, engine='openpyxl')
        print(f"✅ Original-Ergebnisse aktualisiert: {original_file}")
        print(f"   {updates_count} Metriken erfolgreich zurückgeschrieben")
    else:
        print(f"ℹ️ Keine neuen erfolgreichen Evaluationen - Original-Datei unverändert")


def main():
    """Hauptfunktion - Retry mit Index-Auswahl."""
    
    print("\n" + "=" * 80)
    print("🔄 RAGAS RETRY MIT INDEX-AUSWAHL")
    print("=" * 80)
    
    try:
        # 1. Lade existierende Ergebnisse
        results_df, dataset = load_existing_results()
        
        # 2. Zeige fehlgeschlagene Indizes
        failed_indices = show_failed_indices(results_df)
        
        if not failed_indices:
            print("\n✅ Keine Retry-Aktionen erforderlich")
            return 0
        
        # 3. Index-Auswahl basierend auf SELECTIVE_MODE
        if SELECTIVE_MODE:
            print(f"\n📌 SELECTIVE_MODE aktiv - Manuelle Auswahl erforderlich")
            selected_indices = get_user_selection(failed_indices)
            
            if not selected_indices:
                print("\n❌ Keine Indizes ausgewählt - Abbruch")
                return 0
        else:
            print(f"\n🔄 AUTO-MODE - Alle {len(failed_indices)} fehlgeschlagenen Indizes werden retried")
            selected_indices = failed_indices
        
        # 4. Initialisiere LLM
        print("\n🤖 Initialisiere Ollama LLM...")
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            timeout=OLLAMA_EVALUATION_TIMEOUT
        )
        print("✅ LLM bereit")
        
        # 5. Retry ausgewählter Evaluationen
        results_df = retry_selected_evaluations(
            results_df, 
            dataset, 
            selected_indices, 
            llm, 
            max_retry_rounds=3
        )
        
        # 6. Ergebnisse anzeigen und speichern
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        display_and_save_results(results_df, output_suffix=f"_{timestamp}")
        
        print("\n" + "=" * 80)
        print("✅ RETRY ERFOLGREICH ABGESCHLOSSEN!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
