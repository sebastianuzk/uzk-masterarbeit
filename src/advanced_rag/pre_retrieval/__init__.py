"""
Advanced Pre-Retrieval Techniques for RAG
==========================================

Module contains pre-retrieval/indexing techniques that enhance
document processing before storage in the vector database.

Available Techniques:
- Chunking: Semantic text chunking strategies
- Cleaning: Content cleaning and boilerplate removal
- Deduplication: Near-duplicate detection
- Collection Categorization: Thematic document categorization
"""

from .chunking import SemanticChunker
from .cleaning import ContentCleaner
from .deduplication import ContentDeduplicator, normalize_text, compute_normalized_hash
from .collection_categorizer import CollectionCategorizer

__all__ = [
    'SemanticChunker',
    'ContentCleaner',
    'CollectionCategorizer',
    'ContentDeduplicator',
    'normalize_text',
    'compute_normalized_hash',
]
