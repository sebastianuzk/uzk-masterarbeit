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
# WICHTIG: Niedrige Werte verhindern, dass die Website Sie blockiert!
SCRAPER_MAX_CONCURRENT_REQUESTS = 5   # Genutzt in: batch_scraper.py (reduziert von 10 auf 5)
SCRAPER_REQUEST_DELAY = 2.0           # Genutzt in: batch_scraper.py (erhöht von 1.0 auf 2.0)
SCRAPER_TIMEOUT = 30                  # Genutzt in: batch_scraper.py

# Error Handling  
SCRAPER_RETRY_ATTEMPTS = 3            # Genutzt in: batch_scraper.py
SCRAPER_RETRY_DELAY = 2.0             # Genutzt in: batch_scraper.py

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
# PARAMETER ERLÄUTERUNGEN & OPTIMIERUNGSTIPPS
# ==============================================================================

"""
🔧 SCRAPER PARAMETER OPTIMIERUNG
================================

SCRAPER_MAX_CONCURRENT_REQUESTS (Bereich: 1-50, Empfehlung: 5-15):
  ✅ Anzahl gleichzeitiger HTTP-Requests
  🚀 Performance: Höher = schneller Scraping
  ⚠️  Rate Limiting: Niedriger = respektvoller gegenüber Servern
  💡 Optimierung:
     - Kleine Seiten: 15-25
     - Universitäts-Seiten: 5-10 (oft rate-limited)
     - Produktions-Server: 3-8
     - Lokale Tests: 20-50
  
SCRAPER_REQUEST_DELAY (Bereich: 0.1-10.0, Empfehlung: 0.5-2.0):
  ✅ Pause zwischen Requests in Sekunden
  🌐 Respekt: Höher = weniger Server-Last
  ⚡ Geschwindigkeit: Niedriger = schneller
  💡 Optimierung:
     - News-Seiten: 0.5-1.0
     - E-Commerce: 1.0-2.0
     - Universitäten: 1.5-3.0
     - APIs: 0.1-0.5
  
SCRAPER_TIMEOUT (Bereich: 5-120, Empfehlung: 20-45):
  ✅ Request-Timeout in Sekunden
  📶 Stabilität: Höher = weniger Timeouts
  ⏱️  Reaktionszeit: Niedriger = schnellere Fehlerbehandlung
  💡 Optimierung:
     - Schnelle Seiten: 15-25
     - Langsame Seiten: 30-60
     - Mobile/Edge: 45-90

🎯 VECTOR STORE PARAMETER OPTIMIERUNG
====================================

VECTOR_CHUNK_SIZE (Bereich: 200-5000, Empfehlung: 800-2000):
  ✅ Text-Chunk Größe in Zeichen
  🎯 Präzision: Kleiner = präzisere Suche
  🧠 Kontext: Größer = mehr Zusammenhang
  💡 Optimierung:
     - FAQ/Kurze Texte: 400-800
     - Artikel/Blogs: 1200-2000
     - Technische Docs: 800-1500
     - Wissenschaftliche Texte: 1500-3000
  
VECTOR_CHUNK_OVERLAP (Bereich: 0-1000, Empfehlung: 100-400):
  ✅ Überlappung zwischen Chunks in Zeichen
  🔗 Kontinuität: Höher = besserer Zusammenhang
  💾 Speicher: Niedriger = weniger Redundanz
  💡 Optimierung:
     - Chunk_size 800: Overlap 150-200
     - Chunk_size 1500: Overlap 250-350
     - Chunk_size 2500: Overlap 400-600
     - Formel: ~20-25% von chunk_size
  
VECTOR_SIMILARITY_THRESHOLD (Bereich: 0.0-1.0, Empfehlung: 0.1-0.4):
  ✅ Mindest-Ähnlichkeit für Suchergebnisse
  📊 Recall: Niedriger = mehr Ergebnisse
  🎯 Precision: Höher = relevantere Ergebnisse
  💡 Optimierung:
     - Deutsche Texte: 0.1-0.2 (niedriger wegen Sprachkomplexität)
     - Englische Texte: 0.2-0.3
     - Fachbegriffe: 0.15-0.25
     - Allgemeine Suche: 0.1-0.2

🤖 EMBEDDING MODEL OPTIMIERUNG
==============================

VECTOR_EMBEDDING_MODEL Optionen:
  📦 "all-MiniLM-L6-v2" (384 dim, ~23MB):
     ✅ Sehr schnell, geringer Speicher
     🎯 Gut für: Prototyping, große Datenmengen
     ⚡ Performance: Exzellent
     🌐 Sprachen: Englisch++, Deutsch+
     
  🏆 "all-mpnet-base-v2" (768 dim, ~438MB):
     ✅ Beste Qualität für englische Texte
     🎯 Gut für: Produktionsumgebung, hohe Präzision
     ⚡ Performance: Gut
     🌐 Sprachen: Englisch+++, Deutsch++
     
  🇩🇪 "paraphrase-multilingual-MiniLM-L12-v2" (384 dim, ~285MB):
     ✅ Optimiert für deutsche Texte
     🎯 Gut für: Deutsche Universitäts-Inhalte
     ⚡ Performance: Gut
     🌐 Sprachen: Deutsch+++, Multilingual+++
     
  🌍 "paraphrase-multilingual-mpnet-base-v2" (768 dim, ~1.1GB):
     ✅ Beste Qualität für deutsche/multilinguale Texte
     🎯 Gut für: Kritische Anwendungen, gemischte Sprachen
     ⚡ Performance: Langsamer
     🌐 Sprachen: Deutsch+++, Multilingual+++

💡 EMPFOHLENE KONFIGURATIONEN
============================

🚀 SCHNELL (Prototyping):
   MAX_CONCURRENT_REQUESTS = 20
   REQUEST_DELAY = 0.5
   CHUNK_SIZE = 800
   EMBEDDING_MODEL = "all-MiniLM-L6-v2"
   
⚖️ AUSGEWOGEN (Standard):
   MAX_CONCURRENT_REQUESTS = 10
   REQUEST_DELAY = 1.0
   CHUNK_SIZE = 1500
   EMBEDDING_MODEL = "all-mpnet-base-v2"
   
🎯 PRÄZISE (Deutsche Uni-Inhalte):
   MAX_CONCURRENT_REQUESTS = 5
   REQUEST_DELAY = 2.0
   CHUNK_SIZE = 1200
   EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"
   SIMILARITY_THRESHOLD = 0.15
   
🏆 PREMIUM (Beste Qualität):
   MAX_CONCURRENT_REQUESTS = 3
   REQUEST_DELAY = 2.5
   CHUNK_SIZE = 2000
   EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"
   SIMILARITY_THRESHOLD = 0.2

⚠️ TROUBLESHOOTING
==================

❌ Zu wenige Suchergebnisse:
   → SIMILARITY_THRESHOLD senken (0.05-0.1)
   → CHUNK_SIZE verkleinern (800-1200)
   → RAG_SEARCH_RESULTS erhöhen (8-15)
   
❌ Irrelevante Suchergebnisse:
   → SIMILARITY_THRESHOLD erhöhen (0.3-0.5)
   → Besseres EMBEDDING_MODEL verwenden
   → CHUNK_SIZE anpassen
   
❌ Langsames Scraping:
   → MAX_CONCURRENT_REQUESTS erhöhen
   → REQUEST_DELAY reduzieren
   → TIMEOUT reduzieren
   
❌ Rate Limiting/Blockiert:
   → MAX_CONCURRENT_REQUESTS reduzieren (1-3)
   → REQUEST_DELAY erhöhen (3-10)
   → User-Agent ändern
   
❌ Speicherprobleme:
   → CHUNK_SIZE reduzieren
   → Kleineres EMBEDDING_MODEL
   → Weniger MAX_CONCURRENT_REQUESTS
"""