# System Architecture

## Überblick

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │
┌──────▼──────────────┐
│  Streamlit UI       │
└──────┬──────────────┘
       │
┌──────▼──────────────┐
│  LangGraph Agent    │
│  (ReAct Pattern)    │
└──────┬──────────────┘
       │
       ├───► RAG Tool (329 Docs)
       ├───► Web Scraper Tool
       ├───► DuckDuckGo Tool
       ├───► KLIPS2 Tool
       └───► Email Tool
```

## Komponenten

### 1. **Agent System**
- LangGraph's `create_react_agent`
- Ollama LLM (llama3.1)
- Tool-basierte Architektur

### 2. **RAG Pipeline**
- ChromaDB Vector Store
- 5 kategorisierte Collections
- Semantic Search
- 329 Dokumente

### 3. **Tools**
- **RAG Tool**: WiSo-Fakultät Wissens-Datenbank
- **Web Scraper**: Live Website-Daten
- **DuckDuckGo**: Web-Suche
- **KLIPS2**: Registrierungs-Unterstützung
- **Email**: Support-Eskalation

### 4. **Scraper Pipeline**
- Async Batch-Processing
- Intelligente Kategorisierung
- Inkrementelles Update
- PDF-Extraktion
- Duplikat-Erkennung

## Datenfluss

1. **User-Input** → Streamlit UI
2. **Agent** analysiert Intent
3. **Tool-Selection** basierend auf Anfrage
4. **Tool-Execution** (RAG, Web, etc.)
5. **Response-Generation** durch LLM
6. **Output** → UI
