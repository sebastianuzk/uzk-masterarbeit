"""
RAGAS-Evaluation für spezifische Testfragen (gezielt einzelne Indizes)

Evaluiert nur ausgewählte Fragen aus dem Testset und aktualisiert die bestehenden
Ergebnisse in ragas_results.csv (oder erstellt neue, falls nicht vorhanden).
"""

import sys
import os
import random
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List
import time

# Reproduzierbarkeit: Fester Seed für alle Zufallsoperationen
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

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
    LANGSMITH_PROJECT,
    RAGAS_EVAL_MODEL,
    TEMPERATURE,
    CONTEXT_WINDOW,
    RANDOM_SEED
)
from src.agent.react_agent import create_react_agent

# Setze Seeds für Reproduzierbarkeit
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ============================================================================
# KONFIGURATION: Hier die Indizes eintragen (1-basiert wie in CSV)
# ============================================================================
SPECIFIC_INDICES = [116]  # Letzte ID zum Testen
AUTO_DETECT_FAILED = False  # Deaktiviert - wir evaluieren alle
AUTO_DETECT_MISSING = False  # Deaktiviert - wir evaluieren alle
REUSE_EXISTING_RESPONSES = False  # NEUE Antworten generieren
FORCE_RECALC_ALL_METRICS = True  # Alle Metriken neu berechnen


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
    
    # Filtere META/AVG Zeilen aus
    df = df[~df['id'].astype(str).isin(['META', 'AVG'])]
    
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
    
    # Filtere META/AVG Zeilen aus
    df = df[~df['id'].astype(str).isin(['META', 'AVG'])]
    
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
    
    # Filtere META/AVG Zeilen aus
    df = df[~df['id'].astype(str).isin(['META', 'AVG'])]
    
    # Konvertiere ID zu int für korrektes Filtern
    df['id'] = df['id'].astype(int)
    
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


def get_rag_context_from_langsmith(client: Client, trace_id: str) -> tuple:
    """
    Holt RAG-Kontext-Chunks und URLs aus LangSmith.
    
    Returns:
        Tuple (contexts, urls): Listen von RAG-Context-Chunks und zugehörigen URLs
    """
    try:
        child_runs = list(client.list_runs(
            project_name=LANGSMITH_PROJECT,
            trace_id=trace_id,
            is_root=False
        ))
        
        contexts = []
        urls = []
        for child in child_runs:
            if child.run_type == "retriever":
                if child.outputs and isinstance(child.outputs, dict):
                    documents = child.outputs.get('output', [])
                    for doc in documents:
                        if isinstance(doc, dict) and 'page_content' in doc:
                            contexts.append(doc['page_content'])
                            # URL aus metadata.source extrahieren
                            metadata = doc.get('metadata', {})
                            url = metadata.get('source', 'Keine URL')
                            urls.append(url)
        
        if contexts:
            return contexts, urls
        
        return ["Kein RAG-Kontext gefunden"], ["Keine URL"]
    
    except Exception as e:
        print(f"      ⚠️ LangSmith-Fehler: {str(e)[:100]}")
        return ["LangSmith-Fehler"], ["Keine URL"]


def generate_chatbot_responses(df: pd.DataFrame, agent, langsmith_client: Client) -> tuple:
    """
    Generiert Chatbot-Antworten für die gefilterten Fragen.
    
    Returns:
        Tuple (dataset, response_times, urls_list): EvaluationDataset, Liste der Antwortzeiten, Liste der URL-Listen
    """
    print("\n🤖 Generiere Chatbot-Antworten...")
    print("=" * 80)
    
    samples = []
    response_times = []  # Zeit pro Antwort in Sekunden
    urls_list = []  # Liste von URL-Listen pro Frage
    
    for idx, row in df.iterrows():
        question_id = row['id']
        question = row['question']
        expected_answer = row['expected_answer']
        
        print(f"\n[{idx + 1}/{len(df)}] ID={question_id}: {question[:60]}...")
        
        agent.clear_memory()
        
        print(f"   💬 Chatbot fragen...")
        import uuid
        session_id = str(uuid.uuid4())
        
        # Zeit messen für Antwortgenerierung
        response_start = time.time()
        
        answer = agent.chat(question, session_id=session_id)
        
        response_time = time.time() - response_start
        response_times.append(response_time)
        
        print(f"   ✅ Antwort: {answer[:80]}... ({response_time:.2f}s)")
        
        time.sleep(1)  # Reduziert von 3s auf 1s
        
        print(f"   🔍 Hole RAG-Kontext aus LangSmith...")
        
        # Optimiert: Nur den letzten Run holen (statt alle)
        recent_runs = list(langsmith_client.list_runs(
            project_name=LANGSMITH_PROJECT,
            is_root=True,
            limit=1  # Nur den letzten Run
        ))
        
        contexts = ["Kein RAG-Kontext gefunden"]
        urls = ["Keine URL"]
        matching_run = None
        
        # Der letzte Run sollte unser Run sein
        if recent_runs:
            matching_run = recent_runs[0]
        
        if matching_run:
            trace_id = matching_run.trace_id
            contexts, urls = get_rag_context_from_langsmith(langsmith_client, trace_id)
            print(f"   ✅ Run gefunden mit Session-ID: {session_id[:8]}...")
        else:
            print(f"   ⚠️ Kein Run mit Session-ID {session_id[:8]}... gefunden")
        
        urls_list.append(urls)
        
        total_chars = sum(len(c) for c in contexts)
        print(f"   📄 Kontext: {len(contexts)} chunks, {total_chars} Zeichen")
        print(f"   🔗 URLs: {len(urls)} Quellen")
        
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=expected_answer
        )
        samples.append(sample)
    
    print("\n" + "=" * 80)
    print(f"✅ {len(samples)} Antworten generiert\n")
    print(f"   ⏱️ Durchschn. Antwortzeit: {sum(response_times)/len(response_times):.2f}s")
    print(f"   ⏱️ Gesamt Antwortzeit: {sum(response_times):.2f}s\n")
    
    return EvaluationDataset(samples=samples), response_times, urls_list


def run_ragas_evaluation(dataset: EvaluationDataset, metrics_to_compute: List[str] = None) -> tuple:
    """
    Führt RAGAS-Evaluation durch.
    
    Args:
        dataset: Das EvaluationDataset mit den Samples
        metrics_to_compute: Optional - Liste der zu berechnenden Metriken.
                           Falls None, werden alle berechnet.
                           Mögliche Werte: 'faithfulness', 'context_recall', 'context_precision'
    
    Returns:
        Tuple (results_df, evaluation_time): DataFrame mit Ergebnissen und Evaluationszeit in Sekunden
    """
    print("🚀 Starte RAGAS-Evaluation...")
    print("=" * 80)
    
    # Separates LLM für RAGAS-Evaluation (gleiches Setup wie Chatbot, nur anderes Modell)
    llm = ChatOllama(
        model=RAGAS_EVAL_MODEL,  # Separates Modell für Evaluation
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE,  # Gleiche Parameter wie Chatbot
        seed=RANDOM_SEED,
        num_ctx=CONTEXT_WINDOW
    )
    print(f"   RAGAS-LLM: {RAGAS_EVAL_MODEL} @ {OLLAMA_BASE_URL} (ctx={CONTEXT_WINDOW}, temp={TEMPERATURE}, seed={RANDOM_SEED})")
    print(f"   (Chatbot verwendet: {OLLAMA_MODEL})")
    
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
    
    # Zeit messen für Evaluation
    eval_start = time.time()
    
    # Evaluation durchführen
    results = evaluate(
        dataset, 
        metrics=metrics, 
        llm=llm,
        run_config=run_config,
        raise_exceptions=False
    )
    
    evaluation_time = time.time() - eval_start
    
    results_df = results.to_pandas()
    
    print(f"\n✅ RAGAS-Evaluation abgeschlossen in {evaluation_time:.2f}s")
    print(f"   ⏱️ Durchschn. pro Sample: {evaluation_time/len(dataset.samples):.2f}s\n")
    
    return results_df, evaluation_time


def merge_results_with_existing(new_results_df: pd.DataFrame, test_df: pd.DataFrame, 
                                  only_fill_nan: bool = False,
                                  response_times: List[float] = None,
                                  urls_list: List[List[str]] = None) -> pd.DataFrame:
    """
    Merged neue Ergebnisse mit bestehenden ragas_results.csv.
    Wenn ragas_results.csv nicht existiert, wird sie neu erstellt.
    
    Args:
        new_results_df: Neue Evaluationsergebnisse
        test_df: Testset DataFrame mit IDs
        only_fill_nan: Wenn True, werden nur NaN-Werte in bestehenden Einträgen überschrieben
        response_times: Liste der Antwortzeiten pro Frage (optional)
        urls_list: Liste von URL-Listen pro Frage (optional)
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
    
    # Response-Zeiten hinzufügen (falls vorhanden)
    if response_times:
        new_results_df['response_time_seconds'] = response_times[:len(new_results_df)]
    
    # URLs hinzufügen (falls vorhanden)
    if urls_list:
        new_results_df['retrieved_urls'] = [str(urls) for urls in urls_list[:len(new_results_df)]]
    
    metric_cols = ['faithfulness', 'context_recall', 'context_precision']
    
    if results_path.exists():
        print("📂 Lade bestehende Ergebnisse...")
        existing_df = pd.read_csv(results_path, encoding='utf-8')
        
        # Prüfe ob 'id' Spalte existiert
        if 'id' in existing_df.columns:
            # Filtere META/AVG Zeilen aus (werden später neu generiert)
            existing_df = existing_df[~existing_df['id'].astype(str).isin(['META', 'AVG'])].copy()
            
            # Konvertiere id zu int für konsistentes Matching
            existing_df['id'] = existing_df['id'].astype(int)
            
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
                # Metriken ersetzen, aber response_time und urls aus bestehenden Daten beibehalten
                print(f"   🔄 Ersetze Metriken für {len(updated_ids)} IDs: {updated_ids}")
                
                # Speichere bestehende Zeiten/URLs bevor wir ersetzen
                preserve_cols = ['response_time_seconds', 'retrieved_urls']
                preserved_data = {}
                for col in preserve_cols:
                    if col in existing_df.columns:
                        for row_id in updated_ids:
                            mask = existing_df['id'] == row_id
                            if mask.any():
                                val = existing_df.loc[mask, col].values[0]
                                if pd.notna(val) and val != '':
                                    if row_id not in preserved_data:
                                        preserved_data[row_id] = {}
                                    preserved_data[row_id][col] = val
                
                # Entferne alte Einträge
                existing_df = existing_df[~existing_df['id'].isin(updated_ids)]
                merged_df = pd.concat([existing_df, new_results_df], ignore_index=True)
                
                # Stelle die bewahrten Werte wieder her
                for row_id, cols in preserved_data.items():
                    mask = merged_df['id'] == row_id
                    for col, val in cols.items():
                        if col in merged_df.columns:
                            # Nur wiederherstellen wenn neuer Wert leer/NaN ist
                            current_val = merged_df.loc[mask, col].values[0] if mask.any() else None
                            if pd.isna(current_val) or current_val == '' or current_val is None:
                                merged_df.loc[mask, col] = val
                                print(f"      ID {row_id}: {col} beibehalten")
            
            # Stelle sicher, dass alle Spalten vorhanden sind
            for col in new_results_df.columns:
                if col not in merged_df.columns:
                    merged_df[col] = None
            
            # Filtere META/AVG Zeilen aus (werden später neu generiert)
            merged_df = merged_df[~merged_df['id'].astype(str).isin(['META', 'AVG'])].copy()
            
            # Sortiere nach ID und wähle nur die relevanten Spalten (erweitert um neue Spalten)
            available_cols = ['id', 'category', 'difficulty', 'user_input', 'response', 
                              'reference', 'retrieved_contexts', 'retrieved_urls',
                              'faithfulness', 'context_recall', 'context_precision', 
                              'context_count', 'response_time_seconds']
            # Nur vorhandene Spalten verwenden
            cols_to_use = [col for col in available_cols if col in merged_df.columns]
            merged_df = merged_df[cols_to_use].copy()
            # Konvertiere id zu int für korrektes Sortieren
            merged_df['id'] = merged_df['id'].astype(int)
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
        
        # Falls FORCE_RECALC_ALL_METRICS aktiv, alle Metriken neu berechnen
        if FORCE_RECALC_ALL_METRICS:
            print("🔄 FORCE_RECALC_ALL_METRICS aktiviert - Alle Metriken werden neu berechnet")
            all_missing_metrics = None  # None = alle Metriken
        elif all_missing_metrics:
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
        response_times = None
        urls_list = None
        
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
            
            # Antworten generieren (jetzt mit Timing und URLs)
            dataset, response_times, urls_list = generate_chatbot_responses(test_df, agent, langsmith_client)
        
        # 5. RAGAS-Evaluation (nur fehlende Metriken wenn REUSE aktiv, außer FORCE_RECALC)
        metrics_to_compute = list(all_missing_metrics) if all_missing_metrics else None
        results_df, evaluation_time = run_ragas_evaluation(dataset, metrics_to_compute=metrics_to_compute)
        
        # 6. Mit bestehenden Ergebnissen mergen 
        # Bei FORCE_RECALC_ALL_METRICS: Komplette Zeilen ersetzen (nicht nur NaN)
        only_fill_nan = REUSE_EXISTING_RESPONSES and all_missing_metrics is not None and not FORCE_RECALC_ALL_METRICS
        merged_df = merge_results_with_existing(results_df, test_df, only_fill_nan=only_fill_nan,
                                                 response_times=response_times, urls_list=urls_list)
        
        # 7. Ergebnisse anzeigen
        display_results(results_df, test_df)
        
        # 8. Speichern in CSV
        from datetime import datetime
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
        
        # Konvertiere retrieved_urls zu String ohne Zeilenumbrüche (falls vorhanden)
        if 'retrieved_urls' in merged_df.columns:
            merged_df['retrieved_urls'] = merged_df['retrieved_urls'].apply(
                lambda x: str(x).replace('\n', ' ').replace('\r', ' ') if x else ''
            )
        
        # ============================================================================
        # METADATEN-ZEILEN: Modelle, Zeitstempel, Dauern (nur für Daten-Zeilen, nicht META/AVG)
        # ============================================================================
        # Filtere nur echte Daten-Zeilen (keine META/AVG Zeilen)
        data_df = merged_df[~merged_df['id'].astype(str).isin(['META', 'AVG'])].copy()
        
        csv_columns = list(merged_df.columns)
        metadata_rows = []
        
        # Berechne akkumulierte Zeiten aus ALLEN Daten-Zeilen
        total_response_time = 0.0
        if 'response_time_seconds' in data_df.columns:
            valid_times = data_df['response_time_seconds'].dropna()
            if len(valid_times) > 0:
                total_response_time = valid_times.sum()
        
        # Lade bestehende Eval-Zeit aus alter META-Zeile und addiere neue
        existing_eval_time = 0.0
        if output_path_csv.exists():
            try:
                old_df = pd.read_csv(output_path_csv, encoding='utf-8')
                meta_rows = old_df[old_df['id'].astype(str) == 'META']
                if len(meta_rows) > 0:
                    eval_str = str(meta_rows.iloc[0].get('retrieved_contexts', ''))
                    if 'Eval-Zeit gesamt:' in eval_str:
                        # Extrahiere Zahl aus "Eval-Zeit gesamt: 123.45s"
                        import re
                        match = re.search(r'Eval-Zeit gesamt:\s*([\d.]+)s', eval_str)
                        if match:
                            existing_eval_time = float(match.group(1))
                            print(f"📊 Bestehende Eval-Zeit aus CSV: {existing_eval_time:.2f}s")
            except Exception as e:
                print(f"⚠️  Warnung: Konnte bestehende Eval-Zeit nicht laden: {e}")
                pass
        
        # Addiere aktuelle Eval-Zeit zur bestehenden
        total_eval_time = existing_eval_time + (evaluation_time if evaluation_time else 0.0)
        
        # Metadaten-Zeile 1: Allgemeine Infos (mit akkumulierten Werten)
        meta1 = {col: '' for col in csv_columns}
        meta1['id'] = 'META'
        meta1['category'] = 'Evaluation Metadaten'
        meta1['difficulty'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        meta1['user_input'] = f'Chatbot: {OLLAMA_MODEL} (ctx=dynamisch, temp={TEMPERATURE}, seed={RANDOM_SEED})'
        meta1['response'] = f'RAGAS-LLM: {RAGAS_EVAL_MODEL} (ctx={CONTEXT_WINDOW}, temp={TEMPERATURE}, seed={RANDOM_SEED})'
        meta1['reference'] = f'Testset: {len(data_df)} Fragen'
        meta1['retrieved_contexts'] = f'Eval-Zeit gesamt: {total_eval_time:.2f}s'
        if 'retrieved_urls' in csv_columns:
            meta1['retrieved_urls'] = f'Antwort-Zeit gesamt: {total_response_time:.2f}s'
        metadata_rows.append(meta1)
        
        # ============================================================================
        # DURCHSCHNITTE: Gesamt, pro Kategorie, pro Schwierigkeit, kombiniert
        # ============================================================================
        metric_cols = ['faithfulness', 'context_recall', 'context_precision']
        
        # Gesamtdurchschnitt
        avg_row = {col: '' for col in csv_columns}
        avg_row['id'] = 'AVG'
        avg_row['category'] = 'GESAMT'
        avg_row['difficulty'] = f'n={len(data_df)}'
        for metric in metric_cols:
            if metric in data_df.columns:
                avg_row[metric] = data_df[metric].mean()
        if 'response_time_seconds' in data_df.columns and data_df['response_time_seconds'].notna().any():
            avg_row['response_time_seconds'] = data_df['response_time_seconds'].mean()
        metadata_rows.append(avg_row)
        
        # Durchschnitte pro Kategorie
        for category in sorted(data_df['category'].unique()):
            cat_df = data_df[data_df['category'] == category]
            cat_row = {col: '' for col in csv_columns}
            cat_row['id'] = 'AVG'
            cat_row['category'] = category
            cat_row['difficulty'] = f'n={len(cat_df)}'
            for metric in metric_cols:
                if metric in cat_df.columns:
                    cat_row[metric] = cat_df[metric].mean()
            if 'response_time_seconds' in cat_df.columns and cat_df['response_time_seconds'].notna().any():
                cat_row['response_time_seconds'] = cat_df['response_time_seconds'].mean()
            metadata_rows.append(cat_row)
        
        # Durchschnitte pro Schwierigkeit
        for difficulty in ['easy', 'medium', 'hard']:
            diff_df = data_df[data_df['difficulty'] == difficulty]
            if len(diff_df) > 0:
                diff_row = {col: '' for col in csv_columns}
                diff_row['id'] = 'AVG'
                diff_row['category'] = f'Schwierigkeit: {difficulty.upper()}'
                diff_row['difficulty'] = f'n={len(diff_df)}'
                for metric in metric_cols:
                    if metric in diff_df.columns:
                        diff_row[metric] = diff_df[metric].mean()
                if 'response_time_seconds' in diff_df.columns and diff_df['response_time_seconds'].notna().any():
                    diff_row['response_time_seconds'] = diff_df['response_time_seconds'].mean()
                metadata_rows.append(diff_row)
        
        # Durchschnitte pro Kategorie + Schwierigkeit (kombiniert)
        for category in sorted(data_df['category'].unique()):
            for difficulty in ['easy', 'medium', 'hard']:
                combo_df = data_df[(data_df['category'] == category) & (data_df['difficulty'] == difficulty)]
                if len(combo_df) > 0:
                    combo_row = {col: '' for col in csv_columns}
                    combo_row['id'] = 'AVG'
                    combo_row['category'] = f'{category} / {difficulty.upper()}'
                    combo_row['difficulty'] = f'n={len(combo_df)}'
                    for metric in metric_cols:
                        if metric in combo_df.columns:
                            combo_row[metric] = combo_df[metric].mean()
                    if 'response_time_seconds' in combo_df.columns and combo_df['response_time_seconds'].notna().any():
                        combo_row['response_time_seconds'] = combo_df['response_time_seconds'].mean()
                    metadata_rows.append(combo_row)
        
        # Metadaten-DataFrame erstellen und anhängen
        meta_df = pd.DataFrame(metadata_rows)
        final_df = pd.concat([data_df, meta_df], ignore_index=True)
        
        # Speichere mit UTF-8-BOM für korrekte Umlaut-Darstellung
        final_df.to_csv(output_path_csv, index=False, encoding='utf-8-sig', sep=',', quoting=1)
        
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
