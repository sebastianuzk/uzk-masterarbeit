# Hardware-Spezifikation

## Übersicht

Dieses Dokument beschreibt die lokale Hardware-Umgebung, auf der das RAG-System entwickelt und evaluiert wird.

---

## System-Informationen

| Komponente | Spezifikation |
|------------|---------------|
| **Hostname** | DESKTOP-D4OMR55 |
| **Betriebssystem** | Microsoft Windows 10 Pro (64-Bit) |
| **OS Version** | 10.0.19045 (Build 2009) |
| **System-Typ** | x64-based PC |

---

## CPU (Prozessor)

| Eigenschaft | Wert |
|-------------|------|
| **Modell** | Intel Core i7-9700KF |
| **Architektur** | x64 (64-Bit) |
| **Kerne** | 8 physische Kerne |
| **Threads** | 8 (kein Hyper-Threading) |
| **Basistakt** | 3.60 GHz |
| **Max Turbo** | 4.90 GHz |
| **Cache** | 12 MB Intel Smart Cache |
| **TDP** | 95W |
| **Generation** | 9th Gen (Coffee Lake) |

### Anmerkung
Der i7-9700KF ist ein **F-Variante** (ohne integrierte Grafik), daher wird eine dedizierte GPU benötigt.

---

## RAM (Arbeitsspeicher)

| Eigenschaft | Wert |
|-------------|------|
| **Installiert** | 32 GB |
| **Nutzbar** | ~31.9 GB |
| **Typ** | DDR4 (angenommen) |

### RAM-Auslastung (typische Workloads)

| Workload | Ungefähre Auslastung |
|----------|----------------------|
| Idle + VS Code | ~4-6 GB |
| Ollama + LLM (8B) | ~8-12 GB |
| Embedding (BGE-M3) | ~2-4 GB |
| ChromaDB Indexing | ~4-8 GB |
| **Vollständiger RAG-Run** | **~16-24 GB** |

---

## GPU (Grafikkarte)

| Eigenschaft | Wert |
|-------------|------|
| **Modell** | NVIDIA GeForce RTX 2060 SUPER |
| **VRAM** | 8 GB GDDR6 |
| **CUDA Cores** | 2176 |
| **Tensor Cores** | 272 (Gen 2) |
| **Architektur** | Turing (TU106) |
| **Treiber-Version** | 32.0.15.6094 |
| **CUDA Version** | 12.4 |
| **Compute Capability** | 7.5 |

### GPU-Nutzung im Projekt

| Komponente | GPU-Nutzung |
|------------|-------------|
| **Ollama LLM** | ✅ CUDA-beschleunigt |
| **BGE-M3 Embeddings** | ✅ CUDA-beschleunigt |
| **BGE-Reranker** | ✅ CUDA-beschleunigt |
| **ChromaDB** | ❌ CPU-only |
| **BM25 Index** | ❌ CPU-only |

### VRAM-Auslastung (typische Modelle)

| Modell | VRAM-Bedarf |
|--------|-------------|
| llama3.1:8b | ~5-6 GB |
| qwen2.5:7b | ~5-6 GB |
| phi4-mini:3.8b | ~3-4 GB |
| BGE-M3 Embedding | ~1-2 GB |
| BGE-Reranker-v2-M3 | ~1 GB |
| **Parallel (LLM + Embedding)** | **~7-8 GB** |

> ⚠️ **Hinweis:** Bei 8 GB VRAM ist parallele Nutzung von LLM und Embedding-Modell möglich, aber knapp. Größere Modelle (>8B Parameter) benötigen Offloading auf RAM.

---

## Speicher (Festplatten)

### Installierte Laufwerke

| Laufwerk | Modell | Größe | Typ |
|----------|--------|-------|-----|
| **C:** | Apacer AS350 | 256 GB | SSD (SATA) |
| **D:** | TOSHIBA HDWD130 | 3 TB | HDD (7200 RPM) |
| USB | Generic Flash Disk | 32 GB | USB-Stick |

### Speichernutzung im Projekt

| Daten | Speicherort | Größe (ca.) |
|-------|-------------|-------------|
| Python venv | `Masterarbeit/` | ~2-3 GB |
| Ollama Modelle | `Masterarbeit/ollama_models/` | ~25-30 GB |
| ChromaDB | `data/vector_db/` | ~500 MB |
| Content Database | `data/content_database.db` | ~150 MB |
| PDF Cache | `data/pdf_cache/` | ~200 MB |
| **Gesamt Projekt** | `uzk-masterarbeit/` | **~30-35 GB** |

> 📁 **Empfehlung:** Projekt auf SSD (C:) für schnellere I/O-Operationen.

---

## Software-Umgebung

### Python

| Eigenschaft | Wert |
|-------------|------|
| **Version** | Python 3.13.5 |
| **Pfad** | `Masterarbeit\Scripts\python.exe` |
| **venv** | Lokales Virtual Environment |

### PyTorch & CUDA

| Eigenschaft | Wert |
|-------------|------|
| **PyTorch** | 2.6.0+cu124 |
| **CUDA Toolkit** | 12.4 |
| **CUDA verfügbar** | ✅ Ja |
| **cuDNN** | Inkludiert |

### Ollama

| Eigenschaft | Wert |
|-------------|------|
| **Version** | 0.15.2 |
| **Modell-Pfad** | Standard (kann angepasst werden) |
| **GPU-Unterstützung** | ✅ CUDA |

---

## Installierte Ollama-Modelle

### LLM-Modelle (für Chatbot/Agent)

| Modell | Größe | Parameter | Verwendung |
|--------|-------|-----------|------------|
| `llama3.1:8b` | 4.9 GB | 8B | **Haupt-LLM** für Agent |
| `qwen2.5:7b-instruct` | 4.7 GB | 7B | Alternative |
| `qwen3:8b` | 5.2 GB | 8B | Alternative |
| `phi4-mini:3.8b` | 2.5 GB | 3.8B | RAGAS Evaluation |
| `deepseek-r1:8b` | 5.2 GB | 8B | Reasoning-Tests |

### Embedding-Modelle

| Modell | Größe | Dimensionen | Verwendung |
|--------|-------|-------------|------------|
| `bge-m3:latest` | 1.2 GB | 1024 | **Haupt-Embeddings** |
| `nomic-embed-text:v1.5` | 274 MB | 768 | Alternative |
| `embeddinggemma:latest` | 621 MB | - | RAGAS Evaluation |

### Reranker-Modelle

| Modell | Größe | Verwendung |
|--------|-------|------------|
| `qllama/bge-reranker-v2-m3:q8_0` | 635 MB | **Cross-Encoder Reranking** |

### Große Modelle (experimentell)

| Modell | Größe | Status |
|--------|-------|--------|
| `gpt-oss:20b` | 13 GB | Experimentell |
| `gpt-oss:120b` | 65 GB | Benötigt Offloading |

---

## Performance-Benchmarks (geschätzt)

### Embedding-Generierung (BGE-M3)

| Batch-Größe | Chunks/Sekunde | GPU-Auslastung |
|-------------|----------------|----------------|
| 32 | ~150 | ~60% |
| 64 | ~220 | ~75% |
| 128 | ~280 | ~85% |
| 256 | ~320 | ~95% |
| **512** | **~350** | **~98%** |

### LLM-Inferenz (llama3.1:8b)

| Metrik | Wert |
|--------|------|
| Tokens/Sekunde (Generation) | ~25-35 t/s |
| Time to First Token | ~0.5-1.0s |
| Context Window | 128k (nutzen: ~8k) |

### Scraper-Pipeline (Naive)

| Phase | Dauer (2675 Docs) |
|-------|-------------------|
| Phase 1: Decompress+Clean+Chunk | ~2-3 min |
| Phase 2: Embedding+Store | ~5-7 min |
| **Gesamt** | **~8-10 min** |

---

## Limitierungen & Empfehlungen

### Aktuelle Limitierungen

| Bereich | Limitierung | Workaround |
|---------|-------------|------------|
| **VRAM** | 8 GB (knapp für große Modelle) | Kleinere Modelle (≤8B) verwenden |
| **RAM** | 32 GB (ausreichend) | - |
| **SSD** | 256 GB (knapp) | Projekt auf HDD auslagern |
| **CPU** | Kein Hyper-Threading | Batch-Parallelisierung nutzen |

### Empfohlene Upgrades

| Komponente | Empfehlung | Begründung |
|------------|------------|------------|
| **GPU** | RTX 3080/4070 (12+ GB) | Größere Modelle, schnellere Inferenz |
| **SSD** | 1 TB NVMe | Schnellere I/O für DB-Operationen |
| **RAM** | 64 GB | Headroom für größere Batch-Sizes |

---

## Umgebungsvariablen

Relevante Umgebungsvariablen für GPU-Nutzung:

```bash
# CUDA Device (falls mehrere GPUs)
CUDA_VISIBLE_DEVICES=0

# Ollama GPU Layers (für Offloading)
OLLAMA_NUM_GPU=999  # Alle Layer auf GPU

# PyTorch Memory Management
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
```

---

## Monitoring-Befehle

### GPU-Auslastung (PowerShell)

```powershell
# Nvidia-SMI (Echtzeit)
nvidia-smi -l 1

# Nur Memory-Nutzung
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

### RAM-Auslastung

```powershell
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 Name, @{N='Memory(MB)';E={[math]::Round($_.WorkingSet64/1MB,0)}}
```

### Python GPU-Check

```python
import torch
print(f"CUDA: {torch.cuda.is_available()}")
print(f"Device: {torch.cuda.get_device_name(0)}")
print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

---

## Zusammenfassung

| Komponente | Status | Bewertung |
|------------|--------|-----------|
| **CPU** | i7-9700KF (8C/8T) | ✅ Ausreichend |
| **RAM** | 32 GB DDR4 | ✅ Ausreichend |
| **GPU** | RTX 2060 SUPER (8GB) | ⚠️ Knapp für große Modelle |
| **SSD** | 256 GB | ⚠️ Knapp für Daten |
| **HDD** | 3 TB | ✅ Ausreichend für Backups |

**Gesamtbewertung:** Die Hardware ist für die Entwicklung und Evaluation eines lokalen RAG-Systems mit 8B-Parameter-Modellen **gut geeignet**. Für größere Modelle (>13B) oder parallele Inferenz wäre mehr VRAM empfehlenswert.
