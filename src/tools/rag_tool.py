"""
RAG Tool für den Chatbot-Agent

Naives RAG-Tool für Retrieval-Augmented Generation.
Greift auf die vom Web-Scraper erstellte ChromaDB-Vectordatenbank zu.

Modular erweiterbar mit Advanced RAG Techniken aus src.advanced_rag.
Die Techniken werden optional geladen, basierend auf RAGConfig.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from langchain.tools import BaseTool
from pydantic import Field
from langsmith import traceable

logger = logging.getLogger(__name__)

# Import RAG Configuration
try:
    from src.advanced_rag.rag_config import RAGConfig
    CONFIG_AVAILABLE = True
except ImportError:
    logger.warning("RAGConfig nicht gefunden - verwende naive RAG")
    CONFIG_AVAILABLE = False
    RAGConfig = None

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
    
    Naives RAG standardmäßig, optional erweiterbar mit Advanced-Techniken.
    """
    
    name: str = "university_knowledge_search"
    description: str = (
        "Durchsucht die Universitäts-Wissensdatenbank für Fragen zu "
        "Bewerbungen, Studiengängen, Fristen, Prüfungen, Fachsemestern "
        "und anderen Themen der Universität zu Köln / WiSo-Fakultät. "
        "Nutze dieses Tool für spezifische Uni-Fragen."
    )
    
    # Configuration (optional)
    config: Optional[Any] = None
    
    # Advanced technique flags
    _use_advanced: bool = False
    _advanced_available: bool = False
    
    def __init__(self, **data):
        """Initialize RAG tool with optional advanced techniques."""
        super().__init__(**data)
        
        # Wenn config übergeben wurde, nutze es
        if self.config is not None:
            self._use_advanced = self._should_use_advanced()
            logger.info(f"RAG-Tool initialisiert mit übergebener Config (Advanced: {self._use_advanced})")
        # Sonst: Load configuration from env
        elif CONFIG_AVAILABLE and RAGConfig is not None:
            try:
                self.config = RAGConfig.load_from_env()
                self._use_advanced = self._should_use_advanced()
                logger.info(f"RAG-Tool initialisiert (Advanced: {self._use_advanced})")
            except Exception as e:
                logger.warning(f"Fehler beim Laden der RAG-Config: {e}")
                self.config = None
                self._use_advanced = False
        else:
            logger.info("RAG-Tool initialisiert (Naive RAG)")
    
    def _should_use_advanced(self) -> bool:
        """Prüfe ob Advanced-Techniken aktiviert sind."""
        if not self.config:
            return False
        
        # Baseline-Modus = Naive = Kein Advanced
        return not self.config.baseline_enabled
    
    @traceable(run_type="retriever")
    def _naive_retrieve(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Naives RAG: Einfache Vektorsuche in ChromaDB.
        
        Args:
            query: Die Suchanfrage
            k: Anzahl der Ergebnisse
            
        Returns:
            Liste von Dokumenten mit Metadaten
        """
        import chromadb
        from pathlib import Path
        
        # Verbindung zur ChromaDB
        # WICHTIG: Relative Paths benutzen! ChromaDB hat Bug mit absoluten Windows-Pfaden
        vector_db_paths = [
            "data/vector_db",
            "src/scraper/vector_db"
        ]
        
        vector_db_path = None
        for path_str in vector_db_paths:
            if Path(path_str).exists():
                vector_db_path = path_str
                break
        
        if vector_db_path is None:
            return []
        
        client = chromadb.PersistentClient(path=vector_db_path)
        
        # WORKAROUND für ChromaDB Bug: list_collections() Iterator verursacht
        # "Error loading hnsw index" bei großen Collections (41k+ chunks).
        # Lösung: Collection-Namen einzeln holen statt Iterator
        collection_names = [coll.name for coll in client.list_collections()]
        
        if not collection_names:
            return []
        
        # NAIVE: Durchsuche ALLE Collections unabhängig (als wäre es eine große Collection)
        # Im echten Naive-Ansatz würde beim Indexing alles in eine Collection geschrieben
        documents = []
        
        for name in collection_names:
            collection = client.get_collection(name)
            
            try:
                # Suche in jeder Collection
                results = collection.query(
                    query_texts=[query],
                    n_results=min(k, 10)  # Max 10 pro Collection
                )
                
                # Konvertiere Ergebnisse
                if results and results['documents'] and results['documents'][0]:
                    for i, doc in enumerate(results['documents'][0]):
                        # Format für Naive RAG (Backward compatibility)
                        doc_dict = {
                            'page_content': doc,
                            'type': 'Document',
                            'metadata': {}
                        }
                        
                        # Format für Advanced RAG (neue Felder)
                        doc_dict['id'] = results['ids'][0][i] if results.get('ids') else f"doc_{i}"
                        doc_dict['document'] = doc  # Alias für Advanced-Techniken
                        doc_dict['collection'] = name  # Collection-Name
                        
                        # Füge Metadaten hinzu
                        if results.get('metadatas') and results['metadatas'][0]:
                            doc_dict['metadata'] = results['metadatas'][0][i] or {}
                        
                        # Füge Distance hinzu (wichtig für Sorting!)
                        if results.get('distances') and results['distances'][0]:
                            doc_dict['distance'] = results['distances'][0][i]
                            doc_dict['metadata']['distance'] = results['distances'][0][i]
                        
                        documents.append(doc_dict)
            except Exception as e:
                logger.warning(f"Fehler bei Collection {name}: {e}")
                continue
        
        # Naive: Einfach nach Distance sortieren und top-k nehmen
        documents.sort(key=lambda x: x.get('distance', float('inf')))
        return documents[:k]
    
    def _run(self, query: str) -> str:
        """
        Führt eine Suche in der Universitäts-Vectordatenbank durch.
        
        Args:
            query: Die Suchanfrage des Benutzers
            
        Returns:
            Relevante Informationen aus der Wissensdatenbank
        """
        try:
            # Bestimme k basierend auf Config oder Default
            k = self.config.top_k if self.config else RAG_SEARCH_RESULTS
            
            # Naive Retrieval (immer)
            documents = self._naive_retrieve(query, k=k)
            
            if not documents:
                return (
                    "ℹ️ Keine relevanten Informationen in der Universitäts-Wissensdatenbank gefunden. "
                    "Möglicherweise ist die Datenbank leer oder Ihre Anfrage konnte nicht zugeordnet werden."
                )
            
            # Wenn Advanced-Techniken verfügbar und aktiviert sind
            if self._use_advanced and self.config:
                return self._advanced_process(query, documents)
            
            # Naive Ausgabe: Einfache Formatierung
            return self._format_naive_results(documents)
            
        except ImportError:
            return (
                "❌ ChromaDB ist nicht installiert. Bitte installieren Sie es mit: "
                "pip install chromadb"
            )
        except Exception as e:
            logger.error(f"Fehler beim RAG-Tool: {e}", exc_info=True)
            return (
                f"❌ Fehler beim Zugriff auf die Universitäts-Wissensdatenbank: {e}"
            )
    
    def _format_naive_results(self, documents: List[Dict[str, Any]]) -> str:
        """
        Naive Formatierung der Ergebnisse.
        
        Args:
            documents: Liste von Dokumenten
            
        Returns:
            Formatierter String
        """
        if not documents:
            return "Keine Ergebnisse gefunden."
        
        response_parts = ["📚 Informationen aus der Universitäts-Wissensdatenbank:\n"]
        
        for i, doc in enumerate(documents, 1):
            content = doc.get('page_content', '')
            metadata = doc.get('metadata', {})
            
            response_parts.append(f"\n{i}. {content[:500]}...")
            
            # Füge Quelle hinzu wenn vorhanden
            if 'source' in metadata:
                response_parts.append(f"   (Quelle: {metadata['source']})")
        
        return "\n".join(response_parts)
    
    def _advanced_process(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Verarbeite Ergebnisse mit Advanced-Techniken.
        
        Args:
            query: Die ursprüngliche Anfrage
            documents: Liste von Dokumenten (von _naive_retrieve)
            
        Returns:
            Verarbeiteter Response-String mit allen Advanced-Techniken
        """
        from src.advanced_rag.retrieval import (
            DistanceConverter,
            ResultAggregator,
            GlobalReranker
        )
        from src.advanced_rag.post_retrieval import (
            RelevanceFilter,
            ResultFormatter,
            ContextHintProvider,
            EmptyResultHandler
        )
        
        logger.info("Verwende Advanced RAG-Techniken")
        
        # Merke ob wir Ergebnisse vor Filterung hatten
        had_results = len(documents) > 0
        
        # 1. Distance → Relevance Conversion
        if self.config.use_distance_conversion:
            converter = DistanceConverter()
            documents = converter.convert(documents)
            logger.debug("✓ Distance Conversion angewendet")
        
        # 2. Result Aggregation (deduplizieren + sortieren)
        if self.config.use_result_aggregation:
            aggregator = ResultAggregator(top_k=self.config.top_k)
            documents = aggregator.deduplicate(documents)
            documents = aggregator.aggregate(documents, sort_by='relevance')
            logger.debug("✓ Result Aggregation angewendet")
        
        # 3. Global Re-Ranking
        if self.config.use_global_reranking:
            reranker = GlobalReranker(use_relevance=True)
            documents = reranker.rerank(documents)
            # Optional: Diversity-Penalty
            documents = reranker.apply_diversity_penalty(documents, max_per_source=2)
            logger.debug("✓ Global Re-Ranking angewendet")
        
        # 4. Relevance Filtering
        if self.config.use_relevance_filtering:
            relevance_filter = RelevanceFilter(threshold=self.config.relevance_threshold)
            documents = relevance_filter.filter(documents)
            logger.debug(f"✓ Relevance Filtering angewendet (Threshold: {self.config.relevance_threshold})")
        
        # 5. Prüfe ob noch Ergebnisse vorhanden
        if not documents:
            if self.config.use_empty_result_handling:
                handler = EmptyResultHandler()
                return handler.handle_empty_results(
                    query=query,
                    had_results_before_filtering=had_results,
                    relevance_threshold=self.config.relevance_threshold
                )
            else:
                return "ℹ️ Keine relevanten Informationen gefunden."
        
        # 6. Result Formatting
        if self.config.use_result_formatting:
            formatter = ResultFormatter(include_metadata=True, include_sources=True)
            formatted = formatter.format(documents, query=query)
            logger.debug("✓ Result Formatting angewendet")
        else:
            # Fallback: Kompakte Formatierung
            formatted = "\n\n".join([doc.get('document', '') for doc in documents])
        
        # 7. Context Hints
        if self.config.use_context_hints:
            hint_provider = ContextHintProvider()
            formatted = hint_provider.add_hints(formatted, query=query, results=documents)
            logger.debug("✓ Context Hints hinzugefügt")
        
        logger.info("Advanced RAG-Pipeline abgeschlossen")
        return formatted
    
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
