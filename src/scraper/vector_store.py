"""
Vector Store Integration for RAG System
=======================================

This module provides vector database integration for storing and retrieving
scraped web content in a RAG (Retrieval-Augmented Generation) system.

Features:
- Multiple vector database backends (ChromaDB, FAISS, Pinecone)
- Text chunking and embedding generation
- Similarity search and retrieval
- Metadata filtering
- Batch operations
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple, Union
from dataclasses import dataclass, asdict
from pathlib import Path
import logging
from abc import ABC, abstractmethod

# Vector database dependencies
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

# Pinecone removed - using only open source alternatives
PINECONE_AVAILABLE = False

# Embedding dependencies
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# OpenAI removed - using only open source alternatives
OPENAI_AVAILABLE = False

from .batch_scraper import ScrapedContent


@dataclass
class VectorDocument:
    """Document structure for vector storage."""
    id: str
    text: str
    embedding: Optional[List[float]]
    metadata: Dict[str, Any]
    source_url: str
    chunk_index: int
    total_chunks: int


@dataclass
class VectorStoreConfig:
    """Configuration for vector store operations."""
    # Database settings
    backend: str = "chromadb"  # chromadb, faiss (open source only)
    collection_name: str = "scraped_content"
    persist_directory: str = "src/scraper/output/vector_db"
    
    # Chunking settings
    chunk_size: int = 1500  # Larger chunks for better context
    chunk_overlap: int = 300  # More overlap
    
    # Embedding settings
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_provider: str = "sentence_transformers"  # Only sentence_transformers (open source)
    
    # Search settings
    similarity_threshold: float = 0.1  # Very low threshold for better recall
    max_results: int = 10


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    def encode(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """Get the dimension of the embeddings."""
        pass


class SentenceTransformerProvider(EmbeddingProvider):
    """Sentence Transformers embedding provider."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers is required but not installed")
        
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
    
    def encode(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, convert_to_tensor=False)
        return embeddings.tolist()
    
    def get_dimension(self) -> int:
        return self.dimension


# OpenAI Provider removed - using only open source alternatives


class VectorStoreBackend(ABC):
    """Abstract base class for vector store backends."""
    
    @abstractmethod
    def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to the vector store."""
        pass
    
    @abstractmethod
    def search(self, query_embedding: List[float], 
              k: int = 10, metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorDocument, float]]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    def delete_by_source(self, source_url: str) -> None:
        """Delete all documents from a specific source URL."""
        pass
    
    @abstractmethod
    def get_document_count(self) -> int:
        """Get the total number of documents in the store."""
        pass


class ChromaDBBackend(VectorStoreBackend):
    """ChromaDB vector store backend."""
    
    def __init__(self, config: VectorStoreConfig):
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb is required but not installed")
        
        self.config = config
        self.client = chromadb.PersistentClient(path=config.persist_directory)
        self.collection = self.client.get_or_create_collection(
            name=config.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        self.logger = logging.getLogger(__name__)
    
    def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to ChromaDB."""
        if not documents:
            return
        
        ids = [doc.id for doc in documents]
        embeddings = [doc.embedding for doc in documents]
        texts = [doc.text for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        
        self.logger.info(f"Added {len(documents)} documents to ChromaDB")
    
    def search(self, query_embedding: List[float], 
              k: int = 10, metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorDocument, float]]:
        """Search for similar documents in ChromaDB."""
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=metadata_filter
        )
        
        documents = []
        for i in range(len(results['ids'][0])):
            doc = VectorDocument(
                id=results['ids'][0][i],
                text=results['documents'][0][i],
                embedding=None,  # Not returned by default
                metadata=results['metadatas'][0][i],
                source_url=results['metadatas'][0][i].get('source_url', ''),
                chunk_index=results['metadatas'][0][i].get('chunk_index', 0),
                total_chunks=results['metadatas'][0][i].get('total_chunks', 1)
            )
            score = 1 - results['distances'][0][i]  # Convert distance to similarity
            documents.append((doc, score))
        
        return documents
    
    def delete_by_source(self, source_url: str) -> None:
        """Delete all documents from a specific source URL."""
        results = self.collection.get(where={"source_url": source_url})
        if results['ids']:
            self.collection.delete(ids=results['ids'])
            self.logger.info(f"Deleted {len(results['ids'])} documents from {source_url}")
    
    def get_document_count(self) -> int:
        """Get the total number of documents."""
        return self.collection.count()


class FAISSBackend(VectorStoreBackend):
    """FAISS vector store backend."""
    
    def __init__(self, config: VectorStoreConfig, dimension: int):
        if not FAISS_AVAILABLE:
            raise ImportError("faiss-cpu or faiss-gpu is required but not installed")
        
        self.config = config
        self.dimension = dimension
        self.logger = logging.getLogger(__name__)
        
        # Initialize FAISS index
        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        self.documents: Dict[int, VectorDocument] = {}
        self.next_id = 0
        
        # Create persist directory
        self.persist_path = Path(config.persist_directory)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        
        # Try to load existing index
        self._load_index()
    
    def add_documents(self, documents: List[VectorDocument]) -> None:
        """Add documents to FAISS index."""
        if not documents:
            return
        
        embeddings = np.array([doc.embedding for doc in documents], dtype=np.float32)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)
        
        # Add to index
        start_id = self.next_id
        self.index.add(embeddings)
        
        # Store documents
        for i, doc in enumerate(documents):
            self.documents[start_id + i] = doc
        
        self.next_id += len(documents)
        
        # Persist index
        self._save_index()
        
        self.logger.info(f"Added {len(documents)} documents to FAISS index")
    
    def search(self, query_embedding: List[float], 
              k: int = 10, metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorDocument, float]]:
        """Search for similar documents in FAISS."""
        query_vector = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vector)
        
        # Search
        scores, indices = self.index.search(query_vector, min(k, self.index.ntotal))
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
            
            doc = self.documents.get(idx)
            if doc is None:
                continue
            
            # Apply metadata filter
            if metadata_filter:
                if not all(doc.metadata.get(key) == value for key, value in metadata_filter.items()):
                    continue
            
            results.append((doc, float(score)))
        
        return results
    
    def delete_by_source(self, source_url: str) -> None:
        """Delete documents by source URL (rebuild index without them)."""
        # Collect documents to keep
        docs_to_keep = [
            doc for doc in self.documents.values() 
            if doc.source_url != source_url
        ]
        
        # Rebuild index
        self.index = faiss.IndexFlatIP(self.dimension)
        self.documents = {}
        self.next_id = 0
        
        if docs_to_keep:
            self.add_documents(docs_to_keep)
        
        self.logger.info(f"Rebuilt index excluding documents from {source_url}")
    
    def get_document_count(self) -> int:
        """Get the total number of documents."""
        return self.index.ntotal
    
    def _save_index(self) -> None:
        """Save FAISS index and documents to disk."""
        # Save FAISS index
        index_path = self.persist_path / "faiss.index"
        faiss.write_index(self.index, str(index_path))
        
        # Save documents
        docs_path = self.persist_path / "documents.json"
        with open(docs_path, 'w') as f:
            docs_dict = {str(k): asdict(v) for k, v in self.documents.items()}
            json.dump({
                'documents': docs_dict,
                'next_id': self.next_id
            }, f)
    
    def _load_index(self) -> None:
        """Load FAISS index and documents from disk."""
        index_path = self.persist_path / "faiss.index"
        docs_path = self.persist_path / "documents.json"
        
        if index_path.exists() and docs_path.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(index_path))
                
                # Load documents
                with open(docs_path, 'r') as f:
                    data = json.load(f)
                    docs_dict = data['documents']
                    self.next_id = data['next_id']
                    
                    self.documents = {
                        int(k): VectorDocument(**v) for k, v in docs_dict.items()
                    }
                
                self.logger.info(f"Loaded FAISS index with {len(self.documents)} documents")
            except Exception as e:
                self.logger.warning(f"Failed to load existing index: {e}")
                self.index = faiss.IndexFlatIP(self.dimension)


class VectorStore:
    """
    Main vector store class for RAG data storage and retrieval.
    
    This class provides a unified interface for different vector database
    backends and handles text chunking, embedding generation, and search.
    """
    
    def __init__(self, config: Optional[VectorStoreConfig] = None):
        """
        Initialize the vector store.
        
        Args:
            config: Vector store configuration
        """
        self.config = config or VectorStoreConfig()
        self.logger = self._setup_logger()
        
        # Initialize embedding provider
        self.embedding_provider = self._create_embedding_provider()
        
        # Initialize backend
        self.backend = self._create_backend()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logging for the vector store."""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _create_embedding_provider(self) -> EmbeddingProvider:
        """Create the embedding provider based on configuration."""
        if self.config.embedding_provider == "sentence_transformers":
            return SentenceTransformerProvider(self.config.embedding_model)
        else:
            raise ValueError(f"Unknown embedding provider: {self.config.embedding_provider}. Only 'sentence_transformers' is supported (open source only)")
    
    def _create_backend(self) -> VectorStoreBackend:
        """Create the vector store backend based on configuration."""
        if self.config.backend == "chromadb":
            return ChromaDBBackend(self.config)
        elif self.config.backend == "faiss":
            return FAISSBackend(self.config, self.embedding_provider.get_dimension())
        else:
            raise ValueError(f"Unknown backend: {self.config.backend}")
    
    def add_scraped_content(self, scraped_content: List[ScrapedContent]) -> None:
        """
        Add scraped content to the vector store.
        
        Args:
            scraped_content: List of ScrapedContent objects
        """
        all_documents = []
        
        for content in scraped_content:
            if not content.success or not content.content.strip():
                continue
            
            # Chunk the content
            chunks = self._chunk_text(content.content)
            
            # Create documents for each chunk
            for i, chunk in enumerate(chunks):
                doc_id = self._generate_document_id(content.url, i)
                
                # Prepare metadata
                metadata = {
                    'source_url': content.url,
                    'title': content.title,
                    'timestamp': content.timestamp,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'domain': content.metadata.get('domain', ''),
                    'word_count': len(chunk.split())
                }
                
                # Add original metadata
                for key, value in content.metadata.items():
                    if key not in metadata and isinstance(value, (str, int, float, bool)):
                        metadata[key] = value
                
                document = VectorDocument(
                    id=doc_id,
                    text=chunk,
                    embedding=None,  # Will be generated later
                    metadata=metadata,
                    source_url=content.url,
                    chunk_index=i,
                    total_chunks=len(chunks)
                )
                
                all_documents.append(document)
        
        if not all_documents:
            self.logger.warning("No valid documents to add")
            return
        
        # Generate embeddings in batches
        self._generate_embeddings(all_documents)
        
        # Add to backend
        self.backend.add_documents(all_documents)
        
        self.logger.info(f"Added {len(all_documents)} document chunks from {len(scraped_content)} sources")
    
    def _chunk_text(self, text: str) -> List[str]:
        """
        Chunk text into smaller pieces for embedding.
        
        Args:
            text: Text to chunk
            
        Returns:
            List of text chunks
        """
        # Simple sentence-aware chunking
        sentences = text.split('. ')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Add sentence to current chunk
            test_chunk = current_chunk + ". " + sentence if current_chunk else sentence
            
            if len(test_chunk) <= self.config.chunk_size:
                current_chunk = test_chunk
            else:
                # Current chunk is full, start new one
                if current_chunk:
                    chunks.append(current_chunk.strip())
                
                # Handle overlap
                if len(chunks) > 0 and self.config.chunk_overlap > 0:
                    overlap_text = current_chunk[-self.config.chunk_overlap:]
                    current_chunk = overlap_text + ". " + sentence
                else:
                    current_chunk = sentence
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _generate_embeddings(self, documents: List[VectorDocument]) -> None:
        """
        Generate embeddings for documents.
        
        Args:
            documents: List of VectorDocument objects
        """
        texts = [doc.text for doc in documents]
        embeddings = self.embedding_provider.encode(texts)
        
        for doc, embedding in zip(documents, embeddings):
            doc.embedding = embedding
    
    def _generate_document_id(self, url: str, chunk_index: int) -> str:
        """
        Generate a unique document ID.
        
        Args:
            url: Source URL
            chunk_index: Chunk index
            
        Returns:
            Unique document ID
        """
        content = f"{url}#{chunk_index}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def search(self, query: str, k: int = 10, 
              metadata_filter: Optional[Dict] = None) -> List[Tuple[VectorDocument, float]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results to return
            metadata_filter: Optional metadata filter
            
        Returns:
            List of (document, similarity_score) tuples
        """
        # Generate query embedding
        query_embedding = self.embedding_provider.encode([query])[0]
        
        # Search in backend
        results = self.backend.search(query_embedding, k, metadata_filter)
        
        # Filter by similarity threshold
        filtered_results = [
            (doc, score) for doc, score in results 
            if score >= self.config.similarity_threshold
        ]
        
        return filtered_results
    
    def delete_by_source(self, source_url: str) -> None:
        """
        Delete all documents from a specific source URL.
        
        Args:
            source_url: URL to delete documents from
        """
        self.backend.delete_by_source(source_url)
        self.logger.info(f"Deleted documents from {source_url}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get vector store statistics.
        
        Returns:
            Dictionary containing statistics
        """
        return {
            'total_documents': self.backend.get_document_count(),
            'backend': self.config.backend,
            'embedding_model': self.config.embedding_model,
            'chunk_size': self.config.chunk_size,
            'collection_name': self.config.collection_name
        }


# Example usage
if __name__ == "__main__":
    import asyncio
    from batch_scraper import BatchScraper, ScrapingConfig
    
    async def main():
        # Example URLs to scrape
        urls = [
            "https://en.wikipedia.org/wiki/Machine_learning",
            "https://en.wikipedia.org/wiki/Natural_language_processing"
        ]
        
        # Configure and run scraper
        scraper_config = ScrapingConfig(max_concurrent_requests=2)
        scraper = BatchScraper(scraper_config)
        
        print("Scraping URLs...")
        scraped_content = await scraper.scrape_urls(urls)
        
        # Configure vector store
        vector_config = VectorStoreConfig(
            backend="chromadb",
            embedding_provider="sentence_transformers",
            chunk_size=500
        )
        
        # Create vector store and add content
        vector_store = VectorStore(vector_config)
        
        print("Adding content to vector store...")
        vector_store.add_scraped_content(scraped_content)
        
        # Test search
        print("\nSearching for 'machine learning algorithms'...")
        results = vector_store.search("machine learning algorithms", k=3)
        
        for i, (doc, score) in enumerate(results):
            print(f"\nResult {i+1} (Score: {score:.3f}):")
            print(f"Source: {doc.source_url}")
            print(f"Text: {doc.text[:200]}...")
        
        # Print statistics
        stats = vector_store.get_statistics()
        print(f"\nVector Store Statistics:")
        for key, value in stats.items():
            print(f"{key}: {value}")
    
    asyncio.run(main())