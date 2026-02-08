# Maximum Marginal Relevance (MMR): Diversitäts-optimierte Auswahl

## Übersicht

Das MMR-Modul wählt die **finalen Top-K Dokumente** aus den ReRanking-Ergebnissen unter Berücksichtigung von **Diversität**. Ziel ist es, redundante/ähnliche Dokumente zu vermeiden und dem LLM ein breites Spektrum an Informationen zu liefern.

**Anwendungszeitpunkt**: Post-Retrieval (nach ReRanking, vor LLM)

## Verwendete Libraries

```
numpy      # Für Similarity-Matrix und Optimierung
langsmith  # Für Tracing (Swap-Dokumentation)
```

Keine externen ML-Abhängigkeiten – nutzt **vorberechnete Embeddings** aus ChromaDB.

## Konfiguration (rag.env)

```bash
# MMR Hyperparameter
MMR_ENABLED=true
MMR_LAMBDA=0.5              # Trade-off: 1.0 = nur Relevanz, 0.0 = nur Diversität
MMR_SIMILARITY_METRIC=cosine

# Finale Dokumentenzahl
RETRIEVAL_K_FINAL=5         # Anzahl Dokumente für LLM
```

## Algorithmus im Detail

### MMR-Formel

Maximum Marginal Relevance balanciert zwei Ziele:

$$\text{MMR} = \arg\max_{d \in R \setminus S} \left[ \lambda \cdot \text{Sim}(d, q) - (1 - \lambda) \cdot \max_{d_i \in S} \text{Sim}(d, d_i) \right]$$

wobei:
- $R$: Kandidaten-Menge (alle Dokumente nach ReRanking)
- $S$: Bereits ausgewählte Dokumente
- $q$: Query
- $\lambda$: Trade-off Parameter
- $\text{Sim}(d, q)$: Relevanz zur Query (ReRank-Score)
- $\text{Sim}(d, d_i)$: Ähnlichkeit zu bereits ausgewählten Dokumenten

### Greedy Selection

```python
class MaximumMarginalRelevance:
    def __init__(self, lambda_param: float = 0.5, similarity_metric: str = "cosine"):
        self.lambda_param = lambda_param
        self.similarity_metric = similarity_metric
    
    def select(
        self,
        documents: List[Dict],
        document_embeddings: np.ndarray,
        relevance_scores: List[float],
        k_final: int,
        query: str = ""
    ) -> MMRResult:
        """
        Wählt k_final Dokumente mittels MMR aus vorsortierten Kandidaten.
        
        Die Dokumente sind bereits nach Relevanz sortiert (von ReRanking).
        MMR prüft, ob Dokumente durch diversere Alternativen ersetzt werden sollten.
        """
        n_docs = len(documents)
        
        # Vorberechnete paarweise Ähnlichkeiten
        doc_similarity_matrix = self._compute_similarity_matrix(document_embeddings)
        
        selected_indices = []
        remaining_indices = set(range(n_docs))
        swaps = []  # Tracke Austausche
        
        for position in range(k_final):
            best_idx = -1
            best_mmr = float('-inf')
            
            for idx in remaining_indices:
                # Relevanz-Term: λ * relevance_score
                relevance_term = self.lambda_param * relevance_scores[idx]
                
                # Diversität-Term: (1 - λ) * max(Sim(d, d_i))
                if selected_indices:
                    max_sim = max(
                        doc_similarity_matrix[idx, sel_idx]
                        for sel_idx in selected_indices
                    )
                    diversity_penalty = (1 - self.lambda_param) * max_sim
                else:
                    diversity_penalty = 0.0
                
                # MMR Score
                mmr_score = relevance_term - diversity_penalty
                
                if mmr_score > best_mmr:
                    best_mmr = mmr_score
                    best_idx = idx
            
            selected_indices.append(best_idx)
            remaining_indices.remove(best_idx)
        
        return MMRResult(
            documents=[documents[i] for i in selected_indices],
            swaps=swaps,
            total_candidates=n_docs,
            selected_count=k_final,
            lambda_param=self.lambda_param
        )
```

### Similarity-Matrix Berechnung

```python
def _compute_similarity_matrix(self, embeddings: np.ndarray) -> np.ndarray:
    """
    Berechnet paarweise Ähnlichkeitsmatrix.
    
    Embeddings aus ChromaDB sind bereits L2-normalisiert.
    → Cosine Similarity = Dot Product
    """
    if self.similarity_metric == "cosine":
        return np.dot(embeddings, embeddings.T)
    elif self.similarity_metric == "dot":
        return np.dot(embeddings, embeddings.T)
```

## Lambda-Parameter Interpretation

| Lambda (λ) | Verhalten |
|------------|-----------|
| 1.0 | **Nur Relevanz** – Nimmt die Top-K nach ReRank-Score |
| 0.7 | **Leicht diversifiziert** – Bevorzugt relevante, vermeidet sehr ähnliche |
| **0.5** | **Ausgewogen** – Gleiche Gewichtung (Standard) |
| 0.3 | **Diversitäts-fokussiert** – Akzeptiert weniger relevante für mehr Abdeckung |
| 0.0 | **Nur Diversität** – Maximiert Unterschiedlichkeit |

## Datenfluss

```
┌────────────────────────────────────────────────────────────┐
│                ReRanking Ergebnisse                        │
│  (80 Dokumente, sortiert nach rerank_score)               │
│                                                            │
│  + Embeddings aus ChromaDB (für Similarity)               │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│                    MMR Selection                           │
│                                                            │
│  Iteration 1: Wähle relevantestes Dokument                │
│  → Doc_7 (rerank: 0.94, keine Penalty)                    │
│                                                            │
│  Iteration 2: Doc_12 sehr relevant (0.91), ABER           │
│               hohe Ähnlichkeit zu Doc_7 (0.85)            │
│               → Penalty: (1-0.5) * 0.85 = 0.425           │
│               → MMR: 0.5*0.91 - 0.425 = 0.03              │
│                                                            │
│               Doc_23 weniger relevant (0.78), aber         │
│               niedrige Ähnlichkeit zu Doc_7 (0.2)         │
│               → Penalty: (1-0.5) * 0.2 = 0.1              │
│               → MMR: 0.5*0.78 - 0.1 = 0.29                │
│                                                            │
│  → Wähle Doc_23 (höherer MMR-Score!)                      │
│                                                            │
│  Iteration 3-5: Fortsetzen...                             │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│              Finale Auswahl (k_final = 5)                  │
│                                                            │
│  1. Doc_7  (rerank: 0.94, mmr: 0.47, thema: Bewerbung)    │
│  2. Doc_23 (rerank: 0.78, mmr: 0.29, thema: Fristen)      │
│  3. Doc_31 (rerank: 0.71, mmr: 0.25, thema: Unterlagen)   │
│  4. Doc_45 (rerank: 0.68, mmr: 0.22, thema: Zulassung)    │
│  5. Doc_52 (rerank: 0.62, mmr: 0.19, thema: Studienplatz) │
│                                                            │
│  ✓ Breite Themenabdeckung statt 5x Bewerbungsinfos       │
└────────────────────────────────────────────────────────────┘
```

## Swap-Tracking

MMR dokumentiert jeden "Swap" – wenn ein Dokument außerhalb der ursprünglichen Top-K ausgewählt wird:

```python
@dataclass
class MMRSwapInfo:
    """Information über einen Dokumenten-Austausch durch MMR."""
    original_position: int      # Position des ersetzten Dokuments
    original_chunk_id: str      # Chunk-ID des ersetzten Dokuments
    original_relevance: float   # Relevanz-Score des ersetzten Dokuments
    
    new_position: int           # Neue Position
    new_chunk_id: str           # Chunk-ID des eingetauschten Dokuments
    new_relevance: float        # Relevanz-Score
    new_mmr_score: float        # MMR-Score (Relevanz - Diversitäts-Penalty)
    
    swap_reason: str            # z.B. "Hohe Ähnlichkeit (0.85) zu bereits ausgewählten"
```

## Integration im RAG-Tool

```python
from src.advanced_rag.post_retrieval.maximum_marginal_relevance import (
    MaximumMarginalRelevance,
    create_mmr
)

# MMR initialisieren
mmr = create_mmr(lambda_param=0.5, similarity_metric="cosine")

# Embeddings müssen aus ChromaDB geholt werden (während Hybrid Retrieval)
# include_embeddings=True bei hybrid_retrieve()

# MMR anwenden
mmr_result = mmr.select(
    documents=reranked_docs,
    document_embeddings=embeddings_array,  # np.ndarray
    relevance_scores=[doc['metadata']['rerank_score'] for doc in reranked_docs],
    k_final=5,
    query="Wie bewerbe ich mich für den Master BWL?"
)

# Ergebnis
final_docs = mmr_result.documents
print(f"Ausgewählt: {mmr_result.selected_count} von {mmr_result.total_candidates}")
print(f"Swaps: {len(mmr_result.swaps)}")

# Swap-Details
for swap in mmr_result.swaps:
    print(f"  Position {swap.original_position}: "
          f"{swap.original_chunk_id} → {swap.new_chunk_id}")
    print(f"    Grund: {swap.swap_reason}")
```

## LangSmith Tracing

MMR traced alle Selektionen und Swaps für Analyse:

```python
@traceable(
    run_type="chain",
    name="MMR_Selection",
    metadata={"technique": "maximum_marginal_relevance"}
)
def _trace_mmr_result(self, result: MMRResult, query: str, input_documents: List[Dict]):
    """
    Traced:
    - Alle Input-Dokumente (für Verifizierung)
    - Finale Auswahl mit MMR-Scores
    - Swap-Details (wer wurde ersetzt und warum)
    """
```

## Warum MMR?

### Problem: Redundante Retrieval-Ergebnisse

Nach ReRanking sind die Top-Dokumente oft sehr ähnlich:
- Gleiche Information in verschiedenen Dokumenten
- Überlappende Chunks aus demselben Quelldokument
- Verschiedene Formulierungen desselben Inhalts

### Konsequenzen ohne MMR

```
Ohne MMR (Top-5 nach ReRank-Score):
1. "Die Bewerbung für den Master BWL erfolgt über..."
2. "Für die Bewerbung zum Master BWL benötigen Sie..."
3. "Master BWL Bewerber müssen folgende Unterlagen..."
4. "Die Master BWL Bewerbung erfordert..."
5. "Bewerbungsverfahren Master BWL: Einreichen Sie..."

→ 5x fast identische Information!
→ Andere wichtige Aspekte (Fristen, Zulassung) fehlen!
```

### Mit MMR

```
Mit MMR (λ=0.5):
1. "Die Bewerbung für den Master BWL erfolgt über..." (Bewerbung)
2. "Bewerbungsfristen: Sommersemester 15.01..." (Fristen)
3. "Folgende Unterlagen sind erforderlich..." (Unterlagen)
4. "Zulassungsvoraussetzungen für den Master..." (Zulassung)
5. "Bei Fragen wenden Sie sich an das Studierendensekretariat..." (Kontakt)

→ Breite Abdeckung aller relevanten Aspekte!
→ LLM kann umfassendere Antwort generieren
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
│ (80 Kandidaten + Emb.) │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│     ReRanking          │
│ (80 → 80, neu sortiert)│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│ ★ MMR ★                │  ← Hier
│ (80 → 5 mit Diversität)│
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│   LLM Response         │
│ (5 diverse Dokumente)  │
└─────────────────────────┘
```

## Referenzen

- **MMR Paper**: Carbonell, J., & Goldstein, J. (1998). "The use of MMR, diversity-based reranking for reordering documents and producing summaries." SIGIR '98.
- **Implementierung**: `src/advanced_rag/post_retrieval/maximum_marginal_relevance.py`
