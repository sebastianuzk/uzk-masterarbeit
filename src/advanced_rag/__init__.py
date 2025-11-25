"""
RAG (Retrieval-Augmented Generation) Module

Modulares RAG-System mit konfigurierbaren Techniken für:
- Pre-Retrieval: Document processing and indexing
- Retrieval: Dokumenten-Suche
- Post-Retrieval: Ergebnis-Verarbeitung

Verwendung:
    # Standard (Advanced RAG aus Umgebungsvariablen)
    from src.advanced_rag.config import RAGConfig
    config = RAGConfig.load_from_env()
    
    # Pre-Retrieval Techniken
    from src.advanced_rag.pre_retrieval import (
        SemanticChunker,
        ContentCleaner,
        ContentDeduplicator
    )
"""

from src.advanced_rag.config import RAGConfig

# Pre-retrieval techniques
from src.advanced_rag.pre_retrieval import (
    SemanticChunker,
    ContentCleaner,
    ContentDeduplicator,
)

__all__ = [
    # Configuration
    'RAGConfig',
    
    # Pre-retrieval techniques
    'SemanticChunker',
    'ContentCleaner',
    'ContentDeduplicator',
]
