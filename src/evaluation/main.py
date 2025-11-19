"""
Test-Script für RAGAS-Metriken
Testet faithfulness, context_recall, context_precision einzeln mit echten Daten aus Testset.CSV
"""
import sys
import pandas as pd
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from ragas.metrics import faithfulness, context_recall, context_precision
from ragas.dataset_schema import SingleTurnSample, EvaluationDataset
from ragas import evaluate
from langchain_ollama import ChatOllama
from langsmith import Client
from config.settings import (
    OLLAMA_MODEL, 
    OLLAMA_BASE_URL,
    LANGSMITH_API_KEY,
    LANGSMITH_PROJECT
)
from src.agent.react_agent import create_react_agent
import time
import uuid

print("=" * 80)
print("🧪 RAGAS-METRIKEN TEST mit Testset.CSV")
print("=" * 80)

# Konfiguration
NUM_TEST_QUESTIONS = 1  # Anzahl Fragen zum Testen
START_INDEX = 1  # Startindex (0 = erste Frage, 1 = zweite Frage, etc.)

# 1. Lade Testset.CSV
csv_path = Path(__file__).parent / "data" / "Testset.CSV"
df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
test_df = df.iloc[START_INDEX:START_INDEX + NUM_TEST_QUESTIONS]  # Fragen ab START_INDEX

print(f"\n📂 Testset geladen: {len(df)} Fragen verfügbar")
print(f"   Teste mit den ersten {NUM_TEST_QUESTIONS} Fragen\n")

# 2. Initialisiere Chatbot und LangSmith
print(f"🤖 Initialisiere Chatbot...")
agent = create_react_agent()
langsmith_client = Client(api_key=LANGSMITH_API_KEY)
print()

# 3. Generiere Antworten und sammle Samples
samples = []

print("💬 Generiere Antworten...")
print("=" * 80)

for idx, row in test_df.iterrows():
    question = row['question']
    expected_answer = row['expected_answer']
    
    print(f"\n[{idx + 1}/{len(test_df)}] {question[:70]}...")
    
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
        
        for child in child_runs:
            if child.run_type == "retriever" and child.outputs:
                documents = child.outputs.get('output', [])
                contexts = []
                for doc in documents:
                    if isinstance(doc, dict) and 'page_content' in doc:
                        contexts.append(doc['page_content'])
                if contexts:
                    break
    
    total_context_chars = sum(len(c) for c in contexts)
    print(f"   📄 Context: {len(contexts)} chunks, {total_context_chars} total chars")
    
    # Sample erstellen - contexts als Liste übergeben für Context Precision
    sample = SingleTurnSample(
        user_input=question,
        response=response,
        retrieved_contexts=contexts,  # Liste von Chunks!
        reference=expected_answer
    )
    samples.append(sample)

print(f"\n{'=' * 80}")
print(f"✅ {len(samples)} Antworten generiert\n")

# 4. Erstelle Dataset
dataset = EvaluationDataset(samples=samples)

# 5. LLM konfigurieren
llm = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.0
)

print(f"🤖 LLM: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}\n")

# Zeige Dataset-Inhalte
print("=" * 80)
print("📊 DATASET-INHALTE")
print("=" * 80)
for i, sample in enumerate(dataset.samples):
    print(f"\nSample {i+1}:")
    print(f"  User Input: {sample.user_input}")
    print(f"  Response: {sample.response[:100]}...")
    print(f"  Reference: {sample.reference[:100]}...")
    print(f"  Retrieved Contexts ({len(sample.retrieved_contexts)} chunks):")
    for j, ctx in enumerate(sample.retrieved_contexts):
        print(f"    Chunk {j+1} ({len(ctx)} chars): {ctx[:150]}...")

# Test 1: Faithfulness
print("\n" + "=" * 80)
print("TEST 1: Faithfulness")
print("=" * 80)
print(f"📄 Context ({len(dataset.samples[0].retrieved_contexts)} chunks):")
for i, ctx in enumerate(dataset.samples[0].retrieved_contexts[:2]):  # Zeige erste 2 Chunks
    print(f"  Chunk {i+1}: {ctx[:200]}...")
print()
try:
    print("⏳ Evaluiere...")
    result = evaluate(dataset=dataset, metrics=[faithfulness], llm=llm)
    print(f"✅ Faithfulness: {result['faithfulness']}")
except Exception as e:
    print(f"❌ Fehler: {str(e)}")

# Test 2: Context Recall
print("\n" + "=" * 80)
print("TEST 2: Context Recall")
print("=" * 80)
print(f"📄 Context ({len(dataset.samples[0].retrieved_contexts)} chunks):")
for i, ctx in enumerate(dataset.samples[0].retrieved_contexts[:2]):  # Zeige erste 2 Chunks
    print(f"  Chunk {i+1}: {ctx[:200]}...")
print()
try:
    print("⏳ Evaluiere...")
    result = evaluate(dataset=dataset, metrics=[context_recall], llm=llm)
    print(f"✅ Context Recall: {result['context_recall']}")
except Exception as e:
    print(f"❌ Fehler: {str(e)}")

# Test 3: Context Precision  
print("\n" + "=" * 80)
print("TEST 3: Context Precision")
print("=" * 80)
print(f"📄 Context ({len(dataset.samples[0].retrieved_contexts)} chunks):")
for i, ctx in enumerate(dataset.samples[0].retrieved_contexts[:2]):  # Zeige erste 2 Chunks
    print(f"  Chunk {i+1}: {ctx[:200]}...")
print()
try:
    print("⏳ Evaluiere...")
    result = evaluate(dataset=dataset, metrics=[context_precision], llm=llm)
    print(f"✅ Context Precision: {result['context_precision']}")
except Exception as e:
    print(f"❌ Fehler: {str(e)}")

# Test 4: Alle zusammen
print("\n" + "=" * 80)
print("TEST 4: Alle Metriken zusammen")
print("=" * 80)
print(f"📄 Context ({len(dataset.samples[0].retrieved_contexts)} chunks):")
for i, ctx in enumerate(dataset.samples[0].retrieved_contexts[:2]):  # Zeige erste 2 Chunks
    print(f"  Chunk {i+1}: {ctx[:200]}...")
print()
try:
    print("⏳ Evaluiere...")
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, context_recall, context_precision],
        llm=llm
    )
    print(f"✅ Faithfulness: {result['faithfulness']}")
    print(f"✅ Context Recall: {result['context_recall']}")
    print(f"✅ Context Precision: {result['context_precision']}")
except Exception as e:
    print(f"❌ Fehler: {str(e)}")

# Vollständige Kontext-Ausgabe am Ende
print("\n" + "=" * 80)
print("📄 VOLLSTÄNDIGER KONTEXT")
print("=" * 80)

for i, sample in enumerate(dataset.samples):
    print(f"\n{'='*80}")
    print(f"Frage {i+1}: {sample.user_input}")
    print(f"{'='*80}")
    
    for j, context in enumerate(sample.retrieved_contexts):
        print(f"\n--- KONTEXT-CHUNK {j+1} ({len(context)} Zeichen) ---")
        print(context)
        print(f"\n--- ENDE CHUNK {j+1} ---")

# Speichere Kontext in .txt-Datei
print("\n" + "=" * 80)
print("💾 Speichere Kontext in Datei...")

output_dir = Path(__file__).parent / "data"
output_dir.mkdir(exist_ok=True)
output_file = output_dir / f"context_output_{START_INDEX}.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("VOLLSTÄNDIGER KONTEXT - RAGAS EVALUATION\n")
    f.write("=" * 80 + "\n\n")
    
    for i, sample in enumerate(dataset.samples):
        f.write(f"{'='*80}\n")
        f.write(f"Frage {i+1}: {sample.user_input}\n")
        f.write(f"{'='*80}\n\n")
        f.write(f"Antwort: {sample.response}\n\n")
        f.write(f"Erwartete Antwort: {sample.reference}\n\n")
        
        for j, context in enumerate(sample.retrieved_contexts):
            f.write(f"\n--- KONTEXT-CHUNK {j+1} ({len(context)} Zeichen) ---\n")
            f.write(context)
            f.write(f"\n\n--- ENDE CHUNK {j+1} ---\n\n")

print(f"✅ Kontext gespeichert in: {output_file}")

print("\n" + "=" * 80)
print("✅ Test abgeschlossen!")
print("=" * 80)
