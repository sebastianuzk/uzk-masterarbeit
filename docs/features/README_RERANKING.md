# ReRanking: Cross-Encoder basierte Relevanz-Neubewertung

## Übersicht

Das ReRanking-Modul sortiert Retrieval-Kandidaten nach ihrer **tatsächlichen Relevanz** zur Query. Während Embedding-basiertes Retrieval schnell ist, kann ein Cross-Encoder die Query-Dokument-Relevanz präziser bewerten, da er Query und Dokument **gemeinsam** verarbeitet.

**Anwendungszeitpunkt**: Post-Retrieval (nach Hybrid Retrieval, vor MMR)

## Unterstützte Provider

| Provider | Modell | Typ | Kosten |
|----------|--------|-----|--------|
| **Local** | `cross-encoder/msmarco-MiniLM-L12-en-de-v1` | Cross-Encoder | Kostenlos (GPU) |
| Voyage AI | `rerank-2.5`, `rerank-2.5-lite` | API | Per Token |
| Cohere | `rerank-v3.5`, `rerank-multilingual-v3.0` | API | Per Search Unit |

**Aktiv genutzt**: `LocalReranker` mit dem mehrsprachigen Cross-Encoder.

## Verwendete Libraries

```
sentence-transformers  # Für lokalen Cross-Encoder
voyageai              # Optional: Voyage AI API
cohere                # Optional: Cohere API
torch                 # GPU-Unterstützung für lokalen Reranker
langsmith             # Tracing für Token-Usage
```

## Konfiguration (rag.env)

```bash
# ReRanking Hyperparameter
RERANKING_ENABLED=true              # ReRanking aktivieren
RERANKING_PROVIDER=local            # local, voyage, cohere
RERANKING_MODEL=cross-encoder/msmarco-MiniLM-L12-en-de-v1

# Optional: API Keys (nur wenn API-Provider genutzt wird)
# VOYAGE_API_KEY=...
# COHERE_API_KEY=...
```

## Algorithmus im Detail

### Cross-Encoder vs. Bi-Encoder

```
Bi-Encoder (Retrieval):              Cross-Encoder (ReRanking):
┌────────┐  ┌────────┐               ┌────────────────────┐
│ Query  │  │  Doc   │               │   Query + Doc      │
└───┬────┘  └───┬────┘               │   (concatenated)   │
    │           │                    └─────────┬──────────┘
    ▼           ▼                              │
┌────────┐  ┌────────┐                        ▼
│Encoder │  │Encoder │               ┌────────────────────┐
└───┬────┘  └───┬────┘               │   Cross-Encoder    │
    │           │                    │   (BERT-basiert)   │
    ▼           ▼                    └─────────┬──────────┘
┌────────┐  ┌────────┐                         │
│Embedding│  │Embedding│                       ▼
└───┬────┘  └───┬────┘               ┌────────────────────┐
    │           │                    │  Relevanz-Score    │
    └─────┬─────┘                    │  (0.0 - 1.0)       │
          │                          └────────────────────┘
          ▼
   Cosine Similarity                 ✓ Höhere Präzision
   (schnell, aber weniger präzise)   ✗ Langsamer (O(n) Forward-Passes)
```

### LocalReranker Implementierung

```python
class LocalReranker:
    """
    ReRanking mittels lokalem Cross-Encoder Modell.
    
    WICHTIG: Das Modell läuft auf der GPU und belegt VRAM!
    - ms-marco-MiniLM-L-12-v2: ~120MB VRAM
    - Zusammen mit LLM (llama3.1:8b): ~6GB gesamt
    """
    
    DEFAULT_MODEL = "cross-encoder/msmarco-MiniLM-L12-en-de-v1"
    
    def __init__(self, model: str = None):
        self.model_name = model or self.DEFAULT_MODEL
        self._model = None
        self._device = None
    
    @property
    def model(self):
        """Lazy-load des Cross-Encoder Modells."""
        if self._model is None:
            from sentence_transformers import CrossEncoder
            import torch
            
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = CrossEncoder(self.model_name, device=self._device)
        return self._model
    
    def rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        Sortiert ALLE Dokumente nach Relevanz zur Query.
        
        Der Cross-Encoder bewertet jedes (Query, Document) Paar einzeln.
        """
        if not documents:
            return documents
        
        # Erstelle Query-Document Paare für Cross-Encoder
        texts = [doc.get('page_content', '') for doc in documents]
        pairs = [[query, text] for text in texts]
        
        # Cross-Encoder Scoring (Batch-Verarbeitung)
        scores = self.model.predict(pairs)
        
        # Füge Scores zu Metadata hinzu
        for i, doc in enumerate(documents):
            doc['metadata']['rerank_score'] = float(scores[i])
        
        # Sortiere nach Score (absteigend)
        documents.sort(
            key=lambda x: x['metadata'].get('rerank_score', 0),
            reverse=True
        )
        
        return documents
```

### API-basierte Reranker

```python
class VoyageReranker:
    """Voyage AI API für ReRanking."""
    
    def rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        texts = [doc.get('page_content', '') for doc in documents]
        
        # API Call
        response = self.client.rerank(
            query=query,
            documents=texts,
            model="rerank-2.5"
        )
        
        # Verarbeite Response
        for result in response.results:
            documents[result.index]['metadata']['rerank_score'] = result.relevance_score
        
        documents.sort(key=lambda x: x['metadata'].get('rerank_score', 0), reverse=True)
        return documents


class CohereReranker:
    """Cohere API für ReRanking."""
    
    def rerank(self, query: str, documents: List[Dict]) -> List[Dict]:
        texts = [doc.get('page_content', '') for doc in documents]
        
        # API Call
        response = self.client.rerank(
            query=query,
            documents=texts,
            model="rerank-v3.5",
            return_documents=False
        )
        
        for result in response.results:
            documents[result.index]['metadata']['rerank_score'] = result.relevance_score
        
        documents.sort(key=lambda x: x['metadata'].get('rerank_score', 0), reverse=True)
        return documents
```

## Datenfluss

```
┌────────────────────────────────────────────────────────────┐
│                 Hybrid Retrieval Ergebnisse                │
│  (80 Dokumente, sortiert nach RRF-Score)                  │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                     Cross-Encoder                          │
│                                                            │
│  Query: "Wie bewerbe ich mich für den Master BWL?"        │
│                                                            │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Dokument 1: "Die Bewerbung für den Master..."     │     │
│  │ → Score: 0.94                                     │     │
│  │                                                   │     │
│  │ Dokument 2: "BWL-Studierende können..."           │     │
│  │ → Score: 0.73                                     │     │
│  │                                                   │     │
│  │ Dokument 3: "Das Prüfungsamt ist zuständig..."   │     │
│  │ → Score: 0.21                                     │     │
│  └──────────────────────────────────────────────────┘     │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│              Neu sortierte Dokumente                       │
│  (80 Dokumente, sortiert nach rerank_score)               │
│                                                            │
│  1. Dokument 1 (rerank_score: 0.94)                       │
│  2. Dokument 2 (rerank_score: 0.73)                       │
│  3. Dokument 3 (rerank_score: 0.21)                       │
│  ...                                                       │
└────────────────────────────────────────────────────────────┘
```

## Integration im RAG-Tool

```python
from src.advanced_rag.post_retrieval.reranking import (
    LocalReranker,
    VoyageReranker,
    CohereReranker
)

# Provider-Auswahl basierend auf Konfiguration
def get_reranker(provider: str) -> RerankerProtocol:
    if provider == "local":
        return LocalReranker()
    elif provider == "voyage":
        return VoyageReranker(model="rerank-2.5")
    elif provider == "cohere":
        return CohereReranker(model="rerank-v3.5")

# ReRanking durchführen
reranker = get_reranker("local")
reranked_docs = reranker.rerank(
    query="Wie bewerbe ich mich für den Master BWL?",
    documents=hybrid_results  # Nach RRF Fusion
)

# Top-Dokumente auswählen (nach ReRanking)
top_docs = reranked_docs[:k_final]
```

## LangSmith Tracing

Alle Reranker unterstützen LangSmith-Tracing für Monitoring:

```python
@traceable(
    run_type="llm",
    name="LocalReranker",
    metadata={"provider": "local"}
)
def _trace_reranking(
    self, 
    query: str, 
    input_documents: List[Dict],
    output_documents: List[Dict],
    total_tokens: int
) -> Dict:
    """
    Traced:
    - Input/Output Chunk-IDs
    - Rerank-Scores
    - Token-Usage (geschätzt)
    """
```

## Warum ReRanking?

### Problem: Retrieval-Rauschen

Hybrid Retrieval liefert viele Kandidaten, aber:
- Manche sind nur oberflächlich relevant (Keyword-Match)
- Ranking basiert auf Embedding-Ähnlichkeit, nicht Query-Relevanz
- Gute Dokumente können niedrig gerankt sein

### Lösung: Cross-Encoder

Der Cross-Encoder bewertet jedes Dokument **im Kontext der Query**:

| Retrieval (Bi-Encoder) | ReRanking (Cross-Encoder) |
|------------------------|---------------------------|
| Query und Dokument getrennt | Query + Dokument gemeinsam |
| Schnell (einmal embedden) | Langsam (pro Dokument) |
| Approximative Relevanz | Präzise Relevanz |

### Praktischer Nutzen

```
Vor ReRanking (RRF-Ranking):
1. "BWL Studierende können..." (nicht direkt relevant)
2. "Das Master-Programm bietet..." (relevant)
3. "Bewerbungsfristen für den Master..." (sehr relevant)

Nach ReRanking:
1. "Bewerbungsfristen für den Master..." (rerank: 0.94)
2. "Das Master-Programm bietet..." (rerank: 0.82)
3. "BWL Studierende können..." (rerank: 0.35)
```

## Pipeline-Position

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│   Hybrid Retrieval     │
│ (80 Kandidaten)        │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ ★ RERANKING ★          │  ← Hier
│ Cross-Encoder Scoring  │
│ (80 → 80, neu sortiert)│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│     MMR                │
│ (Diversitätsauswahl)   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   k_final Dokumente    │
│ (z.B. 5-10 für LLM)    │
└─────────────────────────┘
```

## Referenzen

- **MS MARCO Cross-Encoder**: https://huggingface.co/cross-encoder
- **Sentence-Transformers Cross-Encoder**: https://www.sbert.net/docs/cross_encoder/cross_encoder.html
- **Voyage AI Rerank**: https://docs.voyageai.com/reference/rerank-api
- **Cohere Rerank**: https://docs.cohere.com/reference/rerank
- **Implementierung**: `src/advanced_rag/post_retrieval/reranking.py`
