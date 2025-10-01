# Web Scraper für RAG System

Dieses Verzeichnis enthält ein umfassendes Web-Scraping-System, das für die Datensammlung und -aufbereitung für ein RAG (Retrieval-Augmented Generation) System entwickelt wurde.

## 🚀 Schnellstart

### Voraussetzungen
- Python 3.8+
- Virtual Environment (empfohlen)

### Installation
```bash
# Alle Abhängigkeiten installieren (aus dem Hauptverzeichnis)
pip install -r requirements.txt

# Oder nur die für den Scraper notwendigen Pakete:
pip install chromadb sentence-transformers beautifulsoup4 aiohttp pandas tqdm
```

## 📋 Praktische Beispiele

### 1. Eine einzelne Seite scrapen

**Befehl:**
```bash
# Mit absolutem Pfad (unabhängig von venv/location)
python /path/to/your/project/src/scraper/scraper_main.py pipeline \
  --urls https://wiso.uni-koeln.de/de/studium/bewerbung/bachelor \
  --collection einzelne_seite \
  --save-scraped

# Oder wenn Sie im Projektverzeichnis sind:
python src/scraper/scraper_main.py pipeline \
  --urls https://wiso.uni-koeln.de/de/studium/bewerbung/bachelor \
  --collection einzelne_seite \
  --save-scraped
```

**Ergebnisse finden Sie hier:**
- **Rohdaten**: `src/scraper/output/scraped_data_einzelne_seite_YYYYMMDD_HHMMSS.json`
- **Vectordatenbank**: `src/scraper/chroma_db/` (ChromaDB Collection: "einzelne_seite")
- **Analyse-Report**: `src/scraper/output/pipeline_analysis_report_einzelne_seite_YYYYMMDD_HHMMSS.html`

### 2. Mehrere Seiten gleichzeitig scrapen

**Befehl:**
```bash
# Mit absolutem Pfad
python /path/to/your/project/src/scraper/scraper_main.py pipeline \
  --urls https://wiso.uni-koeln.de/de/studium/bewerbung/bachelor \
         https://wiso.uni-koeln.de/de/studium/bewerbung/master \
         https://wiso.uni-koeln.de/de/studium/organisatorisches/pruefungen \
  --collection multiple_seiten \
  --save-scraped \
  --concurrent 3

# Oder wenn Sie im Projektverzeichnis sind:
python src/scraper/scraper_main.py pipeline \
  --urls https://wiso.uni-koeln.de/de/studium/bewerbung/bachelor \
         https://wiso.uni-koeln.de/de/studium/bewerbung/master \
         https://wiso.uni-koeln.de/de/studium/organisatorisches/pruefungen \
  --collection multiple_seiten \
  --save-scraped \
  --concurrent 3
```

**Ergebnisse finden Sie hier:**
- **Rohdaten**: `src/scraper/output/scraped_data_multiple_seiten_YYYYMMDD_HHMMSS.json`
- **Vectordatenbank**: `src/scraper/chroma_db/` (ChromaDB Collection: "multiple_seiten")
- **Analyse-Report**: `src/scraper/output/pipeline_analysis_report_multiple_seiten_YYYYMMDD_HHMMSS.html`

### 3. Abfrage an die Vectordatenbank stellen

**Beispiel-Abfrage: "Was benötige ich für die Bewerbung auf ein höheres Fachsemester?"**

```bash
# Mit absolutem Pfad
python /path/to/your/project/src/scraper/scraper_main.py search \
  --query "Was benötige ich für die Bewerbung auf ein höheres Fachsemester?" \
  --collection einzelne_seite \
  --results 5 \
  --threshold 0.1

# Oder wenn Sie im Projektverzeichnis sind:
python src/scraper/scraper_main.py search \
  --query "Was benötige ich für die Bewerbung auf ein höheres Fachsemester?" \
  --collection einzelne_seite \
  --results 5 \
  --threshold 0.1
```

**Weitere Beispiel-Abfragen:**
```bash
# Bewerbungsfristen
python src/scraper/scraper_main.py search \
  --query "Bewerbungsfrist 15. Juli Bachelor" \
  --collection multiple_seiten

# Prüfungsamt Bescheinigungen  
python src/scraper/scraper_main.py search \
  --query "Prüfungsamt Bescheinigung Fachsemestereinstufung" \
  --collection multiple_seiten

# Beruflich Qualifizierte
python src/scraper/scraper_main.py search \
  --query "beruflich qualifiziert ohne Abitur studieren" \
  --collection multiple_seiten
```

**Ergebnisse finden Sie hier:**
- **Konsole**: Direktes Ergebnis mit relevanten Text-Chunks und Similarity-Scores
- **Keine Dateien**: Search-Ergebnisse werden direkt angezeigt

### 4. Chunks der Vectordatenbank anzeigen

```bash
# Alle Chunks anzeigen
python src/scraper/scraper_main.py chunks --collection einzelne_seite

# Nur erste 3 Chunks anzeigen  
python src/scraper/scraper_main.py chunks --collection einzelne_seite --limit 3

# Chunks als JSON exportieren
python src/scraper/scraper_main.py chunks --collection einzelne_seite --export json

# Chunks als TXT exportieren
python src/scraper/scraper_main.py chunks --collection einzelne_seite --export txt
```

**Ergebnisse finden Sie hier:**
- **Konsole**: Chunk-Übersicht mit Metadaten
- **Export-Dateien**: `src/scraper/output/chunks_COLLECTION_YYYYMMDD_HHMMSS.json/txt`

## 📁 Dateistruktur der Ergebnisse

```
src/scraper/output/
├── scraped_data_[collection]_[timestamp].json          # Rohdaten vom Scraping
├── pipeline_analysis_report_[collection]_[timestamp].html  # Analyse-Report  
├── chunks_[collection]_[timestamp].json               # Exportierte Chunks
└── chunks_[collection]_[timestamp].txt                # Chunks als Text

src/scraper/chroma_db/                                  # Vectordatenbank
├── [collection]/                                      # Pro Collection ein Ordner
│   ├── data_level0.bin                               # ChromaDB Daten
│   ├── header.bin
│   ├── length.bin
│   └── ...
```

## 🔧 Systemkomponenten

### 1. BatchScraper (`batch_scraper.py`)
- **Zweck**: Asynchrones Web-Scraping für mehrere URLs
- **Features**:
  - Konfigurierbare Parallelität und Rate-Limiting
  - Fehlerbehandlung und Retry-Logik
  - Content-Extraktion mit anpassbaren Selektoren
  - Metadaten-Sammlung (Links, Bilder, Wortanzahl)
  - Fortschritts-Tracking und Statistiken

### 2. VectorStore (`vector_store.py`)
- **Zweck**: Vector-Datenbank-Integration für gespeicherte Inhalte
- **Unterstützte Backends**:
  - ChromaDB (empfohlen für Entwicklung)
  - FAISS (für Produktion/Performance)
- **Features**:
  - Text-Chunking mit Überlappung
  - Embedding-Provider (Sentence Transformers)
  - Ähnlichkeitssuche mit Metadaten-Filterung
  - Batch-Operationen für Effizienz

### 3. DataStructureAnalyzer (`data_structure_analyzer.py`)
- **Zweck**: Dynamische Analyse und Dokumentation der Datenstrukturen
- **Features**:
  - Feld-Präsenz und Vollständigkeits-Analyse
  - Datenqualitäts-Metriken
  - Optimierungsvorschläge
  - Export-Reports in JSON, Markdown und HTML

### 4. CLI Interface (`scraper_main.py`)
- **Zweck**: Kommandozeilen-Interface für die komplette Pipeline
- **Befehle**:
  - `pipeline`: Kompletter Workflow (scrapen → vektorisieren → analysieren)
  - `search`: Suche in der Vectordatenbank
  - `chunks`: Chunks anzeigen und exportieren
  - `scrape`: URLs scrapen und Ergebnisse speichern
  - `vectorize`: Gescrapte Daten zu Vector-Embeddings konvertieren
  - `analyze`: Datenstruktur und -qualität analysieren

## ⚙️ Konfiguration

### Hyperparameter anpassen

Alle wichtigen Parameter können in verschiedenen Dateien angepasst werden:

#### 1. Scraping-Parameter (`src/scraper/batch_scraper.py`)
```python
# ScrapingConfig Klasse (Zeile ~15-30)
max_concurrent_requests=5     # Anzahl paralleler Anfragen
request_delay=1.0            # Pause zwischen Anfragen (Sekunden)
timeout=30                   # Timeout pro Anfrage (Sekunden)
retry_attempts=3             # Anzahl Wiederholungsversuche
user_agent="Web Scraper"     # User-Agent String
```

#### 2. Vektorisierungs-Parameter (`src/scraper/vector_store.py`)
```python
# VectorStoreConfig Klasse (Zeile ~25-45)
chunk_size=1500              # Zeichen pro Text-Chunk
chunk_overlap=300            # Überlappung zwischen Chunks
embedding_model="all-MiniLM-L6-v2"  # Embedding-Modell
similarity_threshold=0.1      # Schwellwert für deutsche Texte
```

#### 3. Vollständige Parameter-Übersicht (`src/scraper/hyperparameters.py`)
Detaillierte Dokumentation aller verfügbaren Parameter mit Beispielen.

### Beispiel-Konfiguration für deutsche Universitäts-Webseiten
```bash
# Optimiert für deutsche Inhalte
python src/scraper/scraper_main.py pipeline \
  --urls https://wiso.uni-koeln.de/de/studium/bewerbung/bachelor \
  --collection uni_koeln \
  --concurrent 3 \
  --delay 2.0 \
  --chunk-size 1500 \
  --chunk-overlap 300
```

## 🔍 Erweiterte Verwendung

### Programmatische Nutzung
```python
import asyncio
from src.scraper.batch_scraper import BatchScraper, ScrapingConfig
from src.scraper.vector_store import VectorStore, VectorStoreConfig

async def main():
    # Scraping konfigurieren
    scrape_config = ScrapingConfig(
        max_concurrent_requests=5,
        request_delay=1.0,
        timeout=30
    )
    
    # URLs scrapen
    scraper = BatchScraper(scrape_config)
    urls = ["https://example.com"]
    scraped_content = await scraper.scrape_urls(urls)
    
    # In Vectordatenbank speichern
    vector_config = VectorStoreConfig(
        backend="chromadb",
        collection_name="my_collection",
        chunk_size=1500,
        chunk_overlap=300
    )
    vector_store = VectorStore(vector_config)
    vector_store.add_scraped_content(scraped_content)
    
    # Suche durchführen
    results = vector_store.search("Ihre Frage", k=5)
    for doc, score in results:
        print(f"Score: {score:.3f} - {doc.text[:100]}...")

asyncio.run(main())
```

### Integration mit RAG-System
```python
# Nach dem Scraping und Vektorisieren für RAG-Queries verwenden
vector_store = VectorStore()

# Nach relevanten Inhalten suchen
results = vector_store.search("Ihre Frage", k=5)

# Text für RAG-Kontext extrahieren
context_texts = [doc.text for doc, score in results if score > 0.1]
```

## 📊 Datenstrukturen

### ScrapedContent
```python
@dataclass
class ScrapedContent:
    url: str                        # Quell-URL
    title: str                      # Seitentitel
    content: str                    # Extrahierter Text
    metadata: Dict[str, Any]        # Domain, word_count, Links, etc.
    timestamp: str                  # Zeitstempel
    success: bool                   # Erfolgsstatus
    error_message: Optional[str]    # Fehlermeldung falls fehlgeschlagen
```

### VectorDocument
```python
@dataclass
class VectorDocument:
    id: str                         # Eindeutige Chunk-ID
    text: str                       # Text-Inhalt
    embedding: List[float]          # Vector-Embedding
    metadata: Dict[str, Any]        # Metadaten
    source_url: str                 # Quell-URL
    chunk_index: int                # Chunk-Position
    total_chunks: int               # Gesamtanzahl Chunks
```

## 🚨 Fehlerbehebung

### Häufige Probleme

1. **Import-Fehler**: 
   ```bash
   pip install chromadb sentence-transformers beautifulsoup4 aiohttp
   ```

2. **"No chunks found"**: 
   - Prüfen Sie, ob die Collection existiert
   - Verwenden Sie niedrigere similarity_threshold (0.1 für deutsche Texte)

3. **Speicher-Probleme**: 
   - Reduzieren Sie `max_concurrent_requests`
   - Verwenden Sie kleinere `chunk_size`

4. **Rate-Limiting von Webseiten**:
   - Erhöhen Sie `request_delay`
   - Reduzieren Sie `max_concurrent_requests`

### Debug-Modus aktivieren
```bash
python src/scraper/scraper_main.py --verbose pipeline --urls https://example.com
```

## 🎯 Best Practices

1. **Rate-Limiting**: Respektieren Sie Website-Limits und robots.txt
2. **Fehlerbehandlung**: Implementieren Sie umfassende Fehlerbehandlung
3. **Daten-Validierung**: Validieren Sie gescrapte Inhalte vor Vektorisierung
4. **Monitoring**: Verfolgen Sie Scraping-Erfolgsraten und Datenqualität
5. **Backup**: Sichern Sie regelmäßig Vectordatenbanken und Konfigurationen

## 🔧 Erwiterungsmöglichkeiten

Das System ist erweiterbar für:

### Neue Backends hinzufügen
Implementieren Sie die `VectorStoreBackend` abstrakte Klasse

### Benutzerdefinierte Content-Extractoren
Überschreiben Sie Content-Selektoren in `ScrapingConfig`

### Zusätzliche Analyse-Metriken
Erweitern Sie die `DataStructureAnalyzer` Klasse

### Integration mit anderen Tools
Verwenden Sie die programmatische API für benutzerdefinierte Workflows

## 📞 Support

Bei Fragen oder Problemen:
1. Prüfen Sie die `src/scraper/hyperparameters.py` für Parameter-Dokumentation
2. Verwenden Sie `--verbose` für detaillierte Logs
3. Prüfen Sie die Output-Ordner für gespeicherte Ergebnisse
4. Testen Sie mit einzelnen URLs vor Batch-Processing