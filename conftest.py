"""
Pytest Configuration and Fixtures
"""
import pytest
import sys
import os
from pathlib import Path

# Füge das Projekt-Root-Verzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


# ============================================================================
# GLOBAL FIXTURES
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def configure_fast_model():
    """Konfiguriere schnelles Modell für alle Tests"""
    from config.settings import settings
    
    # Speichere Original-Werte
    original_model = settings.OLLAMA_MODEL
    original_timeout = settings.REQUEST_TIMEOUT
    original_temp = settings.TEMPERATURE
    
    # Verwende llama3.2:3b - guter Kompromiss zwischen Geschwindigkeit und Qualität
    settings.OLLAMA_MODEL = "llama3.2:3b"
    settings.REQUEST_TIMEOUT = 60  # Längerer Timeout für Tests
    settings.TEMPERATURE = 0.7  # Moderate Temperatur für ausgewogene Antworten
    
    print(f"\n🚀 Test-Konfiguration: Modell='{settings.OLLAMA_MODEL}', Temp={settings.TEMPERATURE}, Timeout={settings.REQUEST_TIMEOUT}s")
    
    yield
    
    # Stelle Original-Werte wieder her
    settings.OLLAMA_MODEL = original_model
    settings.REQUEST_TIMEOUT = original_timeout
    settings.TEMPERATURE = original_temp


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
    return [
        "Uzk Masterarbeit - Chatbot Agent Tests",
        f"Project Root: {project_root}"
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
