"""
Core Scraper Components
=======================

This package contains the core scraping functionality:
- wiso_crawler.py: WiSo faculty website crawler
"""

from .wiso_crawler import WisoCrawler, CrawlerConfig

__all__ = [
    'WisoCrawler',
    'CrawlerConfig',
]
