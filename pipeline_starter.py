#!/usr/bin/env python3
"""
Pipeline Starter mit korrektem sys.path
"""

import sys
import os

# Füge das Root-Verzeichnis zum Python-Path hinzu
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

# Importiere und starte die Pipeline
from src.scraper.pipelines.crawler_scraper_pipeline import main
import asyncio

if __name__ == "__main__":
    # Setze Command-Line-Argumente
    sys.argv = [
        "pipeline_starter.py",
        "--max-pages", "10000",
        "--crawl-delay", "5.0", 
        "--scrape-delay", "3000.0",
        "--concurrent-requests", "1"
    ]
    
    asyncio.run(main())