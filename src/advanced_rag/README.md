# Modulares RAG-System

Dieses Modul implementiert ein **Retrieval-Augmented Generation (RAG)** System mit konfigurierbaren, modularen Techniken.

## 📋 Überblick

Das RAG-System ist in drei Phasen unterteilt:

1. **Pre-Retrieval**: Query-Optimierung (geplant)
2. **Retrieval**: Dokumenten-Suche in ChromaDB ✅
3. **Post-Retrieval**: Ergebnis-Verarbeitung ✅

Jede Technik kann **unabhängig aktiviert/deaktiviert** werden für:
- A/B-Testing
- Evaluierungen (Naive vs. Advanced)
- Inkrementelle Optimierung

## 🏗️ Architektur

```
src/rag/
├── config.py              # Zentrale Konfiguration (RAGConfig)
├── presets.py             # Vordefinierte Konfigurationen
├── __init__.py            # Modul-Exports
├── retrieval/             # Retrieval-Techniken
│   ├── multi_collection_search.py
│   ├── result_aggregation.py
│   ├── distance_conversion.py
│   └── global_reranking.py
└── post_retrieval/        # Post-Retrieval-Techniken
    ├── relevance_filtering.py
    ├── result_formatting.py
    ├── context_hints.py
    └── empty_result_handler.py
```

## ✅ Implementierte Techniken

### Retrieval (4 Techniken)

| Technik | Flag | Beschreibung |
|---------|------|--------------|
| **Multi-Collection Search** | `use_multi_collection_search` | Durchsucht alle ChromaDB-Collections statt nur einer |
| **Result Aggregation** | `use_result_aggregation` | Aggregiert und sortiert Ergebnisse aus mehreren Quellen |
| **Distance Conversion** | `use_distance_conversion` | Konvertiert Cosine-Distance (0-2) zu Relevance-Score (0-1) |
| **Global Re-ranking** | `use_global_reranking` | Globales Ranking über alle Quellen hinweg |

**Naive Fallback**: Durchsucht nur erste Collection, keine Aggregation/Konversion.

### Post-Retrieval (4 Techniken)

| Technik | Flag | Beschreibung |
|---------|------|--------------|
| **Relevance Filtering** | `use_relevance_filtering` | Filtert Ergebnisse unter Relevanz-Schwellenwert (0.1) |
| **Result Formatting** | `use_result_formatting` | Formatiert Ergebnisse mit Metadaten, Quellen, Emojis |
| **Context Hints** | `use_context_hints` | Fügt kontextspezifische Hinweise hinzu (z.B. Prüfungsamt) |
| **Empty Result Handling** | `use_empty_result_handling` | Intelligente Fehlermeldungen (keine Daten vs. nicht relevant) |

**Naive Fallback**: Kein Filtering, einfache Textkonkatenation, generische Fehler.

## 🚀 Verwendung

### 1. Standard (Advanced RAG aus Environment)

```python
from src.rag.config import RAGConfig

# Lädt Konfiguration aus Umgebungsvariablen
config = RAGConfig.from_env()
```

### 2. Naive Baseline

```python
from src.rag.presets import naive_rag_config

# Alle Techniken deaktiviert
config = naive_rag_config()
```

**Verhalten**:
- Durchsucht nur erste Collection
- Keine Relevanz-Filterung
- Einfache Textausgabe ohne Formatierung
- Keine kontextspezifischen Hinweise

### 3. Advanced RAG

```python
from src.rag.presets import advanced_rag_config

# Alle implementierten Techniken aktiviert
config = advanced_rag_config()
```

**Verhalten**:
- Multi-Collection Search über alle Collections
- Relevanz-Filterung (Threshold 0.1)
- Formatierte Ausgabe mit Metadaten
- Kontextspezifische Hinweise

### 4. Custom Configuration

```python
from src.rag.presets import custom_rag_config

# Nur Retrieval-Techniken
config = custom_rag_config(
    multi_collection=True,
    result_aggregation=True,
    distance_conversion=True,
    global_reranking=True,
    # Post-Retrieval deaktiviert
    result_formatting=False,
    context_hints=False,
    empty_handling=False
)

# Einzelne Technik isoliert testen
config = custom_rag_config(
    multi_collection=False,
    result_aggregation=False,
    distance_conversion=True,  # NUR diese Technik
    global_reranking=False,
    result_formatting=False,
    context_hints=False,
    empty_handling=False
)
```

### 5. Integration in RAG-Tool

Das `UniversityRAGTool` verwendet automatisch die modularen Techniken:

```python
from src.tools.rag_tool import create_university_rag_tool
from src.rag.presets import naive_rag_config

# Erstelle Tool mit Custom-Config
tool = create_university_rag_tool()

# Überschreibe Config für Testing
tool.config = naive_rag_config()

# Verwende Tool
result = tool._run("Was benötige ich für die Bewerbung?")
```

## 🧪 Evaluierung & Testing

### A/B-Test: Naive vs. Advanced

```python
from src.tools.rag_tool import UniversityRAGTool
from src.rag.presets import naive_rag_config, advanced_rag_config

# Naive Baseline
naive_tool = UniversityRAGTool(config=naive_rag_config())
naive_result = naive_tool._run("Bewerbung höheres Fachsemester")

# Advanced RAG
advanced_tool = UniversityRAGTool(config=advanced_rag_config())
advanced_result = advanced_tool._run("Bewerbung höheres Fachsemester")

# Vergleiche Ergebnisse
print("NAIVE:\n", naive_result)
print("\nADVANCED:\n", advanced_result)
```

### Inkrementelles Testing

```python
from src.rag.presets import custom_rag_config

# Baseline
baseline = custom_rag_config(
    multi_collection=False,
    result_aggregation=False,
    distance_conversion=False,
    global_reranking=False,
    result_formatting=False,
    context_hints=False
)

# + Multi-Collection
with_multi = custom_rag_config(
    multi_collection=True,  # NEU
    result_aggregation=False,
    distance_conversion=False,
    global_reranking=False,
    result_formatting=False,
    context_hints=False
)

# + Multi-Collection + Result Aggregation
with_aggregation = custom_rag_config(
    multi_collection=True,
    result_aggregation=True,  # NEU
    distance_conversion=False,
    global_reranking=False,
    result_formatting=False,
    context_hints=False
)

# ... und so weiter
```

### RAGAS Evaluation

```python
from src.evaluation.ragas_evaluation_with_retry import run_ragas_evaluation
from src.rag.presets import naive_rag_config, advanced_rag_config

# Evaluiere Naive Baseline
tool_naive = UniversityRAGTool(config=naive_rag_config())
metrics_naive = run_ragas_evaluation(
    agent_executor=agent_with_naive_tool,
    test_dataset=test_questions
)

# Evaluiere Advanced RAG
tool_advanced = UniversityRAGTool(config=advanced_rag_config())
metrics_advanced = run_ragas_evaluation(
    agent_executor=agent_with_advanced_tool,
    test_dataset=test_questions
)

# Vergleiche Metriken
print(f"Naive Context Recall: {metrics_naive['context_recall']}")
print(f"Advanced Context Recall: {metrics_advanced['context_recall']}")
```

## ⚙️ Konfiguration

### RAGConfig Parameter

| Parameter | Typ | Default | Beschreibung |
|-----------|-----|---------|--------------|
| `baseline_enabled` | bool | True | Nutze Baseline statt Advanced |
| `use_multi_collection_search` | bool | True | Multi-Collection Search |
| `use_result_aggregation` | bool | True | Result Aggregation |
| `use_distance_conversion` | bool | True | Distance-to-Relevance Conversion |
| `use_global_reranking` | bool | True | Global Re-ranking |
| `use_relevance_filtering` | bool | True | Relevance Filtering |
| `use_result_formatting` | bool | True | Rich Result Formatting |
| `use_context_hints` | bool | True | Context-specific Hints |
| `use_empty_result_handling` | bool | True | Smart Empty Result Messages |
| `relevance_threshold` | float | 0.1 | Minimum Relevance Score |
| `k_per_collection` | int | 3 | Ergebnisse pro Collection |
| `top_k` | int | 5 | Finale Top-K Ergebnisse |
| `debug_mode` | bool | False | Debug-Ausgaben |

### Umgebungsvariablen

```bash
# Retrieval
RAG_MULTI_COLLECTION_SEARCH=true
RAG_RESULT_AGGREGATION=true
RAG_DISTANCE_CONVERSION=true
RAG_GLOBAL_RERANKING=true

# Post-Retrieval
RAG_RELEVANCE_FILTERING=true
RAG_RELEVANCE_THRESHOLD=0.1
RAG_RESULT_FORMATTING=true
RAG_CONTEXT_HINTS=true
RAG_EMPTY_RESULT_HANDLING=true

# Allgemein
RAG_K_PER_COLLECTION=3
RAG_TOP_K=5
RAG_DEBUG_MODE=false
```

## 📊 Erwartete Verbesserungen

| Metrik | Naive | Advanced | Verbesserung |
|--------|-------|----------|--------------|
| Context Recall | ~0.60 | ~0.75 | +25% |
| Context Precision | ~0.65 | ~0.80 | +23% |
| Answer Relevancy | ~0.70 | ~0.85 | +21% |
| Faithfulness | ~0.75 | ~0.90 | +20% |

**Basis**: 40 Test-Fragen, evaluiert mit RAGAS (llama3.1:8b via Ollama)

## 🔮 Geplante Techniken

### Pre-Retrieval (noch nicht implementiert)

- Query Expansion
- Query Rewriting
- HyDE (Hypothetical Document Embeddings)
- Multi-Query Generation

### Retrieval (noch nicht implementiert)

- Hybrid Retrieval (BM25 + Dense)
- Parent Document Retrieval
- Advanced Re-ranking (Cross-Encoder)

### Post-Retrieval (noch nicht implementiert)

- Context Compression
- Context Reordering
- Answer Fusion

## 🐛 Debugging

```python
from src.rag.config import RAGConfig

# Aktiviere Debug-Modus
config = RAGConfig.from_env()
config.debug_mode = True

# Erstelle Tool mit Debug-Config
tool = UniversityRAGTool(config=config)

# Führe Query aus (zeigt Debug-Ausgaben)
result = tool._run("Test Query")
```

## 📝 Best Practices

1. **Evaluierungen**: Immer mit Naive Baseline vergleichen
2. **A/B-Testing**: Einzelne Techniken isoliert testen
3. **Production**: Advanced Config mit allen Techniken
4. **Debugging**: Debug-Modus + Custom Config mit einzelnen Techniken
5. **Metriken**: RAGAS für quantitative Evaluierung

## 🔗 Weitere Informationen

- RAG-Hyperparameter: `hyperparameter_documentation.md`
- RAGAS Setup: `LANGSMITH_SETUP.md`
- Scraper: `src/scraper/README.md`
- Tests: `tests/test_system_.py`
