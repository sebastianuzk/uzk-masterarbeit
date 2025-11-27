"""
Multi-Collection Search
=======================

Durchsucht alle ChromaDB-Collections statt nur einer.
"""
import logging
from typing import List, Dict, Any
import chromadb

logger = logging.getLogger(__name__)


class MultiCollectionSearcher:
    """
    Durchsucht mehrere ChromaDB-Collections parallel.
    """
    
    def __init__(self, client: chromadb.Client, k_per_collection: int = 3):
        """
        Initialisiere den Multi-Collection Searcher.
        
        Args:
            client: ChromaDB Client
            k_per_collection: Anzahl Ergebnisse pro Collection
        """
        self.client = client
        self.k_per_collection = k_per_collection
        
    def search_all_collections(
        self,
        query: str,
        query_embedding: List[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Durchsuche alle verfügbaren Collections.
        
        Args:
            query: Suchanfrage
            query_embedding: Optional vorberechnetes Embedding
            
        Returns:
            Liste von Dokumenten mit Metadaten
        """
        all_results = []
        collections = self.client.list_collections()
        
        logger.debug(f"Durchsuche {len(collections)} Collections")
        
        for collection in collections:
            try:
                if query_embedding:
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=self.k_per_collection
                    )
                else:
                    results = collection.query(
                        query_texts=[query],
                        n_results=self.k_per_collection
                    )
                
                # Verarbeite Ergebnisse
                for i in range(len(results['ids'][0])):
                    doc = {
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i],
                        'collection': collection.name
                    }
                    all_results.append(doc)
                
                logger.debug(
                    f"Collection '{collection.name}': "
                    f"{len(results['ids'][0])} Ergebnisse"
                )
                
            except Exception as e:
                logger.warning(f"Fehler bei Collection '{collection.name}': {e}")
                continue
        
        logger.info(f"Multi-Collection Search: {len(all_results)} Ergebnisse gesamt")
        
        return all_results
