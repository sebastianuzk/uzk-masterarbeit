# Exact Deduplication: Textnormalisierung + SHA256 Hashing

## Übersicht

Das Exact Deduplication-Modul identifiziert und entfernt **exakte Duplikate** auf Dokumentebene. Durch Textnormalisierung werden irrelevante Unterschiede (Whitespace, Formatierung, Sonderzeichen) eliminiert, sodass inhaltlich identische Dokumente erkannt werden.

**Anwendungszeitpunkt**: Pre-Retrieval (vor dem Chunking)

## Verwendete Libraries

```
hashlib   # Python Standard Library - SHA256 Hashing
unicodedata  # Python Standard Library - Unicode-Normalisierung (NFKC)
```

Keine externen Abhängigkeiten erforderlich.

## Konfiguration

Die Exact Deduplication hat keine konfigurierbaren Hyperparameter – sie arbeitet deterministisch auf Basis der Normalisierungsregeln.

## Algorithmus im Detail

### 1. Textnormalisierung (`normalize_text`)

Die Normalisierungsfunktion eliminiert Formatierungsunterschiede, die semantisch irrelevant sind:

```python
def normalize_text(text: str) -> str:
    """
    Normalisiert Text für Hash-basierte Duplikaterkennung.
    
    Schritte:
    1. Lowercase-Konvertierung
    2. Unicode-Normalisierung (NFKC)
    3. Anführungszeichen-Vereinheitlichung
    4. Bindestrich-Vereinheitlichung
    5. Aufzählungszeichen-Entfernung
    6. Whitespace-Kollabierung
    """
    
    # 1. Lowercase
    text = text.lower()
    
    # 2. Unicode NFKC Normalisierung
    #    - Kompatibilitätszeichen → kanonische Form
    #    - z.B. "ﬁ" (Ligatur) → "fi"
    text = unicodedata.normalize('NFKC', text)
    
    # 3. Anführungszeichen vereinheitlichen
    #    " " „ ‟ → einfaches "
    text = re.sub(r'[""„‟]', '"', text)
    text = re.sub(r"[''‚‛]", "'", text)
    
    # 4. Bindestriche vereinheitlichen
    #    – — ‐ ‑ → einfacher Bindestrich -
    text = re.sub(r'[–—‐‑]', '-', text)
    
    # 5. Aufzählungszeichen entfernen
    #    • ◦ ▪ ▫ ● ○ → entfernt
    text = re.sub(r'[•◦▪▫●○]', '', text)
    
    # 6. Whitespace kollabieren
    #    Mehrfache Leerzeichen/Tabs/Newlines → einzelnes Leerzeichen
    text = re.sub(r'\s+', ' ', text)
    
    # 7. Trim
    return text.strip()
```

### 2. Hash-Berechnung

```python
def compute_normalized_hash(text: str) -> str:
    """
    Berechnet SHA256-Hash des normalisierten Textes.
    
    Returns:
        64-Zeichen hexadezimaler Hash-String
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
```

### 3. Duplikatgruppierung

```python
def deduplicate_documents_exact(
    documents: List[dict],
    text_key: str = 'text',
    id_key: str = 'doc_id',
    return_groups: bool = False
) -> Union[List[dict], Tuple[List[dict], Dict[str, List[dict]]]]:
    """
    Entfernt exakte Duplikate basierend auf normalisiertem Hash.
    
    Workflow:
    1. Berechne Hash für jedes Dokument
    2. Gruppiere Dokumente mit gleichem Hash
    3. Behalte jeweils ein Dokument pro Gruppe (erstes)
    
    Args:
        documents: Liste von Dokumenten
        text_key: Schlüssel für den Textinhalt
        id_key: Schlüssel für die Dokument-ID
        return_groups: Ob Duplikatgruppen zurückgegeben werden sollen
    
    Returns:
        Deduplizierte Dokumente (und optional Duplikatgruppen)
    """
```

## Mathematische Grundlage

### SHA256 Hashing

SHA256 erzeugt einen 256-Bit (64 Hex-Zeichen) Hash mit folgenden Eigenschaften:

- **Deterministisch**: Gleicher Input → gleicher Output
- **Kollisionsresistent**: Praktisch unmöglich, zwei verschiedene Texte mit gleichem Hash zu finden
- **Lawineneffekt**: Kleine Änderungen → komplett anderer Hash

$$H: \{0,1\}^* \rightarrow \{0,1\}^{256}$$

### Normalisierungsäquivalenz

Zwei Texte $t_1$ und $t_2$ sind **exakt gleich** wenn:

$$\text{normalize}(t_1) = \text{normalize}(t_2)$$

Da SHA256 kollisionsresistent ist:

$$H(\text{normalize}(t_1)) = H(\text{normalize}(t_2)) \Leftrightarrow t_1 \equiv t_2$$

## Datenfluss

```
┌─────────────────┐
│   Dokument 1    │   "Der   Hund läuft."
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  normalize()    │   "der hund läuft."
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    SHA256()     │   "a7b3c2d1..."
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│           Hash-Gruppierung              │
│  ┌──────────────────────────────────┐  │
│  │ "a7b3c2d1..." → [Doc1, Doc5]     │  │
│  │ "f4e6d8a2..." → [Doc2]           │  │
│  │ "b1c9e7f3..." → [Doc3, Doc4, Doc6]│  │
│  └──────────────────────────────────┘  │
└────────┬────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│ Behalte erstes  │   [Doc1, Doc2, Doc3]
│ pro Gruppe      │
└─────────────────┘
```

## Integration im Scraper

```python
from src.advanced_rag.pre_retrieval.deduplication import (
    deduplicate_documents_exact,
    create_dedup_excel
)

# Exact Deduplication durchführen
unique_docs, duplicate_groups = deduplicate_documents_exact(
    documents=all_documents,
    text_key='text',
    id_key='doc_id',
    return_groups=True
)

# Optional: Excel-Report erstellen
create_dedup_excel(
    unique_docs=unique_docs,
    duplicate_groups=duplicate_groups,
    output_path="data/deduplication/exact_dedup_report.xlsx"
)

print(f"Vor Dedup: {len(all_documents)} Dokumente")
print(f"Nach Dedup: {len(unique_docs)} Dokumente")
print(f"Entfernt: {len(all_documents) - len(unique_docs)} Duplikate")
```

## Excel-Export für Analyse

Das Modul erstellt einen detaillierten Excel-Report (`create_dedup_excel`):

| Sheet | Inhalt |
|-------|--------|
| Overview | Statistiken (Anzahl Dokumente, Duplikate, Reduktion %) |
| Unique Documents | Alle beibehaltenen Dokumente mit Hash |
| Duplicate Groups | Alle Duplikatgruppen mit Mitgliedern |

## Warum Exact Deduplication?

### Problem: Identische Inhalte auf verschiedenen URLs

Universitäts-Webseiten haben oft:
- Identische Inhalte unter verschiedenen URL-Parametern
- Gespiegelte Seiten (z.B. `/de/` und `/studium/`)
- Archivierte Versionen

### Lösung

Exact Deduplication erkennt diese **inhaltlich identischen** Dokumente unabhängig von:
- URL-Unterschieden
- Whitespace-Formatierung
- Unicode-Varianten
- Aufzählungszeichen-Styles

### Abgrenzung zu Near-Deduplication

| Exact Deduplication | Near-Deduplication |
|---------------------|-------------------|
| 100% identisch (nach Normalisierung) | ~90% ähnlich |
| SHA256 Hash | MinHash + LSH |
| Schnell (O(n)) | Komplexer (O(n·m)) |
| Keine False Positives | Kann ähnliche Dokumente finden |

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
│ ★ EXACT DEDUP ★    │  ← Hier (vor Near-Dedup)
│ (Textnormalisierung │
│  + SHA256 Hashing)  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   NEAR DEDUP       │
│ (MinHash + LSH)    │
└──────┬─────────────┘
       │
       ▼
┌─────────────────────┐
│ Semantic Chunking  │
└─────────────────────┘
```

## Referenzen

- **SHA256**: NIST FIPS 180-4 Secure Hash Standard
- **Unicode NFKC**: Unicode Standard Annex #15 - Normalization Forms
- **Implementierung**: `src/advanced_rag/pre_retrieval/deduplication.py`
