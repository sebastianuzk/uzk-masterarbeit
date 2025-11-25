"""
Multi-Collection Search
=======================

Advanced Technik: Durchsucht mehrere Collections parallel und aggregiert Ergebnisse.
"""

from typing import List, Dict, Any
import chromadb


class MultiCollectionSearch:
    """
    Durchsucht alle verfügbaren Collections statt nur einer einzigen.
    
    Vorteile:
    - Höhere Recall-Rate durch breitere Suche
    - Keine verpassten Informationen aus anderen Collections
    
    Naive Alternative:
    - Suche nur in einer vordefinierten Collection
    """
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
    
    def search(self, client: chromadb.PersistentClient, query: str, 
               k_per_collection: int = 3) -> List[Dict[str, Any]]:
        """
        Sucht in allen Collections.
        
        Args:
            client: ChromaDB Client
            query: Suchanfrage
            k_per_collection: Anzahl Results pro Collection
            
        Returns:
            Liste aller Results aus allen Collections
        """
        if not self.enabled:
            # Naive: Nur erste Collection
            collections = client.list_collections()
            if not collections:
                return []
            
            collection = client.get_collection(name=collections[0].name)
            results = collection.query(
                query_texts=[query],
                n_results=k_per_collection
            )
            
            return self._format_results(results, collections[0].name)
        
        # Advanced: Alle Collections
        all_results = []
        collections = client.list_collections()
        
        for collection_info in collections:
            try:
                collection = client.get_collection(name=collection_info.name)
                results = collection.query(
                    query_texts=[query],
                    n_results=k_per_collection
                )
                
                formatted = self._format_results(results, collection_info.name)
                all_results.extend(formatted)
                
            except Exception as e:
                print(f"Warnung: Fehler bei Collection '{collection_info.name}': {e}")
                continue
        
        return all_results
    
    def _format_results(self, results: Dict, collection_name: str) -> List[Dict[str, Any]]:
        """Formatiert ChromaDB Results zu einheitlichem Format."""
        formatted = []
        
        if not results['documents'] or not results['documents'][0]:
            return formatted
        
        documents = results['documents'][0]
        metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
        distances = results['distances'][0] if results['distances'] else [0] * len(documents)
        
        for doc, metadata, distance in zip(documents, metadatas, distances):
            enhanced_metadata = metadata.copy() if metadata else {}
            enhanced_metadata['collection'] = collection_name
            enhanced_metadata['distance'] = float(distance)
            enhanced_metadata['relevance_score'] = float(max(0, 1 - distance))
            
            formatted.append({
                'document': doc,
                'metadata': enhanced_metadata,
                'distance': distance
            })
        
        return formatted
