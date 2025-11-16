# Project Structure

```
uzk-masterarbeit/
├── src/
│   ├── agent/          # LangGraph ReAct Agent
│   ├── tools/          # Agent Tools (RAG, Web, etc.)
│   ├── scraper/        # Web Scraping Pipeline
│   ├── ui/             # Streamlit Interface
│   └── dev/            # Development Scripts
├── config/             # Configuration
├── data/               # Vector DB & Cache
├── tests/              # Unit & Integration Tests
│   ├── unit/
│   ├── integration/
│   └── llm/
├── scripts/            # Deployment Scripts
│   ├── deployment/
│   └── ci/
└── docs/               # MkDocs Documentation
```

## Key Files

- `requirements.txt` - Python Dependencies
- `mkdocs.yml` - Documentation Config
- `Makefile` - Build Commands
- `pytest.ini` - Test Configuration
- `docker-compose.yml` - Local Docker Setup
