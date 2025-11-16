# Installation

## Voraussetzungen

- Python 3.8+
- Ollama installiert
- 4GB+ RAM

## Schritt 1: Repository klonen

```bash
git clone https://github.com/sebastianuzk/uzk-masterarbeit.git
cd uzk-masterarbeit
```

## Schritt 2: Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oder
.venv\Scripts\activate     # Windows
```

## Schritt 3: Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Schritt 4: Ollama Modell

```bash
# In separatem Terminal
ollama pull llama3.1:8b
```

## Schritt 5: Environment Variablen

Erstelle `.env` Datei:

```bash
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
LANGSMITH_TRACING=false
```

## ✅ Installation verifizieren

```bash
make test
```
