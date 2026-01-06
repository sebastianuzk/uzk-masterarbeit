"""
Pytest Configuration and Fixtures

Supports testing both single-agent and multi-agent systems via command line:
    pytest tests/                           # Default: single-agent
    pytest tests/ --agent-mode=single       # Explicit single-agent
    pytest tests/ --agent-mode=multi        # Multi-agent system
"""
import pytest
import sys
import os
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# ============================================================================
# COMMAND LINE OPTIONS
# ============================================================================

def pytest_addoption(parser):
    """Füge custom Command-Line-Optionen hinzu"""
    parser.addoption(
        "--agent-mode",
        action="store",
        default="single",
        choices=["single", "multi", "confirmation", "constrained"],
        help="Agent mode: 'single' for ReactAgent, 'multi' for MultiAgentSystem, 'confirmation' for ConfirmationAgent, 'constrained' for ConstrainedAgent (default: single)"
    )


# ============================================================================
# GLOBAL FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def agent_mode(request):
    """Gibt den gewählten Agent-Mode zurück"""
    return request.config.getoption("--agent-mode")


@pytest.fixture(scope="session")
def agent_factory(agent_mode):
    """
    Factory-Fixture für Agenten basierend auf dem gewählten Mode.
    
    Usage in tests:
        def test_something(agent_factory):
            agent = agent_factory()
            response = agent.chat("Hello")
    """
    from src.agent import create_agent
    
    def _create_agent():
        return create_agent(mode=agent_mode)
    
    return _create_agent


@pytest.fixture(scope="function")
def agent(agent_factory):
    """
    Fixture das einen frischen Agenten für jeden Test erstellt.
    
    Usage in tests:
        def test_something(agent):
            response = agent.chat("Hello")
    """
    return agent_factory()


@pytest.fixture(scope="session")
def project_root_path():
    """Gibt den Projekt-Root-Pfad zurück"""
    return project_root


@pytest.fixture(scope="session")
def ollama_available():
    """Prüft ob Ollama verfügbar ist"""
    try:
        import requests
        from config.settings import settings
        
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=3)
        return response.status_code == 200
    except:
        return False


@pytest.fixture(scope="session")
def vector_db_available():
    """Prüft ob Vector DB verfügbar ist"""
    try:
        import chromadb
        from pathlib import Path
        
        db_path = project_root / "data" / "vector_db"
        if not db_path.exists():
            return False
        
        client = chromadb.PersistentClient(path=str(db_path))
        collections = client.list_collections()
        return len(collections) > 0
    except:
        return False


# ============================================================================
# MARKERS
# ============================================================================

def pytest_configure(config):
    """Konfiguriere pytest mit custom markers"""
    config.addinivalue_line(
        "markers", "slow: Langsame Tests die länger als 5 Sekunden dauern"
    )
    config.addinivalue_line(
        "markers", "integration: Integration Tests"
    )
    config.addinivalue_line(
        "markers", "unit: Unit Tests"
    )
    config.addinivalue_line(
        "markers", "llm: LLM Quality Tests"
    )
    config.addinivalue_line(
        "markers", "agent: Tests that use the agent (affected by --agent-mode)"
    )


# ============================================================================
# TEST COLLECTION
# ============================================================================

def pytest_collection_modifyitems(config, items):
    """Modifiziere Test-Sammlung"""
    # Füge automatisch Marker basierend auf Test-Pfad hinzu
    for item in items:
        test_path = str(item.fspath)
        
        if "/unit/" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/llm/" in test_path:
            item.add_marker(pytest.mark.llm)
        
        # Füge slow marker für LLM tests hinzu
        if "/llm/" in test_path:
            item.add_marker(pytest.mark.slow)


# ============================================================================
# REPORTING
# ============================================================================

@pytest.hookimpl(tryfirst=True)
def pytest_report_header(config):
    """Füge custom Header zum Test-Report hinzu"""
    agent_mode = config.getoption("--agent-mode", default="single")
    mode_label = "Multi-Agent" if agent_mode == "multi" else "Single-Agent"
    return [
        "Uzk Masterarbeit - Chatbot Agent Tests",
        f"Project Root: {project_root}",
        f"Agent Mode: {mode_label} ({agent_mode})"
    ]


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Füge custom Summary zum Test-Report hinzu"""
    if hasattr(terminalreporter, 'stats'):
        passed = len(terminalreporter.stats.get('passed', []))
        failed = len(terminalreporter.stats.get('failed', []))
        skipped = len(terminalreporter.stats.get('skipped', []))
        
        terminalreporter.write_sep("=", "Test Summary")
        terminalreporter.write_line(f"✅ Passed:  {passed}")
        terminalreporter.write_line(f"❌ Failed:  {failed}")
        terminalreporter.write_line(f"⏭️  Skipped: {skipped}")
