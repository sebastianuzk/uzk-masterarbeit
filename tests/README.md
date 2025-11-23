# Test Setup

## Voraussetzungen

### Ollama Modelle

Die Tests verwenden `llama3.2:3b` für Balance zwischen Geschwindigkeit und Qualität.

```bash
# Lade das Test-Modell herunter
ollama pull llama3.2:3b
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

### ⚡ Schnelle Tests (Empfohlen)
```bash
# Alle Tests OHNE langsame LLM-Tests (~30-40 Sekunden)
pytest tests/ -v -m "not slow"
```

### 🐌 Alle Tests (inkl. langsame LLM-Tests)
```bash
# Alle Tests inkl. langsame Tests (2-5 Minuten)
pytest tests/ -v
```

### 🎯 Spezifische Test-Kategorien
```bash
# Nur Unit-Tests
pytest tests/unit/ -v

# Nur Integration-Tests
pytest tests/integration/ -v

# Nur LLM-Tests (schnelle)
pytest tests/llm/ -v -m "not slow"

# Nur langsame Tests
pytest tests/ -v -m "slow"

# Spezifischer Test
pytest tests/integration/test_agent.py::TestReactAgent::test_simple_chat -v
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
- Markiert mit `@pytest.mark.slow` für langsame Tests

## Test-Marker

- `@pytest.mark.slow`: Langsame Tests (LLM-Interaktionen), standardmäßig übersprungen
- `@pytest.mark.integration`: Integration-Tests
- `@pytest.mark.unit`: Unit-Tests
- `@pytest.mark.llm`: LLM-Qualitäts-Tests

## Performance-Hinweise

- **Schnelle Tests**: ~30-40 Sekunden (35 Tests)
- **Alle Tests**: ~2-5 Minuten (44 Tests)
- **Test-Modell**: `llama3.2:3b` (guter Kompromiss zwischen Geschwindigkeit und Qualität)
- **Context-Size**: Automatisch angepasst (2048 für 3b-Modell)
