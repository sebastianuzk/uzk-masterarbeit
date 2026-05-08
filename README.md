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
├── Makefile                        # Convenience commands
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
    ├── vector_db/                  # ChromaDB collections (see Vector DB section)
    └── eval/final/                 # Evaluation results by model/agent
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
git clone <REPO_URL>
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

> **Download:** [→ PLACEHOLDER: insert vector database download link here](#)

Extract the archive into `data/vector_db/`:

```bash
tar -xzf vector_db.tar.gz -C data/vector_db/
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

Or via `make`:

```bash
make ui          # Streamlit, Single-Agent
make ui-multi    # Streamlit, Multi-Agent
make run         # CLI, Single-Agent
make run-multi   # CLI, Multi-Agent
```

---

## Running Tests

```bash
make test                # All tests
make test-fast           # Unit tests only (fast)
make test-integration    # Integration tests

# Or directly with pytest:
source .venv/bin/activate
python -m pytest tests/ -v
```

---

## Running Evaluations

Both evaluation types are run via the same entry point:

```bash
python -m eval.run_full_evaluation [options]
```

Results are saved to `data/eval/final/<model>/<timestamp>/`.

### Tool Evaluation

Tests tool-selection accuracy across 100 curated KLIPS2 scenarios. Metrics: F1, precision, recall, and argument matching.

```bash
# llama3.1:8b, single agent
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools

# OpenAI model
python -m eval.run_full_evaluation --model gpt-5.2 --provider openai --agent single --mode tools

# Compare all agent types
python -m eval.run_full_evaluation --model llama3.1:8b --agent all --mode tools

# Specific scenarios only
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --test-ids s1 s2 s3

# Limit number of scenarios
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --tool-limit 20

# With internal trace logging (for failed scenarios)
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --enable-trace

# Ignore existing checkpoints and restart
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode tools --no-resume
```

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

```bash
# llama3.1:8b, single agent, Ollama judge
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag

# Use OpenAI as the RAGAS judge (recommended for quality)
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag \
  --ragas-judge-provider openai --ragas-judge-model gpt-4o-mini

# Limit number of test questions (default: 100, max: 116)
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag --rag-limit 50

# Increase parallel judge workers for faster OpenAI evaluation
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode rag \
  --ragas-judge-provider openai --ragas-workers 150

# Run both tool and RAGAS evaluation in one pass
python -m eval.run_full_evaluation --model llama3.1:8b --agent single --mode all
```

RAGAS judge options:

| Flag | Default | Description |
|---|---|---|
| `--ragas-judge-provider` | auto-detect | `openai` or `ollama` |
| `--ragas-judge-model` | `gpt-4o-mini` / `qwen2.5:7b` | Judge model name |
| `--ragas-workers` | `8` | Parallel judge workers (`150` recommended for OpenAI) |
| `--rag-limit` | `100` | Max number of RAGAS test questions (max 116) |

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
