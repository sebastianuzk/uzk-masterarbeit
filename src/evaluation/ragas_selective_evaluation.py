"""
RAGAS-Evaluation für spezifische Testfragen (gezielt einzelne Indizes)

Evaluiert nur ausgewählte Fragen aus dem Testset und aktualisiert die bestehenden
Ergebnisse in ragas_results.csv (oder erstellt neue, falls nicht vorhanden).
"""

import sys
import os
import pandas as pd
from pathlib import Path
from typing import List
import time

# Fix Windows Terminal encoding für Emojis
if os.name == 'nt':
    import codecs
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

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
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT
)
from src.agent.react_agent import create_react_agent

# ============================================================================
# KONFIGURATION: Hier die Indizes eintragen (1-basiert wie in CSV)
# ============================================================================
SPECIFIC_INDICES = []  # Leer lassen für Auto-Detect (fehlgeschlagen + fehlend)
AUTO_DETECT_FAILED = True  # Automatisch fehlgeschlagene IDs aus ragas_results.csv erkennen
AUTO_DETECT_MISSING = True  # Automatisch noch nicht evaluierte IDs erkennen
REUSE_EXISTING_RESPONSES = True  # Antworten und Kontexte aus ragas_results.csv laden (statt neu generieren)


def detect_failed_and_missing_indices(results_path: Path, testset_path: Path) -> tuple:
    """
    Erkennt fehlgeschlagene IDs aus ragas_results.csv UND noch nicht evaluierte IDs.
    
    Fehlgeschlagen: Mindestens eine Metrik ist NaN
    Fehlend: ID existiert im Testset aber nicht in ragas_results.csv
    
    Returns:
        Tuple (failed_ids, missing_ids)
    """
    failed_ids = []
    missing_ids = []
    
    # Lade Testset um alle erwarteten IDs zu kennen
    testset_df = pd.read_csv(testset_path, sep=';', encoding='utf-8')
    all_expected_ids = set(testset_df['id'].tolist())
    
    if not results_path.exists():
        print("ℹ️  Keine bestehende ragas_results.csv gefunden")
        missing_ids = sorted(list(all_expected_ids))
        print(f"📋 Alle {len(missing_ids)} IDs müssen evaluiert werden: {missing_ids}")
        return failed_ids, missing_ids
    
    df = pd.read_csv(results_path, encoding='utf-8')
    
    if 'id' not in df.columns:
        print("⚠️  CSV hat keine 'id' Spalte - kann Status nicht prüfen")
        missing_ids = sorted(list(all_expected_ids))
        return failed_ids, missing_ids
    
    # Prüfe welche IDs NaN-Werte in den Metriken haben
    metric_cols = ['faithfulness', 'context_recall', 'context_precision']
    existing_ids = set()
    
    for _, row in df.iterrows():
        row_id = int(row['id'])
        existing_ids.add(row_id)
        has_nan = any(pd.isna(row.get(metric)) for metric in metric_cols)
        if has_nan:
            failed_ids.append(row_id)
    
    # Finde IDs die im Testset sind aber nicht in Results
    missing_ids = sorted(list(all_expected_ids - existing_ids))
    
    if failed_ids:
        print(f"🔍 {len(failed_ids)} fehlgeschlagene IDs erkannt: {sorted(failed_ids)}")
    else:
        print("✅ Keine fehlgeschlagenen IDs gefunden")
    
    if missing_ids:
        print(f"📋 {len(missing_ids)} noch nicht evaluierte IDs erkannt: {missing_ids}")
    else:
        print("✅ Alle IDs wurden bereits evaluiert")
    
    return failed_ids, missing_ids


def detect_missing_metrics_per_id(results_path: Path) -> dict:
    """
    Erkennt welche Metriken pro ID noch fehlen (NaN).
    
    Returns:
        Dict mit {id: [liste_fehlender_metriken]}
    """
    if not results_path.exists():
        return {}
    
    df = pd.read_csv(results_path, encoding='utf-8')
    
    if 'id' not in df.columns:
        return {}
    
    metric_cols = ['faithfulness', 'context_recall', 'context_precision']
    missing_metrics = {}
    
    for _, row in df.iterrows():
        row_id = int(row['id'])
        missing = []
        for metric in metric_cols:
            if pd.isna(row.get(metric)):
                missing.append(metric)
        if missing:
            missing_metrics[row_id] = missing
    
    return missing_metrics


def load_testset_filtered(csv_path: str = "data/Testset.CSV", indices: List[int] = None) -> pd.DataFrame:
    """Lädt nur spezifische Fragen aus Testset.CSV"""
    full_path = Path(__file__).parent / csv_path
    df = pd.read_csv(full_path, sep=';', encoding='utf-8')
    
    if indices:
        # Filtere nach ID (1-basiert)
        df = df[df['id'].isin(indices)]
        print(f"✅ {len(df)} Testfragen gefiltert (IDs: {sorted(indices)})")
    else:
        print(f"✅ {len(df)} Testfragen geladen (alle)")
    
    if len(df) == 0:
        print("⚠️  Keine Fragen gefunden für die angegebenen Indizes!")
        sys.exit(1)
    
    print(f"   Kategorien: {df['category'].unique().tolist()}")
    print(f"   Schwierigkeiten: easy={len(df[df['difficulty']=='easy'])}, medium={len(df[df['difficulty']=='medium'])}, hard={len(df[df['difficulty']=='hard'])}")
    
    return df


def load_existing_responses(indices: List[int]) -> EvaluationDataset:
    """
    Lädt bereits generierte Antworten und Kontexte aus ragas_results.csv.
    
    Args:
        indices: Liste der zu ladenden IDs
        
    Returns:
        EvaluationDataset mit den geladenen Samples
    """
    results_path = Path(__file__).parent / "data" / "ragas_results.csv"
    
    if not results_path.exists():
        raise FileNotFoundError(f"ragas_results.csv nicht gefunden: {results_path}")
    
    print("\n📂 Lade existierende Antworten aus ragas_results.csv...")
    print("=" * 80)
    
    df = pd.read_csv(results_path, encoding='utf-8')
    
    # Filtere nach IDs
    df = df[df['id'].isin(indices)]
    
    if len(df) == 0:
        raise ValueError(f"Keine Einträge für IDs {indices} in ragas_results.csv gefunden")
    
    samples = []
    
    for _, row in df.iterrows():
        question_id = int(row['id'])
        question = row['user_input']
        answer = row['response']
        reference = row['reference']
        
        # Konvertiere retrieved_contexts von String zurück zu Liste
        contexts_str = row['retrieved_contexts']
        if isinstance(contexts_str, str):
            try:
                # Versuche als Python-Liste zu parsen
                import ast
                contexts = ast.literal_eval(contexts_str)
            except (ValueError, SyntaxError):
                # Falls das nicht klappt, als einzelnen String behandeln
                contexts = [contexts_str]
        elif isinstance(contexts_str, list):
            contexts = contexts_str
        else:
            contexts = ["Kein RAG-Kontext gefunden"]
        
        print(f"   ID {question_id}: {question[:60]}...")
        print(f"      📄 Kontext: {len(contexts)} chunks, {sum(len(c) for c in contexts)} Zeichen")
        
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=reference
        )
        samples.append(sample)
    
    print("\n" + "=" * 80)
    print(f"✅ {len(samples)} Samples aus CSV geladen\n")
    
    return EvaluationDataset(samples=samples), df


def get_rag_context_from_langsmith(client: Client, trace_id: str) -> List[str]:
    """Holt RAG-Kontext-Chunks aus LangSmith"""
    try:
        child_runs = list(client.list_runs(
            project_name=LANGSMITH_PROJECT,
            trace_id=trace_id,
            is_root=False
        ))
        
        contexts = []
        for child in child_runs:
            if child.run_type == "retriever":
                if child.outputs and isinstance(child.outputs, dict):
                    documents = child.outputs.get('output', [])
                    for doc in documents:
                        if isinstance(doc, dict) and 'page_content' in doc:
                            contexts.append(doc['page_content'])
        
        if contexts:
            return contexts
        
        return ["Kein RAG-Kontext gefunden"]
    
    except Exception as e:
        print(f"      ⚠️ LangSmith-Fehler: {str(e)[:100]}")
        return ["LangSmith-Fehler"]


def generate_chatbot_responses(df: pd.DataFrame, agent, langsmith_client: Client) -> EvaluationDataset:
    """Generiert Chatbot-Antworten für die gefilterten Fragen"""
    print("\n🤖 Generiere Chatbot-Antworten...")
    print("=" * 80)
    
    samples = []
    
    for idx, row in df.iterrows():
        question_id = row['id']
        question = row['question']
        expected_answer = row['expected_answer']
        
        print(f"\n[{idx + 1}/{len(df)}] ID={question_id}: {question[:60]}...")
        
        agent.clear_memory()
        
        print(f"   💬 Chatbot fragen...")
        import uuid
        session_id = str(uuid.uuid4())
        
        answer = agent.chat(question, session_id=session_id)
        print(f"   ✅ Antwort: {answer[:80]}...")
        
        time.sleep(1)  # Reduziert von 3s auf 1s
        
        print(f"   🔍 Hole RAG-Kontext aus LangSmith...")
        
        # Optimiert: Nur den letzten Run holen (statt alle)
        recent_runs = list(langsmith_client.list_runs(
            project_name=LANGSMITH_PROJECT,
            is_root=True,
            limit=1  # Nur den letzten Run
        ))
        
        contexts = ["Kein RAG-Kontext gefunden"]
        matching_run = None
        
        # Der letzte Run sollte unser Run sein
        if recent_runs:
            matching_run = recent_runs[0]
        
        if matching_run:
            trace_id = matching_run.trace_id
            contexts = get_rag_context_from_langsmith(langsmith_client, trace_id)
            print(f"   ✅ Run gefunden mit Session-ID: {session_id[:8]}...")
        else:
            print(f"   ⚠️ Kein Run mit Session-ID {session_id[:8]}... gefunden")
        
        total_chars = sum(len(c) for c in contexts)
        print(f"   📄 Kontext: {len(contexts)} chunks, {total_chars} Zeichen")
        
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=expected_answer
        )
        samples.append(sample)
    
    print("\n" + "=" * 80)
    print(f"✅ {len(samples)} Antworten generiert\n")
    
    return EvaluationDataset(samples=samples)


def run_ragas_evaluation(dataset: EvaluationDataset, metrics_to_compute: List[str] = None) -> pd.DataFrame:
    """
    Führt RAGAS-Evaluation durch.
    
    Args:
        dataset: Das EvaluationDataset mit den Samples
        metrics_to_compute: Optional - Liste der zu berechnenden Metriken.
                           Falls None, werden alle berechnet.
                           Mögliche Werte: 'faithfulness', 'context_recall', 'context_precision'
    """
    print("🚀 Starte RAGAS-Evaluation...")
    print("=" * 80)
    
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,
        num_ctx=12288  # Reduziert für 8GB VRAM (Modell ~5GB + KV-Cache ~1.5GB)
    )
    print(f"   LLM: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL} (num_ctx=12288)")
    
    # Alle verfügbaren Metriken
    all_metrics = {
        'faithfulness': faithfulness,
        'context_recall': context_recall,
        'context_precision': context_precision
    }
    
    # Wähle nur die gewünschten Metriken
    if metrics_to_compute:
        metrics = [all_metrics[m] for m in metrics_to_compute if m in all_metrics]
    else:
        metrics = list(all_metrics.values())
    
    print(f"   Metriken: {[m.name for m in metrics]}")
    print(f"\n   ⏳ Evaluiere {len(dataset.samples)} Samples...")
    print(f"   💡 Dies kann mehrere Minuten dauern (ca. 1-2 Min pro Sample)\n")
    
    # RunConfig mit erhöhtem Timeout für Ollama (lokale GPU kann langsam sein)
    run_config = RunConfig(
        max_workers=1,  # Reduziert von 4 auf 2 für weniger GPU-Last
        timeout=300,  # 5 Minuten Timeout pro Request
        max_retries=3,
        max_wait=30  # Max 30 Sekunden warten zwischen Retries
    )
    
    # Evaluation durchführen
    results = evaluate(
        dataset, 
        metrics=metrics, 
        llm=llm,
        run_config=run_config,
        raise_exceptions=False
    )
    
    results_df = results.to_pandas()
    
    print("\n✅ RAGAS-Evaluation abgeschlossen!\n")
    
    return results_df


def merge_results_with_existing(new_results_df: pd.DataFrame, test_df: pd.DataFrame, only_fill_nan: bool = False) -> pd.DataFrame:
    """
    Merged neue Ergebnisse mit bestehenden ragas_results.csv.
    Wenn ragas_results.csv nicht existiert, wird sie neu erstellt.
    
    Args:
        new_results_df: Neue Evaluationsergebnisse
        test_df: Testset DataFrame mit IDs
        only_fill_nan: Wenn True, werden nur NaN-Werte in bestehenden Einträgen überschrieben
    """
    results_path = Path(__file__).parent / "data" / "ragas_results.csv"
    
    # IDs, Kategorien und Schwierigkeiten zu new_results_df hinzufügen
    new_results_df['id'] = test_df['id'].values
    new_results_df['category'] = test_df['category'].values
    new_results_df['difficulty'] = test_df['difficulty'].values
    
    # Context-Count berechnen
    new_results_df['context_count'] = new_results_df['retrieved_contexts'].apply(
        lambda x: len(x) if isinstance(x, list) else 0
    )
    
    metric_cols = ['faithfulness', 'context_recall', 'context_precision']
    
    if results_path.exists():
        print("📂 Lade bestehende Ergebnisse...")
        existing_df = pd.read_csv(results_path, encoding='utf-8')
        
        # Prüfe ob 'id' Spalte existiert
        if 'id' in existing_df.columns:
            # Konvertiere retrieved_contexts zurück zu Liste falls als String gespeichert
            if 'retrieved_contexts' in existing_df.columns:
                existing_df['retrieved_contexts'] = existing_df['retrieved_contexts'].apply(
                    lambda x: eval(x) if isinstance(x, str) and x.startswith('[') else x
                )
            
            updated_ids = new_results_df['id'].tolist()
            
            if only_fill_nan:
                # Nur NaN-Werte überschreiben (Metriken einzeln aktualisieren)
                print(f"   🔧 Aktualisiere nur fehlende Metriken für IDs: {updated_ids}")
                
                for _, new_row in new_results_df.iterrows():
                    row_id = new_row['id']
                    mask = existing_df['id'] == row_id
                    
                    if mask.any():
                        # Für jede Metrik: nur überschreiben wenn alter Wert NaN und neuer Wert nicht NaN
                        for metric in metric_cols:
                            if metric in new_row and not pd.isna(new_row[metric]):
                                old_val = existing_df.loc[mask, metric].values[0]
                                if pd.isna(old_val):
                                    existing_df.loc[mask, metric] = new_row[metric]
                                    print(f"      ID {row_id}: {metric} = {new_row[metric]:.3f} (war NaN)")
                    else:
                        # ID existiert noch nicht - komplett hinzufügen
                        existing_df = pd.concat([existing_df, new_row.to_frame().T], ignore_index=True)
                        print(f"      ID {row_id}: Neu hinzugefügt")
                
                merged_df = existing_df
            else:
                # Alte Einträge komplett ersetzen
                existing_df = existing_df[~existing_df['id'].isin(updated_ids)]
                print(f"   🔄 Ersetze {len(updated_ids)} alte Einträge für IDs: {updated_ids}")
                merged_df = pd.concat([existing_df, new_results_df], ignore_index=True)
            
            # Stelle sicher, dass alle Spalten vorhanden sind
            for col in new_results_df.columns:
                if col not in merged_df.columns:
                    merged_df[col] = None
            
            # Sortiere nach ID und wähle nur die relevanten Spalten
            merged_df = merged_df[['id', 'category', 'difficulty', 'user_input', 'response', 
                                    'reference', 'retrieved_contexts', 'faithfulness', 
                                    'context_recall', 'context_precision', 'context_count']].copy()
            merged_df = merged_df.sort_values('id').reset_index(drop=True)
            
            print(f"   ✅ Gesamt: {len(merged_df)} Einträge in CSV")
        else:
            # Alte CSV ohne ID-Spalte - ersetze komplett
            print("   ⚠️  Bestehende CSV hat keine ID-Spalte - wird ersetzt")
            merged_df = new_results_df
    else:
        print("📂 Erstelle neue Ergebnisdatei...")
        merged_df = new_results_df
    
    return merged_df


def display_results(results_df: pd.DataFrame, test_df: pd.DataFrame):
    """Zeigt Ergebnisse an (nur für die evaluierten Fragen)"""
    print("\n" + "=" * 80)
    print("📊 RAGAS-EVALUATION ERGEBNISSE (Nur evaluierte Fragen)")
    print("=" * 80)
    
    # Ergebnisse mit IDs verknüpfen
    results_with_ids = results_df.copy()
    results_with_ids['id'] = test_df['id'].values
    
    print("\n📋 Ergebnisse nach Fragen-ID:")
    print("-" * 80)
    for _, row in results_with_ids.iterrows():
        q_id = row['id']
        print(f"\n   ID {q_id}:")
        for metric in ['faithfulness', 'context_recall', 'context_precision']:
            if metric in row:
                print(f"      {metric:20s}: {row[metric]:.3f}")
    
    # Durchschnittliche Scores
    print("\n📈 Durchschnittliche Scores (evaluierte Fragen):")
    print("-" * 80)
    for metric in ['faithfulness', 'context_recall', 'context_precision']:
        if metric in results_df.columns:
            avg = results_df[metric].mean()
            print(f"   {metric:20s}: {avg:.3f}")


def main():
    """Hauptfunktion"""
    
    print("\n" + "=" * 80)
    print("🎯 RAGAS-EVALUATION - Spezifische Indizes")
    print("=" * 80 + "\n")
    
    # Auto-Detect fehlgeschlagene und fehlende IDs wenn aktiviert
    indices_to_eval = SPECIFIC_INDICES.copy()
    
    if AUTO_DETECT_FAILED or AUTO_DETECT_MISSING:
        results_path = Path(__file__).parent / "data" / "ragas_results.csv"
        testset_path = Path(__file__).parent / "data" / "Testset.CSV"
        failed_ids, missing_ids = detect_failed_and_missing_indices(results_path, testset_path)
        
        # Kombiniere alle IDs (manuell + fehlgeschlagen + fehlend)
        all_ids = set(indices_to_eval)
        
        if AUTO_DETECT_FAILED:
            all_ids.update(failed_ids)
        
        if AUTO_DETECT_MISSING:
            all_ids.update(missing_ids)
        
        indices_to_eval = sorted(list(all_ids))
        
        if indices_to_eval:
            print(f"📝 Zu evaluierende Indizes: {indices_to_eval}\n")
        else:
            print("✅ Keine IDs zu evaluieren - alle vollständig!\n")
            sys.exit(0)
    else:
        print(f"🔢 Zu evaluierende Indizes: {sorted(indices_to_eval)}\n")
    
    try:
        # 1. LangSmith Client
        print("🔗 Initialisiere LangSmith...")
        langsmith_client = Client(api_key=LANGSMITH_API_KEY)
        print(f"   ✅ Projekt: {LANGSMITH_PROJECT}\n")
        
        # 2. Ermittle fehlende Metriken pro ID
        results_path = Path(__file__).parent / "data" / "ragas_results.csv"
        missing_metrics_per_id = detect_missing_metrics_per_id(results_path)
        
        # Bestimme welche Metriken insgesamt berechnet werden müssen
        all_missing_metrics = set()
        for metrics_list in missing_metrics_per_id.values():
            all_missing_metrics.update(metrics_list)
        
        if all_missing_metrics:
            print(f"📊 Fehlende Metriken pro ID:")
            for id_, metrics in sorted(missing_metrics_per_id.items()):
                if id_ in indices_to_eval:
                    print(f"   ID {id_}: {metrics}")
            print(f"\n   → Zu berechnende Metriken: {sorted(all_missing_metrics)}\n")
        else:
            print("📊 Alle Metriken werden berechnet (Standard)\n")
            all_missing_metrics = None  # None = alle Metriken
        
        # 3. Testset laden (nur spezifische Indizes)
        print("📂 Lade Testset (gefiltert)...")
        test_df = load_testset_filtered(indices=indices_to_eval)
        print()
        
        # 4. Entweder bestehende Responses wiederverwenden oder neu generieren
        if REUSE_EXISTING_RESPONSES:
            print("♻️  REUSE_EXISTING_RESPONSES aktiviert - Lade bestehende Antworten...")
            dataset, loaded_df = load_existing_responses(indices_to_eval)
            
            if dataset is None:
                print("❌ Konnte keine bestehenden Responses laden!")
                print("   Setze REUSE_EXISTING_RESPONSES = False und starte neu.")
                sys.exit(1)
            
            # Verwende loaded_df als test_df für konsistente IDs
            test_df = loaded_df
        else:
            # Chatbot initialisieren
            print("🤖 Initialisiere Chatbot...")
            agent = create_react_agent()
            print()
            
            # Antworten generieren
            dataset = generate_chatbot_responses(test_df, agent, langsmith_client)
        
        # 5. RAGAS-Evaluation (nur fehlende Metriken wenn REUSE aktiv)
        metrics_to_compute = list(all_missing_metrics) if all_missing_metrics else None
        results_df = run_ragas_evaluation(dataset, metrics_to_compute=metrics_to_compute)
        
        # 6. Mit bestehenden Ergebnissen mergen (nur NaN-Werte überschreiben wenn REUSE aktiv)
        only_fill_nan = REUSE_EXISTING_RESPONSES and all_missing_metrics is not None
        merged_df = merge_results_with_existing(results_df, test_df, only_fill_nan=only_fill_nan)
        
        # 7. Ergebnisse anzeigen
        display_results(results_df, test_df)
        
        # 8. Speichern in CSV
        output_path_csv = Path(__file__).parent / "data" / "ragas_results.csv"
        
        # Entferne Zeilenumbrüche aus Textfeldern für saubere CSV
        text_columns = ['user_input', 'response', 'reference']
        for col in text_columns:
            if col in merged_df.columns:
                merged_df[col] = merged_df[col].apply(lambda x: x.replace('\n', ' ').replace('\r', ' ') if isinstance(x, str) else x)
        
        # Konvertiere retrieved_contexts zu String ohne Zeilenumbrüche
        merged_df['retrieved_contexts'] = merged_df['retrieved_contexts'].apply(
            lambda x: str(x).replace('\n', ' ').replace('\r', ' ') if isinstance(x, list) else str(x)
        )
        
        # Speichere mit UTF-8-BOM für korrekte Umlaut-Darstellung
        merged_df.to_csv(output_path_csv, index=False, encoding='utf-8-sig', sep=',', quoting=1)
        
        print("\n" + "=" * 80)
        print(f"💾 Ergebnisse gespeichert:")
        print(f"   CSV: {output_path_csv}")
        print("=" * 80 + "\n")
        
        print("✅ Evaluation erfolgreich abgeschlossen!\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Evaluation abgebrochen!\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fehler: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
