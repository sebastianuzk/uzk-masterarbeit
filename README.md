# Autonomer RAG-Chatbot – WiSo-Fakultät Universität zu Köln

Ein autonomer Chatbot-Agent für die WiSo-Fakultät der Universität zu Köln, basierend auf LangChain und LangGraph. Das System kombiniert einen vollständig lokal betriebenen LLM-Stack (Ollama) mit einer umfangreichen RAG-Pipeline zur Beantwortung von Fragen rund um die WiSo-Fakultät.

## Überblick

- Beantwortet Fragen zur WiSo-Fakultät (Studiengänge, Bewerbung, Services, Prüfungsamt, etc.)
- Basiert auf einem gecrawlten Corpus aus ~2.675 Dokumenten (HTML + PDF) der WiSo-Website
- Vollständig lokal betrieben – kein externer API-Zwang für Kerndienste
- Konfigurierbare RAG-Pipeline: Naive Baseline bis hin zu Hybrid-Retrieval + ReRanking + MMR

## Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| LLM-Backend | Ollama (`llama3.1:8b`, lokal) |
| Agent-Framework | LangChain + LangGraph (`create_react_agent`) |
| Embedding-Modell | BGE-M3 (`BAAI/bge-m3`, lokal) |
| Vektordatenbank | ChromaDB (persistent, `data/vector_db/`) |
| Sparse Retrieval | BM25 via `rank-bm25` |
| Fusion | Reciprocal Rank Fusion (RRF) |
| Reranking | Voyage AI / Cohere / lokaler CrossEncoder (BGE-Reranker) |
| Diversity | Maximum Marginal Relevance (MMR) |
| Web-UI | Streamlit |
| Evaluation | RAGAS + LangSmith Tracing |
| Content-DB | SQLite (`data/content_database.db`) |

## Corpus-Status

```
Dokumente in Content-DB:   ~2.675  (HTML: ~2.242 | PDF: ~433)
Chunks in Vektordatenbank: ~45.960 (Collection: wiso_documents)
Embedding-Modell:           BAAI/bge-m3 (L2-normalisiert)
```

## Projektstruktur

```
uzk-masterarbeit/
├── src/
│   ├── agent/
│   │   └── react_agent.py                  # LangGraph ReAct-Agent
│   ├── tools/
│   │   └── rag_tool.py                     # UniversityRAGTool (Naive/Advanced/Sparse)
│   ├── scraper/
│   │   ├── pipelines/
│   │   │   └── crawler_scraper_pipeline.py # Schritt 1: Website-Crawler
│   │   ├── tools/
│   │   │   └── import_to_content_db.py     # Schritt 2: Cache → SQLite
│   │   └── run_production_scraper.py       # Schritt 3: SQLite → ChromaDB
│   ├── advanced_rag/
│   │   ├── rag_config.py                   # RAGConfig (liest rag.env)
│   │   ├── pre_retrieval/
│   │   │   ├── chunking.py                 # SemanticChunker
│   │   │   └── deduplication.py            # Exact + Near-Dedup
│   │   ├── retrieval/
│   │   │   └── hybrid_retrieval_rrf.py     # BM25 + RRF
│   │   └── post_retrieval/
│   │       ├── reranking.py                # ReRanker (Voyage/Cohere/Local)
│   │       └── maximum_marginal_relevance.py
│   ├── evaluation/
│   │   ├── ragas_evaluation.py             # Vollständige RAGAS-Evaluation
│   │   ├── ragas_selective_evaluation.py   # Selektive / Batch-Evaluation
│   │   └── data/
│   │       └── Testset.CSV                 # Evaluations-Testset
│   └── ui/
│       └── streamlit_app.py                # Chat-Interface
├── config/
│   └── settings.py                         # Globale Einstellungen (liest .env)
├── data/
│   ├── content_database.db                 # SQLite (Dokumente komprimiert)
│   ├── vector_db/                          # ChromaDB
│   ├── html_cache/                         # Crawler-Output (html_cache.db)
│   ├── pdf_cache/                          # Crawler-Output (*.pdf)
│   └── sparse_index/                       # BM25 Index (pickle)
├── backups/                                # Vektordatenbank-Backups
├── docs/
│   └── SYSTEM_GUIDE.md                     # Betriebsanleitung
├── tests/
├── .env                                    # Umgebungsvariablen (lokal, nicht im Repo)
├── .env.example                            # Vorlage
├── src/advanced_rag/rag.env                # RAG-Feature-Flags
└── requirements.txt
```

## Schnellstart

### Voraussetzungen

- Python 3.10+
- [Ollama](https://ollama.com) installiert und gestartet
- `.env`-Datei im Projektstamm (Vorlage: `.env.example`)

```powershell
# Modell laden (einmalig)
ollama pull llama3.1:8b
```

### Installation

```powershell
# Virtuelle Umgebung erstellen und aktivieren
python -m venv Masterarbeit
& ".\Masterarbeit\Scripts\Activate.ps1"

# Abhängigkeiten installieren
pip install -r requirements.txt
```

### Corpus aufbauen (einmalig)

```powershell
# Schritt 1 – Crawler (überspringen, falls Cache vorhanden)
& ".\Masterarbeit\Scripts\python.exe" -m src.scraper.pipelines.crawler_scraper_pipeline

# Schritt 2 – Cache in SQLite importieren
& ".\Masterarbeit\Scripts\python.exe" -m src.scraper.tools.import_to_content_db

# Schritt 3 – Vektordatenbank aufbauen
& ".\Masterarbeit\Scripts\python.exe" -m src.scraper.run_production_scraper
```

### Chatbot starten

```powershell
& ".\Masterarbeit\Scripts\python.exe" -m streamlit run src/ui/streamlit_app.py
```

Öffnet [http://localhost:8501](http://localhost:8501) im Browser.

## Konfiguration

### RAG-Pipeline – `src/advanced_rag/rag.env`

Steuert alle Feature-Flags (Semantic Chunking, Deduplication, Hybrid Retrieval, ReRanking, MMR) und Hyperparameter. Änderungen an Pre-Retrieval-Flags erfordern einen Neuaufbau der Vektordatenbank (Schritt 3).

### Systemparameter – `.env`

LLM-Modell, Embedding-Modell, Temperaturen, API-Schlüssel. Vorlage: `.env.example`.

Eine vollständige Beschreibung aller Parameter und Pipelines findet sich in **[`docs/SYSTEM_GUIDE.md`](docs/SYSTEM_GUIDE.md)**.

## Evaluation

```powershell
# Vollständige Evaluation (alle Testfragen)
& ".\Masterarbeit\Scripts\python.exe" src/evaluation/ragas_evaluation.py

# Selektive Evaluation (bestimmte IDs / Checkpoint-Fortsetzung)
& ".\Masterarbeit\Scripts\python.exe" src/evaluation/ragas_selective_evaluation.py
```

Testset: `src/evaluation/data/Testset.CSV`. Metriken: MRR@5, Hit@5, Faithfulness, Context Recall u. a. via RAGAS + LangSmith.

## Tests

```powershell
& ".\Masterarbeit\Scripts\python.exe" -m pytest tests/
```

---

Masterarbeit – Universität zu Köln, WiSo-Fakultät