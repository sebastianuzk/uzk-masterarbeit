# WiSo Chatbot – System Guide

Autonomer RAG-basierter Chatbot-Agent für die WiSo-Fakultät der Universität zu Köln.

---

## Voraussetzungen

Python-Umgebung aktivieren:
```powershell
& ".\Masterarbeit\Scripts\Activate.ps1"
```

Ollama läuft lokal. `.env`-Datei im Projektstamm vorhanden (Vorlage: `.env.example`).

### Wichtige `.env`-Parameter

```bash
# Ollama – LLM-Backend
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b

# LLM-Verhalten
TEMPERATURE=0.0        # 0.0 = deterministisch
CONTEXT_WINDOW=14500   # Fallback; Agent überschreibt diesen Wert dynamisch je Modellgröße:
                       # 0.5b → 2048 | 1b → 4096 | 3b → 8192 | 7b/8b → 14500 | 20b/70b → 16384
RANDOM_SEED=42         # Reproduzierbarkeit

# Embedding-Modell
SENTENCE_TRANSFORMER_MODEL=BAAI/bge-m3
EMBEDDING_MAX_SEQ_LENGTH=1024

# Evaluation
RAGAS_EVAL_MODEL=qwen2.5:7b      # lokales Modell für RAGAS-Metriken
OPENAI_EVAL_MODEL=gpt-4.1-mini   # Cloud-Alternative
RUN_EVALUATION_LOCAL=false        # true = lokales Modell (Ollama), false = OpenAI
```

> **Credentials:** API-Schlüssel für LangSmith (`LANGSMITH_API_KEY`), OpenAI (`OPENAI_API_KEY`), Voyage (`VOYAGE_API_KEY`) und Cohere (`COHERE_API_KEY`) müssen ebenfalls gesetzt sein, sofern die jeweiligen Funktionen genutzt werden (Tracing, Cloud-Evaluation, ReRanking). Diese Werte sind personengebunden und **nicht** im Repository enthalten.

---

## Pipelines

### 1. Corpus aufbauen

Die drei Schritte müssen **in dieser Reihenfolge** ausgeführt werden:

#### Schritt 1 – Crawler (optional, falls kein Cache vorhanden)

> **Kann übersprungen werden**, wenn `data/html_cache/html_cache.db` und `data/pdf_cache/` bereits vorhanden sind. In diesem Fall direkt mit Schritt 2 fortfahren.

```powershell
& ".\Masterarbeit\Scripts\python.exe" -m src.scraper.pipelines.crawler_scraper_pipeline
```

Crawlt `wiso.uni-koeln.de` und legt die Ergebnisse im `data/`-Verzeichnis ab:

| Inhalt | Erwarteter Pfad |
|--------|-----------------|
| HTML-Cache (SQLite-Datenbank) | `data/html_cache/html_cache.db` |
| PDF-Dateien | `data/pdf_cache/*.pdf` (ggf. in Unterordnern) |

> **Hinweis:** Dieser Schritt kann übersprungen werden, wenn beide Caches bereits vorhanden sind. **`import_to_content_db` (Schritt 2) erwartet exakt diese Pfade.** Beim manuellen Bereitstellen eines bestehenden Caches sicherstellen, dass die SQLite-Datenbank unter `data/html_cache/html_cache.db` und die PDFs unter `data/pdf_cache/` abgelegt sind.

#### Schritt 2 – Import in die Content-Datenbank

```powershell
& ".\Masterarbeit\Scripts\python.exe" -m src.scraper.tools.import_to_content_db
```

Liest `html_cache/` und `pdf_cache/` ein und schreibt alle Dokumente komprimiert in `data/content_database.db` (SQLite).

#### Schritt 3 – Vektordatenbank aufbauen

```powershell
& ".\Masterarbeit\Scripts\python.exe" -m src.scraper.run_production_scraper
```

> **Hinweis:** Der Hinweis in `rag.env` gilt: **`ENABLE_SEMANTIC_CHUNKING`, `ENABLE_DEDUPLICATION` und `ENABLE_HYBRID_RETRIEVAL`** beeinflussen, wie der Corpus aufgebaut wird. Änderungen an diesen Flags erfordern nach dem Setzen ein **vollständiges Löschen von `data/vector_db/` (und ggf. `data/sparse_index/`) sowie ein erneutes Ausführen von Schritt 3**.

Liest `content_database.db`, führt Preprocessing + Chunking + Embedding durch und schreibt alle Chunks in `data/vector_db/` (ChromaDB, Collection `wiso_documents`).  
Falls `ENABLE_HYBRID_RETRIEVAL=true`: BM25 Sparse Index wird zusätzlich unter `data/sparse_index/wiso_documents/` erstellt.

---

### 2. Chatbot starten

Nach erfolgreichem Schritt 3:

```powershell
& ".\Masterarbeit\Scripts\python.exe" -m streamlit run src/ui/streamlit_app.py
```

Die App ist unter `http://localhost:8501` erreichbar.

---

### 3. Evaluation ausführen

#### Vollständige Evaluation

```powershell
& ".\Masterarbeit\Scripts\python.exe" src/evaluation/ragas_evaluation.py
```

Führt die RAGAS-Evaluation auf dem aktuellen RAG-Setup aus.

**Voraussetzung – Testset:** Die Datei `Testset.CSV` muss unter `src/evaluation/data/Testset.CSV` abgelegt sein. Das Skript erwartet mindestens die Spalten `id`, `question` und eine Ground-Truth-URL-Spalte.

**Checkpoint-Logik:** Nach jeder beantworteten Frage wird automatisch ein Checkpoint gespeichert unter `src/evaluation/data/responses_checkpoint_<TIMESTAMP>.pkl`. Wird die Evaluation unterbrochen (z. B. Absturz, Timeout), kann sie durch **erneutes Starten mit demselben `EVAL_TIMESTAMP`-Wert** nahtlos fortgesetzt werden – bereits verarbeitete Fragen werden übersprungen. Der Timestamp wird beim ersten Start generiert und in der Konsolenausgabe angezeigt; er muss für eine Fortsetzung oben im Skript manuell eingetragen werden.

#### Selektive Evaluation (`ragas_selective_evaluation.py`)

```powershell
& ".\Masterarbeit\Scripts\python.exe" src/evaluation/ragas_selective_evaluation.py
```

Ergänzt die Vollständige Evaluation um zwei zusätzliche Steuerungsmöglichkeiten, die direkt im Skript-Header konfiguriert werden:

```python
# Für eine neue Evaluation (Timestamp wird zur Laufzeit erzeugt):
EVAL_TIMESTAMPS = [datetime.now().strftime("%Y%m%d_%H%M%S")]

# Oder: Einen oder mehrere bestehende Checkpoint-Timestamps wiederverwenden:
EVAL_TIMESTAMPS = [
    "20260403_070914",
    # Weitere Timestamps für Batch-Evaluation...
]

# Nur bestimmte Frage-IDs evaluieren (None = alle):
EVAL_IDS = [1, 5, 10, 15]   # → nur diese IDs
EVAL_IDS = None              # → alle Fragen aus Testset.CSV
```

`EVAL_TIMESTAMPS` kann mehrere Timestamps enthalten – das Skript iteriert dann über alle Einträge und erzeugt pro Timestamp einen eigenen Ergebnisdatensatz (Batch-Evaluation mehrerer Konfigurationen). `EVAL_IDS` filtert die Testfragen vor der Verarbeitung, sodass gezielt einzelne Fragen nachbearbeitet oder problematische Fälle re-evaluiert werden können.

---

## Hilfsbefehle

### Anzahl Chunks in der Vektordatenbank prüfen

```powershell
& ".\Masterarbeit\Scripts\python.exe" -c "import chromadb; client = chromadb.PersistentClient(path='data/vector_db'); cols = client.list_collections(); print('Collections:', len(cols)); [print(c.name, c.count(), 'Chunks') for c in cols] if cols else print('Keine Collections/Chunks vorhanden')"
```

### Vektordatenbank löschen

```powershell
Remove-Item -Recurse -Force "data\vector_db"; Write-Host "✅ Vektordatenbank gelöscht"
```

> Danach muss Schritt 3 erneut ausgeführt werden.

### Backup erstellen

```powershell
Copy-Item -Path "data\vector_db" `
          -Destination "backups\<backup-name>" `
          -Recurse -Force
Write-Host "Backup erstellt: <backup-name>"
```

### Backup wiederherstellen

```powershell
Remove-Item -Recurse -Force "data\vector_db" -ErrorAction SilentlyContinue
Copy-Item -Path "backups\<backup-name>" `
          -Destination "data\vector_db" `
          -Recurse -Force
Write-Host "<backup-name> wiederhergestellt nach data/vector_db"
```

---

## Sparse Index (BM25)

| Aspekt | Details |
|--------|---------|
| **Ablageort** | `data/sparse_index/wiso_documents/` |
| **Erstellt durch** | Schritt 3 (`run_production_scraper`), wenn `ENABLE_HYBRID_RETRIEVAL=true` |
| **Dateien** | `bm25_index.pkl`, `tokenized_corpus.pkl`, `chunk_ids.pkl`, `summary.json` |

> **Wichtig:** Der Sparse Index ist an die Vektordatenbank gebunden – beide müssen aus demselben Scraper-Run stammen. Soll ein anderer Index genutzt werden, den bestehenden zuerst löschen:
> ```powershell
> Remove-Item -Recurse -Force "data\sparse_index\wiso_documents"
> ```
> Anschließend Schritt 3 erneut ausführen.

---

## Konfiguration

### RAG-Features und Parameter – `src/advanced_rag/rag.env`

Alle Feature-Flags und Hyperparameter des RAG-Systems:

```bash
# Naive Baseline (true = alle Advanced-Techniken deaktiviert)
RAG_NAIVE_SETUP=false

# Pre-Retrieval
ENABLE_SEMANTIC_CHUNKING=false      # Semantisches Chunking statt Character-basiert
ENABLE_DEDUPLICATION=false          # Exact + Near-Deduplication (MinHash+LSH)

# Retrieval
ENABLE_HYBRID_RETRIEVAL=false       # Baut BM25 Sparse Index + RRF Fusion
ENABLE_SPARSE_RETRIEVAL=false       # Nur BM25 (kein Dense)

# Post-Retrieval
ENABLE_RERANKING=false              # Cross-Encoder ReRanking
ENABLE_MMR=false                    # Maximum Marginal Relevance

# Chunking-Parameter (wirken sich auf Schritt 3 aus)
NAIVE_CHUNKING_MAX_SIZE=...
NAIVE_CHUNKING_OVERLAP=...
SEMANTIC_CHUNKING_MAX_SIZE=...
...

# Retrieval-Parameter (wirken sofort, kein Neuaufbau nötig)
TOP_K=...
HYBRID_RETRIEVAL_K_RETRIEVE=...
HYBRID_RETRIEVAL_RRF_K=...
RERANKING_CANDIDATES=...
MMR_LAMBDA=...
```

> **Faustregel:** Änderungen an Chunking-Flags oder `-Parametern sowie `ENABLE_HYBRID_RETRIEVAL` erfordern **Löschen der Vektordatenbank (+ ggf. Sparse Index) und erneutes Ausführen von Schritt 3**.  
> Änderungen an Post-Retrieval-Parametern (ReRanking, MMR, TOP_K, Retrieval-Kandidaten) wirken **sofort ohne Neuaufbau**.

### Systemkonfiguration – `.env` / `config/settings.py`

LLM-Modell, Embedding-Modell, LangSmith-Tracing und weitere Parameter. Vorlage: `.env.example`.

---

---

## Code-Struktur – relevante Stellen

---

### Preprocessing & Indexierung

**`src/scraper/run_production_scraper.py`** – Haupteinstiegspunkt für Schritt 3:
- `process_document()` (ca. Zeile 360): naive Preprocessing-Logik
  - HTML: BeautifulSoup entfernt `<script>`, `<style>`, `<nav>`, `<footer>`, Sidebar-Elemente etc.; Headings → Markdown; Listen, Tabellen, Blockquotes → Textprimitive; Whitespace normalisiert
  - PDF: pypdf (primär) / pdfplumber (Fallback); alle Whitespace-Zeichen inkl. Zeilenumbrüche zu einem Leerzeichen
  - Character-basiertes Chunking; Fragmente < 51 Zeichen werden verworfen
- Phase 2 (Embedding + ChromaDB): L2-normalisierte Vektoren, Batch-Embedding, Speicherung mit Metadaten (`doc_id`, `chunk_id`, `url`, `title`, `content_type`, `chunk_index`, `char_count`)

**`src/advanced_rag/pre_retrieval/chunking.py`** – Semantisches Chunking:
- Sentence-Splitting via Regex-Heuristik (Satzendzeichen + Großbuchstabe/Ziffer)
- Einbettung jeder Einheit, Cosine-Similarity zwischen Nachbarn
- Percentile-basierte Breakpoint-Erkennung (dokumentspezifischer Schwellenwert)
- Längenbeschränkungen: zu kurze Chunks werden gemergt, zu lange geteilt; konfigurierbarer Overlap analog zur Naive-Pipeline

**`src/advanced_rag/pre_retrieval/deduplication.py`** und **`deduplication_MinHash_LSH_Framework.py`**:
- Exact Deduplication: Hash-basiert auf Dokumentebene
- Near Deduplication: MinHash + LSH (datasketch); konfigurierbarer Ähnlichkeitsschwellenwert

---

### RAG-Tool & Retrieval

**`src/tools/rag_tool.py`** (`UniversityRAGTool`):
- LangChain `BaseTool`; drei Modi je nach `rag.env`: Naive (Dense-only), Sparse-only (BM25), Advanced (Hybrid + optionale Post-Processing-Stufen)
- Lazy-Initialisierung von ChromaDB-Client, Embedding-Modell und Reranker (einmalig gecacht)

**`src/advanced_rag/retrieval/hybrid_retrieval_rrf.py`**:
- `BM25SparseIndex`: Tokenisierung (lowercase, Umlauterhalt, kein Stemming/Stoppwörter), `BM25Okapi` aus `rank-bm25`
- `hybrid_retrieve()`: parallele Dense- und Sparse-Abfrage, Reciprocal Rank Fusion (RRF)

**`src/advanced_rag/post_retrieval/reranking.py`**:
- Provider: `local` (BGE-Reranker via Ollama), `voyage`, `cohere`
- Nimmt Top-N Kandidaten, gibt nach Score sortierte Dokumente zurück

**`src/advanced_rag/post_retrieval/maximum_marginal_relevance.py`**:
- Iterative Auswahl: $\arg\max_{d \in R \setminus S} \bigl[\lambda \cdot \text{Rel}(d) - (1-\lambda) \cdot \max_{s \in S} \text{Sim}(d, s)\bigr]$
- Cosine-Similarity-basiert; Embeddings werden einmalig berechnet und übergeben

---

### Agent

**`src/agent/react_agent.py`** (`ReactAgent`):
- LangGraph `create_react_agent()` mit `ChatOllama`
- Dynamische Context-Size je nach Modellgröße; `seed=42`, `temperature=0.0` für Reproduzierbarkeit
- FIFO-Memory; System-Prompt mit Tool-First-Strategie (immer erst `university_knowledge_search`)

**`src/ui/streamlit_app.py`** – Web-UI: initialisiert Agent, verwaltet Session-State und Chat-Historie.

---

### Konfigurationsmodell

**`src/advanced_rag/rag_config.py`** (`RAGConfig`): liest alle Feature-Flags und Parameter aus `rag.env`; wird von `run_production_scraper.py` und `rag_tool.py` genutzt.

**`config/settings.py`** (`Settings`): globale Parameter aus `.env` (LLM, Embedding-Modell, LangSmith, TOP_K u. a.).

---

### Evaluation

**`src/evaluation/ragas_evaluation.py`**:
- Agent wird auf Testset (`Testset.CSV`) ausgeführt
- MRR@5 und Hit@5 via URL-Matching der abgerufenen Chunks gegen Ground-Truth-URLs
- LangSmith-Tracing wird genutzt, um abgerufene Dokument-URLs pro Run zu rekonstruieren

---

## Code-Stellen im Detail

### Preprocessing & Indexierung

#### `src/scraper/run_production_scraper.py`

Das Skript liest alle Feature-Flags zu Beginn über `RAGConfig` (Zeilen 35–58: `USE_SEMANTIC_CHUNKING`, `USE_DEDUPLICATION`, `USE_HYBRID_RETRIEVAL`) und verzweigt anhand dieser Flags in verschiedene Pfade.

| Funktion | ca. Zeile | Aufgabe |
|----------|-----------|---------|
| `naive_extract_text_from_html()` | 125 | HTML → Markdown-ähnlicher Text via BeautifulSoup |
| `naive_clean_text()` | 255 | PDF-Text: alle Whitespace-Zeichen → einzelnes Leerzeichen |
| `naive_chunk_text()` | 265 | Character-basiertes Chunking mit Overlap; < 51 Zeichen verwerfen |
| `extract_document_text()` | 315 | Wie `process_document`, aber ohne Chunking (für Dedup-Pfad) |
| `chunk_document()` | 360 | Chunking eines bereits extrahierten Textes (Naive oder Semantic) |
| `process_document()` | 405 | Kombiniert Extraktion + Cleaning + Chunking für ein Dokument |
| `run_production_scraper()` | 462 | Hauptfunktion: DB iterieren, Phase 2 Embedding + ChromaDB, Phase 3 BM25 |

**`naive_extract_text_from_html()`** im Detail (ab Zeile ~125):

1. Entfernt alle nicht-inhaltlichen Tags: `<script>`, `<style>`, `<head>`, `<meta>`, `<noscript>`, `<iframe>`
2. Layout-Container entfernt: `<nav>`, `<header>`, `<footer>`, `<aside>`
3. Klassen/IDs mit boilerplate-Regex (`menu|nav|sidebar|breadcrumb|cookie|banner|popup|modal`) entfernt
4. Headings `<h1>`–`<h6>` → entsprechende `#`–`######` Markdown-Präfixe
5. `<ol>`/`<ul>` → nummerierte bzw. Bullet-Listen
6. `<blockquote>` → `>` Präfix
7. Block-Elemente (`<p>`, `<div>`, `<br>`, `<tr>`) → Zeilenumbrüche; `<td>`/`<th>` → Tab-getrennt
8. UI-Texte (z. B. „Menü schließen", „zum Inhalt springen") via Regex-Liste entfernt
9. Whitespace: mehrfache Spaces/Tabs → 1 Space; max. 2 aufeinanderfolgende Newlines

**Phase 2 – Embedding + Speicherung** (ab Zeile ~826 in `run_production_scraper()`):
- Batch-Embedding aller Chunks mit BGE-M3 über `SentenceTransformer.encode()`
- L2-Normalisierung jedes Embedding-Vektors (`vector / np.linalg.norm(vector)`)
- Speicherung in ChromaDB in Batches von max. 5.000 Chunks (`CHROMADB_BATCH_SIZE`)
- Metadaten pro Chunk: `doc_id`, `chunk_id` (Schema: `{content_type}_{doc_id}_chunk_{i}`), `url`, `title`, `content_type`, `chunk_index`, `total_chunks`, `char_count`

#### `src/scraper/tools/import_to_content_db.py` (Schritt 2)

- `import_html_cache()` (Zeile ~276): liest `data/html_cache/html_cache.db` (SQLite), dekodiert HTML und schreibt komprimiert in `content_database.db`
- `import_pdf_cache()` (Zeile ~367): iteriert rekursiv über `data/pdf_cache/` und importiert alle `.pdf`-Dateien
- `main()` (ab Zeile ~440): orchestriert beide Importe, gibt Fortschrittsausgabe

#### `src/advanced_rag/pre_retrieval/chunking.py` – `SemanticChunker`

Klasse `SemanticChunker` (Zeile 16). Einstiegspunkt: `chunk_by_paragraphs()` (Zeile 359).

| Methode | ca. Zeile | Aufgabe |
|---------|-----------|---------|
| `__init__()` | 17 | Parameter: `max_chunk_size`, `min_chunk_size`, `overlap`, `similarity_threshold`, `use_percentile`, `percentile` |
| `_split_into_sentences()` | 102 | Primär Split an `\n\n`; sekundär Regex `(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9\(\-])` |
| `_compute_embeddings()` | 148 | BGE-M3 Encoding aller Satzeinheiten (Lazy-Load des Modells) |
| `_compute_all_similarities()` | 178 | Cosine-Similarity zwischen je zwei aufeinanderfolgenden Sätzen |
| `_find_breakpoints()` | 200 | Dispatch: statischer Threshold oder Perzentil-Methode |
| `_find_breakpoints_static_threshold()` | 225 | Breakpoint wenn `sim < similarity_threshold` |
| `_find_breakpoints_percentile()` | 262 | Breakpoint wenn `sim ≤ np.percentile(similarities, percentile)` (dokumentspezifisch) |
| `_merge_small_chunks()` | 305 | Zu kurze Chunks gierig mit Nachbar zusammenführen bis `min_chunk_size` erreicht |
| `chunk_by_paragraphs()` | 359 | Hauptmethode: Split → Embed → Breakpoints → Chunks → Merge → Overlap anhängen |

Die Overlap-Logik (nach Zeile ~420) hängt die letzten `overlap` Zeichen des Vorgänger-Chunks an den Anfang des nächsten Chunks – Schnitt möglichst an Satz- oder Wortgrenzen.

#### `src/advanced_rag/pre_retrieval/deduplication.py` und `deduplication_MinHash_LSH_Framework.py`

- **Exact Dedup**: SHA-256-Hash des bereinigten Textes auf Dokumentebene; `deduplicate_documents_exact()` gibt Liste einzigartiger Dokumente zurück; Duplikate werden in `data/deduplication/` als Excel dokumentiert
- **Near Dedup**: MinHash + LSH via `datasketch`; `deduplicate_documents_datasketch()` verwendet Shingling (konfigurierbarer `shingle_size`) und Jaccard-Ähnlichkeitsschwellenwert (`near_deduplication_similarity_threshold` aus `rag.env`)

---

### RAG-Tool & Retrieval

#### `src/tools/rag_tool.py` – `UniversityRAGTool`

Erbt von `langchain.tools.BaseTool` (Zeile ~43). Im Konstruktor (Zeile ~78) werden `RAGConfig` und `Settings` geladen; daraus werden `_use_advanced` und `_use_sparse` gesetzt.

| Methode | Zeile | Aufgabe |
|---------|-------|---------|
| `_get_embedding_model()` | 98 | Lazy-Load BGE-M3; `max_seq_length` aus `settings.py` |
| `_get_reranker()` | 109 | Lazy-Load Reranker; bei `local`-Provider wird CrossEncoder sofort vorgeladen |
| `_should_use_advanced()` | ~150 | `True` wenn `use_hybrid_retrieval OR use_reranking OR use_mmr` |
| `_get_chromadb_client()` | 165 | Sucht `data/vector_db`; Fallback auf `src/scraper/vector_db` |
| `_naive_retrieve()` | 183 | Dense-only: Query embedden, L2-normalisieren, `collection.query(n_results=k)` |
| `_advanced_retrieve()` | 281 | Hybrid/Dense + optionales ReRanking + optionales MMR; gibt finale Dokumentliste zurück |
| `_sparse_retrieve()` | 465 | BM25-only: Sparse Index laden, Top-K zurückgeben |
| `_run()` | 554 | Einstiegspunkt des LangChain-Tools; Modus-Dispatch, Ergebnis als String formatiert |

**`_advanced_retrieve()` – interner Ablauf** (ab Zeile 281):
1. Falls `use_hybrid_retrieval`: ruft `hybrid_retrieve()` auf; Ergebnisse tragen `rrf_score`, `dense_rank`, `sparse_rank`
2. Falls nur Dense + ReRanking: `_naive_retrieve(k=reranking_candidates)`
3. Falls `use_reranking`: `reranker.rerank(query, documents[:reranking_candidates])`
4. Falls `use_mmr`: Embeddings aus Metadaten extrahieren; `mmr.select(documents, embeddings, scores, k_final, query)`
5. Finales Slicing auf `TOP_K`

#### `src/advanced_rag/retrieval/hybrid_retrieval_rrf.py`

**`BM25SparseIndex`** (Klasse, Zeile 55):

| Methode / Funktion | Zeile | Aufgabe |
|--------------------|-------|---------|
| `tokenize()` | 90 | Lowercase → Sonderzeichen entfernen (Umlaute behalten, `re.sub(r'[^a-zäöüß0-9\s]', ' ', ...)`) → `split()`; kein Stemming, keine Stoppwörter |
| `BM25SparseIndex.search()` | 275 | Tokenisiert Query, `bm25.get_scores()`, gibt Top-K als `(chunk_id, score)` zurück |
| `build_sparse_index_from_chunks()` | 573 | Hilfsfunktion: erstellt Index aus ChromaDB-Daten (genutzt in `run_production_scraper`) |
| `save()` / `load()` | ~300 / ~330 | Serialisierung via `pickle` nach `data/sparse_index/wiso_documents/` |

**`reciprocal_rank_fusion()`** (Zeile 619):

$$\text{RRF}(d) = \sum_{\text{Liste}} \frac{1}{k + \text{rank}(d)}$$

Nimmt mehrere Ranking-Listen als `List[List[Tuple[chunk_id, score]]]`; akkumuliert RRF-Scores; gibt fusioniertes Ranking zurück.

**`HybridRetriever`** (Klasse, Zeile 667):
- `_dense_retrieve()`: ChromaDB-Query, L2-Normalisierung → `(chunk_id, similarity)`
- `_sparse_retrieve()`: delegiert an `BM25SparseIndex.search()`
- `retrieve()`: ruft beide Retriever auf → `reciprocal_rank_fusion()` → holt vollständige Metadaten für Top-Ergebnisse aus ChromaDB nach

**`hybrid_retrieve()`** (Zeile 931): Convenience-Funktion; instanziiert `HybridRetriever`, ruft `retrieve()` auf. Wird direkt von `_advanced_retrieve()` im RAG-Tool aufgerufen.

#### `src/advanced_rag/post_retrieval/reranking.py`

Drei Reranker-Klassen hinter dem gemeinsamen Protocol `RerankerProtocol`:

| Klasse | Zeile | Provider | `rerank()` ab |
|--------|-------|----------|---------------|
| `VoyageReranker` | 38 | Voyage AI REST API | 135 |
| `CohereReranker` | 223 | Cohere REST API | 323 |
| `LocalReranker` | 454 | BGE-Reranker-v2-M3 (CrossEncoder, lokal) | 571 |

`create_reranker(provider, model)` (Zeile 771): Factory-Funktion; wählt anhand `RERANKER_PROVIDER` aus `rag.env` die richtige Klasse.

Alle `rerank()`-Methoden nehmen `(query: str, documents: List[dict])` und geben die Dokumente **nach Reranking-Score absteigend sortiert** zurück. Das Limitieren auf Top-N erfolgt anschließend im RAG-Tool.

#### `src/advanced_rag/post_retrieval/maximum_marginal_relevance.py`

Factory: `create_mmr(lambda_param, similarity_metric)` (Zeile 413).

**`select()`** (Zeile 215) – greedy MMR:

1. Berechnet paarweise Dokument-Ähnlichkeitsmatrix einmalig via `_compute_similarity_matrix()`
2. Iteriert bis `k_final` Dokumente ausgewählt:
   $$\text{MMR}(d) = \lambda \cdot \text{Rel}(d) - (1-\lambda) \cdot \max_{s \in S} \text{Sim}(d, s)$$
3. Fügt Dokument mit maximalem Score zu `selected` hinzu
4. Gibt `MMRResult` zurück: enthält `documents`, `lambda_param`, `swaps` (welche Dokumente aus Naive-Top-K verdrängt wurden)

Embeddings und Relevanz-Scores werden von `_advanced_retrieve()` übergeben – keine erneute Berechnung nötig.

---

### Agent

#### `src/agent/react_agent.py` – `ReactAgent`

| Code-Stelle | ca. Zeile | Inhalt |
|------------|-----------|--------|
| LangSmith-Tracing | 24–30 | `os.environ` Felder für LangSmith werden aus `settings` gesetzt |
| `MODEL_CTX_SIZES`-Dict | 35–46 | Mapping Modellgrößen-Schlüsselwörter → Context-Größen (`0.5b`→2048 … `70b`→16384) |
| `ChatOllama`-Initialisierung | ~55 | `seed=42`, `temperature`, `num_ctx` (dynamisch), `num_predict=2048`, `timeout=90` |
| `self.system_message` | ~75 | `SystemMessage` mit Tool-First-Instruktion und Sprachanpassung |
| `self.agent` | ~85 | `create_langgraph_agent(self.llm, self.tools)` – LangGraph ReAct-Graph |
| `chat()` | ~95 | Fügt `HumanMessage` zu FIFO-Memory, begrenzt auf `MEMORY_SIZE` Nachrichten, ruft `self.agent.invoke({"messages": [system_message] + memory})` auf |

Der Context-Size-Dispatch prüft, ob eines der Schlüsselwörter im Modellnamen vorkommt (`"8b" in model_name`), und wählt den passenden Wert aus `MODEL_CTX_SIZES`.

#### `src/ui/streamlit_app.py`

`ReactAgent` wird einmalig im `st.session_state` initialisiert. Chat-Input löst `agent.chat(message)` aus; Antwort und gesamte Chat-Historie werden im Session-State gespeichert und über `st.chat_message()` gerendert.

---

### Konfigurationsmodell

#### `src/advanced_rag/rag_config.py` – `RAGConfig`

- Dataclass; `load_from_env()` liest `src/advanced_rag/rag.env` via `python-dotenv`
- Alle Feature-Flags als `@property`: `baseline_enabled`, `use_semantic_chunking`, `use_deduplication`, `use_hybrid_retrieval`, `use_sparse_retrieval`, `use_reranking`, `use_mmr`
- Bei `baseline_enabled=True` geben alle `use_*`-Properties `False` zurück (Master-Switch für Naive-Baseline)
- Genutzt von `run_production_scraper.py` (Zeile 35) und `rag_tool.py` (Zeile ~87)

#### `config/settings.py` – `Settings`

- Liest `.env` via `python-dotenv`
- Wichtige Attribute: `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `TEMPERATURE`, `CONTEXT_WINDOW`, `SENTENCE_TRANSFORMER_MODEL`, `EMBEDDING_MAX_SEQ_LENGTH`, `TOP_K`, `MEMORY_SIZE`, `LANGSMITH_*`
- `Settings.validate()` prüft Pflichtfelder beim Start

---

### Evaluation

#### `src/evaluation/ragas_evaluation.py`

- Lädt Testset aus `src/evaluation/data/Testset.CSV` (Spalten: Frage, Ground-Truth-URL(s))
- Instanziiert `ReactAgent` und ruft `agent.chat(frage)` für jede Testfrage auf
- Rekonstruiert abgerufene Dokument-URLs aus LangSmith-Traces (Tool-Call-Inputs/-Outputs pro Run)
- `calculate_RR_at5()`: berechnet Reciprocal Rank; normalisiert `file://`-URLs auf Basis-URL für Vergleich mit Ground-Truth
- Ausgabe: MRR@5 und Hit@5 über alle Fragen; Ergebnisse werden als CSV/Excel in `src/evaluation/data/` gespeichert
