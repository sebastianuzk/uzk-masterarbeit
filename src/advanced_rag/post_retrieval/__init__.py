"""Advanced Post-Retrieval Techniques for RAG.

Module contains advanced post-retrieval techniques that can be used
to enhance the naive RAG baseline.
"""

from .reranking import VoyageReranker
from .maximum_marginal_relevance import create_mmr

__all__ = [
    'VoyageReranker',
    'create_mmr',
]
