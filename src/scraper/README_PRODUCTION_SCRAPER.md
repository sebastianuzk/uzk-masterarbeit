# Production Scraper - README

## Übersicht

Der **Production Scraper** (`run_production_scraper.py`) ist das zentrale Skript zur Verarbeitung der gecrawlten WiSo-Fakultätsdokumente. Er transformiert Rohdaten (HTML, PDF) aus der `content_database.db` in eine durchsuchbare Vektordatenbank (ChromaDB).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION SCRAPER PIPELINE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐    │
│  │ content_database│  ──► │  PREPROCESSING   │  ──► │    ChromaDB     │    │
│  │    (SQLite)     │      │  Decompress,     │      │  (Vector Store) │    │
│  │  2675 Dokumente │      │  Clean, Chunk    │      │  46,353 Chunks  │    │
│  └─────────────────┘      └──────────────────┘      └─────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Zwei Modi: Naive vs. Advanced RAG

Der Scraper unterstützt **zwei Modi**, gesteuert über die Umgebungsvariable `RAG_NAIVE_SETUP`:

| Modus | Umgebungsvariable | Beschreibung |
|-------|-------------------|--------------|
| **Naive RAG** | `RAG_NAIVE_SETUP=true` | Baseline-Setup ohne Advanced Pre-Retrieval |
| **Advanced RAG** | `RAG_NAIVE_SETUP=false` | Mit Semantic Chunking, Deduplication, Multi-Collection etc. |

---

## Naive RAG Variante (Baseline)

### Überblick

Die **Naive RAG Variante** ist das Baseline-Setup für Evaluation. Sie nutzt einfache, aber effektive Techniken ohne komplexe Pre-Retrieval-Optimierungen.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          NAIVE RAG PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 1: Decompress → Clean → Chunk (in einem Durchgang)                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │  gzip       │ ─► │ HTML→Text   │ ─► │   Naive     │ ─► │  Single     │  │
│  │ Decompress  │    │  Cleaning   │    │  Chunking   │    │ Collection  │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Phase 2: Embedding → Store                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │  BGE-M3     │ ─► │  Normalize  │ ─► │  ChromaDB   │                      │
│  │ Embeddings  │    │  Vectors    │    │   Store     │                      │
│  └─────────────┘    └─────────────┘    └─────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Deaktivierte Features (Naive Mode)

- ❌ **SemanticChunker** - kein semantisches Chunking
- ❌ **ContentCleaner** - kein erweitertes Cleaning  
- ❌ **Deduplication** - keine Duplikaterkennung (Exact/Near)
- ❌ **CollectionCategorizer** - keine Multi-Collection
- ❌ **Hybrid Retrieval** - kein BM25 Sparse Index

### Aktive Features (Naive Mode)

- ✅ **Naive Chunking** - Character-basiertes Splitting mit Overlap
- ✅ **Single Collection** - Alle Dokumente in `wiso_documents`
- ✅ **Dense Embeddings** - BGE-M3 Embeddings (1024 Dimensionen)
- ✅ **ChromaDB** - Persistente Vektordatenbank

---

## Preprocessing Pipeline (Naive Mode)

### 1. Dekomprimierung

Die Rohdokumente sind gzip-komprimiert in der SQLite-Datenbank gespeichert:

```python
def decompress_content(compressed_data: bytes) -> str:
    """Dekomprimiere gzip-Content."""
    return gzip.decompress(compressed_data).decode('utf-8')
```

**Bibliothek:** `gzip` (Python Standard Library)

---

### 2. HTML-zu-Text Extraktion

Die Funktion `naive_extract_text_from_html()` konvertiert HTML zu Markdown-ähnlichem Text:

```python
def naive_extract_text_from_html(html: str) -> str:
    """
    Naive HTML-zu-Text Extraktion mit Strukturerhaltung.
    Konvertiert HTML zu Markdown-ähnlichem Text.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    # ...
```

**Bibliothek:** `BeautifulSoup4` (bs4)

#### Entfernte Elemente

| Kategorie | Entfernte Tags/Klassen |
|-----------|------------------------|
| Unsichtbar | `script`, `style`, `head`, `meta`, `link`, `noscript`, `iframe` |
| Layout | `nav`, `header`, `footer`, `aside` |
| Klassen/IDs | `menu`, `nav`, `sidebar`, `breadcrumb`, `cookie`, `banner`, `popup`, `modal` |
| UI-Texte | "Menü schließen", "zum Inhalt springen", "Sprache wechseln" etc. |

#### Strukturerhaltung (→ Markdown)

| HTML | Markdown |
|------|----------|
| `<h1>...<h6>` | `#` bis `######` Überschriften |
| `<ul><li>` | `- ` Listenelemente |
| `<ol><li>` | `1. ` Nummerierte Listen |
| `<blockquote>` | `> ` Zitate |
| `<p>`, `<div>` | Zeilenumbrüche |
| `<td>`, `<th>` | Tab-getrennt |

#### Whitespace-Normalisierung

```python
text = re.sub(r'[ \t]+', ' ', text)      # Mehrere Spaces → ein Space
text = re.sub(r'\n{3,}', '\n\n', text)   # Max 2 Zeilenumbrüche
```

---

### 3. PDF-Text-Bereinigung

Für bereits extrahierten PDF-Text (aus dem Crawler):

```python
def naive_clean_text(text: str) -> str:
    """Naive Text-Bereinigung für bereits extrahierten Text (z.B. PDFs)."""
    text = re.sub(r'\s+', ' ', text)                    # Normalisiere Leerzeichen
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)      # Mehrfache Zeilenumbrüche
    return text.strip()
```

**Bibliothek:** `re` (Python Standard Library)

---

### 4. Naive Chunking

Character-basiertes Chunking mit konfigurierbarem Overlap:

```python
def naive_chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    """
    Naive Chunking: Einfaches Character-basiertes Chunking mit Overlap.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Nur hinzufügen wenn nicht zu klein
        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())
        
        # Nächster Start mit Overlap
        start = end - overlap
    
    return chunks
```

#### Hyperparameter (Naive Chunking)

| Parameter | Wert | Quelle |
|-----------|------|--------|
| `chunk_size` | 1500 Zeichen | `rag_config.naive_chunking_max_size` |
| `overlap` | 300 Zeichen | `rag_config.naive_chunking_overlap` |
| `min_chunk_size` | 50 Zeichen | Hardcoded |

#### Beispiel

```
Text: 3000 Zeichen
chunk_size: 1500
overlap: 300

Chunk 1: Zeichen 0-1500
Chunk 2: Zeichen 1200-2700  (Overlap: 300)
Chunk 3: Zeichen 2400-3000  (Overlap: 300)
```

---

### 5. Embedding-Generierung

**Modell:** BAAI/bge-m3 (Multilingual, 1024 Dimensionen)

```python
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True)
embedding_model.max_seq_length = 1024  # Token-Limit

# Batch-Embedding mit Normalisierung
embeddings = embedding_model.encode(
    chunks, 
    show_progress_bar=False,
    normalize_embeddings=True,  # Für Cosine-Similarity
    convert_to_numpy=True
)
```

**Bibliothek:** `sentence-transformers`

#### Embedding-Parameter

| Parameter | Wert |
|-----------|------|
| Model | `BAAI/bge-m3` |
| Dimensionen | 1024 |
| Max Sequence Length | 1024 Tokens |
| Normalisierung | ✅ (für Cosine-Similarity) |
| Batch-Größe | 512 |

---

### 6. Vektorspeicherung (ChromaDB)

```python
import chromadb

client = chromadb.PersistentClient(path="data/vector_db")

collection = client.create_collection(
    name='wiso_documents',
    metadata={"description": "WiSo Fakultät - Alle Dokumente"}
)

collection.add(
    documents=chunks,
    embeddings=embeddings,
    ids=[f"{content_type}_{doc_id}_chunk_{i}" for i, ...],
    metadatas=[{
        'doc_id': doc_id,
        'url': url,
        'title': title,
        'content_type': content_type,  # 'html' oder 'pdf'
        'chunk_index': i,
        'total_chunks': len(chunks),
        'char_count': len(chunk),
        'token_count': token_count
    }]
)
```

**Bibliothek:** `chromadb`

#### Chunk-Metadaten

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `doc_id` | string | Referenz zur Quell-Dokument-ID |
| `url` | string | URL/Pfad des Quelldokuments |
| `title` | string | Dokumenttitel |
| `content_type` | string | `html` oder `pdf` |
| `chunk_index` | int | Position im Dokument (0-basiert) |
| `total_chunks` | int | Gesamtzahl Chunks dieses Dokuments |
| `char_count` | int | Zeichenlänge des Chunks |
| `token_count` | int | BGE-M3 Token-Anzahl |

---

## Verwendete Libraries

### Core Dependencies

| Library | Version | Zweck |
|---------|---------|-------|
| `chromadb` | ≥0.4 | Vektordatenbank |
| `sentence-transformers` | ≥2.2 | Embedding-Modell (BGE-M3) |
| `beautifulsoup4` | ≥4.12 | HTML-Parsing |
| `tqdm` | ≥4.65 | Fortschrittsanzeige |
| `pandas` | ≥2.0 | Excel-Export |
| `openpyxl` | ≥3.1 | Excel-Schreiben |
| `numpy` | ≥1.24 | Numerische Berechnungen |

### Standard Library

| Modul | Zweck |
|-------|-------|
| `sqlite3` | Content-Database Zugriff |
| `gzip` | Dekomprimierung |
| `re` | Regex für Text-Cleaning |
| `pathlib` | Pfadoperationen |
| `pickle` | Checkpoint-Serialisierung |
| `time`, `datetime` | Timing & Timestamps |

---

## Konfiguration

### Umgebungsvariablen (rag.env)

```bash
# Naive Baseline aktivieren
RAG_NAIVE_SETUP=true

# Chunking-Parameter (werden auch im Naive Mode gelesen)
NAIVE_CHUNKING_MAX_SIZE=1500
NAIVE_CHUNKING_OVERLAP=300

# Embedding-Modell
SENTENCE_TRANSFORMER_MODEL=BAAI/bge-m3
EMBEDDING_MAX_SEQ_LENGTH=1024
```

### Pfade

| Pfad | Beschreibung |
|------|--------------|
| `data/content_database.db` | Eingabe: Gecrawlte Dokumente |
| `data/vector_db/` | Ausgabe: ChromaDB Vektordatenbank |
| `checkpoints/` | Checkpoint-Dateien für Resume |
| `src/evaluation/data/` | Excel-Statistiken |

---

## Ausführung

### Naive Baseline starten

```bash
# Windows (PowerShell)
$env:RAG_NAIVE_SETUP="true"
python src/scraper/run_production_scraper.py

# Linux/Mac
RAG_NAIVE_SETUP=true python src/scraper/run_production_scraper.py
```

### VS Code Task

```json
{
    "label": "Run Production Scraper",
    "type": "shell",
    "command": "& \"${workspaceFolder}\\Masterarbeit\\Scripts\\python.exe\" src/scraper/run_production_scraper.py",
    "group": "build"
}
```

---

## Pipeline-Ablauf (Naive Mode)

```
SCHRITT 1: Prüfe bestehenden Fortschritt
├── ChromaDB Collections prüfen
└── Phase 1 Checkpoint laden (falls vorhanden)

SCHRITT 2: Module initialisieren
├── ❌ ContentCleaner (deaktiviert)
├── ❌ SemanticChunker (deaktiviert)
├── ❌ Deduplication (deaktiviert)
├── ❌ CollectionCategorizer (deaktiviert)
└── ✅ Embedding-Modell (BGE-M3)

SCHRITT 3: Dokumente laden
└── SELECT * FROM documents (2675 Dokumente)

SCHRITT 4: Dokumente verarbeiten (Phase 1)
├── Decompress (gzip)
├── Clean (HTML→Text oder PDF→Text)
├── Chunk (Naive Chunking: 1500/300)
└── Checkpoint speichern

SCHRITT 5: Embeddings erstellen (Phase 2)
├── Batch-Tokenisierung (Token-Counts)
├── Batch-Embedding (512er Batches)
└── ChromaDB speichern (5000er Batches)

SCHRITT 6: Statistiken exportieren
└── Excel: src/evaluation/data/scraping_stats_Naive.xlsx
```

---

## Checkpoint-System

Der Scraper unterstützt **inkrementelles Fortsetzen** bei Abbrüchen:

### Phase 1 Checkpoint

Nach Verarbeitung aller Dokumente (vor Embedding) wird ein Checkpoint gespeichert:

```python
checkpoints/phase1_processed_docs.pkl
```

Inhalt: `docs_by_collection` Dictionary mit allen verarbeiteten Chunks.

### Collection-Level Resume

Bereits befüllte ChromaDB-Collections werden automatisch übersprungen:

```
✅ wiso_documents: 46,353 Chunks (wird übersprungen)
```

---

## Output-Statistiken

### Konsolen-Ausgabe (Beispiel)

```
✅ PRODUKTIVER RUN ABGESCHLOSSEN
================================================================================

⏱️  Laufzeit: 8 Minuten 32 Sekunden
📊 Verarbeitete Dokumente: 2,675
   • HTML: 2,242
   • PDF: 433
   • Übersprungen: 3

📦 Erstellte Chunks: 46,353
   • Durchschnitt: 17.3 Chunks/Dokument

🗂️  Collections:
   • wiso_documents: 46,353 Chunks

💾 Vektordatenbank:
   • Pfad: data/vector_db
   • Collections: 1
   • Embedding-Modell: BAAI/bge-m3
```

### Excel-Export

Nach jedem Run wird eine Excel-Datei mit Statistiken erstellt:

**Pfad:** `src/evaluation/data/scraping_stats_Naive.xlsx`

**Sheets:**
1. **Übersicht** - Gesamtstatistiken (Dokumente, Chunks, Laufzeit)
2. **Chunking-Parameter** - Verwendete Hyperparameter
3. **Collections** - Chunk-Verteilung pro Collection
4. **Chunk-Verteilung** - Größenverteilung (Zeichen)
5. **Token-Verteilung** - Token-Verteilung (BGE-M3)

---

## Vergleich: Naive vs. Advanced

| Aspekt | Naive RAG | Advanced RAG |
|--------|-----------|--------------|
| **Chunking** | Character-basiert (1500/300) | Semantic Chunking (Embeddings) |
| **Cleaning** | Basis HTML→Markdown | Erweitertes Content Cleaning |
| **Deduplication** | Keine | Exact + Near (MinHash+LSH) |
| **Collections** | Single (`wiso_documents`) | Multi-Collection (kategorisiert) |
| **Retrieval** | Nur Dense (Cosine) | Hybrid (Dense + BM25 + RRF) |
| **Chunk-Anzahl** | ~46,353 | ~38,000 (nach Dedup) |

---

## Troubleshooting

### Speicherprobleme

Bei großen Datenmengen kann der RAM knapp werden:

```python
# Batch-Größe reduzieren
BATCH_SIZE = 256  # Statt 512
```

### ChromaDB Fehler

```bash
# Collection löschen und neu erstellen
rm -rf data/vector_db/
```

### Checkpoint-Probleme

```bash
# Checkpoint löschen für Neustart
rm checkpoints/phase1_processed_docs.pkl
```

---

## Verwandte Dokumentation

- [ARCHITECTURE_NAIVE_BASELINE.md](../../docs/ARCHITECTURE_NAIVE_BASELINE.md) - Gesamtarchitektur der Naive Baseline
- [hyperparameter_documentation.md](../../hyperparameter_documentation.md) - Alle Hyperparameter
- [rag_config.py](../advanced_rag/rag_config.py) - Konfigurationsklasse
- [rag.env](../advanced_rag/rag.env) - Umgebungsvariablen
