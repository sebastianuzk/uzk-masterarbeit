"""
RAG Tool für den Chatbot-Agent

Einfaches und robustes Tool für Retrieval-Augmented Generation.
Greift auf die vom Web-Scraper erstellte ChromaDB-Vectordatenbank zu.
"""

import os
from typing import Optional
from langchain.tools import BaseTool
from pydantic import Field

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
    """
    
    name: str = "university_knowledge_search"
    description: str = (
        "Durchsucht die Universitäts-Wissensdatenbank für Fragen zu "
        "Bewerbungen, Studiengängen, Fristen, Prüfungen, Fachsemestern "
        "und anderen Themen der Universität zu Köln / WiSo-Fakultät. "
        "Nutze dieses Tool für spezifische Uni-Fragen."
    )
    
    def _run(self, query: str) -> str:
        """
        Führt eine Suche in der Universitäts-Vectordatenbank durch.
        
        Args:
            query: Die Suchanfrage des Benutzers
            
        Returns:
            Relevante Informationen aus der Wissensdatenbank
        """
        try:
            # ChromaDB direkt importieren und verwenden
            import chromadb
            from pathlib import Path
            
            # Verbindung zur ChromaDB mit absolutem Pfad
            # Try both possible locations
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
                return (
                    f"❌ Universitäts-Wissensdatenbank nicht gefunden. "
                    f"Gesucht in: {', '.join(str(p) for p in vector_db_paths)}. "
                    f"Bitte stellen Sie sicher, dass die Daten vorher mit dem "
                    f"Web-Scraper erfasst wurden."
                )
            
            client = chromadb.PersistentClient(path=str(vector_db_path))
            
            # Alle verfügbaren Collections abrufen
            collections = client.list_collections()
            available_collections = [c.name for c in collections]
            
            if not available_collections:
                return (
                    f"❌ Keine Universitäts-Wissensdatenbank gefunden. "
                    f"Bitte stellen Sie sicher, dass die Daten vorher mit dem "
                    f"Web-Scraper erfasst wurden."
                )
            
            # Durchsuche alle verfügbaren Collections
            all_results = []
            searched_collections = []
            
            for collection_name in available_collections:
                try:
                    collection = client.get_collection(name=collection_name)
                    
                    # Suche in dieser Collection durchführen
                    results = collection.query(
                        query_texts=[query],
                        n_results=3
                    )
                    
                    if results['documents'] and results['documents'][0]:
                        # Ergebnisse mit Collection-Info erweitern
                        documents = results['documents'][0]
                        metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
                        distances = results['distances'][0] if results['distances'] else [0] * len(documents)
                        
                        for doc, metadata, distance in zip(documents, metadatas, distances):
                            # Erweitere Metadaten um Collection-Info
                            enhanced_metadata = metadata.copy() if metadata else {}
                            enhanced_metadata['collection'] = collection_name
                            
                            all_results.append({
                                'document': doc,
                                'metadata': enhanced_metadata,
                                'distance': distance
                            })
                    
                    searched_collections.append(collection_name)
                    
                except Exception as e:
                    print(f"Warnung: Fehler beim Zugriff auf Collection '{collection_name}': {str(e)}")
                    continue
            
            if not all_results:
                return (
                    f"❌ Keine relevanten Informationen zu '{query}' gefunden. "
                    f"Durchsuchte Collections: {searched_collections}. "
                    f"Möglicherweise sind noch keine Daten zu diesem Thema "
                    f"in der Universitäts-Wissensdatenbank verfügbar."
                )
            
            # Sortiere alle Ergebnisse nach Relevanz (niedrigere Distance = höhere Relevanz)
            all_results.sort(key=lambda x: x['distance'])
            
            # Nehme die besten Ergebnisse (maximal aus Hyperparametern)
            best_results = all_results[:RAG_SEARCH_RESULTS]
            
            # Ergebnisse formatieren
            formatted_results = []
            
            for i, result in enumerate(best_results, 1):
                doc = result['document']
                metadata = result['metadata']
                distance = result['distance']
                
                # Relevanz-Score (niedrigere Distance = höhere Relevanz)
                relevance = max(0, 1 - distance)
                
                # Nur Ergebnisse mit ausreichender Relevanz
                # Niedrigerer Schwellwert für bessere Recall mit sentence-transformers
                if relevance > 0.1:  # Angepasster Schwellwert
                    source_info = ""
                    collection_info = f" [aus: {metadata.get('collection', 'unbekannt')}]"
                    
                    if metadata:
                        title = metadata.get('title', '')
                        # Prüfe beide möglichen URL-Felder
                        source_url = metadata.get('source_url', '') or metadata.get('original_url', '') or metadata.get('url', '')
                        
                        if title and source_url:
                            source_info = f" (Quelle: {title} - {source_url})"
                        elif title:
                            source_info = f" (Quelle: {title})"
                        elif source_url:
                            source_info = f" (Quelle: {source_url})"
                    
                    formatted_results.append(
                        f"📄 **Information {i}**{source_info}{collection_info}:\n{doc.strip()}"
                    )
            
            if not formatted_results:
                return (
                    f"❌ Die gefundenen Informationen zu '{query}' sind nicht "
                    f"relevant genug. Versuchen Sie eine andere Formulierung "
                    f"oder allgemeinere Begriffe."
                )
            
            # Antwort zusammenstellen
            response = (
                f"🎓 **Informationen aus der Universitäts-Wissensdatenbank** "
                f"(durchsuchte Collections: {', '.join(searched_collections)}):\n\n"
                + "\n\n".join(formatted_results)
            )
            
            # Spezielle Hinweise für häufige Themen
            query_lower = query.lower()
            if any(keyword in query_lower for keyword in ['bewerbung', 'fachsemester', 'höher']):
                response += (
                    "\n\n💡 **Wichtiger Hinweis**: Bei Bewerbungen für höhere "
                    "Fachsemester sind oft spezielle Bescheinigungen vom "
                    "Prüfungsamt der WiSo-Fakultät erforderlich."
                )
            
            return response
            
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