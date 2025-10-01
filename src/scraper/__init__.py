"""
Web Scraper Module for RAG Data Preparation
==========================================

This module provides batch web scraping capabilities for feeding data into
a RAG (Retrieval-Augmented Generation) system with vector database storage.

Main Components:
- BatchScraper: Core scraping functionality
- VectorStore: Vector database integration
- DataStructureAnalyzer: Dynamic data structure documentation
"""

from .batch_scraper import BatchScraper
from .vector_store import VectorStore
from .data_structure_analyzer import DataStructureAnalyzer

__all__ = ['BatchScraper', 'VectorStore', 'DataStructureAnalyzer']