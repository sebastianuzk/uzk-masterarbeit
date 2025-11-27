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
import pandas as pd
from pathlib import Path
from typing import List
import time

# Projekt-Root
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ragas import evaluate
from ragas.metrics import faithfulness, context_recall, context_precision  # answer_relevancy benötigt Embeddings
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langsmith import Client
from config.settings import (
    OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    OLLAMA_EMBEDDING_MODEL,
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT
)
from src.agent.react_agent import create_react_agent


def load_testset(csv_path: str = "data/Testset.CSV", limit: int = None) -> pd.DataFrame:
    """Lädt Testset.CSV"""
    full_path = Path(__file__).parent / csv_path
    df = pd.read_csv(full_path, sep=';', encoding='utf-8')
    
    if limit:
        df = df.head(limit)
    
    print(f"✅ {len(df)} Testfragen geladen")
    print(f"   Kategorien: {df['category'].unique().tolist()}")
    print(f"   Schwierigkeiten: easy={len(df[df['difficulty']=='easy'])}, medium={len(df[df['difficulty']=='medium'])}, hard={len(df[df['difficulty']=='hard'])}")
    
    return df


def get_rag_context_from_langsmith(client: Client, trace_id: str) -> List[str]:
    """
    Holt RAG-Kontext aus LangSmith für eine spezifische Trace-ID.
    
    Die Documents befinden sich im Retriever-Output unter dem Key 'output' (nicht 'documents'!).
    Jedes Document hat 'page_content' und 'metadata'.
    
    Args:
        client: LangSmith Client
        trace_id: Die Trace-ID der Session
        
    Returns:
        Liste von RAG-Context-Chunks aus den Retriever-Documents
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
        for child in child_runs:
            if child.run_type == "retriever":
                if child.outputs and isinstance(child.outputs, dict):
                    # Documents sind unter 'output' Key (nicht 'documents')!
                    documents = child.outputs.get('output', [])
                    for doc in documents:
                        if isinstance(doc, dict) and 'page_content' in doc:
                            contexts.append(doc['page_content'])
        
        if contexts:
            return contexts  # Liste von Chunks zurückgeben
        
        return ["Kein RAG-Kontext gefunden"]  # Als Liste
    
    except Exception as e:
        print(f"      ⚠️ LangSmith-Fehler: {str(e)[:100]}")
        return ["LangSmith-Fehler"]  # Als Liste


def generate_chatbot_responses(df: pd.DataFrame, agent, langsmith_client: Client) -> EvaluationDataset:
    """
    Generiert Chatbot-Antworten für alle Fragen und sammelt RAG-Kontexte.
    """
    print("\n🤖 Generiere Chatbot-Antworten...")
    print("=" * 80)
    
    samples = []
    
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
        
        # Agent.chat() mit session_id aufrufen
        answer = agent.chat(question, session_id=session_id)
        print(f"   ✅ Antwort: {answer[:80]}...")
        
        # Warten damit LangSmith Trace vollständig ist
        time.sleep(3)
        
        # RAG-Kontext aus LangSmith holen - verwende session_id um exakt diesen Run zu finden
        print(f"   🔍 Hole RAG-Kontext aus LangSmith...")
        
        # Hole alle Root-Runs und filtere nach session_id in Metadata
        all_runs = list(langsmith_client.list_runs(
            project_name=LANGSMITH_PROJECT,
            is_root=True
        ))
        
        contexts = ["Kein RAG-Kontext gefunden"]  # Default als Liste
        matching_run = None
        
        # Finde Run mit unserer session_id
        for run in all_runs:
            if run.metadata and run.metadata.get("session_id") == session_id:
                matching_run = run
                break
        
        if matching_run:
            trace_id = matching_run.trace_id
            contexts = get_rag_context_from_langsmith(langsmith_client, trace_id)
            print(f"   ✅ Run gefunden mit Session-ID: {session_id[:8]}...")
        else:
            print(f"   ⚠️ Kein Run mit Session-ID {session_id[:8]}... gefunden")
        
        total_chars = sum(len(c) for c in contexts)
        print(f"   📄 Kontext: {len(contexts)} chunks, {total_chars} Zeichen")
        
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
    
    # Zwischenspeicherung der Antworten und Kontexte
    dataset = EvaluationDataset(samples=samples)
    checkpoint_path = Path(__file__).parent / "data" / "responses_checkpoint.pkl"
    checkpoint_path.parent.mkdir(exist_ok=True)
    
    import pickle
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(dataset, f)
    print(f"💾 Checkpoint gespeichert: {checkpoint_path}")
    print(f"   (Antworten + Kontexte für alle {len(samples)} Fragen)\n")
    
    return dataset


def run_ragas_evaluation(dataset: EvaluationDataset) -> pd.DataFrame:
    """
    Führt RAGAS-Evaluation durch.
    Verwendet 3 Standard-RAGAS-Metriken: faithfulness, context_recall, context_precision.
    (answer_relevancy auskommentiert - benötigt qwen3-embedding:8b)
    """
    print("🚀 Starte RAGAS-Evaluation...")
    print("=" * 80)
    
    # Ollama LLM konfigurieren
    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0
    )
    print(f"   LLM: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
    
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
    
    # Evaluation mit begrenzten Workers für Ollama
    results = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=llm,
        max_workers=4,  # Begrenzt parallele Requests an Ollama
        raise_exceptions=False  # Weiter bei Fehlern
    )
    
    return results.to_pandas()


def display_and_save_results(results_df: pd.DataFrame, test_df: pd.DataFrame):
    """Zeigt Ergebnisse an und speichert sie."""
    
    # IDs, Kategorien und Schwierigkeiten hinzufügen
    results_df['id'] = test_df['id'].values[:len(results_df)]
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
    
    # CSV mit allen wichtigen Spalten
    csv_df = results_df[['id', 'category', 'difficulty', 'user_input', 'response', 
                          'reference', 'retrieved_contexts', 'faithfulness', 
                          'context_recall', 'context_precision', 'context_count']].copy()
    
    # Speichere mit UTF-8-BOM für korrekte Umlaut-Darstellung
    csv_df.to_csv(output_path_csv, index=False, encoding='utf-8-sig', sep=',', quoting=1)
    
    print("\n" + "=" * 80)
    print(f"💾 Ergebnisse gespeichert:")
    print(f"   CSV: {output_path_csv}")
    print("=" * 80 + "\n")


def main():
    """Hauptfunktion"""
    
    print("\n" + "=" * 80)
    print("🎯 RAGAS-EVALUATION - WiSo-Chatbot")
    print("=" * 80 + "\n")
    
    # Anzahl Fragen (für Test: 3, für vollständig: 40)
    NUM_QUESTIONS = 40  # VOLLSTÄNDIGE PRODUKTIVE EVALUATION
    
    try:
        # 1. LangSmith Client
        print("🔗 Initialisiere LangSmith...")
        langsmith_client = Client(api_key=LANGSMITH_API_KEY)
        print(f"   ✅ Projekt: {LANGSMITH_PROJECT}\n")
        
        # 2. Testset laden
        print("📂 Lade Testset...")
        test_df = load_testset(limit=NUM_QUESTIONS)
        print()
        
        # 3. Chatbot initialisieren
        print("🤖 Initialisiere Chatbot...")
        agent = create_react_agent()
        print()
        
        # 4. Antworten generieren
        dataset = generate_chatbot_responses(test_df, agent, langsmith_client)
        
        # 5. RAGAS-Evaluation
        results_df = run_ragas_evaluation(dataset)
        
        # 6. Ergebnisse anzeigen und speichern
        display_and_save_results(results_df, test_df)
        
        print("✅ Evaluation erfolgreich abgeschlossen!")
        print(f"\n💡 Für vollständige Evaluation: NUM_QUESTIONS = 40\n")
        
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
