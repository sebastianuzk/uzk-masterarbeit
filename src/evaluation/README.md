# ARES-basierte RAG-Evaluation

Dieses Modul implementiert ein umfassendes Evaluations-System für RAG (Retrieval-Augmented Generation) Systeme basierend auf dem **Stanford ARES Framework**.

## 📋 Überblick

Das System ersetzt die vorherige ARES-ähnliche Implementierung durch eine echte Integration des Stanford ARES Frameworks und bietet:

- **Authentisches ARES Framework**: Verwendung der offiziellen `ares-ai` Bibliothek
- **Umfassende Metriken**: Context Relevance, Answer Relevance, Answer Faithfulness
- **Flexible Testfälle**: JSON-basierte Testfall-Verwaltung
- **Batch-Processing**: Effiziente Evaluation mehrerer Testfälle
- **Ergebnis-Tracking**: Automatische Speicherung und Analyse

## 🏗️ Architektur

```
src/evaluation/
├── __init__.py              # ARES-basierte Imports
├── ares_evaluator.py        # Stanford ARES Framework Integration
├── evaluation_runner.py     # Orchestrierung von Evaluationen
├── test_cases.py           # Testfall-Datenstrukturen
├── results_manager.py      # Ergebnis-Speicherung und -Verwaltung
├── simple_rag_evaluation.py # Vereinfachte API für Nutzer
├── test_direct_evaluation.py # Test-Scripts
├── test_direct_storage.py  # Test-Scripts
└── data/
    └── wiso_test_cases.json # Standard WiSo-Testfälle
```

## 🚀 Quick Start

### 1. Installation

Das ARES Framework ist bereits installiert:

```bash
# Bereits installiert in der virtuellen Umgebung
pip install ares-ai
```

### 2. Basic Usage

```python
from src.evaluation import quick_evaluation, evaluate_rag_question, ares_score
from src.evaluation.test_cases import create_default_test_cases

# Agent bereitstellen (muss LangChain-Interface unterstützen)
agent = YourRAGAgent()

# Runner erstellen
runner = EvaluationRunner(agent=agent)

# Evaluation durchführen
test_cases = create_default_test_cases()
results = runner.run_complete_evaluation(test_cases)

print(f"Erfolgsrate: {results['statistics']['success_rate']:.2%}")
```

### 3. Single Evaluation

```python
from src.evaluation.ares_evaluator import ARESEvaluator

evaluator = ARESEvaluator()

evaluation = evaluator.evaluate_single(
    query="Welche Master-Programme bietet die WiSo-Fakultät?",
    response="Die WiSo-Fakultät bietet Master in Economics und Business Administration.",
    contexts=["Context from knowledge base..."]
)

print(evaluation)  # {"context_relevance": 0.85, "answer_relevance": 0.78, ...}
```

### 4. Quick Evaluation

```python
from src.evaluation.evaluation_runner import quick_evaluation

questions = [
    "Was sind die Zulassungsvoraussetzungen?",
    "Gibt es internationale Programme?"
]

results = quick_evaluation(agent, questions)
```

## 📊 ARES Metriken

Das System evaluiert drei Hauptmetriken des Stanford ARES Frameworks:

### Context Relevance
- **Beschreibung**: Wie relevant sind die abgerufenen Kontexte für die Anfrage?
- **Bereich**: 0.0 - 1.0
- **Interpretation**: Höhere Werte = bessere Kontext-Auswahl

### Answer Relevance  
- **Beschreibung**: Wie relevant ist die Antwort für die gestellte Frage?
- **Bereich**: 0.0 - 1.0
- **Interpretation**: Höhere Werte = passendere Antworten

### Answer Faithfulness
- **Beschreibung**: Wie treu bleibt die Antwort dem bereitgestellten Kontext?
- **Bereich**: 0.0 - 1.0
- **Interpretation**: Höhere Werte = weniger Halluzinationen

## 🧪 Testfälle

### Standard-Testfälle

Das System enthält 8 vordefinierte Testfälle für WiSo-Domäne:

- **Studienprogramme**: Master-Programme Information
- **Zulassung**: Voraussetzungen und Bewerbung  
- **Forschung**: Forschungsschwerpunkte
- **Services**: Karriere-Services und Support
- **International**: Austauschprogramme
- **Praxis**: Praktika und Partnerschaften
- **Resources**: Technische Ausstattung
- **Komplexe Fragen**: Interdisziplinäre Themen

### Eigene Testfälle

```python
from src.evaluation.test_cases import TestCase

custom_test = TestCase(
    id="custom_test_1",
    question="Ihre Frage hier",
    category="custom",
    expected_answer="Erwartete Antwort (optional)",
    expected_keywords=["Keyword1", "Keyword2"],
    difficulty="medium"
)
```

### JSON-Format

```json
{
  "test_cases": [
    {
      "id": "unique_id",
      "question": "Test question",
      "category": "category_name",
      "expected_answer": "Expected response",
      "expected_keywords": ["keyword1", "keyword2"],
      "context_hint": "Context guidance",
      "difficulty": "easy|medium|hard",
      "metadata": {}
    }
  ]
}
```

## 🔧 Konfiguration

### ARES Evaluator Konfiguration

```python
evaluator = ARESEvaluator(
    # ARES Framework Einstellungen werden automatisch geladen
)
```

### Evaluation Runner Konfiguration

```python
runner = EvaluationRunner(
    agent=your_agent,
    results_dir=Path("custom_results_dir")  # Optional
)
```

## 📈 Ergebnisse

### Ergebnis-Struktur

```json
{
  "metadata": {
    "timestamp": "2024-12-28T...",
    "evaluator": "Stanford_ARES_Framework",
    "version": "1.0.0"
  },
  "statistics": {
    "total_test_cases": 8,
    "successful_responses": 7,
    "failed_responses": 1,
    "success_rate": 0.875,
    "duration_seconds": 45.2,
    "ares_metrics": {
      "context_relevance": 0.82,
      "answer_relevance": 0.78,
      "answer_faithfulness": 0.85
    }
  },
  "test_cases": [...],
  "responses": [...],
  "ares_evaluation": {...}
}
```

### Ergebnis-Speicherung

Ergebnisse werden automatisch gespeichert:

- `evaluation_results_{timestamp}.json`: Vollständige Ergebnisse
- `evaluation_results_latest.json`: Neueste Ergebnisse (Shortcut)

## 🤖 Agent-Integration

### LangChain Agents

```python
# Ihr Agent muss das LangChain Interface unterstützen
class YourRAGAgent:
    def invoke(self, inputs):
        return {
            "output": "Agent response",
            "source_documents": ["context1", "context2"],
            "metadata": {}
        }
```

### Custom Agent Interface

```python
class YourCustomAgent:
    def query(self, question):
        return {
            "answer": "Agent response", 
            "contexts": ["context1", "context2"],
            "metadata": {}
        }
```

## 📋 Verfügbare Scripts

### Demo Script

```bash
# Führe Demo-Evaluationen aus
python scripts/demo_ares_evaluation.py
```

Das Demo-Script zeigt:
- Einzelne Frage Evaluation
- Batch-Evaluation
- Quick-Evaluation
- Testfall-Verwaltung

## 🔍 Debugging

### Logging aktivieren

```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Häufige Probleme

**Problem**: ARES Framework nicht verfügbar
```python
# Fallback auf Mock-Evaluation
evaluation = {
    "context_relevance": 0.0,
    "answer_relevance": 0.0, 
    "answer_faithfulness": 0.0
}
```

**Problem**: Agent Interface nicht kompatibel
```python
# Prüfe verfügbare Methoden
print(dir(your_agent))
# Implementiere entsprechende Wrapper
```

## 🚧 Entwicklung

### Tests ausführen

```bash
python -m pytest tests/test_evaluation.py -v
```

### Neue Metriken hinzufügen

1. Erweitere `ARESEvaluator.evaluate_single()`
2. Update Ergebnis-Struktur in `evaluation_runner.py`
3. Füge Tests hinzu

## 📚 Referenzen

- [Stanford ARES Framework](https://github.com/stanford-futuredata/ARES)
- [ARES Paper](https://arxiv.org/abs/2311.09476)
- [RAG Evaluation Best Practices](https://docs.langchain.com/docs/guides/evaluation)

## 🤝 Migration von alter Evaluation

Die alte ARES-ähnliche Implementierung wurde vollständig durch das echte Stanford ARES Framework ersetzt:

- ✅ `ares-ai` Paket installiert
- ✅ Authentische ARES Metriken
- ✅ Verbesserte Genauigkeit
- ✅ Standardisierte Evaluation
- ✅ Bessere Reproduzierbarkeit

Alle Evaluations-Workflows bleiben kompatibel, nutzen jetzt aber das echte ARES Framework.

---

## Offizielle ARES-API (UES/IDP & PPI) – Nutzung in diesem Projekt

- UES/IDP (LLM-Judge):
  - Aufruf: `ARES(ues_idp=...).ues_idp()`
  - Benötigt: `in_domain_prompts_dataset` (Few-Shot TSV), `unlabeled_evaluation_set` (TSV), `model_choice` (z. B. GPT-3.5)
  - Optional: vLLM (`vllm=True`, `host_url`)

- PPI (LLM-Judge oder Checkpoints):
  - Aufruf: `ARES(ppi=...).evaluate_RAG()`
  - Benötigt: `evaluation_datasets` (TSV). Entweder:
   - LLM-Judge: `few_shot_examples_filepath` + `llm_judge`
   - oder Checkpoints: `checkpoints=[...]` (+ optional `gold_label_path`)

In `ares_evaluator.py` werden automatisch TSVs aus Q/A/Context erzeugt und die Ergebnisse zu `average_scores` und `individual_results` zusammengefasst.

### Beispiel: Single-Evaluation (PPI, LLM-Judge)

```python
from pathlib import Path
from src.evaluation.ares_evaluator import ARESEvaluator

evaluator = ARESEvaluator(
   mode="ppi",
   few_shot_path=Path("src/evaluation/data/ares_few_shot_prompt_for_judge_scoring.tsv"),
   llm_judge_ppi="gpt-3.5-turbo-1106"
)

res = evaluator.evaluate_single_sync(
   query="Welche Master-Programme bietet die WiSo-Fakultät?",
   response="Die WiSo-Fakultät bietet Master in Economics und Business Administration.",
   contexts=["Kontextpassage 1", "Kontextpassage 2"]
)
print(res)
```

### Beispiel: Runner im UES/IDP-Modus

```python
from src.evaluation.evaluation_runner import EvaluationRunner

runner = EvaluationRunner(agent=your_agent, evaluation_mode="ues_idp")
```

### Beispiel-Few-Shot (bereitgestellt)

Eine minimale Few-Shot-Datei liegt unter:
`src/evaluation/data/ares_few_shot_prompt_for_judge_scoring.tsv`

### 2–3 Beispiel-Fragen für deinen Datensatz

1) Frage: "Welche Master-Programme bietet die WiSo-Fakultät an?"
  - Antwort: "Die WiSo-Fakultät bietet Master in Economics, Business Administration und weitere Programme an."
  - Kontext: "Die WiSo-Fakultät bietet verschiedene Master-Programme an ..."

2) Frage: "Wie bewerbe ich mich für ein Masterstudium an der WiSo?"
  - Antwort: "Die Bewerbung erfolgt online über das Bewerbungsportal; Fristen und Anforderungen stehen auf der WiSo-Webseite."
  - Kontext: "Die Bewerbung erfolgt über das Online-Portal der Universität zu Köln ..."

3) (Negativbeispiel) Frage: "Welche Forschungsschwerpunkte hat die WiSo-Fakultät?"
  - Antwort: "Die Mensa öffnet um 11:30 Uhr."  (absichtlich irrelevant)
  - Kontext: "Forschungsschwerpunkte: empirische Wirtschaftsforschung, Verhaltensökonomie, ..."

Hinweis: ARES vergibt Scores pro Beispiel (Kontextrelevanz, Antworttreue, Antwortrelevanz) und bildet daraus aggregierte Kennzahlen.