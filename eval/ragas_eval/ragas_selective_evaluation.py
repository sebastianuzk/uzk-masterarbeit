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

# Import RAGAS library FIRST (before adding project_root to avoid shadowing)
from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, context_precision
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.run_config import RunConfig

# Projekt-Root (add AFTER RAGAS imports)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
from langchain_ollama import ChatOllama
from langsmith import Client
from config.settings import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT,
    RAGAS_JUDGE_MODEL,
    TEMPERATURE,
)
from src.agent.react_agent import create_react_agent

# ============================================================================
# KONFIGURATION: Hier die Indizes eintragen (1-basiert wie in CSV)
# ============================================================================
SPECIFIC_INDICES = []  # Leer lassen für Auto-Detect (fehlgeschlagen + fehlend)
AUTO_DETECT_FAILED = True  # Automatisch fehlgeschlagene IDs aus ragas_results.csv erkennen
AUTO_DETECT_MISSING = True  # Automatisch noch nicht evaluierte IDs erkennen


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


def run_ragas_evaluation(dataset: EvaluationDataset, model: str = None) -> pd.DataFrame:
    """Führt RAGAS-Evaluation durch
    
    Args:
        dataset: RAGAS EvaluationDataset mit Samples
        model: Agent-Modell (nur für Dokumentation, Judge ist immer RAGAS_JUDGE_MODEL)
    """
    print("🚀 Starte RAGAS-Evaluation...")
    print("=" * 80)
    
    # Verwende immer den festen RAGAS Judge für faire Vergleiche
    print(f"   Agent-Modell:  {model if model else 'N/A'}")
    print(f"   RAGAS-Judge:   {RAGAS_JUDGE_MODEL}")
    
    llm = ChatOllama(
        model=RAGAS_JUDGE_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=TEMPERATURE
    )
    
    metrics = [
        faithfulness,
        context_recall,
        context_precision
    ]
    print(f"   Metriken: {[m.name for m in metrics]}")
    print(f"\n   ⏳ Evaluiere {len(dataset.samples)} Samples...")
    print(f"   💡 Dies kann mehrere Minuten dauern (ca. 1-2 Min pro Sample)\n")
    
    # RunConfig für parallele Requests an Ollama
    run_config = RunConfig(max_workers=4)
    
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


def merge_results_with_existing(new_results_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merged neue Ergebnisse mit bestehenden ragas_results.csv.
    Wenn ragas_results.csv nicht existiert, wird sie neu erstellt.
    Die neuen Ergebnisse überschreiben bestehende Einträge mit gleicher ID.
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
            
            # Entferne alte Einträge für diese IDs (sie werden überschrieben)
            updated_ids = new_results_df['id'].tolist()
            existing_df = existing_df[~existing_df['id'].isin(updated_ids)]
            
            print(f"   🔄 Ersetze {len(updated_ids)} alte Einträge für IDs: {updated_ids}")
            
            # Stelle sicher, dass beide DataFrames die gleichen Spalten haben
            for col in new_results_df.columns:
                if col not in existing_df.columns:
                    existing_df[col] = None
            
            # Füge neue Ergebnisse hinzu
            merged_df = pd.concat([existing_df, new_results_df], ignore_index=True)
            
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
        
        # 2. Testset laden (nur spezifische Indizes)
        print("📂 Lade Testset (gefiltert)...")
        test_df = load_testset_filtered(indices=indices_to_eval)
        print()
        
        # 3. Chatbot initialisieren
        print("🤖 Initialisiere Chatbot...")
        agent = create_react_agent()
        print()
        
        # 4. Antworten generieren
        dataset = generate_chatbot_responses(test_df, agent, langsmith_client)
        
        # 5. RAGAS-Evaluation
        results_df = run_ragas_evaluation(dataset, model=OLLAMA_MODEL)
        
        # 6. Mit bestehenden Ergebnissen mergen
        merged_df = merge_results_with_existing(results_df, test_df)
        
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
