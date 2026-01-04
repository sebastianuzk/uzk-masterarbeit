# VS Code Tasks Configuration

Diese Tasks sind für Unix-basierte Systeme (Linux, macOS) optimiert.

## Windows-Kompatibilität

Die Tasks verwenden den `source` Befehl zum Aktivieren der virtuellen Umgebung, was auf Windows nicht funktioniert.

### Für Windows-Nutzer:

Bitte passen Sie die Tasks in `tasks.json` wie folgt an:

**Original (Unix/Linux/macOS):**
```json
"command": "source .venv/bin/activate && python main.py"
```

**Für Windows PowerShell:**
```json
"command": ".venv\\Scripts\\Activate.ps1; python main.py"
```

**Für Windows Command Prompt:**
```json
"command": ".venv\\Scripts\\activate.bat && python main.py"
```

### Alternative: Plattformübergreifende Konfiguration

Sie können auch separate Task-Konfigurationen für verschiedene Betriebssysteme erstellen:

```json
{
    "label": "Start Streamlit App",
    "type": "shell",
    "windows": {
        "command": ".venv\\Scripts\\Activate.ps1; python main.py --ui"
    },
    "linux": {
        "command": "source .venv/bin/activate && python main.py --ui"
    },
    "osx": {
        "command": "source .venv/bin/activate && python main.py --ui"
    }
}
```

## Verfügbare Tasks

- **Start Streamlit App (Single-Agent)**: Startet die Web-UI im Single-Agent-Modus
- **Start Streamlit App (Multi-Agent)**: Startet die Web-UI im Multi-Agent-Modus
- **Run CLI (Single-Agent)**: Startet die CLI im Single-Agent-Modus
- **Run CLI (Multi-Agent)**: Startet die CLI im Multi-Agent-Modus
- **Run Tests**: Führt alle Tests aus
