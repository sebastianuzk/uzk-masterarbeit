"""
RAG Configuration Presets

Vordefinierte Konfigurationen für verschiedene RAG-Szenarien:
- Naive Baseline: Alle Advanced-RAG Techniken deaktiviert
- Advanced: Alle implementierten Techniken aktiviert
- Custom: Benutzerdefinierte Konfigurationen
"""

from src.advanced_rag.config import RAGConfig


def naive_rag_config() -> RAGConfig:
    """
    Naive RAG Baseline Konfiguration.
    
    Alle Advanced-RAG Techniken sind deaktiviert.
    Nutzt nur einfache Vektorsuche ohne zusätzliche Optimierungen.
    
    Verwendungszweck:
    - Baseline für Evaluierungen
    - Vergleich mit Advanced-RAG
    - Debugging
    
    Returns:
        RAGConfig: Naive Baseline Konfiguration
    """
    return RAGConfig(
        # Baseline aktiviert
        baseline_enabled=True,
        
        # Retrieval (implementiert) - alle deaktiviert
        use_multi_collection_search=False,
        use_result_aggregation=False,
        use_distance_conversion=False,
        use_global_reranking=False,
        
        # Post-Retrieval (implementiert) - alle deaktiviert
        use_relevance_filtering=False,
        relevance_threshold=0.0,  # Kein Threshold
        use_result_formatting=False,
        use_context_hints=False,
        use_empty_result_handling=False,
        
        # Pre-Retrieval (future) - alle deaktiviert
        query_expansion_enabled=False,
        query_rewriting_enabled=False,
        hyde_enabled=False,
        multi_query_enabled=False,
        
        # Retrieval (future) - alle deaktiviert
        hybrid_retrieval_enabled=False,
        reranking_enabled=False,
        parent_doc_retrieval_enabled=False,
        
        # Post-Retrieval (future) - alle deaktiviert
        context_compression_enabled=False,
        context_reordering_enabled=False,
        answer_fusion_enabled=False,
        
        # Allgemein - Standard-Werte
        k_per_collection=3,
        top_k=5,
        debug_mode=False
    )


def advanced_rag_config() -> RAGConfig:
    """
    Advanced RAG Konfiguration.
    
    Alle implementierten Advanced-RAG Techniken sind aktiviert.
    Nutzt alle verfügbaren Optimierungen für beste Ergebnisse.
    
    Verwendungszweck:
    - Produktiv-Einsatz
    - Beste Performance
    - Vergleich mit Naive Baseline
    
    Returns:
        RAGConfig: Advanced RAG Konfiguration
    """
    return RAGConfig(
        # Baseline deaktiviert (nutze Advanced)
        baseline_enabled=False,
        
        # Retrieval (implementiert) - alle aktiviert
        use_multi_collection_search=True,
        use_result_aggregation=True,
        use_distance_conversion=True,
        use_global_reranking=True,
        
        # Post-Retrieval (implementiert) - alle aktiviert
        use_relevance_filtering=True,
        relevance_threshold=0.1,  # Standard Threshold
        use_result_formatting=True,
        use_context_hints=True,
        use_empty_result_handling=True,
        
        # Pre-Retrieval (future) - deaktiviert (noch nicht implementiert)
        query_expansion_enabled=False,
        query_rewriting_enabled=False,
        hyde_enabled=False,
        multi_query_enabled=False,
        
        # Retrieval (future) - deaktiviert (noch nicht implementiert)
        hybrid_retrieval_enabled=False,
        reranking_enabled=False,
        parent_doc_retrieval_enabled=False,
        
        # Post-Retrieval (future) - deaktiviert (noch nicht implementiert)
        context_compression_enabled=False,
        context_reordering_enabled=False,
        answer_fusion_enabled=False,
        
        # Allgemein - Optimierte Werte
        k_per_collection=3,
        top_k=5,
        debug_mode=False
    )


def custom_rag_config(
    multi_collection: bool = True,
    result_aggregation: bool = True,
    distance_conversion: bool = True,
    global_reranking: bool = True,
    relevance_filtering: bool = True,
    result_formatting: bool = True,
    context_hints: bool = True,
    empty_handling: bool = True,
    relevance_threshold: float = 0.1,
    k_per_collection: int = 3,
    top_k: int = 5,
    debug: bool = False
) -> RAGConfig:
    """
    Custom RAG Konfiguration.
    
    Ermöglicht individuelle Aktivierung/Deaktivierung von Techniken.
    Ideal für experimentelle Evaluierungen und A/B-Tests.
    
    Args:
        multi_collection: Multi-Collection Search aktivieren
        result_aggregation: Result Aggregation aktivieren
        distance_conversion: Distance-to-Relevance Conversion aktivieren
        global_reranking: Global Re-ranking aktivieren
        relevance_filtering: Relevance Filtering aktivieren
        result_formatting: Result Formatting aktivieren
        context_hints: Context Hints aktivieren
        empty_handling: Empty Result Handling aktivieren
        relevance_threshold: Schwellenwert für Relevanz (0.0-1.0)
        k_per_collection: Anzahl Ergebnisse pro Collection
        top_k: Anzahl finale Top-Ergebnisse
        debug: Debug-Modus aktivieren
        
    Returns:
        RAGConfig: Custom RAG Konfiguration
        
    Beispiele:
        # Nur Retrieval-Techniken
        config = custom_rag_config(
            result_formatting=False,
            context_hints=False,
            empty_handling=False
        )
        
        # Nur Post-Retrieval-Techniken
        config = custom_rag_config(
            multi_collection=False,
            result_aggregation=False,
            distance_conversion=False,
            global_reranking=False
        )
        
        # Einzelne Technik isoliert testen
        config = custom_rag_config(
            multi_collection=False,
            result_aggregation=False,
            distance_conversion=True,  # NUR diese Technik
            global_reranking=False,
            result_formatting=False,
            context_hints=False
        )
    """
    return RAGConfig(
        # Baseline je nach Konfiguration
        baseline_enabled=not any([
            multi_collection, result_aggregation, distance_conversion,
            global_reranking, relevance_filtering, result_formatting,
            context_hints, empty_handling
        ]),
        
        # Retrieval (implementiert)
        use_multi_collection_search=multi_collection,
        use_result_aggregation=result_aggregation,
        use_distance_conversion=distance_conversion,
        use_global_reranking=global_reranking,
        
        # Post-Retrieval (implementiert)
        use_relevance_filtering=relevance_filtering,
        relevance_threshold=relevance_threshold,
        use_result_formatting=result_formatting,
        use_context_hints=context_hints,
        use_empty_result_handling=empty_handling,
        
        # Pre-Retrieval (future) - alle deaktiviert
        query_expansion_enabled=False,
        query_rewriting_enabled=False,
        hyde_enabled=False,
        multi_query_enabled=False,
        
        # Retrieval (future) - alle deaktiviert
        hybrid_retrieval_enabled=False,
        reranking_enabled=False,
        parent_doc_retrieval_enabled=False,
        
        # Post-Retrieval (future) - alle deaktiviert
        context_compression_enabled=False,
        context_reordering_enabled=False,
        answer_fusion_enabled=False,
        
        # Allgemein
        k_per_collection=k_per_collection,
        top_k=top_k,
        debug_mode=debug
    )


# Convenience functions für einfachen Zugriff
def get_naive_config() -> RAGConfig:
    """Shortcut für naive_rag_config()."""
    return naive_rag_config()


def get_advanced_config() -> RAGConfig:
    """Shortcut für advanced_rag_config()."""
    return advanced_rag_config()


def get_custom_config(**kwargs) -> RAGConfig:
    """Shortcut für custom_rag_config()."""
    return custom_rag_config(**kwargs)


# Test-Funktion
if __name__ == "__main__":
    print("🧪 RAG Configuration Presets Test")
    print("=" * 60)
    
    print("\n📊 Naive RAG Config:")
    naive = naive_rag_config()
    print(f"  - Multi-Collection Search: {naive.use_multi_collection_search}")
    print(f"  - Result Formatting: {naive.use_result_formatting}")
    print(f"  - Relevance Threshold: {naive.relevance_threshold}")
    
    print("\n🚀 Advanced RAG Config:")
    advanced = advanced_rag_config()
    print(f"  - Multi-Collection Search: {advanced.use_multi_collection_search}")
    print(f"  - Result Formatting: {advanced.use_result_formatting}")
    print(f"  - Relevance Threshold: {advanced.relevance_threshold}")
    
    print("\n⚙️ Custom RAG Config (nur Distance Conversion):")
    custom = custom_rag_config(
        multi_collection=False,
        result_aggregation=False,
        distance_conversion=True,
        global_reranking=False,
        result_formatting=False,
        context_hints=False,
        empty_handling=False
    )
    print(f"  - Multi-Collection Search: {custom.use_multi_collection_search}")
    print(f"  - Distance Conversion: {custom.use_distance_conversion}")
    print(f"  - Result Formatting: {custom.use_result_formatting}")
    
    print("\n✅ Test abgeschlossen")
