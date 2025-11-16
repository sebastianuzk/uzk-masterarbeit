# Test Setup

## Voraussetzungen

### Ollama Modelle

Die Tests verwenden das extrem schnelle `qwen2.5:0.5b` Modell (nur 397MB!) für schnellste Testausführung.

```bash
# Lade das Test-Modell herunter
ollama pull qwen2.5:0.5b
```

### Ollama Server

Stelle sicher, dass Ollama läuft:

```bash
# Prüfe ob Ollama läuft
curl http://localhost:11434/api/tags

# Falls nicht, starte Ollama
ollama serve
```

## Tests ausführen

```bash
# Alle Tests
pytest tests/

# Nur Unit-Tests
pytest tests/unit/

# Nur Integration-Tests
pytest tests/integration/

# Nur LLM-Tests
pytest tests/llm/

# Spezifischer Test
pytest tests/integration/test_agent.py::TestReactAgent::test_simple_chat

# Ohne langsame LLM-Tests (schnellste Option!)
pytest tests/ -m "not llm" -v

# Mit Ausgabe
pytest tests/ -v

# Mit Fehlerdetails
pytest tests/ -v --tb=short
```

## Test-Kategorien

### Unit Tests (`tests/unit/`)
- Scraper-Komponenten
- Tool-Funktionalität
- Einzelne Module

### Integration Tests (`tests/integration/`)
- Agent-System
- Tool-Integration
- End-to-End Workflows

### LLM Tests (`tests/llm/`)
- RAG-Qualität
- Response-Qualität
- Verwendet kleines `llama3.2:1b` Modell

## Hinweis

Alle LLM-basierten Tests verwenden automatisch das winzige `qwen2.5:0.5b` Modell (397MB) für extrem schnelle Ausführung statt des Standard `llama3.1:8b` Modells (4.7GB). Das ist **12x kleiner** und **deutlich schneller**!
