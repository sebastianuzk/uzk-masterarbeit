"""Advanced Retrieval Techniques for RAG.

Module contains advanced retrieval techniques that can be used
to enhance the naive RAG baseline.
"""

from .hybrid_retrieval_rrf import BM25SparseIndex, build_sparse_index_from_chunks

__all__ = [
    'BM25SparseIndex',
    'build_sparse_index_from_chunks',
]
