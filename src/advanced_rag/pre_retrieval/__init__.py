"""
Advanced Pre-Retrieval Techniques for RAG
==========================================

Module contains pre-retrieval/indexing techniques that enhance
document processing before storage in the vector database.

Available Techniques:
- Chunking: Semantic text chunking strategies
- Cleaning: Content cleaning and boilerplate removal
- Deduplication: Near-duplicate detection
"""

from .chunking import SemanticChunker
from .cleaning import ContentCleaner
from .deduplication import ContentDeduplicator

__all__ = [
    'SemanticChunker',
    'ContentCleaner',
    'ContentDeduplicator',
]
