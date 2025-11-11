#!/usr/bin/env python3
"""
Tech-Stack Validierung für RAG-Evaluation

Überprüft die Kompatibilität der Evaluation mit dem bestehenden System.
"""

import sys
from pathlib import Path
import logging

# Projekt-Root hinzufügen
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def validate_tech_stack():
    """
    Validiert die Kompatibilität des Tech-Stacks.
    
    Returns:
        Dict mit Validierungsergebnissen
    """
    results = {
        'ollama_config': False,
        'chromadb_access': False,
        'embedding_consistency': False,
        'rag_tool_available': False,
        'hyperparameters_loaded': False,
        'overall_status': False
    }
    
    print("🔍 Tech-Stack Validierung für RAG-Evaluation")
    print("=" * 60)
    
    # 1. Ollama-Konfiguration
    try:
        from config.settings import OLLAMA_BASE_URL, OLLAMA_MODEL
        from langchain_ollama import ChatOllama
        
        llm = ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.1
        )
        
        # Teste einfache Ollama-Verbindung
        test_response = llm.invoke("Hallo")
        if test_response:
            results['ollama_config'] = True
            print(f"✅ Ollama: {OLLAMA_MODEL} @ {OLLAMA_BASE_URL}")
        
    except Exception as e:
        print(f"❌ Ollama-Problem: {e}")
    
    # 2. ChromaDB-Zugriff
    try:
        import chromadb
        from pathlib import Path
        
        # Teste beide möglichen Vector-DB-Pfade
        vector_db_paths = [
            Path("src/scraper/vector_db").resolve(),
            Path("data/vector_db").resolve()
        ]
        
        found_db = False
        for path in vector_db_paths:
            if path.exists():
                try:
                    client = chromadb.PersistentClient(path=str(path))
                    collections = client.list_collections()
                    if collections:
                        results['chromadb_access'] = True
                        found_db = True
                        print(f"✅ ChromaDB: {len(collections)} Collections in {path}")
                        for col in collections[:3]:  # Zeige max 3 Collections
                            print(f"   - {col.name}")
                        break
                except Exception as e:
                    continue
        
        if not found_db:
            print(f"❌ ChromaDB: Keine Vector-Datenbank gefunden in {vector_db_paths}")
            
    except Exception as e:
        print(f"❌ ChromaDB-Problem: {e}")
    
    # 3. Embedding-Konsistenz
    try:
        from src.scraper.hyperparameters import VECTOR_EMBEDDING_MODEL
        from langchain_huggingface import HuggingFaceEmbeddings
        
        embeddings = HuggingFaceEmbeddings(
            model_name=VECTOR_EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'}
        )
        
        # Teste Embedding-Generierung
        test_embedding = embeddings.embed_query("Test")
        if test_embedding and len(test_embedding) > 0:
            results['embedding_consistency'] = True
            print(f"✅ Embeddings: {VECTOR_EMBEDDING_MODEL} (Dimension: {len(test_embedding)})")
        
    except Exception as e:
        print(f"❌ Embedding-Problem: {e}")
    
    # 4. RAG-Tool verfügbar
    try:
        from src.tools.rag_tool import create_university_rag_tool
        
        rag_tool = create_university_rag_tool()
        test_result = rag_tool._run("Test-Frage")
        
        if test_result and not test_result.startswith("❌"):
            results['rag_tool_available'] = True
            print(f"✅ RAG-Tool: Funktionsfähig")
        else:
            print(f"⚠️ RAG-Tool: Läuft, aber keine Daten verfügbar")
            print(f"   Antwort: {test_result[:100]}...")
            
    except Exception as e:
        print(f"❌ RAG-Tool-Problem: {e}")
    
    # 5. Hyperparameter laden
    try:
        from src.scraper.hyperparameters import (
            VECTOR_EMBEDDING_MODEL,
            RAG_SEARCH_RESULTS,
            VECTOR_CHUNK_SIZE,
            VECTOR_CHUNK_OVERLAP
        )
        
        results['hyperparameters_loaded'] = True
        print(f"✅ Hyperparameter:")
        print(f"   - Embedding Model: {VECTOR_EMBEDDING_MODEL}")
        print(f"   - RAG Search Results: {RAG_SEARCH_RESULTS}")
        print(f"   - Chunk Size: {VECTOR_CHUNK_SIZE}")
        print(f"   - Chunk Overlap: {VECTOR_CHUNK_OVERLAP}")
        
    except Exception as e:
        print(f"❌ Hyperparameter-Problem: {e}")
    
    # Gesamtstatus
    passed_checks = sum(results.values())
    total_checks = len(results) - 1  # -1 für overall_status
    
    results['overall_status'] = passed_checks >= 4  # Mindestens 4 von 5 Tests
    
    print("\n" + "=" * 60)
    print(f"📊 Ergebnis: {passed_checks}/{total_checks} Tests bestanden")
    
    if results['overall_status']:
        print("✅ Tech-Stack ist kompatibel für RAG-Evaluation!")
    else:
        print("❌ Tech-Stack-Probleme erkannt. Bitte beheben Sie die Fehler.")
        
        # Spezifische Empfehlungen
        if not results['ollama_config']:
            print("💡 Ollama: Starten Sie 'ollama serve' und laden Sie das Modell")
        if not results['chromadb_access']:
            print("💡 ChromaDB: Führen Sie zuerst den Web-Scraper aus")
        if not results['embedding_consistency']:
            print("💡 Embeddings: Installieren Sie 'sentence-transformers'")
        if not results['rag_tool_available']:
            print("💡 RAG-Tool: Überprüfen Sie die Vector-DB-Pfade")
    
    print("=" * 60)
    return results


def check_dependencies():
    """Überprüft erforderliche Dependencies."""
    print("\n🔧 Dependency-Check:")
    print("-" * 30)
    
    dependencies = [
        ('ragas', 'RAGAS-Framework'),
        ('datasets', 'Hugging Face Datasets'),
        ('sentence_transformers', 'Sentence Transformers'),
        ('chromadb', 'ChromaDB'),
        ('langchain_ollama', 'LangChain Ollama'),
        ('langchain_community', 'LangChain Community')
    ]
    
    missing = []
    
    for package, description in dependencies:
        try:
            __import__(package)
            print(f"✅ {description}")
        except ImportError:
            print(f"❌ {description} - FEHLT")
            missing.append(package)
    
    if missing:
        print(f"\n💡 Installieren Sie fehlende Packages:")
        print(f"pip install {' '.join(missing)}")
    
    return len(missing) == 0


if __name__ == "__main__":
    print("🚀 Starte Tech-Stack Validierung...")
    
    deps_ok = check_dependencies()
    if deps_ok:
        results = validate_tech_stack()
        
        if results['overall_status']:
            print("\n🎯 System bereit für RAG-Evaluation!")
            print("Starten Sie mit: python src/evaluation/rag_evaluation.py")
        else:
            print("\n⚠️ Bitte beheben Sie die Probleme vor der Evaluation.")
    else:
        print("\n❌ Installieren Sie zuerst die fehlenden Dependencies.")