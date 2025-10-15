# Test-Dokumentation für das RAG-Chatbot-System

## Übersicht

Das Test-System besteht aus vier fokussierten Test-Dateien, die verschiedene Bereiche des RAG-Chatbot-Systems abdecken:

- **Component Tests**: Tests für einzelne Komponenten (Tools, Agent, Scraper)
- **System Tests**: End-to-End Tests des gesamten Systems

## Test-Dateien

| Datei | Beschreibung |
|-------|-------------|
| `test_tools.py` | Tests für alle Tools (DuckDuckGo, Web-Scraper, RAG) |
| `test_agent.py` | Tests für den React Agent |
| `test_scraper.py` | Tests für das Web-Scraper-System |
| `test_system_.py` | **Vollständige System-Integration-Tests** |

## Testausführung

### Wichtiger Hinweis zur Umgebung

Sie haben zwei Möglichkeiten, die Tests auszuführen:

1. **Mit venv "Masterarbeit"** (Empfohlen) - Alle Abhängigkeiten sind in der venv installiert
2. **Ohne venv** - Abhängigkeiten müssen global installiert sein

### Option 1: Mit virtueller Umgebung "Masterarbeit" (Empfohlen)

**Direkte Ausführung mit venv-Interpreter:**

```bash
# Einzelne Komponenten testen
& "Masterarbeit\Scripts\python.exe" tests\test_tools.py
& "Masterarbeit\Scripts\python.exe" tests\test_agent.py  
& "Masterarbeit\Scripts\python.exe" tests\test_scraper.py

# Vollständiger System-Test
& "Masterarbeit\Scripts\python.exe" tests\test_system_.py

# Mit pytest (detaillierte Ausgabe)
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_tools.py -v
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_agent.py -v
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_scraper.py -v
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_system_.py -v

# Alle Tests ausführen
& "Masterarbeit\Scripts\python.exe" -m pytest tests\ -v
```

**Oder venv aktivieren und dann kurze Commands verwenden:**

```bash
# Venv aktivieren
Masterarbeit\Scripts\Activate.ps1

# Dann normale Commands verwenden
python tests\test_tools.py
python tests\test_agent.py
python -m pytest tests\test_agent.py -v
python -m pytest tests\ -v
```

### Option 2: Ohne virtuelle Umgebung

Falls Sie die Tests ohne venv ausführen möchten (stellen Sie sicher, dass alle Dependencies installiert sind):

```bash
# Einzelne Komponenten testen
python tests\test_tools.py
python tests\test_agent.py  
python tests\test_scraper.py

# Vollständiger System-Test
python tests\test_system_.py

# Mit pytest (detaillierte Ausgabe)
python -m pytest tests\test_tools.py -v
python -m pytest tests\test_agent.py -v
python -m pytest tests\test_scraper.py -v
python -m pytest tests\test_system_.py -v

# Alle Tests ausführen
python -m pytest tests\ -v
```

**Hinweis**: Bei Option 2 müssen alle Abhängigkeiten global installiert sein (`pip install -r requirements.txt`).

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

**Mit venv:**
```bash
# Während der Entwicklung einzelne Komponenten testen
& "Masterarbeit\Scripts\python.exe" tests\test_tools.py
& "Masterarbeit\Scripts\python.exe" tests\test_agent.py
```

**Ohne venv:**
```bash
python tests\test_tools.py
python tests\test_agent.py
```

### Beispiel 2: Feature-Testing

**Mit venv:**
```bash
# RAG-System spezifisch testen
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_tools.py::TestTools::test_rag_search -v -s

# Agent spezifisch testen
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_agent.py::TestReactAgent::test_simple_chat -v -s
```

**Ohne venv:**
```bash
python -m pytest tests\test_tools.py::TestTools::test_rag_search -v -s
python -m pytest tests\test_agent.py::TestReactAgent::test_simple_chat -v -s
```

### Beispiel 3: Integration vor Deployment

**Mit venv:**
```bash
# Vollständige System-Validation
& "Masterarbeit\Scripts\python.exe" tests\test_system_.py
```

**Ohne venv:**
```bash
python tests\test_system_.py
```

### Beispiel 4: Alle Tests für Release

**Mit venv:**
```bash
# Komplett-Test aller Komponenten
& "Masterarbeit\Scripts\python.exe" -m pytest tests\ -v
```

**Ohne venv:**
```bash
python -m pytest tests\ -v
```

## Fehlerdiagnose

### Häufige Probleme und Lösungen:

#### 1. "Ollama-Server nicht erreichbar"

**Mit venv:**
```bash
# Lösung: Ollama starten
ollama serve
# Oder Agent-Tests überspringen:
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_tools.py tests\test_scraper.py -v
```

**Ohne venv:**
```bash
ollama serve
# Oder Agent-Tests überspringen:
python -m pytest tests\test_tools.py tests\test_scraper.py -v
```

#### 2. "ChromaDB nicht verfügbar"

**Mit venv:**
```bash
# Lösung: RAG-System initialisieren (siehe README.md)
# Oder RAG-Tests überspringen:
& "Masterarbeit\Scripts\python.exe" -m pytest tests\test_tools.py -v -k "not rag"
```

**Ohne venv:**
```bash
python -m pytest tests\test_tools.py -v -k "not rag"
```

#### 3. "Internet-Verbindung nicht verfügbar"
```bash
# Tests werden automatisch übersprungen, aber für vollständige Tests:
# Internet-Verbindung herstellen und erneut ausführen
```

#### 4. Import-Fehler

**Mit venv:**
```bash
# Python-Pfad Problem, versuchen Sie:
cd D:\Uni-Köln\Masterarbeit\Software\uzk-masterarbeit
& "Masterarbeit\Scripts\python.exe" tests\test_tools.py
```

**Ohne venv:**
```bash
# Abhängigkeiten installieren:
pip install -r requirements.txt
# Dann erneut versuchen:
python tests\test_tools.py
```

## Entwickler-Workflow

### Empfohlene Test-Reihenfolge während der Entwicklung:

**Mit venv "Masterarbeit":**
```bash
# 1. Schnelle Komponenten-Tests (täglich)
& "Masterarbeit\Scripts\python.exe" tests\test_tools.py
& "Masterarbeit\Scripts\python.exe" tests\test_agent.py

# 2. Scraper-Tests (bei Scraper-Änderungen)
& "Masterarbeit\Scripts\python.exe" tests\test_scraper.py

# 3. System-Tests (vor wichtigen Commits)
& "Masterarbeit\Scripts\python.exe" tests\test_system_.py

# 4. Alle Tests (vor Release)
& "Masterarbeit\Scripts\python.exe" -m pytest tests\ -v
```

**Ohne venv:**
```bash
# 1. Schnelle Komponenten-Tests (täglich)
python tests\test_tools.py
python tests\test_agent.py

# 2. Scraper-Tests (bei Scraper-Änderungen)
python tests\test_scraper.py

# 3. System-Tests (vor wichtigen Commits)
python tests\test_system_.py

# 4. Alle Tests (vor Release)
python -m pytest tests\ -v
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