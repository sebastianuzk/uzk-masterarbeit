"""
RAG (Retrieval-Augmented Generation) Module

Modulares RAG-System mit konfigurierbaren Techniken für:
- Pre-Retrieval: Document processing and indexing
- Retrieval: Dokumenten-Suche
- Post-Retrieval: Ergebnis-Verarbeitung

Verwendung:
    # Standard (Advanced RAG aus Umgebungsvariablen)
    from src.advanced_rag.rag_config import RAGConfig
    config = RAGConfig.load_from_env()
    
    # Pre-Retrieval Techniken
    from src.advanced_rag.pre_retrieval import (
        SemanticChunker,
    )
"""

from src.advanced_rag.rag_config import RAGConfig

# Pre-retrieval techniques
from src.advanced_rag.pre_retrieval import (
    SemanticChunker,
)

__all__ = [
    # Configuration
    'RAGConfig',
    
    # Pre-retrieval techniques
    'SemanticChunker',
]
