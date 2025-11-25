"""
RAG (Retrieval-Augmented Generation) Module

Modulares RAG-System mit konfigurierbaren Techniken für:
- Pre-Retrieval: Query-Optimierung
- Retrieval: Dokumenten-Suche
- Post-Retrieval: Ergebnis-Verarbeitung

Verwendung:
    # Standard (Advanced RAG aus Umgebungsvariablen)
    from src.rag.config import RAGConfig
    config = RAGConfig.from_env()
    
    # Naive Baseline
    from src.rag.presets import naive_rag_config
    config = naive_rag_config()
    
    # Advanced RAG
    from src.rag.presets import advanced_rag_config
    config = advanced_rag_config()
    
    # Custom
    from src.rag.presets import custom_rag_config
    config = custom_rag_config(multi_collection=True, result_formatting=False)
"""

from src.rag.config import RAGConfig
from src.rag.presets import (
    naive_rag_config,
    advanced_rag_config,
    custom_rag_config,
    get_naive_config,
    get_advanced_config,
    get_custom_config
)

# Retrieval techniques
from src.rag.retrieval import (
    MultiCollectionSearch,
    ResultAggregation,
    DistanceToRelevanceConverter,
    GlobalReranker
)

# Post-retrieval techniques
from src.rag.post_retrieval import (
    RelevanceFilter,
    ResultFormatter,
    ContextHintGenerator,
    EmptyResultHandler
)

__all__ = [
    # Configuration
    'RAGConfig',
    'naive_rag_config',
    'advanced_rag_config',
    'custom_rag_config',
    'get_naive_config',
    'get_advanced_config',
    'get_custom_config',
    
    # Retrieval techniques
    'MultiCollectionSearch',
    'ResultAggregation',
    'DistanceToRelevanceConverter',
    'GlobalReranker',
    
    # Post-retrieval techniques
    'RelevanceFilter',
    'ResultFormatter',
    'ContextHintGenerator',
    'EmptyResultHandler',
]
