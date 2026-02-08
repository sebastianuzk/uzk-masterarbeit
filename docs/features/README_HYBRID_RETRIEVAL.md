# Hybrid Retrieval: Dense + Sparse mit RRF Fusion

## Übersicht

Das Hybrid Retrieval-Modul kombiniert **Dense Retrieval** (semantische Vektorsuche via ChromaDB) mit **Sparse Retrieval** (lexikalische BM25-Suche). Die Ergebnisse werden mittels **Reciprocal Rank Fusion (RRF)** zu einem einheitlichen Ranking fusioniert.

**Anwendungszeitpunkt**: Retrieval-Phase (bei User-Query)

## Verwendete Libraries

```
rank_bm25==0.2.2      # BM25Okapi Implementierung für Sparse Index
chromadb==0.4.22      # Vektor-Datenbank für Dense Index
numpy                 # Für Ranking-Berechnungen
sentence-transformers # Für Query-Embedding (BGE-M3)
```

## Konfiguration (rag.env)

```bash
# Hybrid Retrieval Hyperparameter
RETRIEVAL_K_RETRIEVE=80     # Kandidaten pro Retrieval-Methode
RRF_K=60                    # RRF-K Parameter (Standard nach Original-Paper)

# Dense Index
VECTOR_DB_PATH=data/vector_db
COLLECTION_NAME=wiso_documents

# Sparse Index
SPARSE_INDEX_DIR=data/sparse_index
```

## Komponenten

### 1. Dense Index (ChromaDB)

Der Dense Index enthält vorberechnete BGE-M3 Embeddings aller Chunks:

```python
# ChromaDB Query
collection = chromadb.PersistentClient(path="data/vector_db").get_collection("wiso_documents")

# Query-Embedding erstellen und normalisieren
raw_embedding = embedding_model.encode([query])
normalized_embedding = raw_embedding / np.linalg.norm(raw_embedding, axis=1, keepdims=True)

# Ähnlichkeitssuche
results = collection.query(
    query_embeddings=normalized_embedding.tolist(),
    n_results=k_retrieve,
    include=['distances']
)
```

**Vorteile Dense Retrieval**:
- Findet semantisch ähnliche Inhalte
- Robust gegenüber Synonymen und Paraphrasen
- Sprach- und domänenübergreifend (mit BGE-M3)

### 2. Sparse Index (BM25)

Der BM25SparseIndex basiert auf wortbasierter Tokenisierung:

```python
@dataclass
class BM25SparseIndex:
    """
    BM25-basierter Sparse Index für lexikalische Suche.
    
    Tokenisierung:
    - Lowercase
    - Sonderzeichen entfernen (Umlaute behalten: äöüß)
    - Whitespace-basiertes Splitting (keine Subwords)
    - Keine Stoppwortentfernung
    - Kein Stemming
    """
    
    def tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        
        text = text.lower()
        # Behalte: a-z, äöüß, Ziffern
        text = re.sub(r'[^a-zäöüß0-9\s]', ' ', text)
        tokens = text.split()
        return [t for t in tokens if t]
    
    def search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        query_tokens = self.tokenize(query)
        scores = self.bm25.get_scores(query_tokens)
        top_indices = scores.argsort()[::-1][:top_k]
        
        return [(self.chunk_ids[idx], float(scores[idx])) 
                for idx in top_indices if scores[idx] > 0]
```

**Vorteile Sparse Retrieval**:
- Exakte Wortübereinstimmungen
- Gut für Fachbegriffe, Eigennamen, Codes
- Schnell und interpretierbar

### 3. Reciprocal Rank Fusion (RRF)

RRF kombiniert mehrere Rankings zu einem fusionierten Ranking:

```python
def reciprocal_rank_fusion(
    ranked_lists: List[List[Tuple[str, float]]],
    k: int = 60
) -> List[Tuple[str, float]]:
    """
    Reciprocal Rank Fusion (RRF) für mehrere Ranking-Listen.
    
    Formel: RRF_score(d) = Σ 1 / (k + rank(d))
    
    Args:
        ranked_lists: Liste von Rankings [(doc_id, score), ...]
        k: RRF-K Parameter (default: 60)
    
    Returns:
        Fusioniertes Ranking [(doc_id, rrf_score), ...]
    """
    rrf_scores = {}
    
    for ranked_list in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked_list, start=1):
            # RRF-Formel: 1 / (k + rank)
            rrf_score = 1.0 / (k + rank)
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + rrf_score
    
    return sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
```

## Mathematische Grundlagen

### BM25 Scoring

BM25 (Best Matching 25) berechnet die Relevanz eines Dokuments $d$ für eine Query $q$:

$$\text{BM25}(d, q) = \sum_{t \in q} \text{IDF}(t) \cdot \frac{f(t, d) \cdot (k_1 + 1)}{f(t, d) + k_1 \cdot (1 - b + b \cdot \frac{|d|}{\text{avgdl}})}$$

wobei:
- $f(t, d)$: Termfrequenz von $t$ in $d$
- $|d|$: Dokumentlänge
- $\text{avgdl}$: Durchschnittliche Dokumentlänge
- $k_1 = 1.5$, $b = 0.75$: Standard-Parameter

### RRF Fusion

Der RRF-Score für ein Dokument $d$, das in mehreren Rankings vorkommt:

$$\text{RRF}(d) = \sum_{r \in R} \frac{1}{k + \text{rank}_r(d)}$$

wobei:
- $R$: Menge aller Rankings (hier: Dense + Sparse)
- $\text{rank}_r(d)$: Rang von $d$ im Ranking $r$ (1-basiert)
- $k = 60$: Glättungsparameter

**Warum k=60?**
- Höheres $k$ → niedrigere Ränge bekommen mehr Gewicht
- $k=60$ ist der Standard-Wert aus dem Original-Paper
- Gut für Rankings mit unterschiedlichen Score-Verteilungen

## Datenfluss

```
                        ┌──────────────┐
                        │    Query     │
                        │ "Bewerbung   │
                        │  Master BWL" │
                        └──────┬───────┘
                               │
              ┌────────────────┴────────────────┐
              │                                 │
              ▼                                 ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │   Dense Retrieval   │         │   Sparse Retrieval  │
    │   (ChromaDB)        │         │   (BM25)            │
    │                     │         │                     │
    │ Query-Embedding     │         │ Query-Tokenisierung │
    │ → Cosine Similarity │         │ → BM25 Scoring      │
    └──────────┬──────────┘         └──────────┬──────────┘
               │                               │
               │ Top 80                        │ Top 80
               │                               │
               ▼                               ▼
    ┌─────────────────────┐         ┌─────────────────────┐
    │ Dense Ranking:      │         │ Sparse Ranking:     │
    │ 1. chunk_42 (0.89)  │         │ 1. chunk_17 (12.3)  │
    │ 2. chunk_17 (0.87)  │         │ 2. chunk_42 (11.8)  │
    │ 3. chunk_99 (0.85)  │         │ 3. chunk_55 (10.2)  │
    │ ...                 │         │ ...                 │
    └──────────┬──────────┘         └──────────┬──────────┘
               │                               │
               └────────────┬──────────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │     RRF Fusion            │
              │                           │
              │ chunk_42: 1/(60+1) +      │
              │           1/(60+2) = 0.032│
              │ chunk_17: 1/(60+2) +      │
              │           1/(60+1) = 0.032│
              │ chunk_99: 1/(60+3) = 0.016│
              │ chunk_55: 1/(60+3) = 0.016│
              └─────────────┬─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │   Fusioniertes Ranking    │
              │                           │
              │ 1. chunk_42 (0.032)       │
              │ 2. chunk_17 (0.032)       │
              │ 3. chunk_99 (0.016)       │
              │ 4. chunk_55 (0.016)       │
              │ ...                       │
              └───────────────────────────┘
```

## Integration im RAG-Tool

```python
from src.advanced_rag.retrieval.hybrid_retrieval_rrf import HybridRetriever, hybrid_retrieve

# Option 1: HybridRetriever-Klasse
retriever = HybridRetriever(
    collection_name="wiso_documents",
    sparse_index_dir="data/sparse_index",
    vector_db_path="data/vector_db",
    rrf_k=60,
    embedding_model=preloaded_model  # Performance-Optimierung
)

results = retriever.retrieve(
    query="Wie bewerbe ich mich für den Master BWL?",
    k_retrieve=80,
    include_embeddings=True  # Für MMR benötigt
)

# Option 2: Convenience-Funktion
results = hybrid_retrieve(
    query="Wie bewerbe ich mich für den Master BWL?",
    k_retrieve=80,
    collection_name="wiso_documents",
    sparse_index_dir="data/sparse_index",
    vector_db_path="data/vector_db",
    rrf_k=60
)

# Ergebnis-Format
for doc in results:
    print(f"Chunk: {doc['chunk_id']}")
    print(f"  RRF-Score: {doc['rrf_score']:.4f}")
    print(f"  Dense-Rank: {doc['dense_rank']}")
    print(f"  Sparse-Rank: {doc['sparse_rank']}")
    print(f"  Text: {doc['page_content'][:100]}...")
```

## BM25 Index Management

### Index-Erstellung (im Scraper)

```python
from src.advanced_rag.retrieval.hybrid_retrieval_rrf import BM25SparseIndex

# Index erstellen
sparse_index = BM25SparseIndex(collection_name="wiso_documents")

# Chunks hinzufügen
sparse_index.add_documents_batch(
    chunk_ids=[chunk['chunk_id'] for chunk in chunks],
    texts=[chunk['text'] for chunk in chunks]
)

# Index speichern
sparse_index.save("data/sparse_index")
```

### Index-Laden (zur Laufzeit)

```python
# Index laden
sparse_index = BM25SparseIndex.load(
    "data/sparse_index", 
    collection_name="wiso_documents"
)

# Statistiken
stats = sparse_index.get_statistics()
print(f"Dokumente: {stats['total_documents']}")
print(f"Unique Terms: {stats['unique_terms']}")
print(f"Avg Tokens/Doc: {stats['avg_tokens_per_doc']:.1f}")
```

## Warum Hybrid statt nur Dense?

| Szenario | Dense Retrieval | Sparse Retrieval | **Hybrid** |
|----------|-----------------|------------------|------------|
| "BWL Master" | ✓ Findet "Wirtschaftswissenschaften Master" | ✓ Exakter Match | ✓✓ Beste Abdeckung |
| "Prüfungsordnung §12" | △ Semantisch schwer | ✓ Exakter Match | ✓ Nutzt BM25-Stärke |
| "Studium Finanzen" | ✓ Findet "Banking & Finance" | △ Nur bei Wort-Match | ✓ Nutzt Dense-Stärke |

## Pipeline-Position

```
┌─────────────────┐
│   User Query    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ ★ HYBRID RETRIEVAL ★   │  ← Hier
│ Dense + Sparse + RRF   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│     ReRanking          │
│ (Cross-Encoder/API)    │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│     MMR                │
│ (Diversität)           │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│     LLM Response       │
└─────────────────────────┘
```

## Referenzen

- **RRF Paper**: Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). "Reciprocal rank fusion outperforms condorcet and individual rank learning methods." SIGIR '09.
- **BM25 Paper**: Robertson, S., & Zaragoza, H. (2009). "The Probabilistic Relevance Framework: BM25 and Beyond." Foundations and Trends in Information Retrieval.
- **rank_bm25**: https://github.com/dorianbrown/rank_bm25
- **Implementierung**: `src/advanced_rag/retrieval/hybrid_retrieval_rrf.py`
