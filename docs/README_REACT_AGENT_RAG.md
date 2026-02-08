# ReactAgent & RAG-Tool - Dokumentation

## Übersicht

Dieses Dokument beschreibt die Architektur und Funktionsweise des **ReactAgent** und des **RAG-Tools** (Retrieval-Augmented Generation) für den WiSo-Chatbot.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            REACT AGENT ARCHITEKTUR                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐      ┌───────────────┐      ┌─────────────────────────┐   │
│  │   User      │ ───► │  ReactAgent   │ ───► │  LangGraph              │   │
│  │   Query     │      │  (Orchestrator)│      │  create_react_agent()   │   │
│  └─────────────┘      └───────────────┘      └─────────────────────────┘   │
│                              │                          │                   │
│                              ▼                          ▼                   │
│                       ┌─────────────┐          ┌─────────────────┐         │
│                       │ System      │          │ Tool Execution  │         │
│                       │ Prompt      │          │ Loop            │         │
│                       └─────────────┘          └────────┬────────┘         │
│                                                         │                   │
│                              ┌──────────────────────────┘                   │
│                              ▼                                              │
│                       ┌─────────────────────┐                               │
│                       │ university_knowledge │                              │
│                       │ _search (RAG-Tool)  │                               │
│                       └──────────┬──────────┘                               │
│                                  │                                          │
│                                  ▼                                          │
│         ┌────────────────────────────────────────────────────┐              │
│         │                  RETRIEVAL PIPELINE                │              │
│         │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │              │
│         │  │ ChromaDB │  │ ReRanker │  │   MMR    │         │              │
│         │  │ (Dense)  │  │(optional)│  │(optional)│         │              │
│         │  └──────────┘  └──────────┘  └──────────┘         │              │
│         └────────────────────────────────────────────────────┘              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ReactAgent

### Beschreibung

Der **ReactAgent** ist ein autonomer Chatbot-Agent, der das ReAct-Pattern (Reasoning + Acting) implementiert. Er nutzt LangGraph's `create_react_agent()` für die Orchestrierung von LLM-Aufrufen und Tool-Nutzung.

**Datei:** `src/agent/react_agent.py`

### Architektur

```python
class ReactAgent:
    """Autonomer React Agent mit LangGraph und Ollama"""
    
    def __init__(self):
        self.llm = ChatOllama(...)           # Ollama LLM Backend
        self.tools = self._create_tools()    # RAG-Tool
        self.agent = create_langgraph_agent( # LangGraph ReAct Agent
            self.llm,
            self.tools
        )
        self.system_message = SystemMessage(content=system_prompt)
        self.memory = []                     # Konversationshistorie
```

### Verwendete Libraries

| Library | Import | Zweck |
|---------|--------|-------|
| `langchain-ollama` | `ChatOllama` | LLM-Backend (lokales Ollama) |
| `langchain-core` | `AIMessage`, `HumanMessage`, `SystemMessage` | Message-Typen |
| `langchain-core` | `BaseTool` | Tool-Basisklasse |
| `langgraph` | `create_react_agent` | ReAct-Agent Factory |

### LLM-Konfiguration

```python
self.llm = ChatOllama(
    model=settings.OLLAMA_MODEL,        # z.B. "llama3.1:8b"
    base_url=settings.OLLAMA_BASE_URL,  # http://localhost:11434
    temperature=settings.TEMPERATURE,    # 0.0 für deterministische Antworten
    seed=42,                             # Reproduzierbarkeit
    num_ctx=ctx_size,                    # Adaptiver Context (8192-16384)
    timeout=90,                          # Max 90s pro Request
    num_predict=2048,                    # Max 2048 Output-Tokens
)
```

#### Dynamische Context-Size

Die Context-Größe wird basierend auf der Modellgröße automatisch angepasst:

| Modellgröße | Context-Size |
|-------------|--------------|
| 0.5B | 2,048 |
| 1B | 4,096 |
| 3B | 8,192 |
| 7B-8B | 14,500 |
| 20B-70B | 16,384 |

### Memory Management

```python
# Füge Nachricht zum Memory hinzu
human_message = HumanMessage(content=message)
self.memory.append(human_message)

# Begrenze Memory-Größe (FIFO)
if len(self.memory) > settings.MEMORY_SIZE:  # Default: 100
    self.memory = self.memory[-settings.MEMORY_SIZE:]

# Agent-Input mit System-Message
agent_input = {
    "messages": [self.system_message] + self.memory
}
```

### LangSmith Tracing

```python
if settings.LANGSMITH_TRACING and settings.LANGSMITH_API_KEY:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGSMITH_PROJECT
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGSMITH_API_KEY
```

---

## System-Prompt

Der System-Prompt definiert das Verhalten und die Regeln für den Agent:

### Vollständiger System-Prompt

```
Du bist ein KI-Assistent für die Wirtschafts- und Sozialwissenschaftliche Fakultät (WiSo) der Universität zu Köln. Du unterstützt Studierende und Studieninteressierte bei Fragen zu Studiengängen, Fristen, Bewerbungsverfahren und allgemeinen Universitätsthemen.

## KERNAUFGABE

Du beantwortest Fragen zu:
- Studiengängen und der WiSo-Fakultät im (Bachelor, Master)
- Bewerbungsfristen und -verfahren
- Zulassungsvoraussetzungen
- Studienorganisation und -ablauf
- Prüfungsordnungen und Modulhandbücher
- Allgemeine Informationen zur Universität zu Köln und der WiSo-Fakultät

## TOOL-NUTZUNG

### university_knowledge_search
**Zweck**: Durchsucht die Universitäts-Wissensdatenbank nach relevanten Informationen.
**Parameter**:
  - `query`: Deine Suchanfrage (Pflicht)

**Wann nutzen?**
- Bei JEDER Frage zu WiSo Köln und Universität zu Köln
- IMMER zuerst suchen, DANN antworten
- Auch bei scheinbar einfachen Fragen - die Wissensdatenbank hat aktuelle Informationen

## ANTWORTREGELN

1. **IMMER ERST SUCHEN**: Nutze university_knowledge_search bevor du antwortest
2. **QUELLENBASIERT**: Basiere deine Antworten auf den erhaltenen Suchergebnissen und nicht (!) deinem eigenen Wissen
3. **EHRLICHKEIT**: Wenn keine relevanten Informationen gefunden werden, sage das klar
4. **SPRACHANPASSUNG**: Antworte in der Sprache des Nutzers (Deutsch/Englisch)
5. **PRÄZISION**: Gib konkrete Informationen, keine vagen Aussagen und beziehe dich auf den Suchanfrage sowie den Suchergebnissen

## ANTWORTSTIL

- Freundlich und professionell
- Zusammenfassung der Suchergebnisse, aber informativ
- Bei Unsicherheit: Empfehle Kontakt zur Studienberatung

## BEISPIELE

✅ **RICHTIG**:
Nutzer: "Wann ist die Bewerbungsfrist für den BWL Master?"
→ university_knowledge_search mit query="Bewerbungsfrist BWL Master" aufrufen
→ Basierend auf Ergebnissen antworten

✅ **RICHTIG**:
Nutzer: "What are the requirements for the Economics program?"
→ university_knowledge_search mit query="requirements Economics program admission"
→ Auf Englisch antworten
```

### Prompt-Design-Prinzipien

| Aspekt | Design-Entscheidung |
|--------|---------------------|
| **Rolle** | KI-Assistent für WiSo-Fakultät |
| **Tool-First** | IMMER erst suchen, dann antworten |
| **Quellenbasiert** | Keine Antworten aus Modell-Wissen |
| **Ehrlichkeit** | Klar kommunizieren wenn nichts gefunden |
| **Sprachanpassung** | Deutsch/Englisch basierend auf User |

---

## RAG-Tool (UniversityRAGTool)

### Beschreibung

Das **RAG-Tool** (`university_knowledge_search`) ist das Herzstück der Wissensabfrage. Es durchsucht die ChromaDB-Vektordatenbank nach relevanten Dokumenten.

**Datei:** `src/tools/rag_tool.py`

### Tool-Definition

```python
class UniversityRAGTool(BaseTool):
    name: str = "university_knowledge_search"
    description: str = (
        "Durchsucht die Universitäts-Wissensdatenbank für Fragen zu "
        "Bewerbungen, Studiengängen, Fristen, Prüfungen, Fachsemestern "
        "und anderen Themen der Universität zu Köln / WiSo-Fakultät. "
        "Nutze dieses Tool für spezifische Uni-Fragen."
    )
```

### Retrieval-Modi

Das RAG-Tool unterstützt **drei Modi**, gesteuert über `RAGConfig`:

| Modus | Beschreibung | Aktivierung |
|-------|--------------|-------------|
| **Naive RAG** | Einfache Dense-Suche in ChromaDB | `RAG_NAIVE_SETUP=true` |
| **Advanced RAG** | Hybrid (Dense + BM25) + ReRanking + MMR | `enable_hybrid_retrieval=true` |
| **Sparse RAG** | Nur BM25 (lexikalische Suche) | `enable_sparse_retrieval=true` |

### Pipeline-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG RETRIEVAL PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query: "Bewerbungsfrist BWL Master"                                        │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ 1. RETRIEVAL (k_retrieve=80 Kandidaten)                              │   │
│  │    ┌─────────────────┐         ┌─────────────────┐                   │   │
│  │    │  Dense Retrieval│         │ Sparse Retrieval│                   │   │
│  │    │  (ChromaDB +    │         │ (BM25 Index)    │                   │   │
│  │    │   BGE-M3)       │         │                 │                   │   │
│  │    └────────┬────────┘         └────────┬────────┘                   │   │
│  │             │                           │                            │   │
│  │             └───────────┬───────────────┘                            │   │
│  │                         ▼                                            │   │
│  │              ┌─────────────────┐                                     │   │
│  │              │   RRF Fusion    │ (k=60)                              │   │
│  │              │ score = Σ 1/(k+rank)                                  │   │
│  │              └────────┬────────┘                                     │   │
│  └───────────────────────┼─────────────────────────────────────────────┘   │
│                          │                                                  │
│  ┌───────────────────────┼─────────────────────────────────────────────┐   │
│  │ 2. RERANKING (optional, 40 Kandidaten)                              │   │
│  │                       ▼                                              │   │
│  │              ┌─────────────────┐                                     │   │
│  │              │  Cross-Encoder  │                                     │   │
│  │              │  ReRanker       │                                     │   │
│  │              │ (bge-reranker-  │                                     │   │
│  │              │  v2-m3)         │                                     │   │
│  │              └────────┬────────┘                                     │   │
│  └───────────────────────┼─────────────────────────────────────────────┘   │
│                          │                                                  │
│  ┌───────────────────────┼─────────────────────────────────────────────┐   │
│  │ 3. MMR - Maximum Marginal Relevance (optional)                       │   │
│  │                       ▼                                              │   │
│  │              ┌─────────────────┐                                     │   │
│  │              │  Diversitäts-   │ λ=0.7 (relevance vs diversity)      │   │
│  │              │  Auswahl        │                                     │   │
│  │              └────────┬────────┘                                     │   │
│  └───────────────────────┼─────────────────────────────────────────────┘   │
│                          │                                                  │
│                          ▼                                                  │
│              ┌─────────────────┐                                            │
│              │  Top-k=5 Final  │                                            │
│              │  Documents      │                                            │
│              └─────────────────┘                                            │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Naive RAG (Baseline)

### Ablauf

```python
def _naive_retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
    """Einfache Vektorsuche in Single Collection."""
    
    # 1. ChromaDB Client holen
    client = self._get_chromadb_client()
    collection = client.get_collection('wiso_documents')
    
    # 2. Query-Embedding erstellen (BGE-M3)
    embedding_model = self._get_embedding_model()
    raw_embedding = embedding_model.encode([query])
    
    # 3. Normalisieren für Cosine-Similarity
    normalized_embedding = raw_embedding / np.linalg.norm(raw_embedding, axis=1, keepdims=True)
    
    # 4. Vektorsuche in ChromaDB
    results = collection.query(
        query_embeddings=normalized_embedding.tolist(),
        n_results=k,
        include=['distances', 'metadatas', 'documents']
    )
    
    # 5. Ergebnisse formatieren
    return documents
```

### Verwendete Libraries (Naive)

| Library | Zweck |
|---------|-------|
| `chromadb` | Vektordatenbank |
| `sentence-transformers` | BGE-M3 Embedding-Modell |
| `numpy` | Vektor-Normalisierung |
| `langsmith` | Tracing (`@traceable`) |

---

## Advanced RAG (Hybrid + ReRanking + MMR)

### 1. Hybrid Retrieval (Dense + Sparse)

```python
def _advanced_retrieve(self, query: str) -> List[Dict[str, Any]]:
    """Hybrid Retrieval mit RRF Fusion."""
    
    # Dense + Sparse parallel abrufen
    from src.advanced_rag.retrieval.hybrid_retrieval_rrf import hybrid_retrieve
    
    results = hybrid_retrieve(
        query=query,
        k_retrieve=80,           # Kandidaten pro Retrieval-Typ
        collection_name="wiso_documents",
        sparse_index_dir="data/sparse_index",
        vector_db_path="data/vector_db",
        rrf_k=60,                # RRF-Parameter
        embedding_model=self._get_embedding_model()
    )
```

### RRF Fusion (Reciprocal Rank Fusion)

```
RRF Score = Σ 1 / (k + rank_i)

Beispiel (k=60):
- Dokument A: Dense Rank 1, Sparse Rank 3
  Score = 1/(60+1) + 1/(60+3) = 0.0164 + 0.0159 = 0.0323
  
- Dokument B: Dense Rank 5, Sparse Rank 1
  Score = 1/(60+5) + 1/(60+1) = 0.0154 + 0.0164 = 0.0318
```

### 2. ReRanking (Cross-Encoder)

```python
if self.config.use_reranking:
    # Hole vorgeladenen Reranker (wird einmal initialisiert!)
    reranker = self._get_reranker()
    
    # ReRank Top-40 Kandidaten
    documents = reranker.rerank(
        query, 
        documents_for_reranking[:40],
        embedding_model=self._get_embedding_model()
    )
```

**Unterstützte ReRanker:**

| Provider | Modell | Beschreibung |
|----------|--------|--------------|
| `local` | `bge-reranker-v2-m3` | Lokaler Cross-Encoder (Ollama) |
| `voyage` | `rerank-2` | Voyage AI API |
| `cohere` | `rerank-v3` | Cohere API |

### 3. MMR (Maximum Marginal Relevance)

```python
if self.config.use_mmr:
    from src.advanced_rag.post_retrieval.maximum_marginal_relevance import create_mmr
    
    mmr = create_mmr(
        lambda_param=0.7,           # Balance: Relevanz vs. Diversität
        similarity_metric='cosine'  # Cosine-Similarity für Embeddings
    )
    
    mmr_result = mmr.select(
        documents=documents,
        document_embeddings=embeddings,
        relevance_scores=scores,
        k_final=5
    )
```

**MMR-Formel:**

```
MMR = arg max [λ · Relevance(d) - (1-λ) · max Similarity(d, d_selected)]
       d∈R\S

λ = 0.7 → 70% Relevanz, 30% Diversität
```

### Verwendete Libraries (Advanced)

| Library | Zweck |
|---------|-------|
| `rank-bm25` | BM25Okapi für Sparse Index |
| `langsmith` | Tracing (`@traceable`) |
| `numpy` | Vektor-Operationen |
| `sentence-transformers` | Embeddings |

---

## BM25 Sparse Index

### Beschreibung

Der **BM25SparseIndex** implementiert lexikalische Suche für Hybrid Retrieval.

**Datei:** `src/advanced_rag/retrieval/hybrid_retrieval_rrf.py`

### Tokenisierung

```python
def tokenize(self, text: str) -> List[str]:
    """
    Einfache wortbasierte Tokenisierung für BM25.
    
    - Keine Subword-Tokenisierung
    - Keine Stoppwortentfernung (für Deutsch+Englisch problematisch)
    - Kein Stemming
    """
    text = text.lower()
    text = re.sub(r'[^a-zäöüß0-9\s]', ' ', text)  # Behalte Umlaute
    tokens = text.split()
    return tokens
```

### Index-Struktur

```
data/sparse_index/
└── wiso_documents/
    ├── bm25_index.pkl      # Serialisierter BM25Okapi
    ├── tokenized_corpus.pkl # Tokenisierte Dokumente
    ├── chunk_ids.pkl        # Mapping: Index → chunk_id
    └── summary.json         # Statistiken
```

---

## Konfiguration

### RAGConfig (rag.env)

```bash
# Master Switch
RAG_NAIVE_SETUP=false  # false = Advanced RAG

# Hybrid Retrieval
ENABLE_HYBRID_RETRIEVAL=true
HYBRID_RETRIEVAL_K_RETRIEVE=80   # Kandidaten pro Typ
HYBRID_RETRIEVAL_RRF_K=60        # RRF-Parameter

# ReRanking
ENABLE_RERANKING=true
RERANKING_PROVIDER=local         # local, voyage, cohere
RERANKING_MODEL=bge-reranker-v2-m3
RERANKING_CANDIDATES=40          # Max Kandidaten für ReRanking

# MMR
ENABLE_MMR=true
MMR_LAMBDA=0.7                   # 0.0-1.0 (Relevanz vs. Diversität)
MMR_SIMILARITY_METRIC=cosine

# Final Output
TOP_K=5                          # Finale Anzahl Dokumente
```

### Settings (config/settings.py)

```python
# LLM
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"
TEMPERATURE = 0.0

# Embedding
SENTENCE_TRANSFORMER_MODEL = "BAAI/bge-m3"
EMBEDDING_MAX_SEQ_LENGTH = 1024

# RAG
TOP_K = 5  # Finale Dokumente an LLM
```

---

## Datenfluss

### Kompletter Request-Zyklus

```
1. User: "Wann ist die Bewerbungsfrist für den BWL Master?"
   │
2. ReactAgent.chat(message)
   │
   ├── HumanMessage → Memory
   │
3. LangGraph ReAct Loop
   │
   ├── LLM entscheidet: Tool aufrufen
   │
4. Tool: university_knowledge_search(query="Bewerbungsfrist BWL Master")
   │
   ├── [Naive]    → _naive_retrieve()
   │   └── ChromaDB Cosine-Suche
   │
   ├── [Advanced] → _advanced_retrieve()
   │   ├── Dense (ChromaDB) + Sparse (BM25)
   │   ├── RRF Fusion
   │   ├── ReRanking (Cross-Encoder)
   │   └── MMR (Diversität)
   │
5. Tool Return: "📚 Informationen aus der Wissensdatenbank:\n1. ..."
   │
6. LLM generiert finale Antwort basierend auf Suchergebnissen
   │
7. AIMessage → Memory
   │
8. Return: "Die Bewerbungsfrist für den BWL Master ist..."
```

---

## Tracing mit LangSmith

### Aktivierung

```python
# In settings.py oder .env
LANGSMITH_TRACING = true
LANGSMITH_API_KEY = "ls__..."
LANGSMITH_PROJECT = "wiso-chatbot"
```

### Traceable Funktionen

```python
@traceable(run_type="retriever")
def _naive_retrieve(self, query: str, k: int = 5):
    ...

@traceable(run_type="retriever")
def _advanced_retrieve(self, query: str):
    ...
```

### LangSmith Trace-Struktur

```
📊 LangSmith Trace
├── ReactAgent.chat
│   ├── LLM (llama3.1:8b)
│   ├── Tool: university_knowledge_search
│   │   └── _advanced_retrieve
│   │       ├── hybrid_retrieve (Dense + Sparse)
│   │       ├── rerank (Cross-Encoder)
│   │       └── mmr_select (Diversität)
│   └── LLM (finale Antwort)
```

---

## API-Referenz

### ReactAgent

```python
from src.agent.react_agent import create_react_agent

agent = create_react_agent()

# Chat
response = agent.chat("Was sind die Zulassungsvoraussetzungen für BWL?")

# Memory
agent.clear_memory()
summary = agent.get_memory_summary()

# Tools
tools = agent.get_available_tools()  # ['university_knowledge_search']
```

### RAG-Tool (direkte Nutzung)

```python
from src.tools.rag_tool import create_university_rag_tool

rag = create_university_rag_tool()

# Suche
result = rag._run("Bewerbungsfrist Master")

# Naive Retrieval (raw)
docs = rag._naive_retrieve("Bewerbungsfrist", k=10)

# Advanced Retrieval
docs = rag._advanced_retrieve("Bewerbungsfrist")
```

---

## Troubleshooting

### Häufige Fehler

| Fehler | Ursache | Lösung |
|--------|---------|--------|
| `Collection 'wiso_documents' nicht gefunden` | ChromaDB leer | Production Scraper ausführen |
| `Sparse Index nicht gefunden` | BM25 Index fehlt | Mit `USE_HYBRID_RETRIEVAL=true` scrapen |
| `CUDA out of memory` | GPU VRAM voll | Kleineres Modell oder Batch-Size reduzieren |
| `Timeout` | LLM zu langsam | `timeout` erhöhen oder kleineres Modell |

### Debug-Modus

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Oder nur RAG-Tool
logging.getLogger('src.tools.rag_tool').setLevel(logging.DEBUG)
```

---

## Verwandte Dokumentation

- [ARCHITECTURE_NAIVE_BASELINE.md](./ARCHITECTURE_NAIVE_BASELINE.md) - Gesamtarchitektur
- [HARDWARE_SPECIFICATION.md](./HARDWARE_SPECIFICATION.md) - Hardware-Anforderungen
- [README_PRODUCTION_SCRAPER.md](../src/scraper/README_PRODUCTION_SCRAPER.md) - Scraper-Dokumentation
- [hyperparameter_documentation.md](../hyperparameter_documentation.md) - Alle Hyperparameter
