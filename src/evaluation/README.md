# RAG-Evaluation Setup

Dieses Verzeichnis enthält umfassende Evaluation-Tools für das RAG-System des autonomen Chatbots.

## 📋 Überblick

### 1. RAGAS-basierte Evaluation (`rag_evaluation.py`)
- **Zweck**: Wissenschaftlich validierte RAG-Bewertung
- **Metriken**: 
  - Context Precision (Präzision der abgerufenen Kontexte)
  - Context Recall (Vollständigkeit der abgerufenen Kontexte)
  - Faithfulness (Treue der Antwort zum Kontext)
  - Answer Relevancy (Relevanz der Antwort zur Frage)
  - Context Relevancy (Relevanz des Kontexts zur Frage)
- **Besonderheiten**: Automatische Ground Truth Generierung, gewichteter Gesamtscore

### 2. Erweiterte Evaluation (`extended_rag_evaluation.py`)
- **Zweck**: Universitätsspezifische und Performance-Metriken
- **Analysen**:
  - Response Time Performance
  - Domain Coverage (Bewerbung, Prüfungen, International, etc.)
  - Konsistenz bei ähnlichen Fragen
  - Quellenqualitäts-Analyse
- **Besonderheiten**: Fachbereichsspezifische Tests, Konsistenz-Scoring

## 🚀 Installation

```bash
# RAGAS-Dependencies installieren
pip install ragas datasets

# Optional: Für erweiterte Metriken
pip install scikit-learn matplotlib seaborn
```

## 📊 Verwendung

### Terminal-Ausführung

```bash
# RAGAS-Evaluation
python src/evaluation/rag_evaluation.py

# Erweiterte Evaluation  
python src/evaluation/extended_rag_evaluation.py

# Beide nacheinander
python src/evaluation/rag_evaluation.py && python src/evaluation/extended_rag_evaluation.py
```

### Programmatische Verwendung

```python
# RAGAS-Evaluation
from src.evaluation.rag_evaluation import RAGEvaluator
import asyncio

async def run_ragas():
    evaluator = RAGEvaluator()
    results = await evaluator.run_evaluation()
    evaluator.print_summary()
    return results

# Erweiterte Evaluation
from src.evaluation.extended_rag_evaluation import ExtendedRAGEvaluator

def run_extended():
    evaluator = ExtendedRAGEvaluator()
    results = evaluator.run_full_evaluation()
    evaluator.print_extended_summary(results)
    return results
```

## 📁 Ausgaben

### Automatisch generierte Dateien:
- `rag_evaluation_results_YYYYMMDD_HHMMSS.json` - RAGAS-Ergebnisse
- `extended_rag_evaluation_YYYYMMDD_HHMMSS.json` - Erweiterte Ergebnisse

### JSON-Format Beispiel:
```json
{
  "timestamp": "2025-11-06T14:30:00",
  "model": "llama3.1:8b",
  "dataset_size": 8,
  "metrics": {
    "context_precision": 0.85,
    "context_recall": 0.78,
    "faithfulness": 0.82,
    "answer_relevancy": 0.79,
    "context_relevancy": 0.81
  },
  "overall_score": 0.810,
  "detailed_results": {
    "strengths": ["Hohe context_precision: 0.850"],
    "weaknesses": ["Niedrige context_recall: 0.780"],
    "recommendations": ["Erhöhung der Anzahl abgerufener Dokumente"]
  }
}
```

## 🎯 Interpretation der Ergebnisse

### RAGAS-Metriken:
- **🟢 Gut**: ≥ 0.8
- **🟡 Akzeptabel**: 0.6 - 0.8  
- **🔴 Verbesserungsbedarf**: < 0.6

### Empfohlene Aktionen:
- **Context Precision niedrig**: Bessere Embedding-Modelle, Retrieval-Tuning
- **Context Recall niedrig**: Mehr Dokumente abrufen, bessere Chunking-Strategie
- **Faithfulness niedrig**: Prompt-Engineering, Halluzination-Reduktion
- **Answer Relevancy niedrig**: Bessere Antwortgenerierung, Kontext-Integration

## 🔧 Konfiguration

### Test-Dataset anpassen:
Bearbeiten Sie die `_create_test_dataset()` Methode in `rag_evaluation.py`:

```python
def _create_test_dataset(self) -> List[Dict[str, str]]:
    return [
        {
            "question": "Ihre spezifische Frage",
            "ground_truth": "Erwartete Antwort",
            "topic": "kategorie"
        },
        # Weitere Test-Cases...
    ]
```

### Domain-Coverage erweitern:
Bearbeiten Sie `domain_questions` in `extended_rag_evaluation.py`:

```python
domain_questions = {
    'ihr_fachbereich': [
        "Frage 1 für Ihren Bereich",
        "Frage 2 für Ihren Bereich"
    ]
}
```

## 🔄 Integration in CI/CD

### GitHub Actions Beispiel:
```yaml
- name: Run RAG Evaluation
  run: |
    python src/evaluation/rag_evaluation.py
    python src/evaluation/extended_rag_evaluation.py
```

### Automatische Reports:
Die JSON-Outputs können für automatische Performance-Monitoring und Regressions-Tests verwendet werden.

## 🐛 Troubleshooting

### Häufige Probleme:

1. **RAGAS Import-Fehler**:
   ```bash
   pip install ragas datasets
   ```

2. **Ollama nicht erreichbar**:
   ```bash
   ollama serve
   ```

3. **ChromaDB nicht gefunden**:
   - Stellen Sie sicher, dass der Web-Scraper bereits gelaufen ist
   - Prüfen Sie `src/scraper/vector_db/` und `data/vector_db/`

4. **Langsame Evaluation**:
   - Reduzieren Sie die Anzahl der Test-Cases
   - Verwenden Sie ein kleineres Ollama-Modell

### Debug-Modus:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Erweiterungen

### Weitere Metriken hinzufügen:
1. Erstellen Sie eine neue Evaluation-Klasse
2. Implementieren Sie spezifische Metriken
3. Integrieren Sie in `__init__.py`

### Custom Scoring:
```python
def custom_metric(question: str, answer: str, context: str) -> float:
    # Ihre Bewertungslogik
    return score
```