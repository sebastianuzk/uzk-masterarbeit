"""
Collection Categorizer
======================

Kategorisiert Dokumente basierend auf URL-Patterns in thematische Collections.
Advanced Pre-Retrieval Technik für Multi-Collection RAG.
"""
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CollectionCategorizer:
    """
    Kategorisiert Dokumente in thematische Collections basierend auf URL-Patterns.
    
    Ermöglicht Multi-Collection RAG für bessere thematische Trennung und
    präziseres Retrieval.
    """
    
    # Standard-Collections für WiSo-Fakultät
    DEFAULT_COLLECTIONS = {
        'wiso_studium': ['studies', 'students', 'admission', 'application', 'programme', 'bachelor', 'master'],
        'wiso_services': ['services', 'facilities', 'library', 'support', 'career', 'contact'],
        'wiso_forschung': ['research', 'publications', 'projects', 'phd', 'doctoral'],
        'wiso_allgemein': []  # Fallback für alles andere
    }
    
    def __init__(self, collections: Optional[Dict[str, List[str]]] = None):
        """
        Initialisiere CollectionCategorizer.
        
        Args:
            collections: Optional custom Collections-Mapping.
                        Format: {'collection_name': ['keyword1', 'keyword2', ...]}
                        Wenn None, werden DEFAULT_COLLECTIONS verwendet.
        """
        self.collections = collections if collections is not None else self.DEFAULT_COLLECTIONS.copy()
        logger.info(f"CollectionCategorizer initialisiert mit {len(self.collections)} Collections")
        
        # Validiere Collections
        if not any(keywords for keywords in self.collections.values()):
            logger.warning("Keine Keywords definiert - alle Dokumente landen in Fallback-Collection")
    
    def get_collection_name(self, url: str) -> str:
        """
        Bestimme Collection-Name basierend auf URL-Patterns.
        
        Args:
            url: Dokument-URL
            
        Returns:
            Name der zugewiesenen Collection
        """
        url_lower = url.lower()
        
        # Durchsuche alle Collections nach Keywords
        for collection_name, keywords in self.collections.items():
            # Skip Fallback-Collection
            if not keywords:
                continue
            
            # Prüfe ob URL eines der Keywords enthält
            for keyword in keywords:
                if keyword in url_lower:
                    logger.debug(f"URL '{url}' → Collection '{collection_name}' (Keyword: '{keyword}')")
                    return collection_name
        
        # Fallback zur ersten Collection ohne Keywords
        fallback = next((name for name, kw in self.collections.items() if not kw), None)
        
        if fallback:
            logger.debug(f"URL '{url}' → Fallback Collection '{fallback}'")
            return fallback
        
        # Wenn kein Fallback existiert, nimm die erste Collection
        default = list(self.collections.keys())[0]
        logger.debug(f"URL '{url}' → Default Collection '{default}'")
        return default
    
    def get_collection_names(self) -> List[str]:
        """
        Gib alle definierten Collection-Namen zurück.
        
        Returns:
            Liste aller Collection-Namen
        """
        return list(self.collections.keys())
    
    def get_collection_keywords(self, collection_name: str) -> List[str]:
        """
        Gib Keywords für eine bestimmte Collection zurück.
        
        Args:
            collection_name: Name der Collection
            
        Returns:
            Liste der Keywords für diese Collection
        """
        return self.collections.get(collection_name, [])
    
    def add_collection(self, name: str, keywords: List[str]) -> None:
        """
        Füge eine neue Collection hinzu.
        
        Args:
            name: Name der neuen Collection
            keywords: Liste von Keywords für diese Collection
        """
        if name in self.collections:
            logger.warning(f"Collection '{name}' existiert bereits - wird überschrieben")
        
        self.collections[name] = keywords
        logger.info(f"Collection '{name}' hinzugefügt mit {len(keywords)} Keywords")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Gib Statistiken über die Collections zurück.
        
        Returns:
            Dictionary mit Collection-Namen und Keyword-Anzahl
        """
        return {
            name: len(keywords)
            for name, keywords in self.collections.items()
        }
    
    def __repr__(self) -> str:
        """String-Repräsentation."""
        return f"CollectionCategorizer(collections={len(self.collections)})"
