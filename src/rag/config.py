"""
RAG Configuration Management
===========================

Zentrale Konfiguration für das modulare RAG-System.
Lädt Einstellungen aus rag.env und stellt sie für alle Module bereit.
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RAGConfig:
    """Konfiguration für das RAG-System."""
    
    # === BASELINE RAG ===
    baseline_enabled: bool = True
    
    # === PRE-RETRIEVAL TECHNIKEN ===
    query_expansion_enabled: bool = False
    query_rewriting_enabled: bool = False
    hyde_enabled: bool = False
    multi_query_enabled: bool = False
    
    # === RETRIEVAL TECHNIKEN ===
    hybrid_retrieval_enabled: bool = False
    reranking_enabled: bool = False
    parent_doc_retrieval_enabled: bool = False
    
    # === POST-RETRIEVAL TECHNIKEN ===
    context_compression_enabled: bool = False
    context_reordering_enabled: bool = False
    answer_fusion_enabled: bool = False
    
    # === ALLGEMEINE EINSTELLUNGEN ===
    num_results: int = 5
    relevance_threshold: float = 0.1
    debug_mode: bool = False
    
    @classmethod
    def load_from_env(cls, env_file: Optional[str] = None) -> 'RAGConfig':
        """
        Lade Konfiguration aus rag.env Datei.
        
        Args:
            env_file: Pfad zur env-Datei (optional, sucht automatisch)
            
        Returns:
            RAGConfig mit geladenen Einstellungen
        """
        try:
            from dotenv import load_dotenv
            
            # Automatische Suche nach rag.env
            if env_file is None:
                # Suche von aktueller Position nach oben
                current_dir = Path(__file__).parent
                for i in range(5):  # Max 5 Verzeichnisse nach oben
                    candidate = current_dir / "rag.env"
                    if candidate.exists():
                        env_file = str(candidate)
                        break
                    current_dir = current_dir.parent
                
                # Fallback: Projekt-Root
                if env_file is None:
                    project_root = Path(__file__).parent.parent.parent
                    candidate = project_root / "rag.env"
                    if candidate.exists():
                        env_file = str(candidate)
            
            if env_file and os.path.exists(env_file):
                load_dotenv(env_file)
                logger.info(f"RAG-Konfiguration geladen aus: {env_file}")
            else:
                logger.warning("Keine rag.env gefunden - verwende Standardwerte")
                
        except ImportError:
            logger.warning("python-dotenv nicht installiert - verwende Umgebungsvariablen")
        except Exception as e:
            logger.error(f"Fehler beim Laden der RAG-Konfiguration: {e}")
        
        # Erstelle Konfiguration aus Umgebungsvariablen
        return cls(
            # Baseline
            baseline_enabled=_get_bool_env("RAG_BASELINE_ENABLED", True),
            
            # Pre-Retrieval
            query_expansion_enabled=_get_bool_env("RAG_QUERY_EXPANSION_ENABLED", False),
            query_rewriting_enabled=_get_bool_env("RAG_QUERY_REWRITING_ENABLED", False),
            hyde_enabled=_get_bool_env("RAG_HYDE_ENABLED", False),
            multi_query_enabled=_get_bool_env("RAG_MULTI_QUERY_ENABLED", False),
            
            # Retrieval
            hybrid_retrieval_enabled=_get_bool_env("RAG_HYBRID_RETRIEVAL_ENABLED", False),
            reranking_enabled=_get_bool_env("RAG_RERANKING_ENABLED", False),
            parent_doc_retrieval_enabled=_get_bool_env("RAG_PARENT_DOC_RETRIEVAL_ENABLED", False),
            
            # Post-Retrieval
            context_compression_enabled=_get_bool_env("RAG_CONTEXT_COMPRESSION_ENABLED", False),
            context_reordering_enabled=_get_bool_env("RAG_CONTEXT_REORDERING_ENABLED", False),
            answer_fusion_enabled=_get_bool_env("RAG_ANSWER_FUSION_ENABLED", False),
            
            # Allgemein
            num_results=_get_int_env("RAG_NUM_RESULTS", 5),
            relevance_threshold=_get_float_env("RAG_RELEVANCE_THRESHOLD", 0.1),
            debug_mode=_get_bool_env("RAG_DEBUG_MODE", False)
        )
    
    def get_enabled_techniques(self) -> Dict[str, bool]:
        """Gib alle aktivierten Techniken zurück."""
        return {
            "baseline": self.baseline_enabled,
            "query_expansion": self.query_expansion_enabled,
            "query_rewriting": self.query_rewriting_enabled,
            "hyde": self.hyde_enabled,
            "multi_query": self.multi_query_enabled,
            "hybrid_retrieval": self.hybrid_retrieval_enabled,
            "reranking": self.reranking_enabled,
            "parent_doc_retrieval": self.parent_doc_retrieval_enabled,
            "context_compression": self.context_compression_enabled,
            "context_reordering": self.context_reordering_enabled,
            "answer_fusion": self.answer_fusion_enabled
        }
    
    def log_config(self) -> None:
        """Logge aktuelle Konfiguration."""
        enabled = [name for name, enabled in self.get_enabled_techniques().items() if enabled]
        logger.info(f"RAG-Konfiguration - Aktivierte Techniken: {', '.join(enabled)}")
        logger.info(f"RAG-Parameter: results={self.num_results}, threshold={self.relevance_threshold}")


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