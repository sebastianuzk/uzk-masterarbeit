# Configuration

## Environment Variablen

Erstelle `.env` im Root-Verzeichnis:

```bash
# Ollama LLM
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
TEMPERATURE=0.7

# RAG
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# KLIPS2 Integration (Optional)
KLIPS_USERNAME=your_username
KLIPS_PASSWORD=your_password

# LangSmith (Optional)
LANGSMITH_TRACING=false
LANGSMITH_API_KEY=your_key
LANGSMITH_PROJECT=uzk-masterarbeit
```

## Ollama Models

Verfügbare Modelle:

```bash
# Empfohlen (Balance)
ollama pull llama3.1:8b

# Schneller (weniger Qualität)
ollama pull llama3.2:1b

# Bessere Qualität (langsamer)
ollama pull llama3.1:70b
```

## LangSmith Monitoring

Optional für Production:

1. Account: [smith.langchain.com](https://smith.langchain.com/)
2. API-Key generieren
3. In `.env`:
   ```bash
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=ls-...
   ```

## Production Config

Verwende `.env.production.example` als Template:

```bash
cp .env.production.example .env.production
# Bearbeite Werte
```
