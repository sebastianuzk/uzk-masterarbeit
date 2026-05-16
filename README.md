# Autonomous Chatbot Agent with RAG Web Scraper

An autonomous chatbot agent for the WiSo Faculty of the University of Cologne, built with LangChain and LangGraph, featuring an advanced web-scraping pipeline for Retrieval-Augmented Generation (RAG).

> **Reproducibility:** All setup steps are documented in the [Quick Start](#-quick-start) section below. Pre-built vector database available for download: [→ Vector DB Download](#-vector-database)

---

## Overview

This project provides an intelligent chatbot that:
- Answers questions about the WiSo Faculty (programmes, applications, services, etc.)
- Automatically retrieves relevant information from the faculty website
- Classifies content into five categories: Studium, Fakultät, Services, Forschung, Allgemein
- Runs fully locally using open-source components — no external API costs required

## Features

### Agent Architectures
Four agent types are available, selectable at runtime:

| Agent | Description |
|---|---|
| `single` | Standard ReAct agent (`create_react_agent` from LangGraph) |
| `multi` | Multi-agent system with specialised sub-agents |
| `constrained` | Schema-validated agent — rejects malformed tool calls using Pydantic |
| `confirmation` | LLM self-critique agent — validates tool calls semantically before execution |

### Tools
| Tool | Purpose |
|---|---|
| `university_knowledge_search` | RAG over 329 categorised WiSo documents |
| `web_scraper` | Extracts content from arbitrary URLs |
| `duckduckgo_search` | Privacy-friendly web search |
| `klips2_register` | KLIPS2 account registration |
| `klips2_apply_study` | Study application (wizard automation) |
| `klips2_get_course_details` | Course detail retrieval |
| `klips2_change_address` | Address update |
| `klips2_change_password` | Password change |
| `send_email` | Support escalation via SMTP |

> **Disclaimer:** Full end-to-end functionality of the KLIPS2 tools (`klips2_*`) was not a primary objective of this thesis — the research focus was on agent architecture, tool-selection accuracy, and RAG quality. These tools automate interactions with the KLIPS2 web interface via browser automation and may break if the university updates its portal layout or authentication flow. They are provided as a proof-of-concept and are not guaranteed to work against the live system.

### Vector Database
- **329 document chunks** from 50 WiSo web pages
- ChromaDB with `BAAI/bge-m3` embeddings (1024 dimensions, multilingual DE/EN)
- Five named collections: `wiso_studium`, `wiso_fakultaet`, `wiso_services`, `wiso_forschung`, `wiso_allgemein`

## Technology Stack

| Component | Technology |
|---|---|
| LLM Framework | LangChain + LangGraph |
| Local LLM | Ollama (`llama3.1:8b`, `gpt-oss:20b`) |
| Cloud LLMs | OpenAI (GPT-4o, GPT-5), Anthropic (Claude Sonnet/Opus) |
| Vector DB | ChromaDB |
| Embeddings | `BAAI/bge-m3` via Sentence Transformers |
| UI | Streamlit |
| Web Search | DuckDuckGo |
| Web Scraping | aiohttp + BeautifulSoup |
| Evaluation | Custom framework + RAGAS |

## Project Structure

```
uzk-masterarbeit/
├── main.py                         # Entry point (CLI + Streamlit)
├── requirements.txt
├── config/
│   ├── settings.py                 # Central configuration (reads .env)
│   └── logging_config.py
├── src/
│   ├── agent/
│   │   ├── react_agent.py          # Single-agent (ReAct)
│   │   ├── llm_factory.py          # LLM provider abstraction
│   │   ├── tool_loader.py
│   │   ├── tool_specs.py           # Tool metadata for prompts/validation
│   │   ├── json_extraction.py      # UTF-8-safe arg extraction (Ollama fix)
│   │   ├── confirmation/           # Confirmation agent
│   │   ├── constrained/            # Constrained agent (Pydantic schemas)
│   │   └── multi/                  # Multi-agent system
│   ├── tools/
│   │   ├── rag_tool.py
│   │   ├── web_scraper_tool.py
│   │   ├── duckduckgo_tool.py
│   │   ├── email_tool.py
│   │   └── klips/                  # KLIPS2 tool implementations
│   ├── scraper/                    # Web scraping pipeline
│   │   ├── core/                   # Crawler, vector store, batch processing
│   │   ├── pipelines/              # Runnable pipeline scripts
│   │   └── utils/                  # Chunking, deduplication, PDF extraction
│   └── ui/
│       └── streamlit_app.py
├── eval/
│   ├── run_full_evaluation.py      # Main evaluation script
│   ├── core/
│   │   ├── evaluation.py           # Argument matching logic (SEMANTIC mode)
│   │   └── runner.py               # Scenario runner, metrics, reports
│   └── scenarios/
│       └── klips/                  # 100 test scenarios (register, apply, ...)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── llm/
└── data/
    └── eval/final/                 # Evaluation results by model/agent
├── eval/
│   └── ragas_eval/data/vector_db/ # ChromaDB collections (see Vector DB section)
```

---

## Quick Start

### System Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Python | 3.10 | 3.11+ |
| RAM | 8 GB | 16 GB+ |
| GPU VRAM | — | 8 GB+ (for local Ollama models) |
| OS | Linux / macOS / Windows (WSL2) | Linux |

### 1. Clone and Install

```bash
git clone -b Abgabe_JSebastian_de_Wet https://github.com/sebastianuzk/uzk-masterarbeit.git
cd uzk-masterarbeit

python3 -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root. Required fields are marked with `# REQUIRED`:

```dotenv
# ── LLM Provider ─────────────────────────────────────────────────
# Choose one: ollama | openai | anthropic
LLM_PROVIDER=ollama                    # REQUIRED

# ── Ollama (local) ───────────────────────────────────────────────
OLLAMA_BASE_URL=http://localhost:11434  # Address of the Ollama server
OLLAMA_MODEL=llama3.1:8b               # Model name

# ── OpenAI (optional) ────────────────────────────────────────────
OPENAI_API_KEY=sk-...                  # REQUIRED if LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# ── Anthropic (optional) ─────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-...           # REQUIRED if LLM_PROVIDER=anthropic
ANTHROPIC_MODEL=claude-sonnet-4-6

# ── LangSmith Tracing (optional) ─────────────────────────────────
LANGSMITH_TRACING=false
# LANGSMITH_API_KEY=lsv2_pt_...
# LANGSMITH_PROJECT=masterarbeit
# LANGSMITH_ENDPOINT=https://api.smith.langchain.com

# ── Email Tool (optional) ─────────────────────────────────────────
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your@email.com
# SMTP_PASSWORD=your_app_password
# DEFAULT_RECIPIENT=support@example.com

# ── Misc (optional) ──────────────────────────────────────────────
TEMPERATURE=0.0
# NTFY_TOPIC=Evaluation   # Push notifications for evaluation runs
```

### 3. Pull an Ollama Model (if using `LLM_PROVIDER=ollama`)

```bash
# Install Ollama: https://ollama.com/download
ollama pull llama3.1:8b
```

### 4. Vector Database

> **Download:** [→ Vector DB on Google Drive](https://drive.google.com/drive/folders/1aqOYKc6DSfwgWFhHk2JL00eOr7Tbi_0Y?usp=sharing)

Extract the archive into `eval/ragas_eval/data/vector_db/`:

```bash
mkdir -p eval/ragas_eval/data/vector_db/
tar -xzf vector_db.tar.gz -C eval/ragas_eval/data/vector_db/
```

### 5. Run the Agent

```bash
# Streamlit UI — Single-Agent
python main.py --ui

# Streamlit UI — Multi-Agent
python main.py --ui --agent-mode multi

# CLI — Single-Agent
python main.py

# CLI — Multi-Agent
python main.py --agent-mode multi
```

---

## Running Tests

```bash
source .venv/bin/activate

# Recommended: run only unit tests — no LLM, no network, no credentials required
python -m pytest tests/ -m "not llm and not integration and not network and not klips and not email" -v
```


---

## Running Evaluations

Both evaluation types are run via the same entry point:

```bash
python -m eval.run_full_evaluation [options]
```

Results are saved to `data/eval/final/<model>/<timestamp>/`.

### Tool Evaluation

Tests tool-selection accuracy across 100 curated KLIPS2 scenarios.

```bash
# llama3.1:8b, single agent
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools

# OpenAI model (--provider selects the LLM backend for the agent under test)
python -m eval.run_full_evaluation --model gpt-5.2 --provider openai --agent single --mode tools

# Specific scenarios only
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --test-ids s1 s2 s3

# Limit number of scenarios
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --tool-limit 20

# With internal trace logging (for failed scenarios)
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --enable-trace

# Recommended: always pass --no-resume so each run starts clean
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --no-resume
```

**`--provider` flag:** selects the LLM backend for the *agent under test* — independent of the RAGAS judge. Valid values are `ollama`, `openai`, and `anthropic`. When omitted the value falls back to `LLM_PROVIDER` in your `.env`.

> **Recommendation:** run each model and agent variant in a separate command with `--no-resume` rather than using `--agent all`. This gives cleaner checkpoints and makes it easier to re-run a single failed variant without disturbing the others.

Available agent types (`--agent`):

| Value | Description |
|---|---|
| `single` | ReAct agent |
| `constrained` | Pydantic-validated agent |
| `confirmation` | LLM self-critique agent |
| `multi` | Multi-agent system |
| `all` | All four types |

### RAGAS Evaluation

Tests RAG answer quality using RAGAS metrics (faithfulness, context recall, answer relevancy). Runs the agent against up to 116 questions from the testset and uses a judge model to score the responses.

> **Required:** LangSmith tracing must be enabled for RAGAS evaluation to work. Set the following in your `.env` before running:
> ```dotenv
> LANGSMITH_TRACING=true
> LANGSMITH_API_KEY=lsv2_pt_...
> LANGSMITH_PROJECT=masterarbeit
> LANGSMITH_ENDPOINT=https://api.smith.langchain.com
> ```

```bash
# llama3.1:8b, single agent, Ollama judge
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag

# Use OpenAI as the RAGAS judge (recommended for quality)
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag \
  --ragas-judge-provider openai --ragas-judge-model gpt-4.1-mini

# Limit number of test questions (default: 100, max: 116)
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag --rag-limit 50

# Increase parallel judge workers for faster OpenAI evaluation
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag \
  --ragas-judge-provider openai --ragas-judge-model gpt-4.1-mini --ragas-workers 150

# Recommended: run with --no-resume and one model/agent at a time
python -m eval.run_full_evaluation --model gpt-5.2 --provider openai --agent single --mode rag \
  --ragas-judge-provider openai --ragas-judge-model gpt-4.1-mini --no-resume
```

RAGAS judge options:

| Flag | Default | Description |
|---|---|---|
| `--ragas-judge-provider` | auto-detect | `openai` or `ollama` |
| `--ragas-judge-model` | `gpt-4.1-mini` / `qwen2.5:7b` | Judge model name (recommended: `gpt-4.1-mini`) |
| `--ragas-workers` | `8` | Parallel judge workers (`150` recommended for OpenAI) |
| `--rag-limit` | `100` | Max number of RAGAS test questions (max 116) |

> **Recommendation:** run each model and agent variant separately with `--no-resume` to keep results isolated and avoid stale checkpoints carrying over between runs.

---

## Troubleshooting

**Ollama not reachable**
```bash
ollama serve         # start the server
ollama list          # verify available models
```

**Vector database not found**
```bash
python src/scraper/pipelines/crawler_scraper_pipeline.py --organize-by-category
```

**Import errors**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Slow performance with local models**
- Use a smaller model: `ollama pull llama3.2:1b`
- Reduce scraper concurrency: `--concurrent-requests 5`

---

## License

This project was created for academic purposes as part of a Master's thesis at the University of Cologne.

---

**Status:** Research prototype  
**Last updated:** May 2026
