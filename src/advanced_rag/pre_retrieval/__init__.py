"""
Advanced Pre-Retrieval Techniques for RAG
==========================================

Module contains pre-retrieval/indexing techniques that enhance
document processing before storage in the vector database.

Available Techniques:
- Chunking: Semantic text chunking strategies
- Cleaning: Content cleaning and boilerplate removal
- Deduplication: Near-duplicate detection (Naive Jaccard, datasketch MinHash+LSH)
- Collection Categorization: Thematic document categorization
"""

from .chunking import SemanticChunker
from .cleaning import ContentCleaner
from .deduplication import ContentDeduplicator, normalize_text, compute_normalized_hash
from .collection_categorizer import CollectionCategorizer

# MinHash + LSH Near-Deduplication (datasketch Framework)
from .deduplication_MinHash_LSH_Framework import (
    DatasketchConfig,
    deduplicate_documents_datasketch,
)

__all__ = [
    'SemanticChunker',
    'ContentCleaner',
    'CollectionCategorizer',
    'ContentDeduplicator',
    'normalize_text',
    'compute_normalized_hash',
    # MinHash + LSH (datasketch Framework)
    'DatasketchConfig',
    'deduplicate_documents_datasketch',
]
