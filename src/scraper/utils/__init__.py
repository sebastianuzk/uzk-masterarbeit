"""
Scraper Utilities
=================

This package contains utility functions and helpers:
- content_cleaner.py: Content cleaning and normalization
- content_deduplicator.py: Duplicate content detection
- pdf_extractor.py: PDF document extraction
- semantic_chunker.py: Semantic text chunking
- url_cache.py: Intelligent URL caching system
"""

from .url_cache import URLCache, CachedURL

__all__ = [
    'URLCache',
    'CachedURL',
]
