"""
RAG Tool für den Chatbot-Agent

Modulares Tool für Retrieval-Augmented Generation mit konfigurierbaren Techniken.
Greift auf die vom Web-Scraper erstellte ChromaDB-Vectordatenbank zu.
"""

import os
from typing import Optional, List, Dict, Any
from langchain.tools import BaseTool
from pydantic import Field
from langsmith import traceable

# Import modular RAG techniques
from src.rag.config import RAGConfig
from src.rag.retrieval import (
    MultiCollectionSearch,
    ResultAggregation,
    DistanceToRelevanceConverter,
    GlobalReranker
)
from src.rag.post_retrieval import (
    RelevanceFilter,
    ResultFormatter,
    ContextHintGenerator,
    EmptyResultHandler
)

# Import hyperparameters
try:
    from src.scraper.hyperparameters import RAG_SEARCH_RESULTS
except ImportError:
    RAG_SEARCH_RESULTS = 5  # fallback


class UniversityRAGTool(BaseTool):
    """
    Tool für die Universitäts-Wissensdatenbank.
    
    Durchsucht die lokale ChromaDB nach relevanten Informationen
    zu Fragen rund um die Universität zu Köln.
    
    Verwendet modulare RAG-Techniken basierend auf RAGConfig.
    """
    
    name: str = "university_knowledge_search"
    description: str = (
        "Durchsucht die Universitäts-Wissensdatenbank für Fragen zu "
        "Bewerbungen, Studiengängen, Fristen, Prüfungen, Fachsemestern "
        "und anderen Themen der Universität zu Köln / WiSo-Fakultät. "
        "Nutze dieses Tool für spezifische Uni-Fragen."
    )
    
    # RAG configuration and techniques
    config: RAGConfig = Field(default_factory=RAGConfig.load_from_env)
    _multi_collection_search: Optional[MultiCollectionSearch] = None
    _result_aggregation: Optional[ResultAggregation] = None
    _distance_converter: Optional[DistanceToRelevanceConverter] = None
    _global_reranker: Optional[GlobalReranker] = None
    _relevance_filter: Optional[RelevanceFilter] = None
    _result_formatter: Optional[ResultFormatter] = None
    _context_hints: Optional[ContextHintGenerator] = None
    _empty_handler: Optional[EmptyResultHandler] = None
    
    def __init__(self, **data):
        """Initialize RAG tool with modular techniques."""
        super().__init__(**data)
        
        # Initialize retrieval techniques
        self._multi_collection_search = MultiCollectionSearch(
            enabled=self.config.use_multi_collection_search
        )
        self._result_aggregation = ResultAggregation(
            enabled=self.config.use_result_aggregation
        )
        self._distance_converter = DistanceToRelevanceConverter(
            enabled=self.config.use_distance_conversion
        )
        self._global_reranker = GlobalReranker(
            enabled=self.config.use_global_reranking
        )
        
        # Initialize post-retrieval techniques
        self._relevance_filter = RelevanceFilter(
            enabled=self.config.use_relevance_filtering,
            threshold=self.config.relevance_threshold
        )
        self._result_formatter = ResultFormatter(
            enabled=self.config.use_result_formatting
        )
        self._context_hints = ContextHintGenerator(
            enabled=self.config.use_context_hints
        )
        self._empty_handler = EmptyResultHandler(
            enabled=self.config.use_empty_result_handling
        )
    
    @traceable(run_type="retriever")
    def _retrieve_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        Führt eine Suche in der Universitäts-Vectordatenbank durch.
        Verwendet modulare Retrieval-Techniken basierend auf RAGConfig.
        
        Args:
            query: Die Suchanfrage des Benutzers
            
        Returns:
            Relevante Informationen aus der Wissensdatenbank
        """
        import chromadb
        from pathlib import Path
        
        # Verbindung zur ChromaDB
        vector_db_paths = [
            Path("data/vector_db").resolve(),
            Path("src/scraper/vector_db").resolve()
        ]
        
        vector_db_path = None
        for path in vector_db_paths:
            if path.exists():
                vector_db_path = path
                break
        
        if vector_db_path is None:
            return []
        
        client = chromadb.PersistentClient(path=str(vector_db_path))
        collections = client.list_collections()
        
        if not collections:
            return []
        
        # Retrieval Technique 1: Multi-Collection Search
        all_results = self._multi_collection_search.search(
            client=client,
            query=query,
            k_per_collection=self.config.k_per_collection
        )
        
        if not all_results:
            return []
        
        # Retrieval Technique 2: Distance to Relevance Conversion
        all_results = self._distance_converter.convert(all_results)
        
        # Retrieval Technique 3: Global Re-ranking
        all_results = self._global_reranker.rerank(all_results)
        
        # Retrieval Technique 4: Result Aggregation (Top-K Selection)
        top_results = self._result_aggregation.aggregate(
            results=all_results,
            top_k=self.config.top_k
        )
        
        # Konvertiere zu LangSmith-Format (WICHTIG für korrektes Tracing!)
        langsmith_docs = []
        for result in top_results:
            langsmith_docs.append({
                "page_content": result['document'],
                "type": "Document",
                "metadata": result['metadata']
            })
        
        return langsmith_docs
    
    def _run(self, query: str) -> str:
        """
        Führt eine Suche in der Universitäts-Vectordatenbank durch.
        Verwendet modulare Post-Retrieval-Techniken basierend auf RAGConfig.
        
        Args:
            query: Die Suchanfrage des Benutzers
            
        Returns:
            Relevante Informationen aus der Wissensdatenbank
        """
        try:
            # Dokumente abrufen (mit LangSmith Tracing via @traceable Decorator)
            retrieved_docs = self._retrieve_documents(query)
            
            # Konvertiere zurück zu internem Format für Post-Processing
            results = []
            for doc_dict in retrieved_docs:
                results.append({
                    'document': doc_dict.get('page_content', ''),
                    'metadata': doc_dict.get('metadata', {}),
                    'distance': doc_dict.get('metadata', {}).get('distance', 0)
                })
            
            # Post-Retrieval Technique 1: Relevance Filtering
            filtered_results = self._relevance_filter.filter(results)
            
            # Prüfe ob Ergebnisse vorhanden
            if not filtered_results:
                no_data = not results  # True wenn gar keine Daten, False wenn nur nicht relevant
                return self._empty_handler.handle_empty(query, no_data=no_data)
            
            # Post-Retrieval Technique 2: Result Formatting
            formatted_response, searched_collections = self._result_formatter.format(filtered_results)
            
            # Post-Retrieval Technique 3: Context Hints
            response_with_hints = self._context_hints.generate_hint(query, formatted_response)
            
            return response_with_hints
            
        except ImportError:
            return (
                "❌ ChromaDB ist nicht installiert. Bitte installieren Sie es mit: "
                "pip install chromadb"
            )
        except Exception as e:
            return (
                f"❌ Fehler beim Zugriff auf die Universitäts-Wissensdatenbank: {e}"
            )
    
    async def _arun(self, query: str) -> str:
        """Asynchrone Version - ruft die synchrone Version auf."""
        return self._run(query)


def create_university_rag_tool() -> UniversityRAGTool:
    """
    Erstellt ein neues RAG-Tool für die Universitäts-Wissensdatenbank.
    
    Returns:
        UniversityRAGTool: Konfiguriertes RAG-Tool
    """
    return UniversityRAGTool()


# Test-Funktion
def test_rag_tool():
    """Testet das RAG-Tool mit einer Beispiel-Anfrage."""
    print("🧪 Teste Universitäts-RAG-Tool...")
    print("=" * 60)
    
    tool = create_university_rag_tool()
    test_query = "Was benötige ich für die Bewerbung auf ein höheres Fachsemester?"
    
    print(f"📝 Test-Anfrage: {test_query}")
    print("-" * 60)
    
    result = tool._run(test_query)
    print(result)
    
    print("-" * 60)
    print("✅ Test abgeschlossen")


if __name__ == "__main__":
    test_rag_tool()
