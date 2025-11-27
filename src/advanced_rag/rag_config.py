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
    # PRE-RETRIEVAL HYPERPARAMETER
    # ============================================================================
    # Semantic Chunking
    semantic_chunking_max_size: int = 1500
    semantic_chunking_min_size: int = 200
    semantic_chunking_overlap: int = 300
    
    # Content Cleaning
    content_cleaning_min_length: int = 50
    content_cleaning_remove_html: bool = True
    content_cleaning_normalize_whitespace: bool = True
    
    # Deduplication
    deduplication_similarity_threshold: float = 0.85
    deduplication_shingle_size: int = 3
    
    # ============================================================================
    # RETRIEVAL HYPERPARAMETER
    # ============================================================================
    # Multi-Collection Search
    multi_collection_k_per_collection: int = 3
    
    # Result Aggregation
    result_aggregation_top_k: int = 5
    
    # Distance Conversion
    distance_conversion_min: float = 0.0
    distance_conversion_max: float = 2.0
    
    # Global Reranking
    global_reranking_max_per_source: int = 2
    global_reranking_diversity_penalty: float = 0.1
    
    # ============================================================================
    # POST-RETRIEVAL HYPERPARAMETER
    # ============================================================================
    # Relevance Filtering
    relevance_filtering_threshold: float = 0.1
    relevance_filtering_min_results: int = 1
    
    # Result Formatting
    result_formatting_include_metadata: bool = True
    result_formatting_include_sources: bool = True
    result_formatting_max_preview_length: int = 200
    
    # Context Hints
    context_hints_max_hints: int = 3
    
    # Empty Result Handling
    empty_result_fallback_message: str = "Keine relevanten Informationen gefunden."
    empty_result_suggest_alternatives: bool = True
    
    # ============================================================================
    # EMBEDDING & DATABASE
    # ============================================================================
    embedding_model_name: str = "all-MiniLM-L6-v2"
    embedding_model_dimension: int = 384
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
    # COMPUTED PROPERTIES (basierend auf naive_setup)
    # ============================================================================
    
    @property
    def use_semantic_chunking(self) -> bool:
        """Pre-Retrieval: Semantic Chunking aktiv?"""
        return not self.naive_setup
    
    @property
    def use_content_cleaning(self) -> bool:
        """Pre-Retrieval: Content Cleaning aktiv?"""
        return not self.naive_setup
    
    @property
    def use_deduplication(self) -> bool:
        """Pre-Retrieval: Deduplication aktiv?"""
        return not self.naive_setup
    
    @property
    def use_multi_collection_search(self) -> bool:
        """Retrieval: Multi-Collection Search aktiv?"""
        return not self.naive_setup
    
    @property
    def use_result_aggregation(self) -> bool:
        """Retrieval: Result Aggregation aktiv?"""
        return not self.naive_setup
    
    @property
    def use_distance_conversion(self) -> bool:
        """Retrieval: Distance Conversion aktiv?"""
        return not self.naive_setup
    
    @property
    def use_global_reranking(self) -> bool:
        """Retrieval: Global Reranking aktiv?"""
        return not self.naive_setup
    
    @property
    def use_relevance_filtering(self) -> bool:
        """Post-Retrieval: Relevance Filtering aktiv?"""
        return not self.naive_setup
    
    @property
    def use_result_formatting(self) -> bool:
        """Post-Retrieval: Result Formatting aktiv?"""
        return not self.naive_setup
    
    @property
    def use_context_hints(self) -> bool:
        """Post-Retrieval: Context Hints aktiv?"""
        return not self.naive_setup
    
    @property
    def use_empty_result_handling(self) -> bool:
        """Post-Retrieval: Empty Result Handling aktiv?"""
        return not self.naive_setup
    
    @property
    def baseline_enabled(self) -> bool:
        """Baseline RAG (= Naive Setup)?"""
        return self.naive_setup
    
    # Legacy properties für Backward Compatibility
    @property
    def relevance_threshold(self) -> float:
        return self.relevance_filtering_threshold
    
    @property
    def k_per_collection(self) -> int:
        return self.multi_collection_k_per_collection
    
    @property
    def top_k(self) -> int:
        return self.result_aggregation_top_k
    
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
            
            # === PRE-RETRIEVAL HYPERPARAMETER ===
            semantic_chunking_max_size=_get_int_env("SEMANTIC_CHUNKING_MAX_SIZE", 1500),
            semantic_chunking_min_size=_get_int_env("SEMANTIC_CHUNKING_MIN_SIZE", 200),
            semantic_chunking_overlap=_get_int_env("SEMANTIC_CHUNKING_OVERLAP", 300),
            
            content_cleaning_min_length=_get_int_env("CONTENT_CLEANING_MIN_LENGTH", 50),
            content_cleaning_remove_html=_get_bool_env("CONTENT_CLEANING_REMOVE_HTML", True),
            content_cleaning_normalize_whitespace=_get_bool_env("CONTENT_CLEANING_NORMALIZE_WHITESPACE", True),
            
            deduplication_similarity_threshold=_get_float_env("DEDUPLICATION_SIMILARITY_THRESHOLD", 0.85),
            deduplication_shingle_size=_get_int_env("DEDUPLICATION_SHINGLE_SIZE", 3),
            
            # === RETRIEVAL HYPERPARAMETER ===
            multi_collection_k_per_collection=_get_int_env("MULTI_COLLECTION_K_PER_COLLECTION", 3),
            result_aggregation_top_k=_get_int_env("RESULT_AGGREGATION_TOP_K", 5),
            distance_conversion_min=_get_float_env("DISTANCE_CONVERSION_MIN_DISTANCE", 0.0),
            distance_conversion_max=_get_float_env("DISTANCE_CONVERSION_MAX_DISTANCE", 2.0),
            global_reranking_max_per_source=_get_int_env("GLOBAL_RERANKING_MAX_PER_SOURCE", 2),
            global_reranking_diversity_penalty=_get_float_env("GLOBAL_RERANKING_DIVERSITY_PENALTY", 0.1),
            
            # === POST-RETRIEVAL HYPERPARAMETER ===
            relevance_filtering_threshold=_get_float_env("RELEVANCE_FILTERING_THRESHOLD", 0.1),
            relevance_filtering_min_results=_get_int_env("RELEVANCE_FILTERING_MIN_RESULTS", 1),
            result_formatting_include_metadata=_get_bool_env("RESULT_FORMATTING_INCLUDE_METADATA", True),
            result_formatting_include_sources=_get_bool_env("RESULT_FORMATTING_INCLUDE_SOURCES", True),
            result_formatting_max_preview_length=_get_int_env("RESULT_FORMATTING_MAX_PREVIEW_LENGTH", 200),
            context_hints_max_hints=_get_int_env("CONTEXT_HINTS_MAX_HINTS", 3),
            empty_result_fallback_message=os.getenv("EMPTY_RESULT_FALLBACK_MESSAGE", "Keine relevanten Informationen gefunden."),
            empty_result_suggest_alternatives=_get_bool_env("EMPTY_RESULT_SUGGEST_ALTERNATIVES", True),
            
            # === EMBEDDING & DATABASE ===
            embedding_model_name=os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
            embedding_model_dimension=_get_int_env("EMBEDDING_MODEL_DIMENSION", 384),
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
            "content_cleaning": self.use_content_cleaning,
            "deduplication": self.use_deduplication,
            # Retrieval
            "multi_collection_search": self.use_multi_collection_search,
            "result_aggregation": self.use_result_aggregation,
            "distance_conversion": self.use_distance_conversion,
            "global_reranking": self.use_global_reranking,
            # Post-Retrieval
            "relevance_filtering": self.use_relevance_filtering,
            "result_formatting": self.use_result_formatting,
            "context_hints": self.use_context_hints,
            "empty_result_handling": self.use_empty_result_handling
        }
    
    def log_config(self) -> None:
        """Logge aktuelle Konfiguration."""
        mode = "NAIVE BASELINE" if self.naive_setup else "ADVANCED RAG"
        logger.info(f"🔧 RAG-Modus: {mode}")
        enabled = [name for name, enabled in self.get_enabled_techniques().items() if enabled and name != 'naive_setup']
        if enabled:
            logger.info(f"✅ Aktivierte Techniken: {', '.join(enabled)}")
        logger.info(f"📊 Hyperparameter: top_k={self.top_k}, relevance_threshold={self.relevance_threshold}")


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