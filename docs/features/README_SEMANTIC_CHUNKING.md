# Semantic Chunking: Percentile-basierte Segmentierung

## Übersicht

Das Semantic Chunking-Modul segmentiert Dokumente basierend auf **semantischer Ähnlichkeit** zwischen aufeinanderfolgenden Sätzen. Im Gegensatz zu naiven Ansätzen (feste Zeichenzahl) erkennt dieser Ansatz natürliche Themenwechsel im Text und erstellt kohärentere Chunks.

**Aktiv genutzte Methode**: `_find_breakpoints_percentile()` (Percentile-basiert)

## Warum Percentile statt Static Threshold?

Die Entscheidung für den **Percentile-basierten Ansatz** gegenüber dem statischen Similarity-Threshold basiert auf einer umfassenden Analyse (dokumentiert in `multi_doc_chunking_analysis.xlsx`):

| Aspekt | Static Threshold | **Percentile (gewählt)** |
|--------|------------------|--------------------------|
| Sensitivität | Gleicher Schwellwert für alle Dokumente | **Dokumentspezifisch adaptiv** |
| Themenwechsel | Kann bei homogenen Dokumenten versagen | **Findet immer die stärksten Brüche** |
| Kalibrierung | Erfordert manuelles Tuning | **Automatisch skaliert** |
| Robustheit | Abhängig vom Dokumenttyp | **Universell einsetzbar** |

### Kernvorteil

Der Percentile-Ansatz betrachtet die **relative Verteilung** der Ähnlichkeitswerte innerhalb eines Dokuments. Ein Wert im 10. Percentil bedeutet: "Diese Stelle gehört zu den 10% mit der geringsten Ähnlichkeit zum vorherigen Satz" – unabhängig von der absoluten Ähnlichkeit.

## Verwendete Libraries

```
sentence-transformers  # Für BGE-M3 Embedding-Modell
numpy                  # Für Percentile-Berechnung und Cosinus-Ähnlichkeit
```

## Konfiguration (rag.env)

```bash
# Aktive Hyperparameter
CHUNK_MAX_SIZE=1500         # Maximale Chunk-Größe in Zeichen
CHUNK_MIN_SIZE=400          # Minimale Chunk-Größe in Zeichen
CHUNK_OVERLAP=300           # Überlappung zwischen Chunks
CHUNKING_PERCENTILE=10      # Percentile für Breakpoint-Erkennung (10 = 10. Percentil)
```

## Algorithmus im Detail

### 1. Satz-Splitting

```python
def _split_into_sentences(self, text: str) -> List[str]:
    """
    Splittet Text in Sätze unter Berücksichtigung von:
    - Deutschen Abkürzungen (z.B., d.h., u.a.)
    - Aufzählungen mit Nummern
    - Satzzeichen-Kombinationen
    """
```

### 2. Embedding-Berechnung

```python
def _compute_embeddings(self, sentences: List[str]) -> np.ndarray:
    """
    Berechnet normalisierte BGE-M3 Embeddings für jeden Satz.
    - Modell: BAAI/bge-m3 (1024 Dimensionen)
    - Normalisierung: L2-Norm = 1 (für Cosinus-Ähnlichkeit via Dot Product)
    """
```

### 3. Breakpoint-Erkennung (Percentile-Methode)

```python
def _find_breakpoints_percentile(
    self, 
    sentences: List[str], 
    embeddings: np.ndarray
) -> List[int]:
    """
    Findet semantische Breakpoints basierend auf dem n-ten Percentil.
    
    Schritte:
    1. Berechne Cosinus-Ähnlichkeit zwischen aufeinanderfolgenden Sätzen
    2. Bestimme den Percentile-Schwellwert dynamisch
    3. Markiere Positionen unter dem Schwellwert als Breakpoints
    """
    
    # Cosinus-Ähnlichkeiten (Dot Product für normalisierte Vektoren)
    similarities = []
    for i in range(len(embeddings) - 1):
        sim = np.dot(embeddings[i], embeddings[i + 1])
        similarities.append(sim)
    
    # Dynamischer Schwellwert basierend auf Dokumentverteilung
    threshold = np.percentile(similarities, self.percentile)  # z.B. 10. Percentil
    
    # Breakpoints an Stellen mit niedriger Ähnlichkeit
    breakpoints = [i for i, sim in enumerate(similarities) if sim < threshold]
    
    return breakpoints
```

### 4. Chunk-Erstellung mit Constraints

```python
def _create_chunks_from_breakpoints(
    self, 
    sentences: List[str], 
    breakpoints: List[int]
) -> List[str]:
    """
    Erstellt Chunks unter Berücksichtigung von:
    - min_chunk_size: Chunks werden zusammengeführt wenn zu klein
    - max_chunk_size: Chunks werden gesplittet wenn zu groß
    - overlap: Sätze werden zwischen Chunks überlappen
    """
```

## Mathematische Grundlage

### Cosinus-Ähnlichkeit

Für zwei normalisierte Vektoren $\vec{a}$ und $\vec{b}$:

$$\text{sim}(\vec{a}, \vec{b}) = \vec{a} \cdot \vec{b} = \sum_{i=1}^{n} a_i \cdot b_i$$

Da die Vektoren L2-normalisiert sind ($\|\vec{a}\| = \|\vec{b}\| = 1$), entspricht das Dot Product direkt der Cosinus-Ähnlichkeit.

### Percentile-Berechnung

Das $p$-te Percentil der Ähnlichkeitsverteilung:

$$\text{threshold} = P_p(\{s_1, s_2, ..., s_{n-1}\})$$

wobei $s_i = \text{sim}(\text{sent}_i, \text{sent}_{i+1})$

## Datenfluss

```
┌─────────────────┐
│   Rohtext       │
│ (HTML-bereinigt)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Satz-Splitting  │
│ (Regex-basiert) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BGE-M3 Encoding │
│ (1024-dim)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Similarity-     │
│ Berechnung      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Percentile-     │
│ Threshold       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Breakpoint-     │
│ Erkennung       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Chunk-Erstellung│
│ (mit Constraints)│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Semantisch      │
│ kohärente Chunks│
└─────────────────┘
```

## Integration im Scraper

```python
from src.advanced_rag.pre_retrieval.chunking import SemanticChunker
from config.settings import SENTENCE_TRANSFORMER_MODEL

# Initialisierung
chunker = SemanticChunker(
    model=embedding_model,  # Vorgeladenes BGE-M3
    max_chunk_size=1500,
    min_chunk_size=400,
    overlap=300,
    percentile=10           # 10. Percentil für Breakpoints
)

# Chunking
chunks = chunker.chunk(document_text)
# Gibt Liste von Chunk-Strings zurück
```

## Inaktive Alternative: Static Threshold

Die `_find_breakpoints_static_threshold()` Methode existiert, wird aber nicht genutzt:

```python
def _find_breakpoints_static_threshold(
    self, 
    similarities: List[float], 
    threshold: float = 0.5
) -> List[int]:
    """
    NICHT AKTIV - Nutzt festen Schwellwert für alle Dokumente.
    Problem: Gleicher Threshold funktioniert nicht für alle Dokumenttypen.
    """
```

## Referenzen

- **BGE-M3**: BAAI/bge-m3 Multilingual Embedding Model
  - Paper: "BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation"
  
- **Semantic Chunking Konzept**: Adaptiert von LangChain's SemanticChunker
  - Angepasst für Percentile-basierte Breakpoint-Erkennung
  
- **Evaluation**: Dokumentiert in `multi_doc_chunking_analysis.xlsx`
  - Vergleich Percentile vs. Static Threshold über verschiedene Dokumenttypen
