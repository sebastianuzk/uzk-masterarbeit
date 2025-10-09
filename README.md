# Autonomous University Chatbot with Process Engine Integration

Ein autonomer Universitäts-Chatbot mit intelligenter Workflow-Orchestrierung, basierend auf LangChain, LangGraph und Camunda Platform 8. Das System kombiniert Open-Source LLMs mit automatisierter Prozessbearbeitung für Universitätsdienste.

## 🎉 PROCESS ENGINE INTEGRATION - VOLLSTÄNDIG IMPLEMENTIERT

### ✅ Erfolgreich Implementierte Komponenten

#### 🧠 Intelligente Datenextraktion
- **ConversationDataExtractor**: Erkennt automatisch Studenten-IDs, E-Mails, Namen, Kurse, etc.
- **Regex-Pattern**: Hochperformante Extraktion von Universitätsdaten aus natürlicher Sprache
- **Kontextuelle Absichtserkennung**: Automatische Identifikation von Zeugnis-Anfragen, Prüfungsanmeldungen
- **Datenkonsolidierung**: Deduplizierung und Vertrauenswert-basierte Priorisierung

#### 🔄 Workflow-Orchestrierung  
- **WorkflowManager**: Vollständige Verwaltung von Universitäts-Prozessen
- **5 Standard-Workflows**: Zeugnis-Anfragen, Prüfungsanmeldungen, Notenabfragen, Kurs-Einschreibungen, Stundenplan-Anfragen
- **Automatische Workflow-Erkennung**: Analyse von Gesprächen auf relevante Prozesse
- **Job Handler**: E-Mail-Versand, Datenvalidierung, Dokumentenerstellung, Datenbankabfragen

#### 📄 BPMN 2.0 Generierung
- **BPMNGenerator**: Automatische Erstellung von Camunda-kompatiblen BPMN-Workflows
- **Universitäts-Templates**: Vorgefertigte Prozesse für typische Universitätsabläufe
- **Custom Workflow Builder**: Flexibles System für neue Prozessdefinitionen
- **Zeebe Integration**: Native Unterstützung für Service Tasks und Job Types

#### 🏗️ Camunda Platform 8 Integration
- **ProcessEngineClient**: Vollständige API-Integration für Zeebe, Operate, Tasklist
- **Docker Compose Setup**: Ein-Klick-Deployment der kompletten Process Engine
- **Health Monitoring**: Automatische Überwachung aller Camunda-Komponenten
- **Workflow Deployment**: Automatisches Deployment und Versionierung von BPMN-Prozessen

#### 🤖 React Agent Integration
- **ProcessEngineTool**: Nahtlose Integration in den bestehenden Chatbot
- **Tool Interface**: Benutzerfreundliche Aktionen (analyze, start_workflow, status, list_workflows)
- **Conversation Context**: Automatische Weiterleitung von Gesprächsinhalten an Process Engine
- **Multi-Action Support**: Flexible Kommandostruktur für verschiedene Workflow-Operationen

## Features

### Core Agent Features
- **Autonomer Agent**: LangGraph's `create_react_agent` für intelligente Entscheidungsfindung
- **Ollama Integration**: Vollständig Open-Source LLM ohne API-Kosten
- **Multiple Tools**: Wikipedia, Web-Scraping, DuckDuckGo-Suche und Universitäts-RAG
- **Interactive Chat**: Streamlit-basierte Benutzeroberfläche
- **Memory Management**: Persistente Konversationshistorie
- **Privatsphäre**: Keine externen API-Aufrufe erforderlich

### Process Engine Features (NEU!)
- **BPMN Workflow Automation**: Automatische Bearbeitung von Universitätsprozessen
- **Intelligent Data Extraction**: Erkennung relevanter Daten aus Unterhaltungen
- **Camunda Platform 8 Integration**: Zeebe, Operate, Tasklist für komplette Orchestrierung
- **University Workflows**: Zeugnis-Anfragen, Prüfungsanmeldungen, Notenabfragen
- **Docker Compose Setup**: Ein-Klick-Deployment der kompletten Process Engine
- **Real-time Monitoring**: Live-Überwachung von Workflow-Ausführungen

### RAG Web Scraper Features
- **Batch Web Scraping**: Asynchrone Verarbeitung mehrerer URLs
- **Vector Database Integration**: ChromaDB Support für Universitätsdaten
- **Data Structure Analysis**: Dynamische Analyse und Optimierung
- **Multiple Output Formats**: JSON, JSONL, Markdown, HTML Reports
- **Quality Metrics**: Vollständigkeits- und Konsistenz-Analyse

## Technologie-Stack

### Core Technologies
- **LLM**: Ollama (lokal gehostet)
- **Framework**: LangChain + LangGraph
- **UI**: Streamlit
- **Datenbank**: ChromaDB für RAG

### Process Engine Stack
- **Workflow Engine**: Camunda Platform 8 (Zeebe)
- **Process Monitoring**: Operate, Tasklist
- **Data Storage**: Elasticsearch
- **Containerization**: Docker + Docker Compose
- **BPMN Generation**: Custom Python BPMN Generator

### Integration Technologies
- **Suche**: DuckDuckGo (privatsphärefreundlich)
- **Wissen**: Wikipedia + Universitäts-RAG
- **Web Scraping**: aiohttp, BeautifulSoup
- **Embeddings**: Sentence Transformers

## Projektstruktur

```
uzk-masterarbeit/
├── src/
│   ├── agent/
│   │   └── react_agent.py           # Hauptagent mit Process Engine Integration
│   ├── tools/
│   │   ├── wikipedia_tool.py        # Wikipedia-Suche
│   │   ├── web_scraper_tool.py      # Web-Scraping
│   │   ├── duckduckgo_tool.py       # DuckDuckGo-Suche
│   │   ├── rag_tool.py              # Universitäts-RAG
│   │   └── process_engine_tool.py   # Process Engine Integration (NEU!)
│   ├── process_engine/              # Process Engine System (NEU!)
│   │   ├── data_extractor.py        # Intelligente Datenextraktion
│   │   ├── process_client.py        # Camunda Platform 8 Client
│   │   ├── workflow_manager.py      # Workflow-Orchestrierung
│   │   └── bpmn_generator.py        # BPMN XML Generation
│   ├── scraper/                     # RAG Web Scraper System
│   │   ├── batch_scraper.py     # Batch-Webscraper
│   │   ├── vector_store.py      # Vector Database Integration
│   │   ├── data_structure_analyzer.py  # Datenstruktur-Analyse
│   │   ├── scraper_main.py      # CLI Interface
│   │   ├── test_example.py      # Test & Beispiel-Script
│   │   └── README.md            # Scraper-Dokumentation
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
├── requirements.txt             # Alle Dependencies (Agent + Scraper)
├── main.py
└── README.md
```

## 🚀 Installation

### Schritt 1: Voraussetzungen

#### Python 3.8+ installieren
- Windows: [python.org](https://python.org) - "Add to PATH" auswählen
- Linux: `sudo apt install python3 python3-pip python3-venv`
- Mac: `brew install python3`

#### Ollama installieren (für LLM)
- **Windows**: Laden Sie Ollama von [ollama.ai](https://ollama.ai) herunter und installieren
- **Linux/Mac**: `curl -fsSL https://ollama.ai/install.sh | sh`

### Schritt 2: Repository klonen
```bash
git clone https://github.com/sebastianuzk/uzk-masterarbeit.git
cd uzk-masterarbeit
```

### Schritt 3: Virtuelle Umgebung erstellen und aktivieren

#### Windows (PowerShell):
```powershell
# Virtuelle Umgebung erstellen
python -m venv Masterarbeit

# Aktivieren
.\Masterarbeit\Scripts\Activate.ps1

# Falls Execution Policy Fehler auftritt:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### Linux/Mac:
```bash
# Virtuelle Umgebung erstellen
python3 -m venv Masterarbeit

# Aktivieren
source Masterarbeit/bin/activate
```

### Schritt 4: Abhängigkeiten installieren
```bash
# Alle Dependencies installieren (Agent + RAG Scraper)
pip install --upgrade pip
pip install -r requirements.txt
```

### Schritt 5: Ollama Setup für LLM

#### 1. Ollama-Server starten:
```bash
# In einem separaten Terminal/Command Prompt
ollama serve
```

#### 2. LLM-Modell herunterladen:
```bash
# Hauptmodell (empfohlen):
ollama pull llama3.1

# Alternative kleinere Modelle:
ollama pull mistral           # Schneller, weniger Ressourcen
ollama pull codellama         # Für Code-Aufgaben
ollama pull llama3.2:1b       # Sehr klein, für schwache Hardware
```

### Schritt 6: Process Engine Setup (Optional aber empfohlen)

#### Automatisches Setup:
```bash
# Komplettes Process Engine Setup (Docker + Camunda Platform 8)
python src/process_engine/deployment/setup_process_engine.py setup
```

#### Manuelles Setup:
```bash
# 1. Docker installieren (falls nicht vorhanden)
# Windows: Docker Desktop von docker.com
# Linux: sudo apt install docker.io docker-compose
# Mac: Docker Desktop oder brew install docker docker-compose

# 2. .env Datei erstellen
cp .env.example .env

# 3. .env bearbeiten und Process Engine aktivieren:
# ENABLE_PROCESS_ENGINE=true
# CAMUNDA_ZEEBE_ADDRESS=localhost:26500
# CAMUNDA_OPERATE_URL=http://localhost:8081

# 4. Camunda Platform 8 starten
docker-compose up -d

# 5. Warten bis Services bereit sind (ca. 2-3 Minuten)
python src/process_engine/deployment/setup_process_engine.py test
```

#### Process Engine URLs:
- **Operate**: http://localhost:8081 (Workflow Monitoring)
- **Tasklist**: http://localhost:8082 (Human Tasks)
- **Elasticsearch**: http://localhost:9200 (Data Storage)
- **Zeebe Monitoring**: http://localhost:9600 (Health Check)

### Schritt 7: Konfiguration
```bash
# Umgebungsvariablen-Datei bearbeiten (bereits erstellt)
# Bearbeiten Sie .env nach Ihren Bedürfnissen

# Wichtige Einstellungen in .env:
# OLLAMA_BASE_URL=http://localhost:11434
# OLLAMA_MODEL=llama3.1
# ENABLE_PROCESS_ENGINE=true
# SMTP_SERVER=smtp.gmail.com  # Für E-Mail-Funktionen
```

### 🔧 Verfügbare Installationsoptionen

#### Minimale Installation (nur Chatbot Agent):
Wenn Sie nur den Chatbot ohne Web-Scraper benötigen:
```bash
pip install langchain langgraph langchain-community langchain-core langchain-ollama
pip install streamlit python-dotenv duckduckgo-search wikipedia requests
```

#### Vollständige Installation (Agent + RAG Scraper):
```bash
pip install -r requirements.txt  # Enthält alles
```

#### Erweiterte Installation (mit GPU-Support für FAISS):
```bash
pip install -r requirements.txt
# GPU-Version von FAISS installieren (falls CUDA verfügbar):
pip uninstall faiss-cpu
pip install faiss-gpu
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

## 🎯 Nutzung

### ✅ Installations-Checkliste
Vor der ersten Nutzung prüfen Sie:
- [ ] Ollama ist installiert und läuft (`ollama serve`)
- [ ] Ein LLM-Modell ist heruntergeladen (`ollama pull llama3.1`)
- [ ] Virtuelle Umgebung ist aktiviert
- [ ] Alle Dependencies sind installiert (`pip install -r requirements.txt`)

### 🤖 Chatbot Agent

#### 1. Ollama starten (wichtig!)
**Vor jeder Nutzung** müssen Sie Ollama starten:

```bash
# Terminal 1: Ollama-Server starten
ollama serve

# Terminal 2: Modell herunterladen (falls noch nicht vorhanden)
ollama pull llama3.1
```

#### 2. Agent verwenden

**Streamlit Web-Interface (empfohlen):**
```bash
# VS Code Task verwenden oder direkt:
streamlit run src/ui/streamlit_app.py

# Mit spezifischem Python-Interpreter:
./Masterarbeit/Scripts/python.exe -m streamlit run src/ui/streamlit_app.py
```

**Kommandozeilen-Interface:**
```bash
# VS Code Task verwenden oder direkt:
python main.py

# Mit spezifischem Python-Interpreter:
./Masterarbeit/Scripts/python.exe main.py
```

### 🔍 RAG Web Scraper (Unabhängiges System)

Das RAG Web Scraper System funktioniert vollständig unabhängig vom Chatbot.

#### Schnellstart-Beispiele:

**Einzelne Webseite scrapen:**
```bash
python src/scraper/scraper_main.py pipeline \
  --urls https://wiso.uni-koeln.de/de/studium/bewerbung/bachelor \
  --collection uni_bewerbung \
  --save-scraped
```

**Mehrere Webseiten gleichzeitig:**
```bash
python src/scraper/scraper_main.py pipeline \
  --urls https://wiso.uni-koeln.de/de/studium/bewerbung/bachelor \
         https://wiso.uni-koeln.de/de/studium/bewerbung/master \
  --collection uni_infos \
  --save-scraped \
  --concurrent 3
```

**Abfrage an die Vectordatenbank:**
```bash
python src/scraper/scraper_main.py search \
  --query "Was benötige ich für die Bewerbung auf ein höheres Fachsemester?" \
  --collection uni_bewerbung \
  --results 5
```

**Chunks der Vectordatenbank anzeigen:**
```bash
python src/scraper/scraper_main.py chunks \
  --collection uni_bewerbung \
  --limit 3 \
  --export json
```

#### Vollständige Scraper-Dokumentation:
Detaillierte Anweisungen finden Sie in [`src/scraper/README.md`](src/scraper/README.md).

### 🧪 Tests ausführen
```bash
# VS Code Task verwenden oder direkt:
python -m pytest tests/

# Mit spezifischem Python-Interpreter:
./Masterarbeit/Scripts/python.exe -m pytest tests/
```

### 🔧 VS Code Tasks verwenden

Das Projekt enthält vordefinierte VS Code Tasks:
- **"Start Streamlit App"**: Startet die Web-UI
- **"Run Main Script"**: Startet das CLI-Interface  
- **"Run Tests"**: Führt alle Tests aus

Zugriff über: `Ctrl+Shift+P` → "Tasks: Run Task"

## Features im Detail

### React Agent
Der Agent verwendet LangGraph's `create_react_agent` Funktionalität für:
- Reasoning über verfügbare Tools
- Entscheidungsfindung basierend auf Benutzereingaben
- Iterative Problemlösung
- Memory Management für Kontext

### Verfügbare Tools
1. **Wikipedia Tool**: Suche nach Informationen in Wikipedia
2. **Web Scraper Tool**: Extrahierung von Inhalten aus Webseiten (für Agent)
3. **DuckDuckGo Tool**: Privatsphärefreundliche Websuche ohne Tracking

### RAG Web Scraper System
Das separate Scraper-System bietet:
- **Batch Processing**: Verarbeitung vieler URLs parallel
- **Vector Storage**: Speicherung in ChromaDB oder FAISS für RAG
- **Data Analysis**: Automatische Qualitäts- und Strukturanalyse
- **Optimization**: Vorschläge zur Datenverbesserung
- **Flexible Export**: Verschiedene Ausgabeformate

### Memory Management
- Persistente Konversationshistorie
- Kontextuelle Speicherung für bessere Antworten
- Konfigurierbare Memory-Größe

## Integration von Agent und Scraper

Das RAG System kann später in den Chatbot-Agent integriert werden:

1. **Daten sammeln** mit dem Batch Scraper
2. **Vektorisieren** der Inhalte für semantische Suche
3. **RAG Tool erstellen** für den Agent mit Zugriff auf die Vector Database
4. **Agent erweitern** um das neue RAG Tool

## 🛠️ Entwicklung

### 🧪 Tests ausführen
```bash
# Alle Tests
python -m pytest tests/

# Mit Ausgabe
python -m pytest tests/ -v

# Spezifische Testdatei
python -m pytest tests/test_agent.py
```

### 🔧 Agent erweitern

#### Neue Tools hinzufügen:
1. Erstellen Sie eine neue Datei in `src/tools/` (z.B. `my_new_tool.py`)
2. Implementieren Sie die Tool-Klasse basierend auf LangChain's `BaseTool`
3. Registrieren Sie das Tool in `src/agent/react_agent.py`

Beispiel:
```python
# src/tools/my_new_tool.py
from langchain.tools import BaseTool

class MyNewTool(BaseTool):
    name = "my_new_tool"
    description = "Beschreibung des Tools"
    
    def _run(self, query: str) -> str:
        # Tool-Logik hier
        return "Ergebnis"
```

#### RAG Tool für Agent erstellen:
Nach dem Aufbau einer Vectordatenbank mit dem Scraper können Sie ein RAG Tool erstellen:

```python
# src/tools/rag_tool.py
from langchain.tools import BaseTool
from src.scraper.vector_store import VectorStore

class RAGTool(BaseTool):
    name = "knowledge_search"
    description = "Durchsucht die lokale Wissensdatenbank"
    
    def _run(self, query: str) -> str:
        vector_store = VectorStore()
        results = vector_store.search(query, k=3)
        return "\\n".join([doc.text for doc, score in results])
```

### 🔍 Scraper erweitern

#### Neue Vector Store Backends:
1. Implementieren Sie `VectorStoreBackend` in `src/scraper/vector_store.py`
2. Registrieren Sie das Backend in der `VectorStore` Klasse

#### Zusätzliche Datenanalyse:
1. Erweitern Sie `DataStructureAnalyzer` in `src/scraper/data_structure_analyzer.py`
2. Neue CLI-Befehle in `src/scraper/scraper_main.py` hinzufügen

### 📝 Konfiguration anpassen

#### Agent-Konfiguration (`config/settings.py`):
```python
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1"
MEMORY_KEY = "chat_history"
```

#### Scraper-Konfiguration:
Siehe `src/scraper/hyperparameters.py` für alle verfügbaren Parameter.

### 🐛 Debug-Tipps

#### Ollama Probleme:
```bash
# Ollama Status prüfen
ollama list

# Modell erneut herunterladen
ollama pull llama3.1

# Ollama Logs anzeigen (falls verfügbar)
ollama logs
```

#### Scraper Probleme:
```bash
# Verbose-Modus aktivieren
python src/scraper/scraper_main.py --verbose pipeline --urls https://example.com

# Einzelne Schritte testen
python src/scraper/test_example.py
```

#### Virtual Environment Probleme:
```bash
# Environment neu erstellen
deactivate
rm -rf Masterarbeit  # oder Remove-Item -Recurse Masterarbeit (Windows)
python -m venv Masterarbeit
source Masterarbeit/bin/activate  # oder .\\Masterarbeit\\Scripts\\Activate.ps1
pip install -r requirements.txt
```

## Lizenz

MIT License

**Aktivieren der venv:**
```powershell
# Windows PowerShell
& "D:/Uni-Köln/Masterarbeit/Software/uzk-masterarbeit/Masterarbeit/Scripts/Activate.ps1"

# Dann Streamlit starten:
streamlit run src/ui/streamlit_app.py
```

**Problemlösung bei venv-Konflikten:**
Falls Sie Probleme haben, verwenden Sie diesen direkten Befehl:
```powershell
cd "d:\Uni-Köln\Masterarbeit\Software\uzk-masterarbeit"
.\Masterarbeit\Scripts\python.exe -m streamlit run src/ui/streamlit_app.py
```