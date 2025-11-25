"""
RAGAS-Evaluation für WiSo-Chatbot - GEFILTERTE VERSION

Identisch mit ragas_evaluation_with_retry.py, aber:
- Filtert automatisch nach IDs ohne validen Context
- Führt komplette Neu-Evaluation für diese IDs durch
- Merged Ergebnisse zurück in Original-Datei

Features:
- Checkpointing nach jeder erfolgreichen Frage
- Wiederaufnahme bei Abbruch
- Separate Chunks für Context Precision
- Kein automatischer Retry
"""

# ============================================================================
# FILTER-KONFIGURATION
# ============================================================================
# IDs, die neu evaluiert werden sollen (leer = automatisch finden)
FILTER_IDS = []  # z.B. [9, 19, 20] für spezifische IDs

import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
import json
import uuid

# Projekt-Root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, context_precision
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.run_config import RunConfig
from langchain_ollama import ChatOllama
from langsmith import Client
from config.settings import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_EVALUATION_TIMEOUT,
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT
)
from src.agent.react_agent import create_react_agent

# EVALUATION-KONFIGURATION
NUM_QUESTIONS = 40  # Vollständiges Testset
CHECKPOINT_ENABLED = True  # Speichere Fortschritt nach jeder Frage


def save_checkpoint(checkpoint_data: Dict[str, Any], checkpoint_file: Path):
    """Speichere Evaluations-Checkpoint."""
    try:
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)
        print(f"   💾 Checkpoint gespeichert: {checkpoint_file.name}")
    except Exception as e:
        print(f"   ⚠️  Checkpoint-Fehler: {e}")


def load_checkpoint(checkpoint_file: Path) -> Optional[Dict[str, Any]]:
    """Lade Evaluations-Checkpoint."""
    if not checkpoint_file.exists():
        return None
    try:
        with open(checkpoint_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"   ⚠️  Checkpoint laden fehlgeschlagen: {e}")
        return None


def load_testset(csv_path: str = "data/Testset.CSV", limit: int = None) -> pd.DataFrame:
    """Lädt Testset.CSV"""
    full_path = Path(__file__).parent / csv_path
    df = pd.read_csv(full_path, sep=';', encoding='utf-8')
    
    # Stelle sicher, dass ID-Spalte existiert
    if 'id' not in df.columns:
        df['id'] = range(1, len(df) + 1)
    
    # FILTER: Automatisch IDs ohne Context finden oder FILTER_IDS nutzen
    if not FILTER_IDS:
        # Automatische Erkennung
        results_file = Path(__file__).parent / "data" / "ragas_results.xlsx"
        if results_file.exists():
            results_df = pd.read_excel(results_file, engine='openpyxl')
            filter_ids = []
            for idx, row in results_df.iterrows():
                contexts_raw = row['retrieved_contexts']
                try:
                    if pd.isna(contexts_raw):
                        contexts = []
                    elif isinstance(contexts_raw, str):
                        contexts = json.loads(contexts_raw)
                    else:
                        contexts = contexts_raw
                except:
                    contexts = []
                
                is_empty = (
                    len(contexts) == 0 or
                    (len(contexts) == 1 and contexts[0] == "Kein Kontext gefunden")
                )
                if is_empty:
                    filter_ids.append(idx + 1)  # ID = Index + 1
            
            if filter_ids:
                print(f"\n🔍 Automatisch gefiltert: {len(filter_ids)} IDs ohne Context")
                print(f"   IDs: {filter_ids}")
                df = df[df['id'].isin(filter_ids)]
    else:
        # Manuelle Filter-IDs
        print(f"\n🔍 Manuell gefiltert: {len(FILTER_IDS)} IDs")
        print(f"   IDs: {FILTER_IDS}")
        df = df[df['id'].isin(FILTER_IDS)]
    
    if limit:
        df = df.head(limit)
    
    print(f"✅ {len(df)} Testfragen geladen (IDs: {df['id'].min()}-{df['id'].max()})")
    print(f"   Kategorien: {df['category'].unique().tolist()}")
    print(f"   Schwierigkeiten: easy={len(df[df['difficulty']=='easy'])}, "
          f"medium={len(df[df['difficulty']=='medium'])}, "
          f"hard={len(df[df['difficulty']=='hard'])}")
    
    return df


def generate_chatbot_responses(df: pd.DataFrame, agent, langsmith_client) -> EvaluationDataset:
    """
    Generiert Chatbot-Antworten mit RAG-Context aus LangSmith.
    
    Inkludiert:
    - Retry-Mechanismus bei Fehlern
    - Checkpointing nach jeder erfolgreichen Frage
    - Wiederaufnahme bei Abbruch
    """
    # Checkpoint-Datei
    checkpoint_file = Path(__file__).parent / "data" / "evaluation_checkpoint.json"
    
    # Lade existierenden Checkpoint
    checkpoint = load_checkpoint(checkpoint_file) if CHECKPOINT_ENABLED else None
    completed_indices = set(checkpoint.get('completed_indices', [])) if checkpoint else set()
    samples = []
    
    # Restore completed samples from checkpoint
    if checkpoint and 'samples' in checkpoint:
        print(f"\n🔄 Checkpoint gefunden: {len(completed_indices)} Fragen bereits beantwortet")
        print(f"   Fahre fort ab Frage {len(completed_indices) + 1}...\n")
        
        # Rekonstruiere Samples aus Checkpoint
        for sample_data in checkpoint['samples']:
            sample = SingleTurnSample(
                user_input=sample_data['user_input'],
                response=sample_data['response'],
                retrieved_contexts=sample_data['retrieved_contexts'],
                reference=sample_data['reference']
            )
            # Restore session_id
            if 'session_id' in sample_data:
                sample._session_id = sample_data['session_id']
            samples.append(sample)
    
    print("\n💬 Generiere Antworten mit Retry-Mechanismus...")
    print("=" * 80)
    
    for idx, row in df.iterrows():
        # Skip bereits abgeschlossene Fragen
        if idx in completed_indices:
            continue
            
        question_id = row['id']
        question = row['question']
        expected_answer = row['expected_answer']
        
        try:
            print(f"\n[{idx + 1}/{len(df)}] {question[:70]}...")
            
            # Memory löschen
            agent.clear_memory()
            session_id = str(uuid.uuid4())
            
            # Antwort generieren
            response = agent.chat(question, session_id=session_id)
            print(f"   ✅ Antwort: {response[:80]}...")
            
            # Warte und hole Context aus LangSmith
            time.sleep(3)
            all_runs = list(langsmith_client.list_runs(
                project_name=LANGSMITH_PROJECT,
                is_root=True
            ))
            
            matching_run = None
            for run in all_runs:
                if run.metadata and run.metadata.get("session_id") == session_id:
                    matching_run = run
                    break
            
            contexts = ["Kein Kontext gefunden"]
            if matching_run:
                child_runs = list(langsmith_client.list_runs(
                    project_name=LANGSMITH_PROJECT,
                    trace_id=matching_run.trace_id,
                    is_root=False
                ))
                
                # Debug: Zeige alle run_types
                print(f"   🔍 Debug: {len(child_runs)} Child-Runs gefunden")
                run_types = set()
                for child in child_runs:
                    run_types.add(child.run_type)
                    if 'tool' in child.run_type.lower() or 'retriever' in child.run_type.lower():
                        print(f"      - {child.run_type}: {child.name}")
                print(f"   🔍 Unique run_types: {run_types}")
                
                for child in child_runs:
                    # Suche nach retriever UND tool runs (RAG-Tool könnte als "tool" klassifiziert sein)
                    if (child.run_type == "retriever" or 
                        (child.run_type == "tool" and "rag" in child.name.lower())) and child.outputs:
                        documents = child.outputs.get('output', [])
                        print(f"   📄 Gefunden: {child.run_type} '{child.name}' mit {len(documents) if isinstance(documents, list) else 'unknown'} docs")
                        contexts = []
                        for doc in documents:
                            if isinstance(doc, dict) and 'page_content' in doc:
                                contexts.append(doc['page_content'])
                        if contexts:
                            print(f"   ✅ {len(contexts)} Contexts extrahiert")
                            break
                        else:
                            print(f"   ⚠️ Keine page_content in outputs gefunden")
            
            total_context_chars = sum(len(c) for c in contexts)
            print(f"   📄 Context: {len(contexts)} chunks, {total_context_chars} chars")
            
            # Sample erstellen (mit session_id und question_id)
            sample = SingleTurnSample(
                user_input=question,
                response=response,
                retrieved_contexts=contexts,  # Liste von Chunks für Context Precision!
                reference=expected_answer
            )
            samples.append(sample)
            
            # Session-ID und Question-ID für Tracking speichern
            if not hasattr(sample, '_session_id'):
                sample._session_id = session_id
            if not hasattr(sample, '_question_id'):
                sample._question_id = question_id
            
            # Checkpoint speichern
            if CHECKPOINT_ENABLED:
                completed_indices.add(idx)
                checkpoint_data = {
                    'completed_indices': list(completed_indices),
                    'timestamp': time.time(),
                    'samples': [
                        {
                            'user_input': s.user_input,
                            'response': s.response,
                            'retrieved_contexts': s.retrieved_contexts,
                            'reference': s.reference,
                            'session_id': getattr(s, '_session_id', None),
                            'question_id': getattr(s, '_question_id', None)
                        } for s in samples
                    ]
                }
                save_checkpoint(checkpoint_data, checkpoint_file)
            
        except KeyboardInterrupt:
            print(f"\n\n⏸️  Evaluation unterbrochen!")
            print(f"   Checkpoint gespeichert bei Frage {idx + 1}/{len(df)}")
            print(f"   Starte das Skript erneut, um fortzufahren.\n")
            raise
            
        except Exception as e:
            print(f"   ❌ Fehler: {str(e)}")
            print(f"   ⚠️  Überspringe Frage")
            # Erstelle Fallback-Sample
            sample = SingleTurnSample(
                user_input=question,
                response=f"FEHLER: {str(e)}",
                retrieved_contexts=["Fehler beim Abrufen"],
                reference=expected_answer
            )
            if not hasattr(sample, '_question_id'):
                sample._question_id = question_id
            samples.append(sample)
    
    print(f"\n{'=' * 80}")
    print(f"✅ {len(samples)} Antworten erfolgreich generiert\n")
    
    # Lösche Checkpoint nach erfolgreicher Completion
    if CHECKPOINT_ENABLED and checkpoint_file.exists():
        try:
            checkpoint_file.unlink()
            print(f"🧹 Checkpoint gelöscht (alle Fragen abgeschlossen)\n")
        except:
            pass
    
    return EvaluationDataset(samples=samples)


def run_ragas_evaluation(dataset: EvaluationDataset) -> pd.DataFrame:
    """Führt RAGAS-Evaluation durch."""
    
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        timeout=OLLAMA_EVALUATION_TIMEOUT  # 4 Minuten für lange RAGAS-Evaluationen
    )
    
    # RunConfig für Parallelisierung
    run_config = RunConfig(max_workers=4, timeout=OLLAMA_EVALUATION_TIMEOUT)
    
    print("🎯 Starte RAGAS-Evaluation...")
    print("-" * 80)
    print(f"   LLM: {OLLAMA_MODEL}")
    print(f"   Samples: {len(dataset.samples)}")
    print(f"   Max Workers: 4 (parallel)")
    print(f"   Timeout: {OLLAMA_EVALUATION_TIMEOUT}s")
    
    metrics = [
        faithfulness,       # Ist Antwort treu zum Kontext?
        context_recall,     # Ist alle relevante Info im Kontext?
        context_precision   # Sind relevante Chunks höher gerankt?
    ]
    print(f"   Metriken: {[m.name for m in metrics]}")
    print(f"\n   ⏳ Evaluiere {len(dataset.samples)} Samples...")
    print(f"   💡 Dies kann mehrere Minuten dauern (ca. 1-2 Min pro Sample)\n")
    
    # Evaluation mit raise_exceptions=False und RunConfig
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        raise_exceptions=False,
        run_config=run_config
    )
    
    results_df = results.to_pandas()
    
    # Füge session_ids und question_ids hinzu
    results_df['session_id'] = [getattr(sample, '_session_id', None) for sample in dataset.samples]
    results_df['question_id'] = [getattr(sample, '_question_id', None) for sample in dataset.samples]
    
    return results_df


def retry_failed_evaluations(results_df: pd.DataFrame, dataset: EvaluationDataset, llm: ChatOllama, max_retry_rounds: int = 5) -> pd.DataFrame:
    """
    Wiederholt Evaluationen für Zeilen mit fehlenden/NaN-Werten.
    
    Args:
        results_df: DataFrame mit initialen Evaluationsergebnissen
        dataset: Original EvaluationDataset mit allen Samples
        llm: LLM für RAGAS-Evaluation
        max_retry_rounds: Maximale Anzahl von Wiederholungsrunden
    
    Returns:
        Vollständig evaluiertes DataFrame
    """
    metrics = [faithfulness, context_recall, context_precision]
    metric_columns = ['faithfulness', 'context_recall', 'context_precision']
    
    # RunConfig für Retry (gleiche Settings)
    run_config = RunConfig(max_workers=4, timeout=OLLAMA_EVALUATION_TIMEOUT)
    
    for round_num in range(1, max_retry_rounds + 1):
        # Finde Zeilen mit fehlenden Werten
        failed_mask = results_df[metric_columns].isna().any(axis=1)
        failed_indices = results_df[failed_mask].index.tolist()
        
        if not failed_indices:
            print(f"\n✅ Alle {len(results_df)} Evaluationen vollständig!")
            break
        
        print(f"\n🔄 Wiederholungsrunde {round_num}/{max_retry_rounds}")
        print(f"   📋 {len(failed_indices)} fehlgeschlagene Evaluationen gefunden")
        print(f"   🎯 Indizes: {failed_indices}")
        
        # Erstelle Dataset nur mit fehlgeschlagenen Samples
        failed_samples = [dataset.samples[i] for i in failed_indices]
        failed_dataset = EvaluationDataset(samples=failed_samples)
        
        print(f"   ⏳ Re-evaluiere {len(failed_samples)} Samples...")
        
        try:
            # Re-Evaluation mit RunConfig
            retry_results = evaluate(
                dataset=failed_dataset,
                metrics=metrics,
                llm=llm,
                raise_exceptions=False,
                run_config=run_config
            )
            retry_df = retry_results.to_pandas()
            
            # Überschreibe nur die Metrik-Spalten + session_id in den fehlgeschlagenen Zeilen
            for idx, original_idx in enumerate(failed_indices):
                for metric_col in metric_columns:
                    if metric_col in retry_df.columns and not pd.isna(retry_df.iloc[idx][metric_col]):
                        results_df.at[original_idx, metric_col] = retry_df.iloc[idx][metric_col]
                
                # Update session_id für erfolgreiche Retries
                if 'session_id' in retry_df.columns:
                    new_session_id = retry_df.iloc[idx]['session_id']
                    if new_session_id is not None:
                        results_df.at[original_idx, 'session_id'] = new_session_id
            
            # Zähle verbleibende Fehler
            remaining_failed = results_df[metric_columns].isna().any(axis=1).sum()
            print(f"   ✅ Runde {round_num} abgeschlossen - {remaining_failed} Fehler verbleibend")
            
        except Exception as e:
            print(f"   ❌ Fehler bei Re-Evaluation: {e}")
            continue
    
    # Final Check
    final_failed = results_df[metric_columns].isna().any(axis=1).sum()
    if final_failed > 0:
        print(f"\n⚠️  WARNUNG: {final_failed} Evaluationen konnten nicht vollständig durchgeführt werden")
        print(f"   Betroffene Indizes: {results_df[results_df[metric_columns].isna().any(axis=1)].index.tolist()}")
    
    return results_df


def display_and_save_results(results_df: pd.DataFrame, test_df: pd.DataFrame):
    """Zeigt Ergebnisse an und speichert sie."""
    
    # Kategorien und Schwierigkeiten hinzufügen
    results_df['category'] = test_df['category'].values[:len(results_df)]
    results_df['difficulty'] = test_df['difficulty'].values[:len(results_df)]
    
    print("\n" + "=" * 80)
    print("📊 RAGAS-EVALUATION ERGEBNISSE")
    print("=" * 80)
    
    # Gesamtscores
    print("\n📈 Durchschnittliche Scores:")
    print("-" * 80)
    for metric in ['faithfulness', 'context_recall', 'context_precision']:
        if metric in results_df.columns:
            avg = results_df[metric].mean()
            print(f"   {metric:20s}: {avg:.3f}")
    
    # Nach Kategorie
    print("\n📁 Scores nach Kategorie:")
    print("-" * 80)
    for category in results_df['category'].unique():
        cat_df = results_df[results_df['category'] == category]
        print(f"\n   {category}:")
        for metric in ['faithfulness', 'context_recall', 'context_precision']:
            if metric in cat_df.columns:
                avg = cat_df[metric].mean()
                print(f"      {metric:20s}: {avg:.3f}")
    
    # Nach Schwierigkeit
    print("\n⚡ Scores nach Schwierigkeit:")
    print("-" * 80)
    for difficulty in ['easy', 'medium', 'hard']:
        diff_df = results_df[results_df['difficulty'] == difficulty]
        if len(diff_df) > 0:
            print(f"\n   {difficulty.upper()}:")
            for metric in ['faithfulness', 'context_recall', 'context_precision']:
                if metric in diff_df.columns:
                    avg = diff_df[metric].mean()
                    print(f"      {metric:20s}: {avg:.3f}")
    
    # Speichern als Excel (behält JSON-Struktur für retrieved_contexts)
    output_dir = Path(__file__).parent / "data"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "ragas_results.xlsx"
    
    # Konvertiere retrieved_contexts zu JSON-String (Original-Format aus LangSmith)
    import json
    results_df_export = results_df.copy()
    
    # Merge mit Original-Testdaten via question_id
    if 'question_id' in results_df_export.columns and 'id' in test_df.columns:
        # Erstelle Mapping von question_id zu Test-Daten
        test_mapping = test_df.set_index('id')[['category', 'difficulty']]
        results_df_export['category'] = results_df_export['question_id'].map(test_mapping['category'])
        results_df_export['difficulty'] = results_df_export['question_id'].map(test_mapping['difficulty'])
    else:
        # Fallback: Index-basiertes Mapping
        for col in ['category', 'difficulty']:
            if col in test_df.columns:
                results_df_export[col] = test_df[col].values
    
    if 'retrieved_contexts' in results_df_export.columns:
        results_df_export['retrieved_contexts'] = results_df_export['retrieved_contexts'].apply(
            lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, list) else str(x)
        )
    
    # MERGE zurück in Original-Datei (bei gefilterten Evaluationen)
    if FILTER_IDS or len(results_df) < 40:
        print(f"\n🔄 Merge gefilterte Ergebnisse zurück in Original-Datei...")
        
        # Lade Original-Datei (die ALLE 40 Zeilen haben sollte)
        original_df = pd.read_excel(output_file, engine='openpyxl')
        
        if len(original_df) != 40:
            print(f"⚠️  WARNUNG: Original-Datei hat nur {len(original_df)} statt 40 Zeilen!")
            print(f"   Merge wird trotzdem durchgeführt...")
        
        metric_columns = ['faithfulness', 'context_recall', 'context_precision']
        update_columns = ['retrieved_contexts', 'response'] + metric_columns
        updates_count = 0
        
        # Map via question_id ODER user_input
        for _, new_row in results_df_export.iterrows():
            question_id = new_row.get('question_id')
            user_input = new_row.get('user_input')
            
            # Versuche zuerst question_id
            orig_idx = None
            if pd.notna(question_id):
                orig_idx = int(question_id) - 1
            # Fallback: Finde via user_input
            elif pd.notna(user_input):
                matches = original_df[original_df['user_input'] == user_input]
                if len(matches) > 0:
                    orig_idx = matches.index[0]
            
            if orig_idx is not None and orig_idx < len(original_df):
                for col in update_columns:
                    if col in results_df_export.columns:
                        new_value = new_row[col]
                        # Update nur valide Werte
                        if col in metric_columns:
                            if pd.notna(new_value):
                                original_df.at[orig_idx, col] = new_value
                                updates_count += 1
                        else:
                            original_df.at[orig_idx, col] = new_value
        
        if updates_count > 0:
            original_df.to_excel(output_file, index=False, engine='openpyxl')
            print(f"✅ {updates_count} Metriken in Original-Datei aktualisiert")
            print(f"   Datei hat jetzt {len(original_df)} Zeilen")
        else:
            print(f"ℹ️  Keine Updates erforderlich")
    else:
        # Keine Filterung - normale Speicherung
        results_df_export.to_excel(output_file, index=False, engine='openpyxl')
        print(f"\n💾 Ergebnisse gespeichert: {output_file}")


def main():
    """Hauptfunktion."""
    
    print("\n" + "=" * 80)
    print("RAGAS-EVALUATION FÜR WISO-CHATBOT (GEFILTERT)")
    print("=" * 80)
    
    try:
        # 1. Lade Testset
        print("\n📂 Lade Testset...")
        test_df = load_testset(limit=NUM_QUESTIONS)
        
        # 2. Initialisiere Agent und LangSmith
        print("\n🤖 Initialisiere Chatbot...")
        agent = create_react_agent()
        langsmith_client = Client(api_key=LANGSMITH_API_KEY)
        print("✅ Chatbot und LangSmith-Client bereit")
        
        # 3. Generiere Antworten mit Retry
        dataset = generate_chatbot_responses(test_df, agent, langsmith_client)
        
        # 4. RAGAS-Evaluation (initial)
        results_df = run_ragas_evaluation(dataset)
        
        # 5. LLM für Retry vorbereiten
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.0,
            timeout=OLLAMA_EVALUATION_TIMEOUT
        )
        
        # 6. Ergebnisse anzeigen und speichern
        display_and_save_results(results_df, test_df)
        
        print("\n" + "=" * 80)
        print("✅ EVALUATION ERFOLGREICH ABGESCHLOSSEN!")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⏸️  Evaluation durch Benutzer unterbrochen")
        print("   Checkpoint wurde gespeichert - Fortfahren jederzeit möglich")
        
    except Exception as e:
        print(f"\n❌ Evaluation fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
