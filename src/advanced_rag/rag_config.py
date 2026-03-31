"""
RAG Configuration Management
===========================

Zentrale Konfiguration für das modulare RAG-System.
Lädt Hyperparameter aus rag.env, Aktivierung/Deaktivierung erfolgt über naive_setup.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class RAGConfig:
    """
    Konfiguration für das RAG-System.
    
    Aktivierung/Deaktivierung:
    - naive_setup=True  → Alle Advanced-Techniken AUS (Baseline RAG)
    - naive_setup=False → Alle Advanced-Techniken AN
    
    Hyperparameter werden aus src/advanced_rag/rag.env geladen.
    """
    
    # ============================================================================
    # MASTER SWITCH (steuert ALLE Advanced-Techniken)
    # ============================================================================
    naive_setup: bool = False  # False = Advanced RAG, True = Naive Baseline
    
    # ============================================================================
    # INDIVIDUAL FEATURE FLAGS (ermöglichen granulare Kontrolle)
    # Wenn naive_setup=True, sind alle deaktiviert.
    # Wenn naive_setup=False, können einzelne Features hier deaktiviert werden.
    # ============================================================================
    enable_semantic_chunking: bool = False
    enable_deduplication: bool = False  # Aktiviert Exact + Near Deduplication
    enable_hybrid_retrieval: bool = False  # BM25 Sparse Index + RRF Fusion
    enable_sparse_retrieval: bool = True  # Nur BM25 Sparse Index (ohne Dense)
    enable_reranking: bool = True
    enable_mmr: bool = False  # Maximum Marginal Relevance für Diversität
    
    # ============================================================================
    # PRE-RETRIEVAL HYPERPARAMETER
    # HINWEIS: Diese Defaults sollten mit rag.env synchron sein!
    # Single Source of Truth: src/advanced_rag/rag.env
    # ============================================================================
    # Semantic Chunking (Defaults aus rag.env)
    semantic_chunking_max_size: int = 1500
    semantic_chunking_min_size: int = 400
    semantic_chunking_overlap: int = 300
    semantic_chunking_similarity_threshold: float = 0.4  # Schwellwert für Themenwechsel (static_threshold)
    semantic_chunking_use_percentile: bool = True  # Wenn True: Percentile-Methode statt static_threshold
    semantic_chunking_percentile: int = 10  # X-tes Perzentil für Breakpoints (nur wenn use_percentile=True)
    
    # Naive Chunking (fallback wenn Semantic Chunking deaktiviert)
    naive_chunking_max_size: int = 1500
    naive_chunking_overlap: int = 300
    
    # Deduplication (Exact)
    deduplication_similarity_threshold: float = 0.85
    deduplication_shingle_size: int = 3
    
    # Near-Deduplication (Document-Level)
    near_deduplication_shingle_k: int = 5
    near_deduplication_similarity_threshold: float = 0.90
    near_deduplication_min_words: int = 120
    near_deduplication_num_perm: int = 128
    
    # ============================================================================
    # RETRIEVAL HYPERPARAMETER
    # ============================================================================
    # Hybrid Retrieval (BM25 + Dense)
    hybrid_retrieval_rrf_k: int = 60  # RRF-K Parameter (höher = mehr Gewicht auf niedrigere Ränge)
    hybrid_retrieval_k_retrieve: int = 80  # Kandidaten pro Retrieval-Type (Dense + Sparse)
    
    # ============================================================================
    # POST-RETRIEVAL HYPERPARAMETER
    # ============================================================================
    # ReRanking
    reranking_provider: str = "voyage"  # "voyage", "cohere" oder "local"
    reranking_model: str = "rerank-2.5"  # Modellname (provider-abhängig, bei local: cross-encoder/ms-marco-MiniLM-L-12-v2)
    reranking_candidates: int = 40  # Anzahl Dokumente die dem ReRanker übergeben werden
    
    # Maximum Marginal Relevance (MMR)
    mmr_lambda: float = 0.9  # Trade-off: 0.0 = Diversität, 1.0 = Relevanz
    mmr_similarity_metric: str = "cosine"  # "cosine" oder "dot"
    
    # ============================================================================
    # EMBEDDING & DATABASE
    # ============================================================================
    embedding_model_name: str = "BAAI/bge-m3"
    embedding_model_dimension: int = 1024
    vector_db_path: str = "data/vector_db"
    vector_db_distance_metric: str = "cosine"
    
    # ============================================================================
    # GENERAL
    # ============================================================================
    debug_mode: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Validierung nach Initialisierung."""
        if self.naive_setup and self.debug_mode:
            logger.info("🔒 NAIVE SETUP aktiviert - alle Advanced-Techniken deaktiviert")
    
    # ============================================================================
    # COMPUTED PROPERTIES (basierend auf naive_setup UND individual flags)
    # ============================================================================
    
    @property
    def use_semantic_chunking(self) -> bool:
        """Pre-Retrieval: Semantic Chunking aktiv?"""
        return (not self.naive_setup) and self.enable_semantic_chunking
    
    @property
    def use_deduplication(self) -> bool:
        """Pre-Retrieval: Deduplication (Exact + Near) aktiv?"""
        return (not self.naive_setup) and self.enable_deduplication
    
    @property
    def use_near_deduplication(self) -> bool:
        """Pre-Retrieval: Near-Deduplication (Document-Level) aktiv?
        
        Automatisch aktiviert wenn Deduplication aktiviert ist.
        """
        return self.use_deduplication  # Near-Dedup ist Teil von Deduplication
    
    @property
    def use_hybrid_retrieval(self) -> bool:
        """Retrieval: Hybrid Retrieval (BM25 + Dense + RRF) aktiv?"""
        return (not self.naive_setup) and self.enable_hybrid_retrieval
    
    @property
    def use_sparse_retrieval(self) -> bool:
        """Retrieval: Nur Sparse Retrieval (BM25 ohne Dense) aktiv?"""
        return (not self.naive_setup) and self.enable_sparse_retrieval
    
    @property
    def use_reranking(self) -> bool:
        """Post-Retrieval: ReRanking aktiv? (UNABHÄNGIG von Retrieval-Methode!)"""
        return (not self.naive_setup) and self.enable_reranking
    
    @property
    def use_mmr(self) -> bool:
        """Post-Retrieval: Maximum Marginal Relevance (MMR) aktiv?"""
        return (not self.naive_setup) and self.enable_mmr
    
    @property
    def baseline_enabled(self) -> bool:
        """Baseline RAG (= Naive Setup)?"""
        return self.naive_setup
    
    @classmethod
    def load_from_env(cls, env_file: Optional[str] = None) -> 'RAGConfig':
        """
        Lade Hyperparameter aus rag.env Datei.
        
        Args:
            env_file: Pfad zur env-Datei (optional, sucht automatisch in src/advanced_rag/)
            
        Returns:
            RAGConfig mit geladenen Hyperparametern
        """
        try:
            from dotenv import load_dotenv
            
            # Automatische Suche nach rag.env (jetzt in src/advanced_rag/)
            if env_file is None:
                # Primär: Im selben Verzeichnis wie diese Datei
                current_dir = Path(__file__).parent
                candidate = current_dir / "rag.env"
                if candidate.exists():
                    env_file = str(candidate)
                else:
                    logger.warning(f"rag.env nicht gefunden in: {current_dir}")
            
            if env_file and os.path.exists(env_file):
                load_dotenv(env_file)
                logger.info(f"✅ RAG-Hyperparameter geladen aus: {env_file}")
            else:
                logger.warning("⚠️ Keine rag.env gefunden - verwende Standardwerte")
                
        except ImportError:
            logger.warning("python-dotenv nicht installiert - verwende Umgebungsvariablen")
        except Exception as e:
            logger.error(f"Fehler beim Laden der RAG-Konfiguration: {e}")
        
        # Erstelle Konfiguration aus Umgebungsvariablen
        return cls(
            # === MASTER SWITCH ===
            naive_setup=_get_bool_env("RAG_NAIVE_SETUP", False),
            
            # === INDIVIDUAL FEATURE FLAGS ===
            enable_semantic_chunking=_get_bool_env("ENABLE_SEMANTIC_CHUNKING", True),
            enable_deduplication=_get_bool_env("ENABLE_DEDUPLICATION", False),  # Aktiviert Exact + Near
            enable_hybrid_retrieval=_get_bool_env("ENABLE_HYBRID_RETRIEVAL", False),
            enable_sparse_retrieval=_get_bool_env("ENABLE_SPARSE_RETRIEVAL", False),
            enable_reranking=_get_bool_env("ENABLE_RERANKING", False),
            enable_mmr=_get_bool_env("ENABLE_MMR", False),
            
            # === PRE-RETRIEVAL HYPERPARAMETER ===
            # Fallback-Werte synchron mit rag.env (Single Source of Truth)
            semantic_chunking_max_size=_get_int_env("SEMANTIC_CHUNKING_MAX_SIZE", 1750),
            semantic_chunking_min_size=_get_int_env("SEMANTIC_CHUNKING_MIN_SIZE", 400),
            semantic_chunking_overlap=_get_int_env("SEMANTIC_CHUNKING_OVERLAP", 200),
            semantic_chunking_similarity_threshold=_get_float_env("SEMANTIC_CHUNKING_SIMILARITY_THRESHOLD", 0.7),
            semantic_chunking_use_percentile=_get_bool_env("SEMANTIC_CHUNKING_USE_PERCENTILE", False),
            semantic_chunking_percentile=_get_int_env("SEMANTIC_CHUNKING_PERCENTILE", 10),
            
            # Naive Chunking (separate Parameter)
            naive_chunking_max_size=_get_int_env("NAIVE_CHUNKING_MAX_SIZE", 1750),
            naive_chunking_overlap=_get_int_env("NAIVE_CHUNKING_OVERLAP", 300),
            
            deduplication_similarity_threshold=_get_float_env("DEDUPLICATION_SIMILARITY_THRESHOLD", 0.85),
            deduplication_shingle_size=_get_int_env("DEDUPLICATION_SHINGLE_SIZE", 3),
            
            # Near-Deduplication (Document-Level)
            near_deduplication_shingle_k=_get_int_env("NEAR_DEDUPLICATION_SHINGLE_K", 5),
            near_deduplication_similarity_threshold=_get_float_env("NEAR_DEDUPLICATION_SIMILARITY_THRESHOLD", 0.90),
            near_deduplication_min_words=_get_int_env("NEAR_DEDUPLICATION_MIN_WORDS", 120),
            near_deduplication_num_perm=_get_int_env("NEAR_DEDUPLICATION_NUM_PERM", 128),
            
            # === RETRIEVAL HYPERPARAMETER ===
            hybrid_retrieval_rrf_k=_get_int_env("RRF_K", 60),
            hybrid_retrieval_k_retrieve=_get_int_env("HYBRID_RETRIEVAL_K_RETRIEVE", 80),
            
            # === RERANKING ===
            reranking_provider=os.getenv("RERANKING_PROVIDER", "voyage"),
            reranking_model=os.getenv("RERANKING_MODEL", "rerank-2.5"),
            reranking_candidates=_get_int_env("RERANKING_CANDIDATES", 40),
            
            # === MMR (Maximum Marginal Relevance) ===
            mmr_lambda=_get_float_env("MMR_LAMBDA", 0.5),
            mmr_similarity_metric=os.getenv("MMR_SIMILARITY_METRIC", "cosine"),
            
            # === EMBEDDING & DATABASE ===
            embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3"),
            embedding_model_dimension=_get_int_env("EMBEDDING_MODEL_DIMENSION", 1024),
            vector_db_path=os.getenv("VECTOR_DB_PATH", "data/vector_db"),
            vector_db_distance_metric=os.getenv("VECTOR_DB_DISTANCE_METRIC", "cosine"),
            
            # === GENERAL ===
            debug_mode=_get_bool_env("DEBUG_MODE", False),
            log_level=os.getenv("LOG_LEVEL", "INFO")
        )
    
    def get_enabled_techniques(self) -> Dict[str, bool]:
        """Gib alle aktivierten Techniken zurück."""
        return {
            "naive_setup": self.naive_setup,
            "baseline": self.baseline_enabled,
            # Pre-Retrieval
            "semantic_chunking": self.use_semantic_chunking,
            "deduplication": self.use_deduplication,
            # Retrieval
            "hybrid_retrieval": self.use_hybrid_retrieval,
            "sparse_retrieval": self.use_sparse_retrieval,
            # Post-Retrieval
            "reranking": self.use_reranking,
            "mmr": self.use_mmr
        }
    
    def log_config(self) -> None:
        """Logge aktuelle Konfiguration."""
        mode = "NAIVE BASELINE" if self.naive_setup else "ADVANCED RAG"
        logger.info(f"🔧 RAG-Modus: {mode}")
        enabled = [name for name, enabled in self.get_enabled_techniques().items() if enabled and name != 'naive_setup']
        if enabled:
            logger.info(f"✅ Aktivierte Techniken: {', '.join(enabled)}")
        logger.info(f"📊 Konfiguration geladen")


def _get_bool_env(key: str, default: bool = False) -> bool:
    """Hilfsfunktion für Boolean-Umgebungsvariablen."""
    value = os.getenv(key, str(default)).lower()
    return value in ("true", "1", "yes", "on")


def _get_int_env(key: str, default: int) -> int:
    """Hilfsfunktion für Integer-Umgebungsvariablen."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_float_env(key: str, default: float) -> float:
    """Hilfsfunktion für Float-Umgebungsvariablen."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


# Globale Konfigurationsinstanz
_global_config: Optional[RAGConfig] = None


def get_rag_config() -> RAGConfig:
    """
    Hole globale RAG-Konfiguration (Singleton).
    
    Returns:
        RAGConfig-Instanz
    """
    global _global_config
    if _global_config is None:
        _global_config = RAGConfig.load_from_env()
    return _global_config


def reload_rag_config() -> RAGConfig:
    """
    Lade RAG-Konfiguration neu.
    
    Returns:
        Neue RAGConfig-Instanz
    """
    global _global_config
    _global_config = RAGConfig.load_from_env()
    return _global_config


# Convenience-Funktionen
def is_technique_enabled(technique_name: str) -> bool:
    """Prüfe ob eine bestimmte Technik aktiviert ist."""
    config = get_rag_config()
    return config.get_enabled_techniques().get(technique_name, False)