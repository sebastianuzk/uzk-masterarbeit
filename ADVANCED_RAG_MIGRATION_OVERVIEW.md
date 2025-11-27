# Advanced RAG - Migrations-Übersicht

**Datum:** 26. November 2025  
**Status:** Migration abgeschlossen ✅

## 📋 Zusammenfassung

Alle Advanced-RAG-Techniken wurden erfolgreich von `src/scraper/utils` nach `src/advanced_rag/pre_retrieval` migriert und die Duplikate entfernt.

## ✅ Migrierte Module

### Pre-Retrieval Techniken

| Modul | Alt (❌ Gelöscht) | Neu (✅ Aktiv) | Status |
|-------|-------------------|----------------|--------|
| **ContentDeduplicator** | `src/scraper/utils/content_deduplicator.py` | `src/advanced_rag/pre_retrieval/deduplication.py` | ✅ Migriert |
| **ContentCleaner** | `src/scraper/utils/content_cleaner.py` | `src/advanced_rag/pre_retrieval/cleaning.py` | ✅ Migriert |
| **SemanticChunker** | `src/scraper/utils/semantic_chunker.py` | `src/advanced_rag/pre_retrieval/chunking.py` | ✅ Migriert |

### Techniken-Details

#### 1. ContentDeduplicator
**Technologie:** Shingling + MinHash + Jaccard Similarity  
**Features:**
- Exakte Duplikatserkennung via SHA256-Hash
- Near-Duplicate Detection via Shingles (n-grams)
- Konfigurierbare Similarity Threshold (default: 0.85)
- Batch-Processing Support

**Verwendung:**
```python
from src.advanced_rag.pre_retrieval import ContentDeduplicator

dedup = ContentDeduplicator(similarity_threshold=0.85, shingle_size=3)
is_dup, reason = dedup.is_duplicate(text, url)
unique, duplicates = dedup.deduplicate_batch(documents)
```

#### 2. ContentCleaner
**Technologie:** BeautifulSoup + Regex + Heuristiken  
**Features:**
- HTML-Boilerplate-Entfernung (Navigation, Footer, Cookie-Banner)
- Wiederholte Textzeilen-Entfernung
- Text-Normalisierung (Whitespace, Zeilenumbrüche)
- Content-Quality-Checks (Länge, Wortanzahl, durchschn. Wortlänge)

**Verwendung:**
```python
from src.advanced_rag.pre_retrieval import ContentCleaner

cleaner = ContentCleaner()
cleaned_text = cleaner.clean_html(html_content)
clean_doc = cleaner.clean_document({'content': text})
is_substantial = cleaner.is_substantial_content(text)
```

#### 3. SemanticChunker
**Technologie:** Multi-Strategie Chunking  
**Features:**
- **Paragraph-based:** Natürliche Textgrenzen (Absätze)
- **Header-aware:** Strukturerhaltung mit Überschriften
- **Smart Chunking:** Kombination beider Methoden
- Konfigurierbarer Chunk-Overlap für Kontext-Erhaltung
- Token-basierte Größenkontrolle

**Verwendung:**
```python
from src.advanced_rag.pre_retrieval import SemanticChunker

chunker = SemanticChunker(
    max_chunk_size=500,
    chunk_overlap=50,
    preserve_structure=True
)

# Paragraphen-basiert
chunks = chunker.chunk_by_paragraphs(text)

# Mit Header-Kontext
chunks_with_headers = chunker.chunk_with_headers(text)

# Intelligente Strategie-Auswahl
chunks = chunker.chunk_document(text, url, metadata)
```

## 🔄 Import-Anpassungen

### Vorher (Alte Imports):
```python
# ❌ Veraltet - Duplikate aus scraper/utils
from src.scraper.utils.content_deduplicator import ContentDeduplicator
from src.scraper.utils.content_cleaner import ContentCleaner
from src.scraper.utils.semantic_chunker import SemanticChunker
```

### Nachher (Neue Imports):
```python
# ✅ Korrekt - Zentrale Advanced-RAG-Module
from src.advanced_rag.pre_retrieval import (
    ContentDeduplicator,
    ContentCleaner,
    SemanticChunker
)
```

### Aktualisierte Dateien

| Datei | Status | Imports Aktualisiert |
|-------|--------|---------------------|
| `src/scraper/pipelines/crawler_scraper_pipeline.py` | ✅ | Ja (bereits korrekt) |
| `src/advanced_rag/__init__.py` | ✅ | Ja (bereits korrekt) |
| `src/scraper/utils/content_deduplicator.py` | ❌ | Gelöscht |
| `src/scraper/utils/content_cleaner.py` | ❌ | Gelöscht |
| `src/scraper/utils/semantic_chunker.py` | ❌ | Gelöscht |

## 📂 Neue Struktur

```
src/
├── advanced_rag/                          # ✅ Zentrale RAG-Techniken
│   ├── pre_retrieval/                    # Pre-Retrieval Optimierungen
│   │   ├── deduplication.py             # ContentDeduplicator
│   │   ├── cleaning.py                  # ContentCleaner
│   │   └── chunking.py                  # SemanticChunker
│   ├── retrieval/                        # Retrieval Techniken
│   │   └── __init__.py                  # (leer, geplant)
│   ├── post_retrieval/                   # Post-Retrieval Optimierungen
│   │   └── __init__.py                  # (leer, geplant)
│   ├── config.py                         # RAG-Konfiguration
│   ├── presets.py                        # Vordefinierte Configs
│   └── README.md                         # Dokumentation
│
└── scraper/
    ├── utils/                            # ✅ Nur Scraper-Utilities
    │   ├── content_database.py          # SQLite Content Storage
    │   ├── html_cache.py                # HTML Caching
    │   ├── pdf_extractor.py             # PDF Text Extraction
    │   ├── url_cache.py                 # URL State Caching
    │   ├── error_cache.py               # Error Tracking
    │   └── full_content_cache.py        # Full Content Cache
    └── pipelines/
        └── crawler_scraper_pipeline.py   # ✅ Verwendet advanced_rag

```

## 🎯 Verbleibende Scraper-Utils

Die folgenden Module bleiben in `src/scraper/utils`, da sie **spezifisch für Web-Scraping** sind:

| Modul | Zweck | Kategorie |
|-------|-------|-----------|
| `content_database.py` | SQLite-Datenbank für offline Content | Persistence |
| `html_cache.py` | HTML-Caching mit Kompression | Caching |
| `pdf_extractor.py` | PDF-Text-Extraktion (PyPDF2, pdfplumber) | Extraction |
| `url_cache.py` | URL-Status und Scraping-State | Caching |
| `error_cache.py` | Fehlerprotokollierung und Retry-Logic | Error Handling |
| `full_content_cache.py` | Vollständiger Content Cache | Caching |

**Begründung:** Diese Module sind **nicht Teil der RAG-Pipeline**, sondern **Scraper-Infrastruktur**.

## 🚀 Verwendung in Pipelines

### Crawler-Scraper Pipeline

Die Pipeline verwendet alle drei Pre-Retrieval-Techniken:

```python
from src.advanced_rag.pre_retrieval import (
    ContentDeduplicator,
    ContentCleaner,
    SemanticChunker
)

# Initialisierung
deduplicator = ContentDeduplicator(similarity_threshold=0.85)
cleaner = ContentCleaner()
chunker = SemanticChunker(max_chunk_size=500)

# Pipeline-Integration (Stage 3: Content Processing)
for content in scraped_data:
    # 1. Deduplication
    is_dup, reason = deduplicator.is_duplicate(
        content.content, 
        content.url
    )
    if is_dup:
        continue
    
    # 2. Cleaning
    cleaned = cleaner._clean_text(content.content)
    
    # 3. Chunking
    chunks = chunker.chunk_document(
        text=cleaned,
        url=content.url,
        metadata=content.metadata
    )
```

### Offline-Scraper (Geplant)

Der Offline-Scraper wird die Content Database nutzen und dieselben Advanced-RAG-Techniken anwenden:

```python
from src.scraper.utils.content_database import ContentDatabase
from src.advanced_rag.pre_retrieval import (
    ContentCleaner,
    SemanticChunker
)

# Content aus Datenbank laden
content_db = ContentDatabase("data/content_database.db")
documents = content_db.list_documents()

# Advanced-RAG-Pipeline
cleaner = ContentCleaner()
chunker = SemanticChunker(max_chunk_size=500)

for doc in documents:
    # Content aus DB abrufen (bereits dedupliziert)
    url, title, content = content_db.get_document(doc['id'])
    
    # Cleaning + Chunking
    cleaned = cleaner._clean_text(content)
    chunks = chunker.chunk_document(cleaned, url, doc['metadata'])
```

## 📊 Nächste Schritte

### Kurzfristig (Diese Session):
1. ✅ Migration der Pre-Retrieval-Techniken abgeschlossen
2. ⏳ Offline-Scraper implementieren (nutzt content_database.db + Advanced-RAG)
3. ⏳ Testen: Offline-Pipeline mit 2675 Dokumenten

### Mittelfristig:
1. ⏳ Retrieval-Techniken implementieren (Hybrid Search, Re-Ranking)
2. ⏳ Post-Retrieval-Techniken erweitern (Context Compression)
3. ⏳ RAGAS-Evaluation: Naive vs. Advanced RAG

### Langfristig:
1. ⏳ Query-Optimierung (Pre-Retrieval): Query Expansion, HyDE
2. ⏳ Advanced Re-Ranking: Cross-Encoder statt Distance-basiert
3. ⏳ Production-Ready Deployment

## 🔍 Überprüfung

### Imports überprüfen:
```bash
# Keine Importe aus alten Pfaden
grep -r "from src.scraper.utils.content_deduplicator" src/
grep -r "from src.scraper.utils.content_cleaner" src/
grep -r "from src.scraper.utils.semantic_chunker" src/

# Sollte keine Treffer geben ✅
```

### Module-Existenz:
```bash
# Alte Module gelöscht
ls src/scraper/utils/content_deduplicator.py  # ❌ Existiert nicht mehr
ls src/scraper/utils/content_cleaner.py       # ❌ Existiert nicht mehr
ls src/scraper/utils/semantic_chunker.py      # ❌ Existiert nicht mehr

# Neue Module vorhanden
ls src/advanced_rag/pre_retrieval/deduplication.py  # ✅ Existiert
ls src/advanced_rag/pre_retrieval/cleaning.py       # ✅ Existiert
ls src/advanced_rag/pre_retrieval/chunking.py       # ✅ Existiert
```

### Pipeline funktioniert:
```bash
# Testen der Pipeline mit neuen Imports
python -c "from src.advanced_rag.pre_retrieval import ContentDeduplicator, ContentCleaner, SemanticChunker; print('✅ Imports erfolgreich')"
```

## 📝 Zusammenfassung

**Ergebnis:**
- ✅ 3 Advanced-RAG-Module erfolgreich migriert
- ✅ Duplikate aus `src/scraper/utils` entfernt
- ✅ Imports in Pipeline bereits korrekt
- ✅ Scraper-spezifische Utils bleiben unberührt
- ✅ Klare Trennung: RAG-Techniken vs. Scraper-Infrastruktur

**Vorteile:**
- 🎯 Zentrale RAG-Techniken in `src/advanced_rag`
- 🔧 Modulare, wiederverwendbare Komponenten
- 📊 Klare Separation of Concerns
- 🧪 Einfacheres Testing und Evaluierung
- 📚 Bessere Dokumentation und Wartbarkeit

**Nächster Fokus:**
Offline-Scraper implementieren, der die Content Database nutzt und alle Advanced-RAG-Techniken anwendet (Cleaning, Chunking) für die 2675 gespeicherten Dokumente.
