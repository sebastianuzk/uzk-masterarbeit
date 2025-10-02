"""
Zentrale Hyperparameter-Konfiguration für das Web Scraper RAG System
===================================================================

Einfache zentrale Verwaltung aller Hyperparameter.
Ändern Sie hier die Werte um das Verhalten des Systems anzupassen.
"""

# ==============================================================================
# BATCH SCRAPER PARAMETER
# ==============================================================================

# Performance & Rate Limiting
SCRAPER_MAX_CONCURRENT_REQUESTS = 10  # Genutzt in: batch_scraper.py
SCRAPER_REQUEST_DELAY = 1.0           # Genutzt in: batch_scraper.py
SCRAPER_TIMEOUT = 30                  # Genutzt in: batch_scraper.py

# Error Handling  
SCRAPER_RETRY_ATTEMPTS = 3            # Genutzt in: batch_scraper.py
SCRAPER_RETRY_DELAY = 2.0            # Genutzt in: batch_scraper.py

# Content Extraction
SCRAPER_CONTENT_SELECTORS = {         # Genutzt in: batch_scraper.py
    "title": "title, h1, .title, .headline",
    "content": "article, main, .content, .article-body, p"
}

SCRAPER_EXCLUDE_SELECTORS = [         # Genutzt in: batch_scraper.py
    "script", "style", "nav", "footer", 
    ".advertisement", ".ads", ".sidebar"
]

# ==============================================================================
# VECTOR STORE PARAMETER  
# ==============================================================================

# Database
VECTOR_BACKEND = "chromadb"                    # Genutzt in: vector_store.py
VECTOR_PERSIST_DIRECTORY = "src/scraper/vector_db"  # Genutzt in: vector_store.py

# Text Processing
VECTOR_CHUNK_SIZE = 1500              # Genutzt in: vector_store.py
VECTOR_CHUNK_OVERLAP = 300            # Genutzt in: vector_store.py

# Embeddings
VECTOR_EMBEDDING_MODEL = "all-MiniLM-L6-v2"        # Genutzt in: vector_store.py
VECTOR_EMBEDDING_PROVIDER = "sentence_transformers" # Genutzt in: vector_store.py

# Search
VECTOR_SIMILARITY_THRESHOLD = 0.1     # Genutzt in: vector_store.py
VECTOR_MAX_RESULTS = 10               # Genutzt in: vector_store.py

# ==============================================================================
# RAG TOOL PARAMETER
# ==============================================================================

RAG_SEARCH_RESULTS = 5               # Genutzt in: rag_tool.py

# ==============================================================================
# PARAMETER ERLÄUTERUNGEN
# ==============================================================================

"""
SCRAPER_MAX_CONCURRENT_REQUESTS (1-50):
  Anzahl gleichzeitiger HTTP-Requests. Höher = schneller, aber mehr Server-Last.
  
SCRAPER_REQUEST_DELAY (0.1-10.0):
  Pause zwischen Requests in Sekunden. Höher = respektvoller, aber langsamer.
  
SCRAPER_TIMEOUT (5-120):
  Request-Timeout in Sekunden. Höher = weniger Timeouts, aber längere Wartezeit.
  
VECTOR_CHUNK_SIZE (200-5000):
  Text-Chunk Größe in Zeichen. Größer = mehr Kontext, weniger präzise Suche.
  
VECTOR_CHUNK_OVERLAP (0-1000):
  Überlappung zwischen Chunks. Höher = besserer Kontext, mehr Speicher.
  
VECTOR_SIMILARITY_THRESHOLD (0.0-1.0):
  Mindest-Ähnlichkeit für Suchergebnisse. Niedriger = mehr Ergebnisse.
  
VECTOR_EMBEDDING_MODEL:
  - "all-MiniLM-L6-v2": Schnell, kompakt
  - "all-mpnet-base-v2": Beste Qualität, langsamer  
  - "paraphrase-multilingual-MiniLM-L12-v2": Für deutsche Texte
"""