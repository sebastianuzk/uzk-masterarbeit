# Autonomous Chatbot Agent

Ein autonomer Chatbot-Agent basierend auf LangChain und LangGraph mit Open-Source-Komponenten.

## Features

- **Autonomer Agent**: Verwendet LangGraph's `create_react_agent` für intelligente Entscheidungsfindung
- **Ollama Integration**: Vollständig Open-Source LLM ohne API-Kosten
- **Multiple Tools**: Wikipedia-Suche, Web-Scraping und DuckDuckGo-Websuche
- **Interactive Chat**: Streamlit-basierte Benutzeroberfläche
- **Memory Management**: Persistente Konversationshistorie
- **Tool Integration**: Modulare Tool-Architektur für einfache Erweiterung
- **Privatsphäre**: Keine externen API-Aufrufe erforderlich

## Technologie-Stack

- **LLM**: Ollama (lokal gehostet)
- **Framework**: LangChain + LangGraph
- **UI**: Streamlit
- **Suche**: DuckDuckGo (privatsphärefreundlich)
- **Wissen**: Wikipedia

## Projektstruktur

```
autonomous-agent/
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── react_agent.py       # Hauptagent mit LangGraph
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── wikipedia_tool.py    # Wikipedia-Suche
│   │   ├── web_scraper_tool.py  # Web-Scraping
│   │   └── duckduckgo_tool.py   # DuckDuckGo-Suche
│   └── ui/
│       ├── __init__.py
│       └── streamlit_app.py     # Streamlit Interface
├── config/
│   ├── __init__.py
│   └── settings.py              # Konfiguration
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   └── test_tools.py
├── Masterarbeit/                # Virtuelles Environment
├── .env.example
├── .gitignore
├── requirements.txt
├── main.py
└── README.md
```

## Installation

### Voraussetzungen

1. **Ollama installieren**:
   - Windows: Laden Sie Ollama von [ollama.ai](https://ollama.ai) herunter
   - Linux/Mac: `curl -fsSL https://ollama.ai/install.sh | sh`

2. **Repository klonen und in das Verzeichnis wechseln**

3. **Virtuelle Umgebung verwenden**:
   ```bash
   # Virtuelle Umgebung aktivieren (Windows)
   Masterarbeit\Scripts\activate
   # oder (Linux/Mac)
   source Masterarbeit/bin/activate
   ```

4. **Abhängigkeiten installieren**:
   ```bash
   pip install -r requirements.txt
   ```

### Ollama Setup

1. **Ollama-Server starten**:
   ```bash
   ollama serve
   ```

2. **Gewünschtes Modell herunterladen**:
   ```bash
   # Hauptmodell:
   ollama pull llama3.1
   
   # Alternative Modelle:
   ollama pull mistral           # Alternative
   ollama pull codellama         # Für Code-Aufgaben
   ```

3. **Optional: Umgebungsvariablen konfigurieren**:
   ```bash
   cp .env.example .env
   ```
   Bearbeiten Sie `.env` für benutzerdefinierte Einstellungen.

## Konfiguration

Erstellen Sie optional eine `.env` Datei mit folgenden Variablen:

```
# Ollama Konfiguration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1
```

## Nutzung

### 🚀 Ollama zuerst starten
**Wichtig**: Bevor Sie den Agent verwenden, müssen Sie Ollama starten:

```bash
# Ollama-Server starten
ollama serve

# In einem neuen Terminal: Modell herunterladen (falls noch nicht vorhanden)
ollama pull llama3.1
```

### Streamlit Interface starten:
```bash
# Verwenden Sie die VS Code Task "Start Streamlit App" oder:
streamlit run src/ui/streamlit_app.py
```

### Direkte Verwendung:
```bash
# Verwenden Sie die VS Code Task "Run Main Script" oder:
python main.py
```

### Tests ausführen:
```bash
# Verwenden Sie die VS Code Task "Run Tests" oder:
python -m pytest tests/
```

## Features im Detail

### React Agent
Der Agent verwendet LangGraph's `create_react_agent` Funktionalität für:
- Reasoning über verfügbare Tools
- Entscheidungsfindung basierend auf Benutzereingaben
- Iterative Problemlösung
- Memory Management für Kontext

### Verfügbare Tools
1. **Wikipedia Tool**: Suche nach Informationen in Wikipedia
2. **Web Scraper Tool**: Extrahierung von Inhalten aus Webseiten
3. **DuckDuckGo Tool**: Privatsphärefreundliche Websuche ohne Tracking

### Memory Management
- Persistente Konversationshistorie
- Kontextuelle Speicherung für bessere Antworten
- Konfigurierbare Memory-Größe

## Entwicklung

### Tests ausführen:
```bash
python -m pytest tests/
```

### Neue Tools hinzufügen:
1. Erstellen Sie eine neue Datei in `src/tools/`
2. Implementieren Sie die Tool-Klasse
3. Registrieren Sie das Tool in `src/agent/react_agent.py`

## Lizenz

MIT License

**Aktivieren der venv:**
```powershell
# Windows PowerShell
& "D:/Uni-Köln/Masterarbeit/Software/Autonomous Agent/Masterarbeit/Scripts/Activate.ps1"

# Dann Streamlit starten:
streamlit run src/ui/streamlit_app.py
```

**Problemlösung bei venv-Konflikten:**
Falls Sie Probleme haben, verwenden Sie diesen direkten Befehl:
```powershell
cd "d:\Uni-Köln\Masterarbeit\Software\Autonomous Agent"
.\Masterarbeit\Scripts\python.exe -m streamlit run src/ui/streamlit_app.py
```