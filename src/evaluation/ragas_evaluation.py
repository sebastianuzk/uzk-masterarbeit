"""
RAGAS-Evaluation für WiSo-Chatbot

Evaluiert den Chatbot mit RAGAS-Framework:
- Verwendet Ollama (qwen3:8b) als LLM-Judge
- Lädt Testfragen aus Testset.CSV
- Generiert Antworten mit dem Chatbot
- Extrahiert RAG-Kontexte aus LangSmith
- Berechnet RAGAS-Metriken (Faithfulness, Context Recall)
"""

import sys
import random
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List
import time

# Reproduzierbarkeit: Seeds werden aus config.settings geladen
import random
import numpy as np

# Projekt-Root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, context_precision  # answer_relevancy benötigt Embeddings
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas.run_config import RunConfig
from langchain_ollama import ChatOllama, OllamaEmbeddings
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


def load_testset(csv_path: str = "data/Testset.CSV", limit: int = None) -> pd.DataFrame:
    """Lädt Testset.CSV"""
    full_path = Path(__file__).parent / csv_path
    df = pd.read_csv(full_path, sep=';', encoding='utf-8')
    
    if limit:
        df = df.head(limit)
    
    print(f"✅ {len(df)} Testfragen geladen")
    
    return df


def get_rag_context_from_langsmith(client: Client, trace_id: str) -> tuple:
    """
    Holt RAG-Kontext und URLs aus LangSmith für eine spezifische Trace-ID.
    
    Die Documents befinden sich im Retriever-Output unter dem Key 'output' (nicht 'documents'!).
    Jedes Document hat 'page_content' und 'metadata' (mit 'source' URL).
    
    Args:
        client: LangSmith Client
        trace_id: Die Trace-ID der Session
        
    Returns:
        Tuple (contexts, urls): Listen von RAG-Context-Chunks und zugehörigen URLs
    """
    try:
        # Hole alle Child-Runs für diese Trace
        child_runs = list(client.list_runs(
            project_name=LANGSMITH_PROJECT,
            trace_id=trace_id,
            is_root=False
        ))
        
        # Suche nach Retriever-Run
        contexts = []
        urls = []
        for child in child_runs:
            if child.run_type == "retriever":
                if child.outputs and isinstance(child.outputs, dict):
                    # Documents sind unter 'output' Key (nicht 'documents')!
                    documents = child.outputs.get('output', [])
                    for doc in documents:
                        if isinstance(doc, dict) and 'page_content' in doc:
                            contexts.append(doc['page_content'])
                            # URL aus metadata.source extrahieren
                            metadata = doc.get('metadata', {})
                            url = metadata.get('source', 'Keine URL')
                            urls.append(url)
        
        if contexts:
            return contexts, urls  # Tuple von Listen zurückgeben
        
        return ["Kein RAG-Kontext gefunden"], ["Keine URL"]  # Als Listen
    
    except Exception as e:
        print(f"      ⚠️ LangSmith-Fehler: {str(e)[:100]}")
        return ["LangSmith-Fehler"], ["Keine URL"]  # Als Listen


def generate_chatbot_responses(df: pd.DataFrame, agent, langsmith_client: Client) -> tuple:
    """
    Generiert Chatbot-Antworten für alle Fragen und sammelt RAG-Kontexte.
    
    Returns:
        Tuple (dataset, response_times, urls_list): EvaluationDataset, Liste der Antwortzeiten, Liste der URL-Listen
    """
    print("\n🤖 Generiere Chatbot-Antworten...")
    print("=" * 80)
    
    samples = []
    response_times = []  # Zeit pro Antwort in Sekunden
    urls_list = []  # Liste von URL-Listen pro Frage
    
    for idx, row in df.iterrows():
        question = row['question']
        expected_answer = row['expected_answer']
        
        print(f"\n[{idx + 1}/{len(df)}] {question[:70]}...")
        
        # Memory löschen für isolierte Evaluation
        agent.clear_memory()
        
        # Chatbot fragen - mit Session-ID für LangSmith-Tracking
        print(f"   💬 Chatbot fragen...")
        import uuid
        session_id = str(uuid.uuid4())
        
        # Zeit messen für Antwortgenerierung
        response_start = time.time()
        
        # Agent.chat() mit session_id aufrufen
        answer = agent.chat(question, session_id=session_id)
        
        response_time = time.time() - response_start
        response_times.append(response_time)
        
        print(f"   ✅ Antwort: {answer[:80]}... ({response_time:.2f}s)")
        
        # Warten damit LangSmith Trace vollständig ist
        time.sleep(1)  # Reduziert von 3s auf 1s
        
        # RAG-Kontext aus LangSmith holen - nur den letzten Run abrufen
        print(f"   🔍 Hole RAG-Kontext aus LangSmith...")
        
        # Optimiert: Nur den letzten Run holen (statt alle)
        recent_runs = list(langsmith_client.list_runs(
            project_name=LANGSMITH_PROJECT,
            is_root=True,
            limit=1  # Nur den letzten Run
        ))
        
        contexts = ["Kein RAG-Kontext gefunden"]  # Default als Liste
        urls = ["Keine URL"]  # Default als Liste
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
        
        # RAGAS-Sample erstellen
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,  # Jetzt bereits eine Liste von Chunks
            reference=expected_answer
        )
        samples.append(sample)
    
    print("\n" + "=" * 80)
    print(f"✅ {len(samples)} Antworten generiert\n")
    print(f"   ⏱️ Durchschn. Antwortzeit: {sum(response_times)/len(response_times):.2f}s")
    print(f"   ⏱️ Gesamt Antwortzeit: {sum(response_times):.2f}s\n")
    
    # Zwischenspeicherung der Antworten und Kontexte
    dataset = EvaluationDataset(samples=samples)
    checkpoint_path = Path(__file__).parent / "data" / "responses_checkpoint.pkl"
    checkpoint_path.parent.mkdir(exist_ok=True)
    
    import pickle
    checkpoint_data = {
        'dataset': dataset,
        'test_df': df,
        'response_times': response_times,
        'urls_list': urls_list
    }
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(checkpoint_data, f)
    print(f"💾 Checkpoint gespeichert: {checkpoint_path}")
    print(f"   (Antworten + Kontexte + Zeiten + URLs für alle {len(samples)} Fragen)\n")
    
    return dataset, response_times, urls_list


# ============================================================================
# KONFIGURATION
# ============================================================================
# Limit für Testfragen (None = alle, z.B. 3 für Test)
TEST_LIMIT = 3  # Für Test mit 3 Fragen (auf None setzen für vollständige Evaluation)


def run_ragas_evaluation(dataset: EvaluationDataset) -> tuple:
    """
    Führt RAGAS-Evaluation durch.
    Verwendet 3 Standard-RAGAS-Metriken: faithfulness, context_recall, context_precision.
    (answer_relevancy auskommentiert - benötigt qwen3-embedding:8b)
    
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
    
    # Ollama Embeddings für answer_relevancy (später aktivieren)
    # embeddings = OllamaEmbeddings(
    #     model=OLLAMA_EMBEDDING_MODEL,
    #     base_url=OLLAMA_BASE_URL
    # )
    # print(f"   Embeddings: {OLLAMA_EMBEDDING_MODEL} @ {OLLAMA_BASE_URL}")
    
    # Standard RAGAS-Metriken
    metrics = [
        faithfulness,       # Ist Antwort treu zum Kontext?
        context_recall,     # Wurden alle relevanten Infos abgerufen?
        context_precision   # Sind relevante Chunks höher gerankt?
        # answer_relevancy  # Ist Antwort relevant zur Frage? (benötigt Embeddings)
    ]
    print(f"   Metriken: {[m.name for m in metrics]}")
    print(f"\n   ⏳ Evaluiere {len(dataset.samples)} Samples...")
    print(f"   💡 Dies kann mehrere Minuten dauern (ca. 1-2 Min pro Sample)\n")
    
    # RunConfig für parallele Requests an Ollama
    run_config = RunConfig(max_workers=4)
    
    # Zeit messen für Evaluation
    eval_start = time.time()
    
    # Evaluation durchführen
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        run_config=run_config,
        raise_exceptions=False  # Weiter bei Fehlern
    )
    
    evaluation_time = time.time() - eval_start
    
    print(f"\n   ✅ Evaluation abgeschlossen in {evaluation_time:.2f}s")
    print(f"   ⏱️ Durchschn. pro Sample: {evaluation_time/len(dataset.samples):.2f}s\n")
    
    return results.to_pandas(), evaluation_time


def display_and_save_results(results_df: pd.DataFrame, test_df: pd.DataFrame, 
                              response_times: List[float] = None, urls_list: List[List[str]] = None,
                              evaluation_time: float = None):
    """
    Zeigt Ergebnisse an und speichert sie.
    
    Args:
        results_df: DataFrame mit RAGAS-Ergebnissen
        test_df: DataFrame mit Testdaten
        response_times: Liste der Antwortzeiten pro Frage (optional)
        urls_list: Liste von URL-Listen pro Frage (optional)
        evaluation_time: Gesamtzeit für RAGAS-Evaluation in Sekunden (optional)
    """
    from datetime import datetime
    
    # IDs, Kategorien und Schwierigkeiten hinzufügen
    results_df['id'] = test_df['id'].values[:len(results_df)]
    results_df['category'] = test_df['category'].values[:len(results_df)]
    results_df['difficulty'] = test_df['difficulty'].values[:len(results_df)]
    
    # Antwortzeiten hinzufügen (falls vorhanden)
    if response_times:
        results_df['response_time_seconds'] = response_times[:len(results_df)]
    else:
        results_df['response_time_seconds'] = None
    
    # URLs hinzufügen (falls vorhanden)
    if urls_list:
        results_df['retrieved_urls'] = [str(urls) for urls in urls_list[:len(results_df)]]
    else:
        results_df['retrieved_urls'] = None
    
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
    
    # Speichern in CSV (alle Spalten)
    output_path_csv = Path(__file__).parent / "data" / "ragas_results.csv"
    
    # Berechne Anzahl der Context-Chunks
    results_df['context_count'] = results_df['retrieved_contexts'].apply(lambda x: len(x) if isinstance(x, list) else 0)
    
    # Entferne Zeilenumbrüche aus Textfeldern für saubere CSV
    text_columns = ['user_input', 'response', 'reference']
    for col in text_columns:
        if col in results_df.columns:
            results_df[col] = results_df[col].apply(lambda x: x.replace('\n', ' ').replace('\r', ' ') if isinstance(x, str) else x)
    
    # Konvertiere retrieved_contexts zu String ohne Zeilenumbrüche
    results_df['retrieved_contexts'] = results_df['retrieved_contexts'].apply(
        lambda x: str(x).replace('\n', ' ').replace('\r', ' ') if isinstance(x, list) else str(x)
    )
    
    # Konvertiere retrieved_urls zu String ohne Zeilenumbrüche (falls vorhanden)
    if 'retrieved_urls' in results_df.columns:
        results_df['retrieved_urls'] = results_df['retrieved_urls'].apply(
            lambda x: str(x).replace('\n', ' ').replace('\r', ' ') if x else ''
        )
    
    # CSV mit allen wichtigen Spalten (erweitert um response_time und urls)
    csv_columns = ['id', 'category', 'difficulty', 'user_input', 'response', 
                   'reference', 'retrieved_contexts', 'retrieved_urls',
                   'faithfulness', 'context_recall', 'context_precision', 
                   'context_count', 'response_time_seconds']
    
    # Nur vorhandene Spalten verwenden
    csv_columns = [col for col in csv_columns if col in results_df.columns]
    csv_df = results_df[csv_columns].copy()
    
    # ============================================================================
    # METADATEN-ZEILEN: Modelle, Zeitstempel, Dauern
    # ============================================================================
    metadata_rows = []
    
    # Metadaten-Zeile 1: Allgemeine Infos
    meta1 = {col: '' for col in csv_columns}
    meta1['id'] = 'META'
    meta1['category'] = 'Evaluation Metadaten'
    meta1['difficulty'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    meta1['user_input'] = f'Chatbot: {OLLAMA_MODEL} (ctx=dynamisch, temp={TEMPERATURE}, seed={RANDOM_SEED})'
    meta1['response'] = f'RAGAS-LLM: {RAGAS_EVAL_MODEL} (ctx={CONTEXT_WINDOW}, temp={TEMPERATURE}, seed={RANDOM_SEED})'
    meta1['reference'] = f'Testset: {len(results_df)} Fragen'
    if evaluation_time:
        meta1['retrieved_contexts'] = f'Eval-Zeit: {evaluation_time:.2f}s'
    if response_times:
        meta1['retrieved_urls'] = f'Antwort-Zeit gesamt: {sum(response_times):.2f}s'
    metadata_rows.append(meta1)
    
    # ============================================================================
    # DURCHSCHNITTE: Gesamt, pro Kategorie, pro Schwierigkeit, kombiniert
    # ============================================================================
    metric_cols = ['faithfulness', 'context_recall', 'context_precision']
    
    # Gesamtdurchschnitt
    avg_row = {col: '' for col in csv_columns}
    avg_row['id'] = 'AVG'
    avg_row['category'] = 'GESAMT'
    avg_row['difficulty'] = f'n={len(results_df)}'
    for metric in metric_cols:
        if metric in results_df.columns:
            avg_row[metric] = results_df[metric].mean()
    if 'response_time_seconds' in results_df.columns and results_df['response_time_seconds'].notna().any():
        avg_row['response_time_seconds'] = results_df['response_time_seconds'].mean()
    metadata_rows.append(avg_row)
    
    # Durchschnitte pro Kategorie
    for category in sorted(results_df['category'].unique()):
        cat_df = results_df[results_df['category'] == category]
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
        diff_df = results_df[results_df['difficulty'] == difficulty]
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
    for category in sorted(results_df['category'].unique()):
        for difficulty in ['easy', 'medium', 'hard']:
            combo_df = results_df[(results_df['category'] == category) & (results_df['difficulty'] == difficulty)]
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
    csv_df = pd.concat([csv_df, meta_df], ignore_index=True)
    
    # Speichere mit UTF-8-BOM für korrekte Umlaut-Darstellung
    csv_df.to_csv(output_path_csv, index=False, encoding='utf-8-sig', sep=',', quoting=1)
    
    # Excel mit Formatierung erstellen
    output_path_excel = Path(__file__).parent / "data" / "ragas_results.xlsx"
    
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.utils.dataframe import dataframe_to_rows
        
        wb = Workbook()
        
        # Sheet 1: Detaillierte Ergebnisse
        ws_details = wb.active
        ws_details.title = "Detaillierte Ergebnisse"
        
        # Header-Style
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF", size=11)
        
        # Daten schreiben
        for r_idx, row in enumerate(dataframe_to_rows(csv_df, index=False, header=True), 1):
            for c_idx, value in enumerate(row, 1):
                cell = ws_details.cell(row=r_idx, column=c_idx, value=value)
                
                # Header formatieren
                if r_idx == 1:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                else:
                    # Metriken-Spalten (faithfulness, context_recall, context_precision) farbig
                    if c_idx in [8, 9, 10]:  # Metrik-Spalten
                        if isinstance(value, (int, float)):
                            if value >= 0.8:
                                cell.fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                            elif value >= 0.6:
                                cell.fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                            else:
                                cell.fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                            cell.number_format = '0.000'
                    
                    # Text-Wrap für lange Texte
                    if c_idx in [4, 5, 6, 7]:  # user_input, response, reference, contexts
                        cell.alignment = Alignment(wrap_text=True, vertical='top')
        
        # Spaltenbreiten anpassen
        ws_details.column_dimensions['A'].width = 8   # id
        ws_details.column_dimensions['B'].width = 20  # category
        ws_details.column_dimensions['C'].width = 12  # difficulty
        ws_details.column_dimensions['D'].width = 50  # user_input
        ws_details.column_dimensions['E'].width = 60  # response
        ws_details.column_dimensions['F'].width = 50  # reference
        ws_details.column_dimensions['G'].width = 40  # contexts
        ws_details.column_dimensions['H'].width = 15  # faithfulness
        ws_details.column_dimensions['I'].width = 15  # context_recall
        ws_details.column_dimensions['J'].width = 17  # context_precision
        ws_details.column_dimensions['K'].width = 15  # context_count
        
        # Sheet 2: Zusammenfassung
        ws_summary = wb.create_sheet("Zusammenfassung")
        
        # Titel
        ws_summary['A1'] = "📊 RAGAS-Evaluation Zusammenfassung"
        ws_summary['A1'].font = Font(bold=True, size=14)
        ws_summary.merge_cells('A1:D1')
        
        # Durchschnittliche Scores
        row = 3
        ws_summary[f'A{row}'] = "Durchschnittliche Scores"
        ws_summary[f'A{row}'].font = Font(bold=True, size=12)
        row += 1
        
        for metric in ['faithfulness', 'context_recall', 'context_precision']:
            if metric in results_df.columns:
                avg = results_df[metric].mean()
                ws_summary[f'A{row}'] = metric
                ws_summary[f'B{row}'] = avg
                ws_summary[f'B{row}'].number_format = '0.000'
                
                # Farbe basierend auf Score
                if avg >= 0.8:
                    ws_summary[f'B{row}'].fill = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")
                elif avg >= 0.6:
                    ws_summary[f'B{row}'].fill = PatternFill(start_color="FFEB9C", end_color="FFEB9C", fill_type="solid")
                else:
                    ws_summary[f'B{row}'].fill = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")
                
                row += 1
        
        # Nach Kategorie
        row += 2
        ws_summary[f'A{row}'] = "Scores nach Kategorie"
        ws_summary[f'A{row}'].font = Font(bold=True, size=12)
        row += 1
        
        # Header für Kategorie-Tabelle
        ws_summary[f'A{row}'] = "Kategorie"
        ws_summary[f'B{row}'] = "Faithfulness"
        ws_summary[f'C{row}'] = "Context Recall"
        ws_summary[f'D{row}'] = "Context Precision"
        for col in ['A', 'B', 'C', 'D']:
            ws_summary[f'{col}{row}'].font = Font(bold=True)
            ws_summary[f'{col}{row}'].fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
        row += 1
        
        for category in sorted(results_df['category'].unique()):
            cat_df = results_df[results_df['category'] == category]
            ws_summary[f'A{row}'] = category
            
            for idx, metric in enumerate(['faithfulness', 'context_recall', 'context_precision'], 2):
                if metric in cat_df.columns:
                    avg = cat_df[metric].mean()
                    col_letter = chr(65 + idx)  # B, C, D
                    ws_summary[f'{col_letter}{row}'] = avg
                    ws_summary[f'{col_letter}{row}'].number_format = '0.000'
            
            row += 1
        
        # Nach Schwierigkeit
        row += 2
        ws_summary[f'A{row}'] = "Scores nach Schwierigkeit"
        ws_summary[f'A{row}'].font = Font(bold=True, size=12)
        row += 1
        
        # Header
        ws_summary[f'A{row}'] = "Schwierigkeit"
        ws_summary[f'B{row}'] = "Faithfulness"
        ws_summary[f'C{row}'] = "Context Recall"
        ws_summary[f'D{row}'] = "Context Precision"
        for col in ['A', 'B', 'C', 'D']:
            ws_summary[f'{col}{row}'].font = Font(bold=True)
            ws_summary[f'{col}{row}'].fill = PatternFill(start_color="D9D9D9", end_color="D9D9D9", fill_type="solid")
        row += 1
        
        for difficulty in ['easy', 'medium', 'hard']:
            diff_df = results_df[results_df['difficulty'] == difficulty]
            if len(diff_df) > 0:
                ws_summary[f'A{row}'] = difficulty.upper()
                
                for idx, metric in enumerate(['faithfulness', 'context_recall', 'context_precision'], 2):
                    if metric in diff_df.columns:
                        avg = diff_df[metric].mean()
                        col_letter = chr(65 + idx)
                        ws_summary[f'{col_letter}{row}'] = avg
                        ws_summary[f'{col_letter}{row}'].number_format = '0.000'
                
                row += 1
        
        # Spaltenbreiten für Zusammenfassung
        ws_summary.column_dimensions['A'].width = 30
        ws_summary.column_dimensions['B'].width = 15
        ws_summary.column_dimensions['C'].width = 18
        ws_summary.column_dimensions['D'].width = 18
        
        # Speichern
        wb.save(output_path_excel)
        
        print("\n" + "=" * 80)
        print(f"💾 Ergebnisse gespeichert:")
        print(f"   CSV:   {output_path_csv}")
        print(f"   Excel: {output_path_excel}")
        print("=" * 80 + "\n")
        
    except ImportError:
        print("\n" + "=" * 80)
        print(f"💾 Ergebnisse gespeichert:")
        print(f"   CSV: {output_path_csv}")
        print(f"   ⚠️ Excel-Export nicht verfügbar (openpyxl nicht installiert)")
        print("=" * 80 + "\n")


def main():
    """Hauptfunktion"""
    
    print("\n" + "=" * 80)
    print("🎯 RAGAS-EVALUATION - WiSo-Chatbot")
    print("=" * 80 + "\n")
    
    # Checkpoint-Pfad
    checkpoint_path = Path(__file__).parent / "data" / "responses_checkpoint.pkl"
    
    # Variablen für Timing und URLs initialisieren
    response_times = None
    urls_list = None
    
    try:
        # Prüfe ob Checkpoint existiert
        if checkpoint_path.exists():
            print("📂 Lade Checkpoint...")
            import pickle
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
            
            # Checkpoint kann EvaluationDataset oder dict sein
            if isinstance(checkpoint_data, dict):
                dataset = checkpoint_data['dataset']
                test_df = checkpoint_data['test_df']
                # Neue Felder aus erweitertem Checkpoint laden (falls vorhanden)
                response_times = checkpoint_data.get('response_times', None)
                urls_list = checkpoint_data.get('urls_list', None)
            else:
                # Alter Checkpoint-Format (nur Dataset)
                dataset = checkpoint_data
                # test_df muss neu geladen werden
                test_df = load_testset()  # Alle Fragen laden
            
            print(f"   ✅ {len(dataset.samples)} Antworten aus Checkpoint geladen\n")
            if response_times:
                print(f"   ⏱️ Antwortzeiten aus Checkpoint: {len(response_times)} Einträge")
            if urls_list:
                print(f"   🔗 URLs aus Checkpoint: {len(urls_list)} Einträge")
            
        else:
            # Kein Checkpoint → Vollständiger Durchlauf
            # 1. LangSmith Client
            print("🔗 Initialisiere LangSmith...")
            langsmith_client = Client(api_key=LANGSMITH_API_KEY)
            print(f"   ✅ Projekt: {LANGSMITH_PROJECT}\n")
            
            # 2. Testset laden (mit optionalem Limit)
            print("📂 Lade Testset...")
            test_df = load_testset(limit=TEST_LIMIT)
            print()
            
            # 3. Chatbot initialisieren
            print("🤖 Initialisiere Chatbot...")
            agent = create_react_agent()
            print()
            
            # 4. Antworten generieren (jetzt mit Timing und URLs)
            dataset, response_times, urls_list = generate_chatbot_responses(test_df, agent, langsmith_client)
        
        # 5. RAGAS-Evaluation (immer ausführen, jetzt mit Timing)
        results_df, evaluation_time = run_ragas_evaluation(dataset)
        
        # 6. Ergebnisse anzeigen und speichern (mit allen neuen Daten)
        display_and_save_results(results_df, test_df, response_times, urls_list, evaluation_time)
        
        print("✅ Evaluation erfolgreich abgeschlossen!")
        
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
