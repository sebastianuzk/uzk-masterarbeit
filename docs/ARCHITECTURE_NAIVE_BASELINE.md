# Naive RAG Baseline - Systemarchitektur

## Übersicht

Dieses Dokument beschreibt die Architektur der **Naive RAG Baseline** für den autonomen Chatbot-Agenten der WiSo-Fakultät der Universität zu Köln.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BENUTZERINTERFACE                               │
│                         (Streamlit Web UI)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         REACT AGENT                                      │
│                    (LangGraph + ChatOllama)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  System Prompt │ Tool Selection │ Response Generation           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         RAG TOOL                                         │
│                  (university_knowledge_search)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Query Embedding │ Vector Search │ Top-K Retrieval              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      VECTOR DATABASE                                     │
│                        (ChromaDB)                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Collection: wiso_documents │ 46.353 Chunks │ 1024-dim Vectors  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Komponenten

### 1.1 Benutzerinterface (Streamlit)

| Aspekt | Details |
|--------|---------|
| **Framework** | Streamlit ≥1.29.0 |
| **Datei** | `src/ui/streamlit_app.py` |
| **Features** | Chat-Interface, Session-Management, LangSmith-Tracing |

```python
# Streamlit initialisiert den Agent und verwaltet die Chat-Historie
from src.agent.react_agent import create_react_agent
agent = create_react_agent()
response = agent.chat(user_message, session_id=session_id)
```

---

### 1.2 React Agent (LangGraph)

| Aspekt | Details |
|--------|---------|
| **Framework** | LangGraph ≥0.0.26 |
| **Datei** | `src/agent/react_agent.py` |
| **Architektur** | ReAct (Reasoning + Acting) |
| **LLM** | Ollama (lokal) |

#### LLM-Konfiguration

| Parameter | Wert | Beschreibung |
|-----------|------|--------------|
| **Modell** | `llama3.1:8b` | Meta Llama 3.1 (8B Parameter) |
| **Temperature** | 0.0 | Deterministische Antworten |
| **Context Window** | 14.500 Tokens | Adaptiv nach Modellgröße |
| **Max Output** | 2.048 Tokens | Begrenzt Endlos-Generierung |
| **Seed** | 42 | Reproduzierbarkeit |
| **Timeout** | 90s | Max. Zeit pro Request |

#### Agent-Erstellung

```python
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

# LLM initialisieren
llm = ChatOllama(
    model="llama3.1:8b",
    temperature=0.0,
    seed=42,
    num_ctx=14500,
    num_predict=2048
)

# ReAct Agent mit LangGraph erstellen
agent = create_react_agent(llm, tools=[rag_tool])
```

#### System Prompt

Der Agent nutzt einen spezialisierten System Prompt für:
- Fokus auf WiSo-Fakultät Themen
- Tool-Nutzung (immer erst suchen, dann antworten)
- Sprachanpassung (Deutsch/Englisch)
- Quellenbasierte Antworten

---

### 1.3 RAG Tool (Retrieval-Augmented Generation)

| Aspekt | Details |
|--------|---------|
| **Framework** | LangChain ≥0.1.0 |
| **Datei** | `src/tools/rag_tool.py` |
| **Klasse** | `UniversityRAGTool` (erbt von `BaseTool`) |

#### Naive Retrieval Pipeline

```
User Query
    │
    ▼
┌─────────────────────────────────────┐
│  1. Query Embedding                 │
│     BGE-M3 (1024 Dimensionen)       │
│     + L2-Normalisierung             │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  2. Vector Search (ChromaDB)        │
│     Cosine Similarity               │
│     Single Collection               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  3. Top-K Selection                 │
│     k=5 (konfigurierbar)            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  4. Context Formatting              │
│     Dokumente + Metadaten           │
└─────────────────────────────────────┘
```

#### Embedding-Modell

| Aspekt | Details |
|--------|---------|
| **Modell** | BAAI/bge-m3 |
| **Dimensionen** | 1024 |
| **Max Sequence Length** | 1024 Tokens |
| **Multilingual** | Ja (Deutsch/Englisch) |
| **Framework** | sentence-transformers ≥2.2.0 |

```python
from sentence_transformers import SentenceTransformer

embedding_model = SentenceTransformer("BAAI/bge-m3", trust_remote_code=True)
embedding_model.max_seq_length = 1024

# Query-Embedding mit Normalisierung
query_embedding = embedding_model.encode([query])
normalized = query_embedding / np.linalg.norm(query_embedding, axis=1, keepdims=True)
```

---

### 1.4 Vector Database (ChromaDB)

| Aspekt | Details |
|--------|---------|
| **Framework** | ChromaDB ≥0.4.0 |
| **Speicherort** | `data/vector_db/` |
| **Collection** | `wiso_documents` (Single Collection) |

#### Korpus-Statistiken

| Metrik | Wert |
|--------|------|
| **Gesamt Dokumente** | 2.272 |
| **Gesamt Chunks** | 46.353 |
| **Durchschn. Chunks/Dokument** | ~20 |
| **HTML-Dokumente** | 2.242 |
| **PDF-Dokumente** | 433 |

#### Sprachverteilung

| Sprache | Dokumente | Chunks |
|---------|-----------|--------|
| Deutsch | 1.102 (48,5%) | 26.382 (56,9%) |
| Englisch | 1.167 (51,4%) | 19.951 (43,0%) |

#### Chunk-Verteilung

| Statistik | Wert |
|-----------|------|
| Minimum | 10 Zeichen |
| Maximum | 1.500 Zeichen |
| Durchschnitt | 1.219 Zeichen |
| Median | 1.406 Zeichen |

---

### 1.5 Web Scraper

| Aspekt | Details |
|--------|---------|
| **Datei** | `src/scraper/run_production_scraper.py` |
| **Quelle** | wiso.uni-koeln.de |
| **Crawl-Datum** | 26. November 2025 |

#### Scraper-Pipeline (Naive Mode)

```
┌─────────────────────────────────────┐
│  1. Dokumente aus SQLite laden      │
│     content_database.db             │
│     (HTML + PDF, gzip-komprimiert)  │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  2. Text-Extraktion                 │
│     HTML → BeautifulSoup → Markdown │
│     PDF → pypdf/pdfplumber          │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  3. Naive Chunking                  │
│     Character-basiert               │
│     max_size=1500, overlap=300      │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  4. Embedding (BGE-M3)              │
│     Batch-Encoding (512 pro Batch)  │
│     L2-Normalisierung               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  5. ChromaDB Speicherung            │
│     Collection: wiso_documents      │
└─────────────────────────────────────┘
```

#### Naive Chunking

```python
def naive_chunk_text(text: str, chunk_size: int = 1500, overlap: int = 300) -> list:
    """Character-basiertes Chunking mit Overlap"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())
        start = end - overlap
    return chunks
```

---

## 2. Datenfluss

```
                    ┌──────────────────────────────────────────────────────────────┐
                    │                    OFFLINE (einmalig)                         │
                    │                                                               │
                    │  wiso.uni-koeln.de                                           │
                    │         │                                                     │
                    │         ▼                                                     │
                    │  ┌─────────────────┐                                         │
                    │  │  Web Crawler    │  → content_database.db (SQLite)         │
                    │  │  (2.675 Docs)   │    (HTML/PDF, gzip-komprimiert)         │
                    │  └─────────────────┘                                         │
                    │         │                                                     │
                    │         ▼                                                     │
                    │  ┌─────────────────┐                                         │
                    │  │  Production     │                                         │
                    │  │  Scraper        │  → vector_db/ (ChromaDB)                │
                    │  │  (Chunking +    │    (46.353 Chunks + Embeddings)         │
                    │  │   Embedding)    │                                         │
                    │  └─────────────────┘                                         │
                    └──────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────────────────────────────────────┐
                    │                    ONLINE (pro Anfrage)                       │
                    │                                                               │
                    │  User                                                         │
                    │    │                                                          │
                    │    ▼                                                          │
                    │  ┌─────────────────┐                                         │
                    │  │  Streamlit UI   │                                         │
                    │  └─────────────────┘                                         │
                    │    │                                                          │
                    │    ▼                                                          │
                    │  ┌─────────────────┐     ┌─────────────────┐                 │
                    │  │  ReAct Agent    │────▶│  RAG Tool       │                 │
                    │  │  (LangGraph)    │     │  (Vector Search)│                 │
                    │  └─────────────────┘     └─────────────────┘                 │
                    │    │                           │                              │
                    │    │                           ▼                              │
                    │    │                     ┌─────────────────┐                 │
                    │    │                     │  ChromaDB       │                 │
                    │    │                     │  (46.353 Chunks)│                 │
                    │    │                     └─────────────────┘                 │
                    │    │                           │                              │
                    │    ▼                           │                              │
                    │  ┌─────────────────┐◀──────────┘                             │
                    │  │  Ollama LLM     │  (Top-5 Chunks als Context)             │
                    │  │  (llama3.1:8b)  │                                         │
                    │  └─────────────────┘                                         │
                    │    │                                                          │
                    │    ▼                                                          │
                    │  Antwort                                                      │
                    └──────────────────────────────────────────────────────────────┘
```

---

## 3. Technologie-Stack

### 3.1 Frameworks & Libraries

| Kategorie | Library | Version | Zweck |
|-----------|---------|---------|-------|
| **Agent** | LangGraph | ≥0.0.26 | ReAct Agent Framework |
| | LangChain | ≥0.1.0 | Tool-Abstraktion |
| | langchain-ollama | ≥0.1.0 | Ollama-Integration |
| **LLM** | Ollama | - | Lokale LLM-Inferenz |
| | llama3.1:8b | 8B | Sprachmodell |
| **Embeddings** | sentence-transformers | ≥2.2.0 | Embedding-Berechnung |
| | BAAI/bge-m3 | - | Multilinguales Embedding-Modell |
| **Vector DB** | ChromaDB | ≥0.4.0 | Vektordatenbank |
| **UI** | Streamlit | ≥1.29.0 | Web-Interface |
| **Scraping** | BeautifulSoup4 | ≥4.12.2 | HTML-Parsing |
| | aiohttp | ≥3.8.0 | Async HTTP |
| | pypdf | ≥3.0.0 | PDF-Extraktion |
| **Tracing** | LangSmith | ≥0.1.0 | Observability |

### 3.2 Systemanforderungen

| Komponente | Anforderung |
|------------|-------------|
| **GPU VRAM** | 8 GB (für LLM + Embeddings) |
| **RAM** | 16 GB empfohlen |
| **Storage** | ~5 GB (Modelle + Vektordatenbank) |
| **Python** | ≥3.10 |

### 3.3 VRAM-Aufteilung (8 GB GPU)

| Modell | VRAM |
|--------|------|
| Ollama llama3.1:8b | ~5.5 GB |
| BGE-M3 Embedding | ~1.5 GB |
| **Gesamt** | ~7.0 GB |

---

## 4. Konfiguration

### 4.1 Umgebungsvariablen (.env)

```bash
# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
TEMPERATURE=0.0

# Embeddings
SENTENCE_TRANSFORMER_MODEL=BAAI/bge-m3
EMBEDDING_MAX_SEQ_LENGTH=1024

# RAG
TOP_K=5
RAG_NAIVE_SETUP=true  # Naive Baseline aktivieren

# Tracing (optional)
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=wiso-chatbot
LANGSMITH_TRACING=true
```

### 4.2 Naive vs. Advanced RAG

| Feature | Naive (Baseline) | Advanced |
|---------|------------------|----------|
| Chunking | Character-basiert | Semantic Chunking |
| Deduplication | ❌ | Exact + Near (MinHash+LSH) |
| Retrieval | Dense-only | Hybrid (Dense + BM25) |
| ReRanking | ❌ | Voyage/Cohere/Local |
| MMR | ❌ | Maximum Marginal Relevance |
| Collections | Single | Multi-Collection |

---

## 5. Projektstruktur

```
uzk-masterarbeit/
├── config/
│   └── settings.py              # Zentrale Konfiguration
├── data/
│   ├── content_database.db      # Gecrawlte Rohdaten (SQLite)
│   └── vector_db/               # ChromaDB Vektordatenbank
├── src/
│   ├── agent/
│   │   └── react_agent.py       # LangGraph ReAct Agent
│   ├── scraper/
│   │   ├── core/                # Crawler-Komponenten
│   │   └── run_production_scraper.py
│   ├── tools/
│   │   └── rag_tool.py          # RAG Tool für Agent
│   └── ui/
│       └── streamlit_app.py     # Web-Interface
├── .env                         # Umgebungsvariablen
└── requirements.txt             # Python Dependencies
```

---

## 6. Ausführung

### 6.1 Voraussetzungen

```bash
# 1. Ollama installieren und Modell laden
ollama pull llama3.1:8b

# 2. Python-Umgebung erstellen
python -m venv Masterarbeit
.\Masterarbeit\Scripts\activate

# 3. Dependencies installieren
pip install -r requirements.txt
```

### 6.2 Scraper ausführen (einmalig)

```bash
# Naive Chunking aktivieren
set RAG_NAIVE_SETUP=true

# Production Scraper starten
python src/scraper/run_production_scraper.py
```

### 6.3 Chatbot starten

```bash
# Streamlit App starten
streamlit run src/ui/streamlit_app.py
```

---

## 7. Limitierungen der Naive Baseline

| Limitation | Auswirkung |
|------------|------------|
| **Kein Semantic Chunking** | Chunks können mitten im Satz enden |
| **Keine Deduplication** | Redundante Inhalte in der Vektordatenbank |
| **Nur Dense Retrieval** | Lexikalische Matches werden übersehen |
| **Kein ReRanking** | Suboptimale Ranking-Qualität |
| **Single Collection** | Keine thematische Gruppierung |

Diese Limitierungen werden durch die **Advanced RAG Techniken** adressiert.

---

*Erstellt: Februar 2026*
*Projekt: Masterarbeit - Autonomer Chatbot-Agent für die WiSo-Fakultät*
