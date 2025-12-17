"""
Multi-Collection Search
=======================

Durchsucht alle ChromaDB-Collections statt nur einer.
Komplette Advanced-Retrieval-Logik inkl. Client-Management.
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
import chromadb
from pathlib import Path
from langsmith import traceable

logger = logging.getLogger(__name__)


def get_chromadb_client() -> chromadb.Client:
    """
    Hole ChromaDB Client (Shared Helper).
    
    Returns:
        ChromaDB Client
        
    Raises:
        FileNotFoundError: Wenn Vector DB nicht gefunden
    """
    # WICHTIG: Relative Paths benutzen! ChromaDB hat Bug mit absoluten Windows-Pfaden
    vector_db_paths = [
        "data/vector_db",
        "src/scraper/vector_db"
    ]
    
    for path_str in vector_db_paths:
        if Path(path_str).exists():
            return chromadb.PersistentClient(path=path_str)
    
    raise FileNotFoundError("Vector DB nicht gefunden")


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


def advanced_retrieve(query: str, k_per_collection: int = 3) -> List[Dict[str, Any]]:
    """
    Complete Advanced RAG Retrieval (für RAG-Tool).
    
    Durchsucht alle Collections mit MultiCollectionSearcher und
    liefert Ergebnisse im Format für Advanced-Pipeline.
    
    Args:
        query: Suchanfrage
        k_per_collection: Anzahl Ergebnisse pro Collection
        
    Returns:
        Liste von Dokumenten mit erweiterten Metadaten
        (document, id, collection, distance, page_content, type, metadata)
    """
    try:
        client = get_chromadb_client()
    except FileNotFoundError:
        logger.warning("Vector DB nicht gefunden")
        return []
    
    # Lade Embedding-Modell für Query-Encoding
    from sentence_transformers import SentenceTransformer
    from config.settings import SENTENCE_TRANSFORMER_MODEL
    embedding_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    raw_embedding = embedding_model.encode([query])
    # Normalisiere Query-Embedding für echte Cosine-Similarity
    normalized_embedding = raw_embedding / np.linalg.norm(raw_embedding, axis=1, keepdims=True)
    query_embedding = normalized_embedding.tolist()[0]
    
    # Multi-Collection Searcher
    searcher = MultiCollectionSearcher(
        client=client,
        k_per_collection=k_per_collection
    )
    
    # Durchsuche alle Collections mit dem korrekten Embedding
    documents = searcher.search_all_collections(query, query_embedding=query_embedding)
    
    # Konvertiere Format für Advanced-Pipeline
    # Füge page_content und type für Backward-Compatibility hinzu
    for doc in documents:
        doc['page_content'] = doc.get('document', '')
        doc['type'] = 'Document'
        # metadata ist bereits gesetzt von search_all_collections
    
    logger.info(f"Advanced Retrieve: {len(documents)} Dokumente zurückgegeben")
    
    return documents
