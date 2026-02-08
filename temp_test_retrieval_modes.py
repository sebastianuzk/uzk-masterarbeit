"""
Test aller Retrieval-Modi mit dem echten ReAct-Agent Chatbot
=============================================================
Testet: 1) Hybrid, 2) Sparse-Only, 3) Dense-Only (Naive)
"""

import os
import sys

# Test-Query für den Chatbot
TEST_QUERY = "Welche Fristen gelten für die Masterbewerbung?"


def test_mode(mode_name: str, hybrid: bool, sparse: bool):
    """Testet einen spezifischen Retrieval-Modus mit dem echten ReAct-Agent."""
    print("\n" + "=" * 100)
    print(f"🧪 TEST: {mode_name}")
    print(f"   ENABLE_HYBRID_RETRIEVAL = {hybrid}")
    print(f"   ENABLE_SPARSE_RETRIEVAL = {sparse}")
    print("=" * 100)
    
    # Setze Environment-Variablen VOR dem Import
    os.environ['ENABLE_HYBRID_RETRIEVAL'] = str(hybrid).lower()
    os.environ['ENABLE_SPARSE_RETRIEVAL'] = str(sparse).lower()
    os.environ['RAG_NAIVE_SETUP'] = 'false'
    
    # Lösche gecachte Module für frischen Import
    modules_to_reload = [
        'src.advanced_rag.rag_config',
        'src.tools.rag_tool',
        'src.agent.react_agent',
    ]
    for mod in list(sys.modules.keys()):
        if any(mod.startswith(m) or mod == m for m in modules_to_reload):
            del sys.modules[mod]
    
    # Importiere ReAct-Agent frisch
    from src.agent.react_agent import create_react_agent
    from src.advanced_rag.rag_config import RAGConfig
    from src.tools.rag_tool import UniversityRAGTool
    
    # Zeige Config
    config = RAGConfig.load_from_env()
    print(f"\n📋 Config geladen:")
    print(f"   config.enable_hybrid_retrieval = {config.enable_hybrid_retrieval}")
    print(f"   config.enable_sparse_retrieval = {config.enable_sparse_retrieval}")
    print(f"   config.use_hybrid_retrieval = {config.use_hybrid_retrieval}")
    print(f"   config.use_sparse_retrieval = {config.use_sparse_retrieval}")
    
    # Teste zuerst RAG-Tool direkt
    print(f"\n🔧 Teste RAG-Tool direkt...")
    rag_tool = UniversityRAGTool(config=config)
    print(f"   _use_hybrid = {rag_tool._use_hybrid}")
    print(f"   _use_sparse = {rag_tool._use_sparse}")
    print(f"   _use_advanced = {rag_tool._use_advanced}")
    
    # Direkter RAG-Tool Test
    direct_result = rag_tool._run(TEST_QUERY)
    print(f"\n📄 Direktes RAG-Tool Ergebnis ({len(direct_result)} Zeichen):")
    print(direct_result[:800] + "..." if len(direct_result) > 800 else direct_result)
    
    # Erstelle ReAct-Agent (Chatbot)
    print(f"\n⏳ Initialisiere ReAct-Agent...")
    agent = create_react_agent()
    print(f"   Tools: {agent.get_available_tools()}")
    
    # Führe Chat aus
    print(f"\n📝 User Query: \"{TEST_QUERY}\"")
    print("-" * 80)
    
    try:
        response = agent.chat(TEST_QUERY)
        print(f"\n🤖 Agent Response:")
        print(response[:2000] + "..." if len(response) > 2000 else response)
    except Exception as e:
        print(f"\n❌ Fehler: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Teste alle drei Modi mit dem Chatbot."""
    print("\n" + "#" * 100)
    print("# RETRIEVAL-MODI TEST MIT REACT-AGENT (CHATBOT)")
    print("# Testet: 1) Hybrid, 2) Sparse-Only, 3) Dense-Only (Naive)")
    print("#" * 100)
    
    # Test 1: Hybrid Retrieval (Dense + Sparse + RRF)
    test_mode(
        mode_name="HYBRID RETRIEVAL (Dense + Sparse + RRF)",
        hybrid=True,
        sparse=False
    )
    
    # Test 2: Sparse-Only Retrieval (nur BM25)
    test_mode(
        mode_name="SPARSE RETRIEVAL (nur BM25)",
        hybrid=False,
        sparse=True
    )
    
    # Test 3: Dense-Only Retrieval (Naive/ChromaDB)
    test_mode(
        mode_name="DENSE RETRIEVAL (Naive/ChromaDB)",
        hybrid=False,
        sparse=False
    )
    
    print("\n" + "#" * 100)
    print("# ✅ ALLE TESTS MIT REACT-AGENT ABGESCHLOSSEN")
    print("#" * 100)


if __name__ == "__main__":
    main()
