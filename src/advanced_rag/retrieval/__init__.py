"""Advanced Retrieval Techniques for RAG.

Module contains advanced retrieval techniques that can be used
to enhance the naive RAG baseline.
"""

from .multi_collection_search import MultiCollectionSearcher
from .result_aggregation import ResultAggregator
from .distance_conversion import DistanceConverter
from .global_reranking import GlobalReranker
from .hybrid_retrieval_rrf import BM25SparseIndex, build_sparse_index_from_chunks

__all__ = [
    'MultiCollectionSearcher',
    'ResultAggregator',
    'DistanceConverter',
    'GlobalReranker',
    'BM25SparseIndex',
    'build_sparse_index_from_chunks'
]