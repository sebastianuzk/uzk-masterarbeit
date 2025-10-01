"""
Hyperparameter-Konfiguration für das Web Scraper RAG System
==========================================================

Diese Datei zeigt alle verfügbaren Hyperparameter und wo sie konfiguriert werden können.
"""

# ==============================================================================
# 1. SCRAPING HYPERPARAMETER (ScrapingConfig in batch_scraper.py)
# ==============================================================================

SCRAPING_HYPERPARAMETERS = {
    # Performance & Rate Limiting
    "max_concurrent_requests": {
        "default": 10,
        "description": "Maximale Anzahl gleichzeitiger HTTP-Requests",
        "location": "src/scraper/batch_scraper.py:45",
        "cli_arg": "--concurrent",
        "range": "1-50",
        "impact": "Höher = schneller, aber mehr Server-Load"
    },
    
    "request_delay": {
        "default": 1.0,
        "description": "Verzögerung zwischen Requests in Sekunden",
        "location": "src/scraper/batch_scraper.py:46", 
        "cli_arg": "--delay",
        "range": "0.1-10.0",
        "impact": "Höher = respektvoller zu Servern, aber langsamer"
    },
    
    "timeout": {
        "default": 30,
        "description": "HTTP-Request Timeout in Sekunden",
        "location": "src/scraper/batch_scraper.py:47",
        "cli_arg": "--timeout", 
        "range": "5-120",
        "impact": "Höher = weniger Timeouts, aber längere Wartezeiten"
    },
    
    # Error Handling
    "retry_attempts": {
        "default": 3,
        "description": "Anzahl Wiederholungsversuche bei Fehlern",
        "location": "src/scraper/batch_scraper.py:48",
        "cli_arg": "--retries",
        "range": "1-10", 
        "impact": "Höher = robuster, aber langsamer bei Fehlern"
    },
    
    "retry_delay": {
        "default": 2.0,
        "description": "Verzögerung zwischen Retry-Versuchen",
        "location": "src/scraper/batch_scraper.py:49",
        "cli_arg": "Nur programmatisch",
        "range": "0.5-10.0",
        "impact": "Höher = weniger Server-Stress bei Fehlern"
    },
    
    # Content Extraction
    "content_selectors": {
        "default": {"title": "title, h1", "content": "article, main, .content, p"},
        "description": "CSS-Selektoren für Content-Extraktion", 
        "location": "src/scraper/batch_scraper.py:54-57",
        "cli_arg": "Nur programmatisch",
        "impact": "Bestimmt welcher Content extrahiert wird"
    },
    
    "exclude_selectors": {
        "default": ["script", "style", "nav", "footer"],
        "description": "CSS-Selektoren für auszuschließende Elemente",
        "location": "src/scraper/batch_scraper.py:58-61", 
        "cli_arg": "Nur programmatisch",
        "impact": "Filtert unwichtige Inhalte heraus"
    }
}

# ==============================================================================
# 2. VECTORIZATION HYPERPARAMETER (VectorStoreConfig in vector_store.py)
# ==============================================================================

VECTORIZATION_HYPERPARAMETERS = {
    # Text Chunking
    "chunk_size": {
        "default": 1500,
        "description": "Maximale Größe eines Text-Chunks in Zeichen",
        "location": "src/scraper/vector_store.py:77",
        "cli_arg": "--chunk-size",
        "range": "200-5000",
        "impact": "Größer = mehr Kontext, aber weniger präzise Suche"
    },
    
    "chunk_overlap": {
        "default": 300,
        "description": "Überlappung zwischen aufeinanderfolgenden Chunks",
        "location": "src/scraper/vector_store.py:78", 
        "cli_arg": "--chunk-overlap",
        "range": "0-1000",
        "impact": "Höher = besserer Kontext, aber mehr Redundanz"
    },
    
    # Search & Retrieval
    "similarity_threshold": {
        "default": 0.1,
        "description": "Minimaler Similarity-Score für Suchergebnisse",
        "location": "src/scraper/vector_store.py:85",
        "cli_arg": "Nur programmatisch",
        "range": "0.0-1.0",
        "impact": "Niedriger = mehr Ergebnisse, aber weniger relevant"
    },
    
    "max_results": {
        "default": 10,
        "description": "Maximale Anzahl Suchergebnisse",
        "location": "src/scraper/vector_store.py:86",
        "cli_arg": "--results",
        "range": "1-100",
        "impact": "Höher = mehr Kontext für RAG, aber langsamere Verarbeitung"
    },
    
    # Embedding Configuration  
    "embedding_model": {
        "default": "all-MiniLM-L6-v2",
        "description": "Sentence Transformer Modell für Embeddings",
        "location": "src/scraper/vector_store.py:82",
        "cli_arg": "--embedding-model", 
        "options": ["all-MiniLM-L6-v2", "all-mpnet-base-v2", "paraphrase-multilingual-MiniLM-L12-v2"],
        "impact": "Größere Modelle = bessere Qualität, aber langsamer"
    },
    
    "embedding_provider": {
        "default": "sentence_transformers", 
        "description": "Embedding-Anbieter (nur Open Source)",
        "location": "src/scraper/vector_store.py:83",
        "cli_arg": "--embedding-provider",
        "options": ["sentence_transformers"],
        "impact": "Bestimmt Embedding-Qualität und -Geschwindigkeit"
    },
    
    # Database Configuration
    "backend": {
        "default": "chromadb",
        "description": "Vector Database Backend",
        "location": "src/scraper/vector_store.py:72",
        "cli_arg": "--backend",
        "options": ["chromadb", "faiss"],
        "impact": "ChromaDB = einfach, FAISS = performance"
    }
}

# ==============================================================================
# 3. WO HYPERPARAMETER ANGEPASST WERDEN KÖNNEN
# ==============================================================================

CONFIGURATION_LOCATIONS = {
    "CLI_Argumente": {
        "location": "src/scraper/scraper_main.py",
        "description": "Direkte Konfiguration über Kommandozeile",
        "example": """
python src/scraper/scraper_main.py pipeline \\
  --urls "https://example.com" \\
  --concurrent 5 \\
  --delay 2.0 \\
  --chunk-size 2000 \\
  --chunk-overlap 400
        """
    },
    
    "Programmatische_Konfiguration": {
        "location": "src/scraper/batch_scraper.py + vector_store.py",
        "description": "Erstelle Config-Objekte im Code",
        "example": """
from src.scraper.batch_scraper import ScrapingConfig
from src.scraper.vector_store import VectorStoreConfig

# Scraping-Konfiguration
scraping_config = ScrapingConfig(
    max_concurrent_requests=5,
    request_delay=2.0,
    timeout=45,
    retry_attempts=5,
    content_selectors={
        'title': 'h1, .title, .headline',
        'content': 'article, .main-content, .post-body'
    }
)

# Vector Store Konfiguration  
vector_config = VectorStoreConfig(
    chunk_size=2000,
    chunk_overlap=400,
    similarity_threshold=0.05,
    embedding_model="all-mpnet-base-v2"
)
        """
    },
    
    "Vordefinierte_Profile": {
        "location": "src/scraper/test_example.py",
        "description": "Verwendung vordefinierter Konfigurationsprofile", 
        "example": """
# Verfügbare Profile:
SCRAPING_CONFIGS = {
    "conservative": ScrapingConfig(max_concurrent_requests=3, request_delay=2.0),
    "balanced": ScrapingConfig(max_concurrent_requests=8, request_delay=1.0), 
    "aggressive": ScrapingConfig(max_concurrent_requests=15, request_delay=0.5)
}

VECTOR_CONFIGS = {
    "development": VectorStoreConfig(chunk_size=800, chunk_overlap=150),
    "production": VectorStoreConfig(chunk_size=1200, chunk_overlap=200)
}
        """
    },
    
    "JSON_Konfigurationsdateien": {
        "location": "Projektverzeichnis",
        "description": "Externe JSON-Konfigurationsdateien",
        "example": """
# config.json
{
    "scraping": {
        "max_concurrent_requests": 10,
        "request_delay": 1.5,
        "content_selectors": {
            "title": "h1, .page-title",
            "content": ".content, .article-body"
        }
    },
    "vectorization": {
        "chunk_size": 1800,
        "chunk_overlap": 350,
        "similarity_threshold": 0.15
    }
}
        """
    }
}

# ==============================================================================
# 4. OPTIMIERUNGS-TIPPS
# ==============================================================================

OPTIMIZATION_TIPS = {
    "Für_deutsche_Inhalte": {
        "similarity_threshold": "0.05-0.15 (niedriger als englisch)",
        "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
        "chunk_size": "1200-2000 (deutsche Sätze sind länger)"
    },
    
    "Für_Performance": {
        "max_concurrent_requests": "5-15 je nach Server",
        "request_delay": "0.5-1.0 für schnelle Server",
        "backend": "faiss für große Datenmengen",
        "chunk_size": "1000-1500 (Balance zwischen Kontext und Speed)"
    },
    
    "Für_Qualität": {
        "similarity_threshold": "0.05-0.1 für hohen Recall",
        "chunk_overlap": "300-500 für besseren Kontext",
        "embedding_model": "all-mpnet-base-v2 für beste Qualität",
        "retry_attempts": "3-5 für Robustheit"
    },
    
    "Für_Respektvolles_Scraping": {
        "max_concurrent_requests": "1-3",
        "request_delay": "2.0-5.0",
        "timeout": "30-60",
        "retry_delay": "5.0-10.0"
    }
}

# ==============================================================================
# 5. DYNAMISCHE KONFIGURATION
# ==============================================================================

def get_optimal_config_for_language(language: str):
    """Gibt optimale Konfiguration für spezifische Sprache zurück."""
    configs = {
        "german": {
            "similarity_threshold": 0.1,
            "chunk_size": 1800,
            "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2"
        },
        "english": {
            "similarity_threshold": 0.2, 
            "chunk_size": 1500,
            "embedding_model": "all-MiniLM-L6-v2"
        }
    }
    return configs.get(language, configs["english"])

def get_optimal_config_for_domain(domain: str):
    """Gibt optimale Konfiguration für spezifische Domains zurück."""
    configs = {
        "academic": {
            "chunk_size": 2000,
            "chunk_overlap": 400,
            "content_selectors": {
                "title": "h1, .article-title, .paper-title",
                "content": ".abstract, .content, .article-body, p"
            }
        },
        "news": {
            "chunk_size": 1200,
            "chunk_overlap": 200, 
            "content_selectors": {
                "title": "h1, .headline, .article-title",
                "content": ".article-body, .story-content, p"
            }
        },
        "ecommerce": {
            "chunk_size": 800,
            "chunk_overlap": 150,
            "content_selectors": {
                "title": "h1, .product-title",
                "content": ".description, .product-details, .features"
            }
        }
    }
    return configs.get(domain, configs["academic"])


if __name__ == "__main__":
    print("=== HYPERPARAMETER ÜBERSICHT ===")
    print("\\nScraping Parameter:")
    for param, config in SCRAPING_HYPERPARAMETERS.items():
        print(f"  {param}: {config['default']} - {config['description']}")
    
    print("\\nVectorization Parameter:")  
    for param, config in VECTORIZATION_HYPERPARAMETERS.items():
        print(f"  {param}: {config['default']} - {config['description']}")