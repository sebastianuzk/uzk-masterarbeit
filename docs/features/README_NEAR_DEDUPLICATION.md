# Near Deduplication: MinHash + LSH Framework (datasketch)

## Übersicht

Das Near Deduplication-Modul identifiziert und entfernt **semantisch ähnliche** Dokumente (ca. 90% Übereinstimmung), die keine exakten Duplikate sind. Es nutzt das **MinHash + Locality-Sensitive Hashing (LSH)** Framework der `datasketch` Library für effiziente Ähnlichkeitssuche.

**Anwendungszeitpunkt**: Pre-Retrieval (nach Exact Deduplication, vor Chunking)

## Verwendete Libraries

```
datasketch==1.6.1   # MinHash und MinHashLSH Implementierung
```

## Konfiguration (rag.env)

```bash
# Near-Deduplication Hyperparameter
NEAR_DEDUP_THRESHOLD=0.9     # Jaccard-Ähnlichkeit für Duplikaterkennung (90%)
NEAR_DEDUP_NUM_PERM=128      # Anzahl der MinHash-Permutationen
NEAR_DEDUP_MIN_WORDS=120     # Mindest-Wortanzahl für Near-Dedup
```

**Hardcoded** (im Code):
- `shingle_k=5` (Wort-Shingle Größe)
- `seed=42` (Reproduzierbarkeit)

## Algorithmus im Detail

### Konzept: Jaccard-Ähnlichkeit

Die Jaccard-Ähnlichkeit zwischen zwei Mengen A und B:

$$J(A, B) = \frac{|A \cap B|}{|A \cup B|}$$

Für zwei Dokumente mit Wort-Shingles:
- $J = 1.0$: Identische Shingle-Mengen
- $J = 0.0$: Keine gemeinsamen Shingles
- $J \geq 0.9$: Near-Duplicate (bei threshold=0.9)

### 1. Wort-Shingles erstellen

```python
def _create_word_shingles(text: str, k: int = 5) -> Set[str]:
    """
    Erstelle Wort-Shingles (k-grams) aus normalisiertem Text.
    
    Ein 5-gram Shingle besteht aus 5 aufeinanderfolgenden Wörtern.
    
    Beispiel für k=5:
        "Der Student geht zur Universität Köln und studiert BWL"
        → {"der student geht zur universität",
           "student geht zur universität köln",
           "geht zur universität köln und",
           "zur universität köln und studiert",
           "universität köln und studiert bwl"}
    """
    normalized = normalize_text(text)  # Lowercase, NFKC, etc.
    words = normalized.split()
    
    if len(words) < k:
        return {" ".join(words)} if words else set()
    
    shingles = set()
    for i in range(len(words) - k + 1):
        shingle = " ".join(words[i:i + k])
        shingles.add(shingle)
    
    return shingles
```

### 2. MinHash-Signatur erstellen

```python
def _create_minhash(shingles: Set[str], num_perm: int = 128, seed: int = 42) -> MinHash:
    """
    Erstelle MinHash-Signatur für ein Shingle-Set.
    
    MinHash komprimiert eine beliebig große Shingle-Menge zu einer
    festen Anzahl von Hash-Werten (num_perm).
    
    WICHTIG: Der seed=42 gewährleistet Reproduzierbarkeit!
    """
    from datasketch import MinHash
    
    mh = MinHash(num_perm=num_perm, seed=seed)
    
    for shingle in shingles:
        mh.update(shingle.encode('utf-8'))
    
    return mh
```

### 3. LSH für effiziente Ähnlichkeitssuche

```python
from datasketch import MinHashLSH

# LSH-Index erstellen
lsh = MinHashLSH(threshold=threshold, num_perm=num_perm)

# Dokumente indizieren
for doc_id, minhash in doc_minhashes.items():
    # query() findet VORHER eingefügte Kandidaten mit Jaccard ≥ threshold
    candidates = lsh.query(minhash)
    
    if candidates:
        # Dokument ist Near-Duplicate von einem Kandidaten
        union_find.union(doc_id, candidates[0])
    
    # Dokument zum Index hinzufügen
    lsh.insert(doc_id, minhash)
```

### 4. Union-Find für Cluster-Bildung

Near-Duplicates werden in Clustern gruppiert. Der Union-Find-Algorithmus verwaltet diese Cluster effizient:

```python
class UnionFind:
    """
    Disjoint-Set Datenstruktur für Cluster-Verwaltung.
    
    Wenn A ~ B und B ~ C, dann sind A, B, C im gleichen Cluster.
    """
    def find(self, x):
        """Finde Repräsentanten des Clusters"""
        ...
    
    def union(self, x, y):
        """Vereinige zwei Cluster"""
        ...
```

### 5. Kanonische URL-Auswahl

Aus jedem Cluster wird **ein** Dokument behalten (das "kanonische"):

```python
def _select_canonical_url(documents: List[dict], id_key: str = 'doc_id') -> dict:
    """
    Wähle das "kanonische" Dokument aus einer Gruppe von Near-Duplicates.
    
    Heuristiken (Priorität):
    1. Kürzere URL bevorzugen (oft Hauptseite)
    2. Weniger URL-Parameter bevorzugen
    3. Keine Anker (#) bevorzugen
    4. Bei Gleichheit: Mehr Text bevorzugen (vollständiger)
    """
```

## Mathematische Grundlagen

### MinHash-Eigenschaft

Die Wahrscheinlichkeit, dass zwei MinHash-Signaturen an einer Position übereinstimmen, entspricht der Jaccard-Ähnlichkeit:

$$P[h_{min}(A) = h_{min}(B)] = J(A, B)$$

Mit `num_perm=128` Permutationen wird die Jaccard-Ähnlichkeit mit hoher Genauigkeit geschätzt.

### LSH-Bandstruktur

MinHashLSH teilt die Signatur in Bänder (bands) auf:
- Zwei Dokumente werden als Kandidaten erkannt, wenn mindestens ein Band identisch ist
- Die Anzahl der Bänder und Zeilen pro Band wird automatisch basierend auf `threshold` berechnet

Für `threshold=0.9` mit `num_perm=128`:
- Dokumente mit $J \geq 0.9$ werden mit hoher Wahrscheinlichkeit als Kandidaten erkannt
- Dokumente mit $J < 0.9$ werden mit hoher Wahrscheinlichkeit gefiltert

## Datenfluss

```
┌─────────────────────────────────────────────────────┐
│              Dokument-Korpus (nach Exact-Dedup)     │
│  Doc1: "Der Student geht zur Uni und studiert..."  │
│  Doc2: "Der Student geht zur Universität und..."   │
│  Doc3: "Die Professorin hält eine Vorlesung..."    │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│               Wort-Shingles (k=5)                   │
│  Doc1: {"der student geht zur uni", ...}           │
│  Doc2: {"der student geht zur universität", ...}   │
│  Doc3: {"die professorin hält eine vorlesung", ...}│
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│              MinHash-Signaturen (128 Werte)         │
│  Doc1: [42, 17, 83, 91, ...]                       │
│  Doc2: [42, 17, 83, 91, ...]  ← Sehr ähnlich!      │
│  Doc3: [15, 66, 29, 44, ...]  ← Unterschiedlich    │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│                LSH-Kandidatensuche                  │
│  Doc2 inserting → query finds [Doc1] as candidate  │
│  Doc3 inserting → query finds [] (no candidates)   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│                Union-Find Clustering                │
│  Cluster 1: {Doc1, Doc2}  ← Near-Duplicates        │
│  Cluster 2: {Doc3}        ← Unique                 │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────┐
│            Kanonische Auswahl                       │
│  Behalte: Doc1 (kürzere URL), Doc3                 │
│  Entfernt: Doc2                                    │
└─────────────────────────────────────────────────────┘
```

## Integration im Scraper

```python
from src.advanced_rag.pre_retrieval.deduplication_MinHash_LSH_Framework import (
    DatasketchConfig,
    deduplicate_documents_datasketch
)

# Konfiguration aus rag.env laden
config = DatasketchConfig.from_rag_config()
# Oder manuell:
config = DatasketchConfig(
    threshold=0.9,
    num_perm=128,
    min_words=120
)

# Near-Deduplication durchführen
unique_docs, stats = deduplicate_documents_datasketch(
    documents=exact_deduped_docs,  # Nach Exact-Dedup!
    config=config,
    text_key='text',
    id_key='doc_id'
)

print(f"Near-Dedup Statistiken:")
print(f"  Input: {stats['input_count']} Dokumente")
print(f"  Output: {stats['output_count']} Dokumente")
print(f"  Cluster: {stats['num_clusters']}")
print(f"  Übersprungen (zu kurz): {stats['skipped_short']}")
```

## Warum Threshold=0.9?

| Threshold | Effekt |
|-----------|--------|
| 0.7 | Sehr aggressiv - entfernt auch nur ähnliche Dokumente |
| 0.8 | Moderat - findet paraphrasierte Inhalte |
| **0.9** | **Konservativ - nur fast-identische Dokumente** |
| 0.95 | Sehr konservativ - fast nur Kopien |

Mit `threshold=0.9` werden nur Dokumente entfernt, die zu **90%+ identisch** sind:
- Gleicher Inhalt mit minimalen Textänderungen
- Kopien mit leicht unterschiedlicher Formatierung
- Archivierte Versionen mit Datumsänderungen

## Warum min_words=120?

Dokumente mit weniger als 120 Wörtern werden übersprungen:
- Sehr kurze Dokumente haben wenige Shingles
- MinHash-Schätzung wird ungenau bei kleinen Mengen
- Navigationselemente/Footer werden oft als ähnlich erkannt
- 120 Wörter ≈ ein Absatz mit relevanten Informationen

## Pipeline-Position

```
┌─────────────┐
│   Scraping  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ HTML → Text │
└──────┬──────┘
       │
       ▼
┌─────────────────────┐
│   EXACT DEDUP      │
│ (SHA256 Hashing)   │
└──────┬─────────────┘
       │
       ▼
┌─────────────────────┐
│ ★ NEAR DEDUP ★     │  ← Hier
│ (MinHash + LSH)    │
└──────┬─────────────┘
       │
       ▼
┌─────────────────────┐
│ Semantic Chunking  │
└─────────────────────┘
```

## Referenzen

- **datasketch Library**: https://ekzhu.com/datasketch/
- **MinHash Paper**: Broder, A. Z. (1997). "On the resemblance and containment of documents"
- **LSH Paper**: Indyk, P., & Motwani, R. (1998). "Approximate nearest neighbors: towards removing the curse of dimensionality"
- **Implementierung**: `src/advanced_rag/pre_retrieval/deduplication_MinHash_LSH_Framework.py`
