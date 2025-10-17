# Test-Dokumentation

Umfassende Test-Suite für den Autonomen Chatbot-Agenten mit LangChain und LangGraph.

## 📁 Test-Struktur

```
tests/
├── unit/                           # Unit Tests (isolierte Komponenten)
│   ├── test_tools.py              # Tests für einzelne Tools
│   ├── test_scraper_components.py # Tests für Scraper-Komponenten
│   └── test_scraper.py            # Tests für Scraper-System
├── integration/                    # Integration Tests (Zusammenspiel)
│   ├── test_agent.py              # Tests für React Agent
│   ├── test_system_.py            # Tests für System-Integration
│   └── test_enhanced_pipeline.py  # Tests für Scraper-Pipeline
├── llm/                           # LLM Quality Tests (Modell-Qualität)
│   ├── test_response_quality.py   # Tests für Antwort-Qualität
│   └── test_rag_quality.py        # Tests für RAG-basierte Antworten
├── __init__.py
├── conftest.py                    # Pytest Konfiguration & Fixtures
└── pytest.ini                     # Pytest Einstellungen
```

## 🎯 Test-Kategorien

### 1. Unit Tests (`tests/unit/`)
Testen einzelne Komponenten isoliert ohne externe Dependencies.

**Dateien:**
- `test_tools.py`: Web Scraper, DuckDuckGo, RAG Tool, E-Mail Tool
- `test_scraper_components.py`: URL Cache, Content Deduplicator, PDF Extractor, etc.
- `test_scraper.py`: Scraper-Importe und grundlegende Funktionalität

**Ausführen:**
```bash
pytest tests/unit/ -v
```

### 2. Integration Tests (`tests/integration/`)
Testen das Zusammenspiel mehrerer Komponenten.

**Dateien:**
- `test_agent.py`: React Agent Initialisierung, Memory, Tool-Integration
- `test_system_.py`: System-weite Integration, Fehlerbehandlung
- `test_enhanced_pipeline.py`: Scraper-Pipeline, Vector DB, RAG Integration

**Ausführen:**
```bash
pytest tests/integration/ -v
```

### 3. LLM Quality Tests (`tests/llm/`) ⭐ NEU
Testen die Qualität und Korrektheit der LLM-Antworten.

**Dateien:**
- `test_response_quality.py`: Allgemeine Antwort-Qualität
- `test_rag_quality.py`: RAG-spezifische Qualität

**Ausführen:**
```bash
pytest tests/llm/ -v
```

## 📊 LLM Test-Übersicht

### Test Response Quality (`test_response_quality.py`)

#### Faktentreue Tests
- ✅ `test_university_name_accuracy` - Korrekte Verwendung "Universität zu Köln"
- ✅ `test_faculty_name_accuracy` - Korrekte Verwendung "WiSo-Fakultät"
- ✅ `test_no_hallucination_on_unknown_info` - Keine Halluzinationen bei unbekannten Infos

#### Relevanz Tests
- ✅ `test_relevance_for_study_program_query` - Relevante Begriffe bei Studiengangsfragen
- ✅ `test_no_off_topic_response` - Keine Off-Topic Antworten

#### Antwortformat Tests
- ✅ `test_response_not_empty` - Antworten nicht leer
- ✅ `test_response_reasonable_length` - Vernünftige Antwortlänge (20-2000 Zeichen)
- ✅ `test_response_is_german` - Deutsche Antworten auf deutsche Fragen
- ✅ `test_urls_are_included_when_using_tools` - URLs werden mitgeliefert

#### Konsistenz Tests
- ✅ `test_consistent_answers_on_repeated_questions` - Konsistente Antworten

#### Konversationsfluss Tests
- ✅ `test_maintains_context_in_conversation` - Kontext wird beibehalten
- ✅ `test_friendly_greeting_response` - Freundliche Begrüßungen
- ✅ `test_no_unnecessary_tool_use_for_greetings` - Keine Tools bei Smalltalk

### Test RAG Quality (`test_rag_quality.py`)

#### RAG Nutzung Tests
- ✅ `test_uses_rag_for_university_questions` - RAG wird bei Uni-Fragen verwendet
- ✅ `test_rag_provides_source_urls` - Quellen-URLs werden geliefert

#### RAG Daten-Qualität Tests
- ✅ `test_rag_returns_relevant_documents` - Relevante Dokumente
- ✅ `test_rag_returns_multiple_sources` - Mehrere Quellen
- ✅ `test_rag_empty_query_handling` - Umgang mit leeren Queries

#### Kategorie-spezifische Tests
- ✅ `test_rag_studium_category_accuracy` - Studiums-Kategorie
- ✅ `test_rag_bewerbung_category_accuracy` - Bewerbungs-Kategorie
- ✅ `test_rag_services_category_accuracy` - Service-Kategorie

#### Antwort-Integration Tests
- ✅ `test_agent_integrates_rag_naturally` - Natürliche Integration
- ✅ `test_agent_combines_rag_with_reasoning` - Kombination mit Reasoning

#### Fehlerbehandlung Tests
- ✅ `test_handles_no_rag_results_gracefully` - Umgang mit fehlenden Ergebnissen
- ✅ `test_doesnt_confuse_categories` - Keine Kategorie-Verwechslungen

#### Performance Tests
- ⏱️ `test_rag_response_time_reasonable` - Response-Zeit < 30s
- ⏱️ `test_multiple_rag_queries_stable` - Mehrere Queries stabil

## 🚀 Test-Ausführung

### Alle Tests ausführen
```bash
pytest
```

### Spezifische Test-Kategorien
```bash
# Nur Unit Tests
pytest tests/unit/ -v

# Nur Integration Tests
pytest tests/integration/ -v

# Nur LLM Tests
pytest tests/llm/ -v
```

### Mit Markern
```bash
# Nur schnelle Tests (ohne slow marker)
pytest -m "not slow"

# Nur LLM Tests
pytest -m llm

# Nur Unit Tests
pytest -m unit
```

### Einzelne Test-Dateien
```bash
# Response Quality Tests
pytest tests/llm/test_response_quality.py -v

# RAG Quality Tests
pytest tests/llm/test_rag_quality.py -v
```

### Einzelne Tests
```bash
# Spezifischer Test
pytest tests/llm/test_response_quality.py::TestLLMResponseQuality::test_university_name_accuracy -v
```

## ⚙️ Test-Konfiguration

### pytest.ini
Zentrale pytest-Konfiguration:
- Test Discovery Patterns
- Marker Definitionen
- Output-Formatierung
- Asyncio-Mode

### conftest.py
Globale Fixtures und Hooks:
- `project_root_path` - Projekt-Root Pfad
- `ollama_available` - Prüft Ollama-Verfügbarkeit
- `vector_db_available` - Prüft Vector DB-Verfügbarkeit
- Auto-Marker basierend auf Test-Pfad

## 📋 Voraussetzungen

### Für alle Tests
- Python 3.8+
- Installierte Dependencies (`pip install -r requirements.txt`)

### Für Integration Tests
- Ollama läuft (`ollama serve`)
- Modell geladen (`ollama pull llama3.1:8b`)

### Für LLM Tests
- Ollama läuft mit Modell
- Vector Database vorhanden (`data/vector_db/`)
- Mindestens eine Collection mit Daten

## 🔍 Test-Strategien

### LLM Quality Testing
Die LLM Tests verwenden verschiedene Strategien:

1. **Assertions**: Überprüfung von erwarteten Mustern
   ```python
   assert "Universität zu Köln" in response
   ```

2. **Keyword-Matching**: Suche nach relevanten Begriffen
   ```python
   relevant_terms = ["master", "studium", "programm"]
   found_terms = sum(1 for term in relevant_terms if term in response.lower())
   assert found_terms >= 2
   ```

3. **Warnings statt Failures**: Bei unsicheren Kriterien
   ```python
   if not has_url:
       print(f"⚠️  Warnung: Keine URL gefunden")
   ```

4. **Context Management**: Tests mit sauberem State
   ```python
   agent.clear_memory()  # Sauberer Start für jeden Test
   ```

## 📈 Coverage

### Coverage aktivieren
Uncomment in `pytest.ini`:
```ini
addopts = --cov=src --cov-report=html --cov-report=term
```

### Coverage-Report generieren
```bash
pytest --cov=src --cov-report=html
```

Report öffnen:
```bash
open htmlcov/index.html
```

## 🐛 Debugging

### Verbose Output
```bash
pytest -vv
```

### Zeige Print-Statements
```bash
pytest -s
```

### Stoppe bei erstem Fehler
```bash
pytest -x
```

### Zeige volle Tracebacks
```bash
pytest --tb=long
```

### Debug-Modus
```bash
pytest --pdb
```

## 📊 CI/CD Integration

Die Tests sind in der GitHub Actions Pipeline integriert:
```yaml
- name: Run tests
  run: |
    python -m pytest tests/ -v
```

### Schnelle Tests für CI
```bash
# Ohne langsame LLM Tests
pytest -m "not slow" -v
```

## 💡 Best Practices

### Test-Isolation
- Jeder Test sollte unabhängig sein
- `agent.clear_memory()` zwischen Tests
- Keine shared state zwischen Tests

### Test-Naming
- Beschreibende Namen: `test_university_name_accuracy`
- Prefix `test_` für Test-Funktionen
- Prefix `Test` für Test-Klassen

### Assertions
- Klare, spezifische Assertions
- Hilfreiche Fehlermeldungen
- Kein `assert True` oder leere Tests

### Fixtures
- Verwende Fixtures für Setup/Teardown
- Scope wählen: `function`, `class`, `module`, `session`
- Cleanup in Fixtures

## 🔧 Troubleshooting

### Ollama nicht erreichbar
```
SKIPPED [1] Ollama-Server nicht erreichbar
```
**Lösung**: `ollama serve` starten

### Vector DB nicht gefunden
```
SKIPPED [1] Vector DB nicht verfügbar
```
**Lösung**: Pipeline ausführen: `python src/scraper/crawler_scraper_pipeline.py`

### Tests zu langsam
```bash
# Nur schnelle Tests
pytest -m "not slow"
```

### Import-Fehler
```python
ModuleNotFoundError: No module named 'src'
```
**Lösung**: `sys.path.insert(0, project_root)` in Tests oder PYTHONPATH setzen

## 📚 Weitere Ressourcen

- [pytest Dokumentation](https://docs.pytest.org/)
- [LangChain Testing Guide](https://python.langchain.com/docs/guides/testing)
- [Testing LLM Applications](https://eugeneyan.com/writing/llm-testing/)

---

**Version**: 1.0  
**Letztes Update**: Oktober 2025  
**Status**: ✅ Produktionsbereit
