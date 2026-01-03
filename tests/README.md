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

## Agent-Modi

Die Tests unterstützen sowohl den **Single-Agent** als auch den **Multi-Agent** Modus.
Standardmäßig wird der Single-Agent verwendet.

```bash
# Single-Agent (Standard)
pytest tests/ -v

# Multi-Agent
pytest tests/ -v --agent-mode=multi
```

## Tests ausführen

### ⚡ Schnelle Tests (Empfohlen)
```bash
# Single-Agent (Standard)
pytest tests/ -v -m "not slow"

# Multi-Agent
pytest tests/ -v -m "not slow" --agent-mode=multi
```

### 🐌 Alle Tests (inkl. langsame LLM-Tests)
```bash
# Single-Agent
pytest tests/ -v

# Multi-Agent
pytest tests/ -v --agent-mode=multi
```

### 🎯 Spezifische Test-Kategorien
```bash
# Nur Unit-Tests
pytest tests/unit/ -v

# Nur Integration-Tests (Single-Agent)
pytest tests/integration/ -v

# Nur Integration-Tests (Multi-Agent)
pytest tests/integration/ -v --agent-mode=multi

# Nur LLM-Tests (schnelle)
pytest tests/llm/ -v -m "not slow"

# Nur langsame Tests
pytest tests/ -v -m "slow"

# Nur Agent-Tests
pytest tests/ -v -m "agent"

# Spezifischer Test
pytest tests/integration/test_agent.py::TestAgentInitialization::test_agent_initialization -v
```

### 📊 Evaluierung
```bash
# Evaluierung mit Single-Agent
python -m tests.eval.run_evaluation

# Evaluierung mit Multi-Agent
python -m tests.eval.run_evaluation --agent-mode=multi
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
