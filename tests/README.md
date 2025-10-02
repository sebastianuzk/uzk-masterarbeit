# Test-Dokumentation für das RAG-Chatbot-System

## Übersicht

Das Test-System besteht aus vier fokussierten Test-Dateien, die verschiedene Bereiche des RAG-Chatbot-Systems abdecken:

- **Component Tests**: Tests für einzelne Komponenten (Tools, Agent, Scraper)
- **System Tests**: End-to-End Tests des gesamten Systems

## Test-Dateien

| Datei | Beschreibung |
|-------|-------------|
| `test_tools.py` | Tests für alle Tools (Wikipedia, DuckDuckGo, Web-Scraper, RAG) |
| `test_agent.py` | Tests für den React Agent |
| `test_scraper.py` | Tests für das Web-Scraper-System |
| `test_system_.py` | **Vollständige System-Integration-Tests** |

## Testausführung

### Direkte Ausführung (Empfohlen)

Führen Sie Tests direkt mit Python aus:

```bash
# Einzelne Komponenten testen
python tests/test_tools.py
python tests/test_agent.py  
python tests/test_scraper.py

# Vollständiger System-Test
python tests/test_system_.py

# Mit pytest (detaillierte Ausgabe)
python -m pytest tests/test_tools.py -v
python -m pytest tests/test_agent.py -v
python -m pytest tests/test_scraper.py -v
python -m pytest tests/test_system_.py -v

# Alle Tests ausführen
python -m pytest tests/ -v
```

### VS Code Task verwenden

Sie können auch die vordefinierte VS Code Task verwenden:

```bash
# Über VS Code Command Palette: "Tasks: Run Task" → "Run Tests"
# Oder direkt:
python -m pytest tests/ -v
```

## Test-Kategorien

### 1. Komponenten-Tests
- **test_tools.py**: ~10 Sekunden - Unit Tests für alle Tools
- **test_agent.py**: ~20 Sekunden - React Agent Funktionalität  
- **test_scraper.py**: ~30 Sekunden - Web-Scraping System

### 2. System-Test
- **test_system_.py**: 2-5 Minuten - Vollständige End-to-End Integration

## Abhängigkeiten

### Erforderlich für alle Tests:
- Python 3.8+
- Alle Pakete aus `requirements.txt`

### Erforderlich für spezielle Tests:

| Test-Datei | Zusätzliche Anforderungen |
|-----------|--------------------------|
| test_agent.py | Ollama Server läuft |
| test_tools.py (RAG-Tests) | ChromaDB mit Daten verfügbar |
| test_tools.py (externe Tools) | Internet-Verbindung |
| test_scraper.py | Internet-Verbindung |
| test_system_.py | Alle oben genannten |

## Test-Beispiele

### Beispiel 1: Entwicklung - Komponenten testen
```bash
# Während der Entwicklung einzelne Komponenten testen
python tests/test_tools.py
python tests/test_agent.py
```

### Beispiel 2: Feature-Testing
```bash
# RAG-System spezifisch testen
python -m pytest tests/test_tools.py::TestTools::test_rag_search -v -s

# Agent spezifisch testen
python -m pytest tests/test_agent.py::TestReactAgent::test_simple_chat -v -s
```

### Beispiel 3: Integration vor Deployment
```bash
# Vollständige System-Validation
python tests/test_system_.py
```

### Beispiel 4: Alle Tests für Release
```bash
# Komplett-Test aller Komponenten
python -m pytest tests/ -v
```

## Fehlerdiagnose

### Häufige Probleme und Lösungen:

#### 1. "Ollama-Server nicht erreichbar"
```bash
# Lösung: Ollama starten
ollama serve
# Oder Agent-Tests überspringen:
python -m pytest tests/test_tools.py tests/test_scraper.py -v
```

#### 2. "ChromaDB nicht verfügbar"
```bash
# Lösung: RAG-System initialisieren (siehe README.md)
# Oder RAG-Tests überspringen:
python -m pytest tests/test_tools.py -v -k "not rag"
```

#### 3. "Internet-Verbindung nicht verfügbar"
```bash
# Tests werden automatisch übersprungen, aber für vollständige Tests:
# Internet-Verbindung herstellen und erneut ausführen
```

#### 4. Import-Fehler
```bash
# Python-Pfad Problem, versuchen Sie:
cd /path/to/uzk-masterarbeit
python tests/test_tools.py
```

## Entwickler-Workflow

### Empfohlene Test-Reihenfolge während der Entwicklung:

```bash
# 1. Schnelle Komponenten-Tests (täglich)
python tests/test_tools.py
python tests/test_agent.py

# 2. Scraper-Tests (bei Scraper-Änderungen)
python tests/test_scraper.py

# 3. System-Tests (vor wichtigen Commits)
python tests/test_system_.py

# 4. Alle Tests (vor Release)
python -m pytest tests/ -v
```

## Test-Ergebnisse interpretieren

### Erfolgreiche Ausführung:
```
...
----------------------------------------------------------------------
Ran X tests in Y.YYYs

OK
```

### Fehlgeschlagene Tests:
```
...
======================================================================
FAIL: test_example (tests.test_tools.TestTools.test_example)
----------------------------------------------------------------------
...
FAILED (failures=1)
```

### Tests übersprungen:
```
...
test_example ... skipped 'Ollama-Server nicht erreichbar'
...
```

## Weitere Informationen

- Tests sind so designed, dass sie bei fehlenden Abhängigkeiten übersprungen werden
- Alle Tests können offline ausgeführt werden (außer externe Tool-Tests)
- Tests erstellen temporäre Dateien, die automatisch gelöscht werden
- Bei Problemen: Siehe detaillierte Fehlerausgabe und Haupt-README.md