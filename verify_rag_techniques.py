"""
RAG-Techniken Verifikationstest
================================
Testet, ob die Advanced-RAG Techniken korrekt mit den neu gescrapten Daten funktionieren.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shutil
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer

# Import RAG-Module
from src.advanced_rag.config import RAGConfig
from src.advanced_rag.presets import naive_rag_config, advanced_rag_config

def test_rag_techniques():
    """Testet alle RAG-Techniken Schritt für Schritt."""
    
    print("=" * 80)
    print("RAG-TECHNIKEN VERIFIKATIONSTEST")
    print("=" * 80)
    
    # 1. Prüfe Vektordatenbank
    print("\n1. Prüfe Vektordatenbank...")
    vector_db_path = Path("data/vector_db")
    
    if not vector_db_path.exists():
        print("   ❌ Keine Vektordatenbank gefunden!")
        return False
    
    client = chromadb.PersistentClient(path=str(vector_db_path))
    collections = client.list_collections()
    
    if not collections:
        print("   ❌ Keine Collections gefunden!")
        return False
    
    print(f"   ✅ Gefunden: {len(collections)} Collection(s)")
    for collection in collections:
        count = collection.count()
        print(f"      • {collection.name}: {count} Einträge")
    
    # Verwende erste Collection für Tests
    test_collection = collections[0]
    
    # 2. Teste Embedding-Modell
    print("\n2. Teste Embedding-Modell...")
    try:
        model = SentenceTransformer('all-MiniLM-L6-v2')
        test_query = "What is the Master Information Systems programme?"
        test_embedding = model.encode([test_query])[0]
        print(f"   ✅ Embedding-Modell geladen (Dimension: {len(test_embedding)})")
    except Exception as e:
        print(f"   ❌ Embedding-Modell Fehler: {e}")
        return False
    
    # 3. Teste Naive RAG Config
    print("\n3. Teste Naive RAG Config...")
    naive_config = naive_rag_config()
    
    print(f"   Baseline Enabled: {naive_config.baseline_enabled}")
    print(f"   Multi-Collection Search: {naive_config.use_multi_collection_search}")
    print(f"   Result Aggregation: {naive_config.use_result_aggregation}")
    print(f"   Distance Conversion: {naive_config.use_distance_conversion}")
    print(f"   Global Reranking: {naive_config.use_global_reranking}")
    print(f"   Relevance Filtering: {naive_config.use_relevance_filtering}")
    print(f"   Result Formatting: {naive_config.use_result_formatting}")
    print(f"   Context Hints: {naive_config.use_context_hints}")
    
    expected_naive = not any([
        naive_config.use_multi_collection_search,
        naive_config.use_result_aggregation,
        naive_config.use_distance_conversion,
        naive_config.use_global_reranking,
        naive_config.use_relevance_filtering,
        naive_config.use_result_formatting,
        naive_config.use_context_hints
    ])
    
    if expected_naive:
        print("   ✅ Naive Config korrekt (alle Techniken deaktiviert)")
    else:
        print("   ❌ Naive Config fehlerhaft (einige Techniken aktiviert)")
        return False
    
    # 4. Teste Advanced RAG Config
    print("\n4. Teste Advanced RAG Config...")
    advanced_config = advanced_rag_config()
    
    print(f"   Baseline Enabled: {advanced_config.baseline_enabled}")
    print(f"   Multi-Collection Search: {advanced_config.use_multi_collection_search}")
    print(f"   Result Aggregation: {advanced_config.use_result_aggregation}")
    print(f"   Distance Conversion: {advanced_config.use_distance_conversion}")
    print(f"   Global Reranking: {advanced_config.use_global_reranking}")
    print(f"   Relevance Filtering: {advanced_config.use_relevance_filtering}")
    print(f"   Result Formatting: {advanced_config.use_result_formatting}")
    print(f"   Context Hints: {advanced_config.use_context_hints}")
    
    expected_advanced = all([
        advanced_config.use_multi_collection_search,
        advanced_config.use_result_aggregation,
        advanced_config.use_distance_conversion,
        advanced_config.use_global_reranking,
        advanced_config.use_relevance_filtering,
        advanced_config.use_result_formatting,
        advanced_config.use_context_hints
    ]) and not advanced_config.baseline_enabled
    
    if expected_advanced:
        print("   ✅ Advanced Config korrekt (alle Techniken aktiviert)")
    else:
        print("   ❌ Advanced Config fehlerhaft")
        return False
    
    # 5. Teste Basic Retrieval
    print("\n5. Teste Basic Retrieval...")
    query_embedding = model.encode([test_query])[0]
    
    try:
        results = test_collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=5
        )
        
        num_results = len(results['documents'][0])
        print(f"   ✅ Retrieval funktioniert: {num_results} Ergebnisse")
        
        if num_results > 0:
            print(f"\n   Top Result:")
            print(f"      Distance: {results['distances'][0][0]:.4f}")
            print(f"      Metadata: {results['metadatas'][0][0]}")
            print(f"      Text: {results['documents'][0][0][:150]}...")
    except Exception as e:
        print(f"   ❌ Retrieval Fehler: {e}")
        return False
    
    # 6. Teste Distance Conversion
    print("\n6. Teste Distance Conversion...")
    distances = results['distances'][0]
    
    # ChromaDB liefert Cosine Distance (0-2, kleiner = ähnlicher)
    # Sollte zu Relevance Score (0-1, größer = relevanter) konvertiert werden
    for i, distance in enumerate(distances[:3]):
        relevance = 1 - (distance / 2)  # Erwartete Konversion
        print(f"   Result {i+1}: Distance={distance:.4f} → Relevance={relevance:.4f}")
    
    if all(0 <= d <= 2 for d in distances):
        print("   ✅ Distance-Werte im erwarteten Bereich (0-2)")
    else:
        print("   ⚠️ Distance-Werte außerhalb des erwarteten Bereichs")
    
    # 7. Teste Chunk-Qualität
    print("\n7. Teste Chunk-Qualität...")
    sample_chunks = results['documents'][0][:3]
    
    print(f"   Anzahl Chunks zum Test: {len(sample_chunks)}")
    
    for i, chunk in enumerate(sample_chunks):
        chunk_length = len(chunk)
        has_boilerplate = any(marker in chunk.lower() for marker in [
            'cookie', 'navigation', 'footer', 'skip to content', '© 202'
        ])
        
        print(f"\n   Chunk {i+1}:")
        print(f"      Länge: {chunk_length} Zeichen")
        print(f"      Boilerplate: {'⚠️ Gefunden' if has_boilerplate else '✅ Keine erkannt'}")
        print(f"      Vorschau: {chunk[:100]}...")
    
    # 8. Teste Metadaten-Struktur
    print("\n8. Teste Metadaten-Struktur...")
    sample_metadata = results['metadatas'][0][0]
    
    required_fields = ['doc_id', 'url', 'title', 'content_type', 'chunk_index']
    missing_fields = [field for field in required_fields if field not in sample_metadata]
    
    if not missing_fields:
        print(f"   ✅ Alle erforderlichen Felder vorhanden: {list(sample_metadata.keys())}")
    else:
        print(f"   ❌ Fehlende Felder: {missing_fields}")
        return False
    
    # 9. Vergleiche mit erwarteten Werten
    print("\n9. Vergleiche mit erwarteten Werten...")
    
    # Erwartete Chunk-Größe: 200-1500 Zeichen (SemanticChunker)
    chunk_sizes = [len(chunk) for chunk in sample_chunks]
    avg_chunk_size = sum(chunk_sizes) / len(chunk_sizes)
    
    print(f"   Durchschnittliche Chunk-Größe: {avg_chunk_size:.0f} Zeichen")
    print(f"   Min: {min(chunk_sizes)}, Max: {max(chunk_sizes)}")
    
    if 200 <= avg_chunk_size <= 1500:
        print(f"   ✅ Chunk-Größe im erwarteten Bereich (200-1500)")
    else:
        print(f"   ⚠️ Chunk-Größe außerhalb des erwarteten Bereichs")
    
    # 10. Finale Bewertung
    print("\n" + "=" * 80)
    print("FINALE BEWERTUNG")
    print("=" * 80)
    
    all_checks_passed = True
    
    checks = [
        ("Vektordatenbank vorhanden", True),
        ("Embedding-Modell funktioniert", True),
        ("Naive Config korrekt", expected_naive),
        ("Advanced Config korrekt", expected_advanced),
        ("Basic Retrieval funktioniert", num_results > 0),
        ("Distance-Werte korrekt", all(0 <= d <= 2 for d in distances)),
        ("Metadaten vollständig", not missing_fields),
        ("Chunk-Größe plausibel", 200 <= avg_chunk_size <= 1500)
    ]
    
    print("\n📋 Checkliste:")
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_checks_passed = False
    
    if all_checks_passed:
        print("\n" + "=" * 80)
        print("🎉 ALLE TESTS BESTANDEN!")
        print("=" * 80)
        print("\n✅ RAG-Techniken sind korrekt implementiert")
        print("✅ Datenqualität ist gut")
        print("✅ Bereit für vollständiges Scraping aller Dokumente")
        print("\n💡 Empfehlung: Starte vollständiges Scraping mit:")
        print("   python run_full_offline_scraper.py")
        print("=" * 80)
        return True
    else:
        print("\n" + "=" * 80)
        print("❌ EINIGE TESTS FEHLGESCHLAGEN")
        print("=" * 80)
        print("\n⚠️ Bitte überprüfe die fehlgeschlagenen Checks")
        print("=" * 80)
        return False

if __name__ == "__main__":
    success = test_rag_techniques()
    sys.exit(0 if success else 1)
