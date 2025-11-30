# RAGAS Evaluation für WiSo RAG System

Dieses Verzeichnis enthält die RAGAS-basierte Evaluation des WiSo RAG-Systems.

## 📁 Struktur

```
src/evaluation/
├── ragas_evaluation.py          # Hauptskript für RAGAS-Evaluation
├── data/                         # Test-Datensätze
│   ├── ares_unlabeled_evaluation.tsv    # 10 Q/A/Kontext-Triplets
│   ├── ares_few_shot_examples.csv       # Annotierte Beispiele
│   └── ragas_results.csv               # Evaluation-Ergebnisse (generiert)
└── README.md                     # Diese Datei
```

## 🚀 Schnellstart

### 1. RAGAS installieren

```bash
pip install ragas langchain-ollama
```

### 2. Ollama starten

Stelle sicher, dass Ollama läuft:

```bash
ollama serve
```

### 3. Evaluation durchführen

```bash
python src/evaluation/ragas_evaluation.py
```

## 📊 RAGAS Metriken

Das Skript evaluiert 3 Kernmetriken:

### 1. **Faithfulness** (Treue)
- **Frage**: Ist die Antwort treu zum abgerufenen Kontext?
- **Berechnung**: Überprüft, ob alle Aussagen in der Antwort durch den Kontext gestützt werden
- **Score**: 0.0 (untreu) bis 1.0 (völlig treu)

### 2. **Answer Relevancy** (Antwort-Relevanz)
- **Frage**: Ist die Antwort relevant zur gestellten Frage?
- **Berechnung**: Misst semantische Ähnlichkeit zwischen Frage und Antwort
- **Score**: 0.0 (irrelevant) bis 1.0 (sehr relevant)

### 3. **Context Precision** (Kontext-Präzision)
- **Frage**: Sind die abgerufenen Kontexte präzise für die Frage?
- **Berechnung**: Überprüft, ob relevante Kontexte höher gerankt sind als irrelevante
- **Score**: 0.0 (unpräzise) bis 1.0 (sehr präzise)

## 📈 Ergebnisse interpretieren

Nach der Evaluation werden folgende Ergebnisse angezeigt:

```
📊 RAGAS EVALUATION ERGEBNISSE
================================================================

📈 Durchschnittliche Scores:
----------------------------------------------------------------
faithfulness             : 0.856
answer_relevancy         : 0.723
context_precision        : 0.612

================================================================
```

**Interpretation:**
- **> 0.8**: Exzellent
- **0.6 - 0.8**: Gut
- **0.4 - 0.6**: Verbesserungsbedürftig
- **< 0.4**: Schlecht

## 🔧 Konfiguration

### Ollama-Modell ändern

Bearbeite `config/settings.py`:

```python
OLLAMA_MODEL = "qwen3:8b"  # Oder ein anderes Modell
```

### Test-Daten anpassen

Die Test-Daten liegen in `data/ares_unlabeled_evaluation.tsv`:

```tsv
Question	Answer	Document	ID
Welche Studienbereiche...	Der Menüpunkt...	Den Studierenden...	eval_1
```

Format:
- **Question**: Die Frage an das RAG-System
- **Answer**: Die generierte Antwort
- **Document**: Der abgerufene Kontext
- **ID**: Eindeutige ID

## 📚 RAGAS Dokumentation

- **Offizielle Docs**: https://docs.ragas.io/
- **Quickstart**: https://docs.ragas.io/en/latest/getstarted/quickstart/
- **Metriken**: https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
- **Ollama Integration**: https://docs.ragas.io/en/latest/howtos/customizations/customize_models/

## 🆚 RAGAS vs. ARES

| Aspekt | RAGAS | ARES |
|--------|-------|------|
| **Installation** | `pip install ragas` | Komplex (vLLM/GPU benötigt) |
| **Ollama Support** | ✅ Nativ | ❌ Nur mit vLLM |
| **Python 3.13** | ✅ Kompatibel | ⚠️ NumPy-Konflikt |
| **Metriken** | 7+ Metriken | 3 Metriken |
| **Entwicklung** | Aktiv (Nov 2024) | Stagniert (Mar 2024) |
| **GPU Bedarf** | ❌ Nicht benötigt | ✅ Für vLLM erforderlich |
| **Wissenschaftlich** | ✅ Etabliert | ✅ Etabliert |

**Fazit**: RAGAS ist besser geeignet für ressourcenbeschränkte Setups und bietet mehr Funktionalität.

## 🐛 Troubleshooting

### Fehler: "Connection refused"

**Problem**: Ollama läuft nicht.

**Lösung**:
```bash
ollama serve
```

### Fehler: "Module not found: ragas"

**Problem**: RAGAS nicht installiert.

**Lösung**:
```bash
pip install ragas langchain-ollama
```

### Fehler: "Model not found"

**Problem**: Das Ollama-Modell ist nicht heruntergeladen.

**Lösung**:
```bash
ollama pull qwen3:8b  # Oder dein konfiguriertes Modell
```

## 📝 Zitierung

Wenn du RAGAS in deiner Masterarbeit verwendest:

```bibtex
@software{ragas2024,
  title = {RAGAS: Evaluation framework for Retrieval Augmented Generation},
  author = {Exploding Gradients},
  year = {2024},
  url = {https://github.com/explodinggradients/ragas},
  note = {Version 0.2.x}
}
```

## 🤝 Support

- **RAGAS Discord**: https://discord.gg/5djav8GGNZ
- **GitHub Issues**: https://github.com/explodinggradients/ragas/issues
- **Office Hours**: https://cal.com/team/vibrantlabs/office-hours
