"""
Advanced Pre-Retrieval Techniques for RAG
==========================================

Module contains pre-retrieval/indexing techniques that enhance
document processing before storage in the vector database.

Available Techniques:
- Chunking: Semantic text chunking strategies
- Deduplication: Near-duplicate detection (datasketch MinHash+LSH)
"""

from .chunking import SemanticChunker

# MinHash + LSH Near-Deduplication (datasketch Framework)
from .deduplication_MinHash_LSH_Framework import (
    DatasketchConfig,
    deduplicate_documents_datasketch,
)

__all__ = [
    'SemanticChunker',
    # MinHash + LSH (datasketch Framework)
    'DatasketchConfig',
    'deduplicate_documents_datasketch',
]
