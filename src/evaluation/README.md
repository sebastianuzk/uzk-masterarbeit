# RAG Evaluation Pipeline

Eine leichtgewichtige ARES (Automated Rating using Evaluation by Synthesis) basierte Pipeline zur Evaluation des RAG-Chatbots.

## 🎯 Überblick

Die Pipeline evaluiert RAG-Systeme anhand von drei Hauptmetriken:
- **Context Relevance**: Wie relevant ist der gefundene Kontext für die Frage?
- **Answer Faithfulness**: Ist die Antwort konsistent mit dem Kontext?
- **Answer Relevance**: Beantwortet die Response die ursprüngliche Frage?

## 📁 Struktur

```
src/evaluation/
├── __init__.py           # Module exports
├── ares_evaluator.py     # ARES-basierter Evaluator
├── metrics.py           # Metriken und Reporting
├── test_cases.py        # Testfälle-Management
├── pipeline.py          # End-to-End Pipeline
├── quick_eval.py        # Quick-Start Skript
└── README.md           # Diese Datei
```

## 🚀 Quick Start

### 1. Quick-Evaluation ausführen
```bash
cd src/evaluation
python quick_eval.py
```

Dies führt eine Evaluation mit 5 Sample-Testfällen durch und erstellt:
- Evaluation-Ergebnisse (JSON)
- Metriken-Export (JSON)
- Text-Bericht (TXT)

### 2. Programmatische Nutzung
```python
from src.evaluation import EvaluationPipeline, load_test_cases

# Pipeline initialisieren
pipeline = EvaluationPipeline()

# Testfälle laden (oder Sample-Testfälle verwenden)
test_cases = load_test_cases()

# Evaluation durchführen
results = pipeline.run_batch_evaluation(test_cases)
```

## 📊 Sample-Testfälle

Die Pipeline enthält 5 vorgefertigte Testfälle:

1. **TC_001**: VWL Master Bewerbung (easy, studium)
2. **TC_002**: Wirtschaftsinformatik Forschung (medium, forschung) 
3. **TC_003**: Studienberatung Sprechstunden (easy, services)
4. **TC_004**: Interdisziplinäre Programme (hard, studium)
5. **TC_005**: Internationale Netzwerke (medium, international)

## 🔧 Konfiguration

### ARES Evaluator anpassen
```python
from src.evaluation import ARESEvaluator

evaluator = ARESEvaluator(
    model_name="gpt-4o-mini",  # LLM für Evaluation
    temperature=0.1            # Temperature für konsistente Bewertungen
)
```

### Pipeline konfigurieren
```python
from src.evaluation import EvaluationPipeline
from pathlib import Path

pipeline = EvaluationPipeline(
    output_dir=Path("custom_results"),  # Custom Output-Verzeichnis
    rag_tool=my_rag_tool                # Custom RAG-Tool
)
```

## 📈 Metriken

### ARES Metriken
- `context_relevance`: 0.0 - 1.0
- `answer_faithfulness`: 0.0 - 1.0  
- `answer_relevance`: 0.0 - 1.0
- `overall_ares_score`: Gewichteter Durchschnitt (30% + 40% + 30%)

### Performance Metriken
- `retrieval_time_ms`: Zeit für Kontext-Retrieval
- `generation_time_ms`: Zeit für Antwort-Generierung
- `total_time_ms`: Gesamtzeit

### Response Metriken
- `response_length`: Länge der generierten Antwort
- `response_completeness`: Heuristik für Vollständigkeit (0.0 - 1.0)

## 📝 Testfälle hinzufügen

### JSON-Format
```json
{
  "metadata": {
    "total_test_cases": 1
  },
  "test_cases": [
    {
      "id": "tc_custom_001",
      "question": "Ihre Frage hier?",
      "expected_context": "Was der ideale Kontext enthalten sollte...",
      "expected_answer": "Beispiel einer guten Antwort...",
      "category": "studium",
      "difficulty": "medium",
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### Programmatisch
```python
from src.evaluation import TestCase

new_test_case = TestCase(
    id="tc_006",
    question="Ihre neue Frage?",
    expected_context="Erwarteter Kontext...",
    expected_answer="Erwartete Antwort...",
    category="services",
    difficulty="easy",
    tags=["custom", "test"]
)
```

## 📊 Evaluation-Berichte

### JSON-Export
Vollständige Ergebnisse mit allen Metriken und Einzelbewertungen.

### Metriken-Export  
Aggregierte Statistiken und Performance-Daten.

### Text-Bericht
```
RAG Evaluation Bericht
=====================

Anzahl Evaluationen: 5

ARES Metriken:
--------------
Context Relevance:      0.850
Answer Faithfulness:    0.900
Answer Relevance:       0.800
Overall ARES Score:     0.850

Performance Metriken:
--------------------
Ø Retrieval Zeit:       45.2ms
Ø Generation Zeit:      120.8ms
Ø Gesamt Zeit:          166.0ms

Bewertung:
----------
🟢 Excellent - RAG-System zeigt sehr gute Performance
```

## 🔄 Integration mit echtem RAG-Tool

Für die Integration mit dem produktiven RAG-Tool:

1. **RAG-Tool übergeben**:
```python
from src.tools.rag_tool import RAGTool

rag_tool = RAGTool()  # Ihr echtes RAG-Tool
pipeline = EvaluationPipeline(rag_tool=rag_tool)
```

2. **LLM-Integration** (in `ares_evaluator.py`):
```python
def _query_llm(self, prompt: str) -> str:
    # Ersetze Mock-Implementation durch echte LLM-Calls
    # z.B. OpenAI API oder Ollama
    pass
```

## 🛠️ Erweiterungen

### Custom Metriken hinzufügen
Erweitere `RAGMetrics` in `metrics.py` um zusätzliche Metriken.

### Neue Evaluation-Methoden
Implementiere zusätzliche Evaluator-Klassen neben ARES.

### Advanced Filtering
Nutze die Filter-Funktionen in `test_cases.py` für spezifische Evaluationen.

## 📋 Nächste Schritte

1. **LLM-Integration**: Echte LLM-Calls für ARES-Evaluation
2. **RAG-Tool Integration**: Verbindung mit produktivem RAG-System
3. **Mehr Testfälle**: Erweitere die Testfall-Sammlung
4. **Advanced Metriken**: Implementiere zusätzliche Evaluation-Metriken
5. **Benchmarking**: Vergleiche mit anderen RAG-Systemen