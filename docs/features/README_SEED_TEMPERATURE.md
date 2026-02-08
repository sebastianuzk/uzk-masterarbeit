# Seed & Temperature Parameter - Dokumentation

## Übersicht

Diese Dokumentation beschreibt alle Stellen im Code, an denen die Parameter **Seed** und **Temperature** für Reproduzierbarkeit und deterministische Ausgaben eingesetzt werden.

---

## Zentrale Konfiguration

### `.env` (Single Source of Truth)

```dotenv
# LLM Parameter
TEMPERATURE=0.0
RANDOM_SEED=42
```

| Parameter | Wert | Zweck |
|-----------|------|-------|
| `TEMPERATURE` | `0.0` | Deterministische LLM-Antworten (kein Sampling) |
| `RANDOM_SEED` | `42` | Reproduzierbare Zufallszahlen |

### `config/settings.py`

```python
class Settings:
    # Zeile 25-26
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.0"))
    
    # Zeile 41
    RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))
```

Die zentrale `Settings`-Klasse lädt beide Parameter aus der `.env`-Datei und exportiert sie als Modul-Variablen:

```python
# Zeile 104
TEMPERATURE = settings.TEMPERATURE

# Zeile 127
RANDOM_SEED = settings.RANDOM_SEED
```

---

## Temperature-Parameter Verwendung

### 1. Chatbot Agent

**Datei:** `src/agent/react_agent.py`

```python
# Zeilen 57-64
self.llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=settings.TEMPERATURE,  # ← Aus zentrale Settings
    seed=42,
    num_ctx=ctx_size,
    timeout=90,
    num_predict=2048,
)
```

| Parameter | Wert | Begründung |
|-----------|------|------------|
| `temperature` | `settings.TEMPERATURE` (0.0) | Deterministische Antworten für konsistente Beratung |

### 2. RAGAS Evaluation (Lokal - Ollama)

**Datei:** `src/evaluation/ragas_evaluation.py`

```python
# Zeilen 667-673
llm = ChatOllama(
    model=RAGAS_EVAL_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=TEMPERATURE,  # ← Gleiche Temperature wie Chatbot
    seed=RANDOM_SEED,
    num_ctx=CONTEXT_WINDOW
)
```

| Parameter | Wert | Begründung |
|-----------|------|------------|
| `temperature` | `TEMPERATURE` (0.0) | Identische Bedingungen wie Chatbot für faire Evaluation |

### 3. RAGAS Evaluation (Cloud - OpenAI)

**Datei:** `src/evaluation/ragas_evaluation.py`

```python
# Zeilen 698-703
openai_llm = ChatOpenAI(
    model=OPENAI_EVAL_MODEL,
    api_key=OPENAI_API_KEY,
    temperature=0.0,  # ← Hardcoded für deterministische Evaluation
    seed=RANDOM_SEED,
    max_retries=5
)
```

| Parameter | Wert | Begründung |
|-----------|------|------------|
| `temperature` | `0.0` (hardcoded) | Deterministische Metrik-Berechnung, unabhängig von Chatbot-Settings |

### 4. Streamlit UI (Anzeige)

**Datei:** `src/ui/streamlit_app.py`

```python
# Zeile 116
st.write(f"Temperatur: {settings.TEMPERATURE}")
```

Zeigt dem Benutzer die aktuelle Temperature-Konfiguration in der Sidebar an.

---

## Seed-Parameter Verwendung

### 1. Chatbot Agent

**Datei:** `src/agent/react_agent.py`

```python
# Zeilen 57-64
self.llm = ChatOllama(
    model=settings.OLLAMA_MODEL,
    temperature=settings.TEMPERATURE,
    seed=42,  # ← ACHTUNG: Hardcoded, nicht aus Settings!
    ...
)
```

| Parameter | Wert | Status |
|-----------|------|--------|
| `seed` | `42` (hardcoded) | ⚠️ Sollte `settings.RANDOM_SEED` nutzen |

### 2. RAGAS Evaluation - Python Random

**Datei:** `src/evaluation/ragas_evaluation.py`

```python
# Zeilen 75-76
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
```

| Funktion | Zweck |
|----------|-------|
| `random.seed()` | Python Standard-Library Zufallsgenerator |
| `np.random.seed()` | NumPy Zufallsgenerator für Array-Operationen |

### 3. RAGAS Evaluation - LLM Seed

**Datei:** `src/evaluation/ragas_evaluation.py`

```python
# Ollama LLM (Zeile 671)
llm = ChatOllama(
    ...
    seed=RANDOM_SEED,  # ← Aus zentrale Settings
)

# OpenAI LLM (Zeile 703)
openai_llm = ChatOpenAI(
    ...
    seed=RANDOM_SEED,  # ← Aus zentrale Settings
)
```

### 4. RAGAS Evaluation - RunConfig

**Datei:** `src/evaluation/ragas_evaluation.py`

```python
# Lokal (Zeile 682)
run_config = RunConfig(
    max_workers=4,
    seed=RANDOM_SEED,
    timeout=300
)

# Cloud (Zeile 715)
run_config = RunConfig(
    max_workers=150,
    seed=RANDOM_SEED,
    timeout=1800,
    max_retries=5
)
```

Die `RunConfig` kontrolliert das Parallelisierungsverhalten von RAGAS und nutzt den Seed für reproduzierbare Batch-Verarbeitung.

### 5. MinHash/LSH Near-Deduplication

**Datei:** `src/advanced_rag/pre_retrieval/deduplication_MinHash_LSH_Framework.py`

```python
# Zeilen 88-96 (DeduplicationConfig)
from config.settings import RANDOM_SEED

return cls(
    num_perm=rag_config.MINHASH_NUM_PERM,
    jaccard_threshold=rag_config.MINHASH_THRESHOLD,
    ...
    seed=RANDOM_SEED  # ← Aus zentrale Settings
)

# Zeilen 144-146 (MinHash-Erstellung)
def _create_minhash(shingles: Set[str], num_perm: int = 128, seed: int = 42) -> MinHash:
    mh = MinHash(num_perm=num_perm, seed=seed)
    ...

# Zeile 278 (Aufruf)
mh = _create_minhash(shingles, num_perm=config.num_perm, seed=config.seed)
```

| Komponente | Seed-Quelle | Zweck |
|------------|-------------|-------|
| `DeduplicationConfig` | `RANDOM_SEED` (Settings) | Deterministische Hash-Permutationen |
| `MinHash()` | `config.seed` | Reproduzierbare Signaturen |

### 6. Scraper Deduplication (Legacy)

**Datei:** `src/scraper/deduplication_implementation.py`

```python
# Zeile 55 - Lokale Konstante
RANDOM_SEED = 42

# Zeile 818
random.seed(RANDOM_SEED)
```

| Status | Anmerkung |
|--------|-----------|
| ⚠️ Legacy | Hat eigene lokale `RANDOM_SEED`-Konstante statt zentrale Settings |

---

## Zusammenfassung: Seed-Verwendung

| Komponente | Datei | Seed-Quelle | Konsistent? |
|------------|-------|-------------|-------------|
| **Chatbot LLM** | `react_agent.py:61` | `42` (hardcoded) | ⚠️ Nein |
| **Evaluation LLM (Ollama)** | `ragas_evaluation.py:671` | `RANDOM_SEED` | ✅ Ja |
| **Evaluation LLM (OpenAI)** | `ragas_evaluation.py:703` | `RANDOM_SEED` | ✅ Ja |
| **Evaluation RunConfig** | `ragas_evaluation.py:682,715` | `RANDOM_SEED` | ✅ Ja |
| **Python/NumPy Random** | `ragas_evaluation.py:75-76` | `RANDOM_SEED` | ✅ Ja |
| **MinHash/LSH** | `deduplication_MinHash_LSH_Framework.py:96,278` | `RANDOM_SEED` | ✅ Ja |
| **Scraper Dedup** | `deduplication_implementation.py:55,818` | `42` (lokal) | ⚠️ Nein |

---

## Zusammenfassung: Temperature-Verwendung

| Komponente | Datei | Temperature-Wert | Konsistent? |
|------------|-------|------------------|-------------|
| **Chatbot LLM** | `react_agent.py:60` | `settings.TEMPERATURE` | ✅ Ja |
| **Evaluation LLM (Ollama)** | `ragas_evaluation.py:670` | `TEMPERATURE` | ✅ Ja |
| **Evaluation LLM (OpenAI)** | `ragas_evaluation.py:702` | `0.0` (hardcoded) | ⚠️ Bewusst |

---

## Warum Temperature=0.0 und Seed=42?

### Temperature = 0.0

Bei `temperature=0.0` wählt das LLM immer das wahrscheinlichste Token, was zu **deterministischen Ausgaben** führt:

```
Input: "Was sind die Bewerbungsfristen?"
Output: Immer identisch (bei gleichem Kontext)
```

**Vorteile für RAG-Chatbot:**
- Konsistente Antworten auf gleiche Fragen
- Reproduzierbare Evaluation
- Keine zufällige Variation bei Fakten-Fragen

### Seed = 42

Der Seed initialisiert Pseudo-Zufallsgeneratoren deterministisch:

1. **LLM-Seed:** Kontrolliert interne Sampling-Prozesse (relevant bei temperature > 0)
2. **MinHash-Seed:** Garantiert identische Hash-Permutationen für gleiche Dokumente
3. **Python/NumPy-Seed:** Deterministische Stichprobenziehung in Evaluation

**Warum 42?** Konvention aus Douglas Adams' "Per Anhalter durch die Galaxis" - die Antwort auf alles.

---

## Empfehlungen

### ⚠️ Inkonsistenzen beheben

1. **react_agent.py:** Hardcoded `seed=42` durch `seed=settings.RANDOM_SEED` ersetzen
2. **deduplication_implementation.py:** Lokale `RANDOM_SEED` durch Import aus `config.settings` ersetzen

### ✅ Best Practice

Alle Seeds und Temperature-Werte sollten aus der zentralen `.env`/`config/settings.py` geladen werden, um:
- Single Source of Truth zu gewährleisten
- Experimente mit verschiedenen Seeds zu ermöglichen
- Dokumentierte Reproduzierbarkeit sicherzustellen

---

## Diagramm: Seed-Propagation

```
┌─────────────────────────────────────────────────────────────────────┐
│                           .env                                       │
│                      RANDOM_SEED=42                                  │
│                      TEMPERATURE=0.0                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     config/settings.py                               │
│                   Settings.RANDOM_SEED                               │
│                   Settings.TEMPERATURE                               │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
           ▼                   ▼                   ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│   react_agent    │ │ ragas_evaluation │ │ MinHash/LSH      │
│   ChatOllama     │ │ ChatOllama       │ │ Deduplication    │
│   seed=42 ⚠️     │ │ seed=RANDOM_SEED │ │ seed=RANDOM_SEED │
│   temp=TEMP ✅   │ │ temp=TEMP ✅     │ │                  │
└──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

**Zuletzt aktualisiert:** Februar 2026
