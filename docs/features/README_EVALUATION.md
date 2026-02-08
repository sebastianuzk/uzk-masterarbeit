# RAGAS-Evaluation: Systematische Bewertung des WiSo-Chatbots

## Übersicht

Das Evaluation-Modul führt eine **systematische Bewertung** des WiSo-Chatbots mittels des RAGAS-Frameworks (Retrieval-Augmented Generation Assessment) durch. Es kombiniert automatisierte Metrik-Berechnung mit LLM-basierter Qualitätsbewertung.

**Kernfunktionen**:
- Automatische Antwortgenerierung für Testfragen
- Extraktion von RAG-Kontexten aus LangSmith
- Berechnung von 9+ Evaluationsmetriken
- Unterstützung für lokale (Ollama) und Cloud (OpenAI) Evaluation
- Checkpoint-System für Wiederaufnahme bei Abbruch
- Excel/CSV-Export mit detaillierten Ergebnissen

## Verwendete Libraries

```
ragas==0.3.x           # RAGAS-Framework für RAG-Evaluation
langsmith              # Tracing und Kontext-Extraktion
langchain-ollama       # Lokale LLM-Evaluation (Ollama)
langchain-openai       # Cloud LLM-Evaluation (OpenAI)
bert-score             # Token-Level semantische Ähnlichkeit
pandas                 # Datenverarbeitung
openpyxl               # Excel-Export
numpy                  # Numerische Berechnungen
```

## Konfiguration (.env)

```bash
# Evaluationsmodus
RUN_EVALUATION_LOCAL=true         # true = Ollama, false = OpenAI

# Lokale Evaluation (Ollama)
RAGAS_EVAL_MODEL=llama3.1:70b     # Separates Modell für RAGAS-Judge
OLLAMA_BASE_URL=http://localhost:11434

# Cloud Evaluation (OpenAI)
OPENAI_API_KEY=sk-...
OPENAI_EVAL_MODEL=gpt-4o-mini     # OpenAI Modell für RAGAS-Judge

# Embeddings (IMMER lokal)
RAGAS_EMBEDDING_MODEL=embeddinggemma

# Reproduzierbarkeit
RANDOM_SEED=42
TEMPERATURE=0.1
CONTEXT_WINDOW=131072
```

## Evaluationsmetriken

### RAGAS-Metriken

| Metrik | Beschreibung | Bereich |
|--------|--------------|---------|
| **Faithfulness** | Ist die Antwort treu zum Kontext? (keine Halluzinationen) | 0.0 - 1.0 |
| **Context Recall** | Wurden alle relevanten Infos aus dem Kontext genutzt? | 0.0 - 1.0 |
| **Context Precision** | Sind relevante Chunks höher gerankt? | 0.0 - 1.0 |
| **Semantic Similarity** | Semantische Ähnlichkeit zwischen Antwort und Referenz | 0.0 - 1.0 |
| **Context Entity Recall** | Entitäten-Recall zwischen Referenz und Kontext | 0.0 - 1.0 |
| **Answer Relevancy** | Relevanz der Antwort zur gestellten Frage | 0.0 - 1.0 |

### Zusätzliche Metriken

| Metrik | Beschreibung | Bereich |
|--------|--------------|---------|
| **BERT-F1** | Token-Level semantische Ähnlichkeit (xlm-roberta-large) | 0.0 - 1.0 |
| **BERT-Precision** | BERT-Score Precision | 0.0 - 1.0 |
| **BERT-Recall** | BERT-Score Recall | 0.0 - 1.0 |
| **MRR@5** | Mean Reciprocal Rank der Referenz-URL in Top-5 | 0.0 - 1.0 |
| **Hit@5** | Ist Referenz-URL in Top-5 enthalten? | 0.0 / 1.0 |
| **Latency** | Antwortzeit in Sekunden | ≥ 0 |
| **Total Tokens** | LLM Token-Verbrauch pro Anfrage | ≥ 0 |

## Testset-Format

Das Testset wird als CSV-Datei mit Semikolon-Trennung bereitgestellt (`data/Testset.CSV`):

```csv
id;question;expected_answer;context_hint;category;difficulty;Reference_Chunks
1;Wie bewerbe ich mich...;Die Bewerbung erfolgt...;https://wiso.uni-koeln.de/...;Bachelor-Studium;easy;"Chunk 1 / Chunk 2"
```

| Spalte | Beschreibung |
|--------|--------------|
| `id` | Eindeutige Fragen-ID |
| `question` | Die Testfrage |
| `expected_answer` | Erwartete Referenzantwort (Ground Truth) |
| `context_hint` | URL der erwarteten Quelle (für MRR@5/Hit@5) |
| `category` | Kategorie (Allgemein, Bachelor-Studium, Master-Studium, etc.) |
| `difficulty` | Schwierigkeitsgrad (easy, medium, hard) |
| `Reference_Chunks` | Erwartete Referenz-Chunks (für manuelles Review) |

## Evaluations-Workflow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           EVALUATION WORKFLOW                                │
└──────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐
│  Testset.CSV    │
│  (920 Fragen)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: ANTWORTGENERIERUNG                              │
│                                                                             │
│  Für jede Frage:                                                            │
│  1. Chatbot erhält Frage (via create_react_agent)                          │
│  2. RAG-Pipeline wird ausgeführt (Hybrid Retrieval → ReRanking → MMR)      │
│  3. LLM generiert Antwort                                                   │
│  4. LangSmith tracet alle Schritte                                         │
│  5. Checkpoint wird gespeichert (inkrementell)                             │
│                                                                             │
│  Extrahierte Daten:                                                         │
│  - response: Chatbot-Antwort                                               │
│  - retrieved_contexts: RAG-Chunks (aus LangSmith)                          │
│  - urls: Quell-URLs                                                         │
│  - content_types: Inhaltstypen (html, pdf)                                 │
│  - token_usage: LLM + ReRanking Tokens                                     │
│  - response_time: Latenz in Sekunden                                       │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GPU-SPEICHER FREIGEBEN                                   │
│                                                                             │
│  1. Chatbot-LLM (llama3.1:8b) entladen via `ollama stop`                   │
│  2. Embedding-Modell (BGE-M3) freigeben                                     │
│  3. CUDA Cache leeren                                                       │
│                                                                             │
│  → Platz für RAGAS-Evaluation-LLM                                          │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 2: RAGAS-EVALUATION                                │
│                                                                             │
│  Modi:                                                                      │
│  ┌─────────────────────────────┐  ┌──────────────────────────────┐        │
│  │ LOKAL (RUN_EVALUATION_      │  │ CLOUD (RUN_EVALUATION_       │        │
│  │        LOCAL=true)          │  │        LOCAL=false)          │        │
│  │                             │  │                              │        │
│  │ LLM: Ollama (llama3.1:70b) │  │ LLM: OpenAI (gpt-4o-mini)   │        │
│  │ Embeddings: Ollama (gemma) │  │ Embeddings: Ollama (gemma)  │        │
│  │ Workers: 4                  │  │ Workers: 150                 │        │
│  │ Timeout: 300s               │  │ Timeout: 1800s               │        │
│  └─────────────────────────────┘  └──────────────────────────────┘        │
│                                                                             │
│  Berechnete Metriken:                                                       │
│  - faithfulness, context_recall, context_precision                         │
│  - semantic_similarity, context_entity_recall, answer_relevancy            │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 3: BERT-SCORE                                      │
│                                                                             │
│  Modell: xlm-roberta-large (multilingual)                                  │
│  Berechnet: Precision, Recall, F1 auf Token-Level                          │
│  Vorteil: Semantische Ähnlichkeit ohne LLM-Judge                           │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 4: RETRIEVAL-METRIKEN                              │
│                                                                             │
│  MRR@5 (Mean Reciprocal Rank):                                             │
│  - Prüft ob context_hint URL in retrieved_urls vorkommt                    │
│  - Score = 1/rank (1.0 für Platz 1, 0.5 für Platz 2, ...)                 │
│                                                                             │
│  Hit@5:                                                                     │
│  - Binär: 1.0 wenn Referenz-URL in Top-5, sonst 0.0                        │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 5: EXPORT                                          │
│                                                                             │
│  Dateien (mit Timestamp):                                                   │
│  - ragas_results_raw_{timestamp}.csv    (Rohdaten)                         │
│  - ragas_results_{timestamp}.csv        (mit Durchschnitten)               │
│  - ragas_results_{timestamp}.xlsx       (formatiert)                        │
│                                                                             │
│  Enthält:                                                                   │
│  - Alle Einzelergebnisse pro Frage                                         │
│  - Durchschnitte: Gesamt, pro Kategorie, pro Schwierigkeit                │
│  - Kombinierte Durchschnitte (Kategorie × Schwierigkeit)                   │
│  - Metadaten (Modelle, Timestamps, Dauern)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Checkpoint-System

Die Evaluation unterstützt **inkrementelles Checkpointing**:

```python
# Checkpoint wird nach JEDER Frage gespeichert
checkpoint_path = f"data/responses_checkpoint_{EVAL_TIMESTAMP}.pkl"

# Checkpoint enthält:
checkpoint_data = {
    'dataset': EvaluationDataset,      # RAGAS-Format
    'test_df': DataFrame,              # Verarbeitete Zeilen
    'response_times': List[float],     # Latenz pro Frage
    'urls_list': List[List[str]],      # URLs pro Frage
    'content_types_list': List[...],   # Content-Types
    'token_usage_list': List[dict]     # Tokens pro Frage
}
```

**Vorteile**:
- Wiederaufnahme nach Abbruch/Fehler
- Keine doppelte Verarbeitung
- Separierung von Antwortgenerierung und RAGAS-Evaluation

## Batch-Evaluation

Mehrere Evaluationen können nacheinander ausgeführt werden:

```python
# In ragas_evaluation.py
EVAL_TIMESTAMPS = [
    "20260128_165351",  # Run 1
    "20260128_174356",  # Run 2
    "20260128_183659",  # Run 3
]
```

Jeder Timestamp repräsentiert einen separaten Evaluationslauf mit eigenem Checkpoint.

## Ausführung

### Neue Evaluation starten

```python
# In ragas_evaluation.py
EVAL_TIMESTAMPS = [datetime.now().strftime("%Y%m%d_%H%M%S")]
```

```bash
# Starten
python src/evaluation/ragas_evaluation.py
```

### Bestehende Evaluation fortsetzen

```python
# Timestamp des abgebrochenen Runs verwenden
EVAL_TIMESTAMPS = ["20260128_174356"]
```

### Nur RAGAS-Evaluation (ohne Antwortgenerierung)

Wenn Checkpoint vollständig ist, wird nur die RAGAS-Evaluation ausgeführt.

## LangSmith-Integration

Die Evaluation extrahiert Daten aus LangSmith:

```python
def get_rag_context_from_langsmith(client: Client, trace_id: str):
    """
    Extrahiert RAG-Kontexte aus LangSmith Retriever-Runs.
    
    WICHTIG: Bei mehreren Retriever-Runs (naive + advanced)
    wird der Run mit den WENIGSTEN Dokumenten genommen,
    da das die finale Auswahl ist (nach MMR).
    """
    
def get_token_usage_from_langsmith(client: Client, trace_id: str):
    """
    Extrahiert Token-Usage aus allen LLM-Runs.
    Unterscheidet zwischen:
    - LLM-Tokens (prompt + completion)
    - ReRanking-Tokens (Voyage/Cohere/Local)
    """
```

## GPU-Speichermanagement

Die Evaluation verwaltet GPU-Speicher aktiv:

```python
# Nach Antwortgenerierung: Chatbot entladen
stop_ollama_model(OLLAMA_MODEL)      # z.B. "llama3.1:8b"
stop_embedding_model()                # BGE-M3 freigeben
gc.collect()
torch.cuda.empty_cache()

# Dann: RAGAS-Evaluation mit separatem LLM
# Lokal:  llama3.1:70b (größeres Modell für präzisere Bewertung)
# Cloud:  gpt-4o-mini (API-basiert, kein lokaler GPU-Bedarf)
```

## Ergebnis-Dateien

### CSV-Format

```csv
id,category,difficulty,user_input,response,reference,retrieved_contexts,
retrieved_urls,retrieved_content_types,faithfulness,context_recall,
context_precision,semantic_similarity,context_entity_recall,answer_relevancy,
bert_f1,bert_precision,bert_recall,RR_at5,hit_at5,latency,
prompt_tokens,completion_tokens,total_tokens,reranking_tokens
```

### Excel-Format

| Sheet | Inhalt |
|-------|--------|
| Detaillierte Ergebnisse | Alle Einzelergebnisse |
| Zusammenfassung | Durchschnitte nach Kategorie/Schwierigkeit |

## Testset-Kategorien

| Kategorie | Beschreibung | Beispiel-Fragen |
|-----------|--------------|-----------------|
| Allgemein | Fakultätsübergreifende Infos | "Was bietet die WiSo-Fakultät?" |
| Bachelor-Studium | Bachelor-spezifisch | "Welche Bachelorstudiengänge gibt es?" |
| Master-Studium | Master-spezifisch | "Wann starten die Masterprogramme?" |
| Modulhandbuch/PO | Prüfungsordnungen | "Wo finde ich das Modulhandbuch?" |
| Studiengang spezifisch | Einzelne Programme | "Was lerne ich im Master IS?" |
| Services/Info | Beratung, Tools | "Was ist Chat with Paco?" |

## Schwierigkeitsgrade

| Level | Beschreibung | Erwartete Performance |
|-------|--------------|----------------------|
| easy | Direkte Fakten-Fragen | Hoch (>0.8) |
| medium | Mehrere Aspekte kombiniert | Mittel (0.6-0.8) |
| hard | Komplexe Zusammenhänge | Variabel (<0.6) |

## Referenzen

- **RAGAS Framework**: https://docs.ragas.io/
- **BERT-Score**: Zhang, T. et al. (2019). "BERTScore: Evaluating Text Generation with BERT"
- **LangSmith**: https://docs.smith.langchain.com/
- **Implementierung**: `src/evaluation/ragas_evaluation.py`
- **Testset**: `src/evaluation/data/Testset.CSV`
