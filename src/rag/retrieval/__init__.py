"""
Retrieval-Phase Techniken für RAG
==================================

Modulare Retrieval-Techniken die aktiviert/deaktiviert werden können.
"""

from .multi_collection_search import MultiCollectionSearch
from .result_aggregation import ResultAggregation
from .distance_conversion import DistanceToRelevanceConverter
from .global_reranking import GlobalReranker

__all__ = [
    'MultiCollectionSearch',
    'ResultAggregation',
    'DistanceToRelevanceConverter',
    'GlobalReranker'
]
