# Autonomer Chatbot-Agent mit RAG Web Scraper

Ein autonomer Chatbot-Agent für die WiSo-Fakultät der Universität zu Köln, basierend auf LangChain und LangGraph mit Open-Source-Komponenten und einem erweiterten Web-Scraping-System für RAG (Retrieval-Augmented Generation).

## 🎯 Überblick

Dieses Projekt bietet einen intelligenten Chatbot, der:
- ✅ **Fragen zur WiSo-Fakultät beantwortet** (Studiengänge, Bewerbung, Services, etc.)
- ✅ **Automatisch relevante Informationen** aus der Fakultäts-Website sammelt
- ✅ **Intelligent kategorisiert** (5 Kategorien: Studium, Fakultät, Services, Forschung, Allgemein)
- ✅ **Vollständig Open-Source** ohne externe API-Kosten arbeitet
- ✅ **Lokal läuft** für maximale Privatsphäre

## ✨ Hauptfunktionen

### Chatbot-Agent
- **Autonomer Agent**: LangGraph's `create_react_agent` für intelligente Entscheidungsfindung
- **Ollama Integration**: Vollständig Open-Source LLM (llama3.1) ohne API-Kosten
- **Universitäts-RAG**: Durchsucht 329 kategorisierte Dokumente der WiSo-Fakultät
- **Multiple Tools**: Wikipedia, Web-Scraping, DuckDuckGo-Suche
- **Streamlit UI**: Moderne, benutzerfreundliche Chat-Oberfläche
- **Konversations-Memory**: Persistente Chat-Historie

### Erweiterter Web Scraper (NEU)
- **Intelligente Kategorisierung**: Automatische Zuordnung zu 5 Kategorien
- **Multi-Collection Vector DB**: Separate ChromaDB-Collections pro Kategorie
- **Metadaten-Anreicherung**: 10+ Metadatenfelder pro Dokument
- **Batch Processing**: Asynchrone Verarbeitung mehrerer URLs
- **Qualitätsmetriken**: Vollständige Analyse und Reporting
- **329 Dokumente**: 50 Seiten, 100% Erfolgsrate

## 📊 Daten-Status

```
✅ 50 Webseiten erfolgreich gescraped
✅ 329 Dokument-Chunks in Vector-Datenbank
✅ 5 intelligente Kategorien:
   • wiso_studium (95 Dokumente)      - Studiengänge, Bewerbung
   • wiso_fakultaet (117 Dokumente)   - Struktur, Departments
   • wiso_services (61 Dokumente)     - IT, Support, Beratung
   • wiso_forschung (46 Dokumente)    - Forschungsprojekte
   • wiso_allgemein (10 Dokumente)    - Sonstiges
```

## 🛠️ Technologie-Stack

- **LLM**: Ollama (llama3.1, lokal gehostet)
- **Framework**: LangChain + LangGraph
- **UI**: Streamlit
- **Vector DB**: ChromaDB mit sentence-transformers
- **Embeddings**: all-MiniLM-L6-v2 (384 Dimensionen)
- **Web Scraping**: aiohttp, BeautifulSoup
- **Suche**: DuckDuckGo, Wikipedia

## 📁 Projektstruktur

```
uzk-masterarbeit/
├── src/
│   ├── agent/
│   │   └── react_agent.py           # LangGraph ReAct Agent
│   ├── tools/
│   │   ├── rag_tool.py              # RAG für WiSo-Fakultät ⭐
│   │   ├── wikipedia_tool.py        # Wikipedia-Suche
│   │   ├── web_scraper_tool.py      # Web-Scraping
│   │   └── duckduckgo_tool.py       # DuckDuckGo-Suche
│   ├── scraper/                     # Erweiterte Web Scraper Pipeline ⭐
│   │   ├── crawler_scraper_pipeline.py  # Haupt-Pipeline
│   │   ├── wiso_crawler.py          # WiSo-Website Crawler
│   │   ├── batch_scraper.py         # Batch-Scraper
│   │   ├── vector_store.py          # Vector DB Integration
│   │   ├── reprocess_existing_data.py   # Daten-Wiederaufbereitung
│   │   ├── hyperparameters.py       # Zentrale Konfiguration
│   │   └── data_analysis/           # Gescrapte Daten & Reports
│   └── ui/
│       └── streamlit_app.py         # Chat-Interface
├── config/
│   └── settings.py                  # Globale Einstellungen
├── data/
│   └── vector_db/                   # ChromaDB Collections ⭐
├── tests/
│   └── test_*.py                    # Test-Suite
├── main.py                          # CLI-Einstiegspunkt
├── test_enhanced_pipeline.py        # Pipeline-Tests
└── requirements.txt                 # Alle Dependencies
```

## 🚀 Schnellstart

### Voraussetzungen
- Python 3.10+
- Ollama installiert und laufend
- 4GB+ RAM empfohlen

### Installation in 5 Minuten

```bash
# 1. Repository klonen
git clone https://github.com/sebastianuzk/uzk-masterarbeit.git
cd uzk-masterarbeit

# 2. Virtuelle Umgebung erstellen
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# oder
venv\Scripts\activate     # Windows

# 3. Dependencies installieren
pip install --upgrade pip
pip install -r requirements.txt

# 4. Ollama-Modell laden (in separatem Terminal)
ollama pull llama3.1:8b

# 5. Chatbot starten
streamlit run src/ui/streamlit_app.py
```

### Erste Schritte

Nach dem Start können Sie Fragen stellen wie:
- "Welche Master-Programme bietet die WiSo-Fakultät an?"
- "Wie bewerbe ich mich für ein höheres Fachsemester?"
- "Wo finde ich IT-Support an der WiSo?"
- "Welche Forschungsschwerpunkte gibt es?"

## 💡 Verwendung

### Chatbot starten
```bash
streamlit run src/ui/streamlit_app.py
```
Öffnet http://localhost:8501 im Browser.

### Pipeline ausführen (Daten aktualisieren)
```bash
# WiSo-Website scrapen und kategorisieren
python src/scraper/crawler_scraper_pipeline.py --organize-by-category

# Vorhandene Daten wiederaufbereiten
python src/scraper/reprocess_existing_data.py --organize-by-category
```

### CLI-Modus (ohne UI)
```bash
python main.py
```

### Tests ausführen
```bash
# Pipeline-Tests
python test_enhanced_pipeline.py

# Unit-Tests
pytest tests/
```

##  Konfiguration

### Ollama-Einstellungen
Bearbeiten Sie `config/settings.py`:
```python
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.1:8b"  # oder mistral, llama3.2, etc.
TEMPERATURE = 0.7
```

### Scraper-Hyperparameter
Bearbeiten Sie `src/scraper/hyperparameters.py`:
```python
# Performance
SCRAPER_MAX_CONCURRENT_REQUESTS = 10
SCRAPER_REQUEST_DELAY = 1.0

# Vector Store
VECTOR_CHUNK_SIZE = 1500
VECTOR_CHUNK_OVERLAP = 300
VECTOR_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
```

## 🎯 Beispiel-Anfragen

### Studium
```
"Welche Bachelor-Programme gibt es?"
"Wie ist das Master-Programm strukturiert?"
"Was sind Double Degree Programme?"
```

### Bewerbung
```
"Wie bewerbe ich mich für ein höheres Fachsemester?"
"Welche Fristen muss ich beachten?"
"Was sind die Zulassungsvoraussetzungen für Master?"
```

### Services
```
"Wo finde ich IT-Support?"
"Welche Beratungsangebote gibt es?"
"Wie erreiche ich das Prüfungsamt?"
```

### Fakultät & Forschung
```
"Welche Departments hat die WiSo-Fakultät?"
"Welche Forschungsschwerpunkte gibt es?"
"Wie ist die Fakultätsverwaltung organisiert?"
```

## 🛠️ Erweiterte Features

### Web Scraper Pipeline

Die erweiterte Pipeline bietet:
- ✅ **Intelligente Kategorisierung**: 8 Kategorien-Muster
- ✅ **Metadaten-Anreicherung**: Sprache, Themen, Qualität
- ✅ **Multi-Collection DB**: Separate Collections pro Kategorie
- ✅ **Batch-Processing**: Asynchrone URL-Verarbeitung
- ✅ **Qualitätsprüfung**: Automatische Validierung

```bash
# Standard-Pipeline mit Kategorisierung
python src/scraper/crawler_scraper_pipeline.py --organize-by-category

# Erweiterte Optionen
python src/scraper/crawler_scraper_pipeline.py \
  --max-pages 2000 \
  --concurrent-requests 20 \
  --crawl-delay 0.5 \
  --organize-by-category
```

### RAG Tool direkt verwenden

```python
from src.tools.rag_tool import UniversityRAGTool

tool = UniversityRAGTool()
result = tool._run("Wie bewerbe ich mich für Master?")
print(result)
```

### Vector-Datenbank Status prüfen

```python
import chromadb
from pathlib import Path

client = chromadb.PersistentClient(path='data/vector_db')
collections = client.list_collections()

for c in collections:
    print(f'{c.name}: {c.count()} Dokumente')
```

## 🔍 Fehlerbehebung

### Ollama nicht erreichbar
```bash
# Prüfen ob Ollama läuft
ollama list

# Ollama starten
ollama serve
```

### Keine Vector-Datenbank gefunden
```bash
# Pipeline ausführen um Daten zu erstellen
python src/scraper/crawler_scraper_pipeline.py --organize-by-category
```

### Import-Fehler
```bash
# Sicherstellen dass virtuelle Umgebung aktiviert ist
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Dependencies erneut installieren
pip install -r requirements.txt
```

### Langsame Performance
- Kleineres Ollama-Modell verwenden: `ollama pull llama3.2:1b`
- Weniger concurrent requests: `--concurrent-requests 5`
- Größere Delays: `--crawl-delay 2.0`

## 📈 Performance-Metriken

| Metrik | Wert |
|--------|------|
| Gescrapte Seiten | 50 |
| Dokument-Chunks | 329 |
| Collections | 5 |
| Erfolgsrate | 100% |
| Durchschn. Antwortzeit | < 1 Sekunde |
| Embedding-Dimensionen | 384 |
| Pipeline-Laufzeit | ~30 Sekunden |

## 🔐 Datenschutz

- ✅ Alle Daten werden lokal verarbeitet
- ✅ Kein Senden von Daten an externe APIs
- ✅ Ollama LLM läuft vollständig lokal
- ✅ Vector-Datenbank auf lokalem Dateisystem
- ✅ Keine Telemetrie oder Tracking

## 🤝 Beitragen

Dieses Projekt ist Teil einer Masterarbeit an der Universität zu Köln.

## 📄 Lizenz

Dieses Projekt ist für akademische Zwecke erstellt.

## 🙏 Danksagungen

- WiSo-Fakultät, Universität zu Köln
- LangChain & LangGraph Teams
- Ollama Team
- Open-Source Community

---

**Version**: 2.0  
**Letztes Update**: Januar 2025  
**Status**: ✅ Produktionsbereit  
**Daten**: 329 kategorisierte Dokumente aus 50 WiSo-Seiten