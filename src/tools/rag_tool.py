"""
RAG Tool für den Chatbot-Agent

Einfaches und robustes Tool für Retrieval-Augmented Generation.
Greift auf die vom Web-Scraper erstellte ChromaDB-Vectordatenbank zu.
"""

import os
from typing import Optional
from langchain.tools import BaseTool
from pydantic import Field


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
            
            # Verbindung zur ChromaDB
            client = chromadb.PersistentClient(path="src/scraper/output/vector_db")
            
            try:
                collection = client.get_collection(name="verbesserte_suche")
            except Exception:
                return (
                    "❌ Die Universitäts-Wissensdatenbank ist nicht verfügbar. "
                    "Bitte stellen Sie sicher, dass die Daten vorher mit dem "
                    "Web-Scraper erfasst wurden."
                )
            
            # Suche durchführen
            results = collection.query(
                query_texts=[query],
                n_results=3
            )
            
            if not results['documents'] or not results['documents'][0]:
                return (
                    f"❌ Keine relevanten Informationen zu '{query}' gefunden. "
                    f"Möglicherweise sind noch keine Daten zu diesem Thema "
                    f"in der Universitäts-Wissensdatenbank verfügbar."
                )
            
            # Ergebnisse formatieren
            formatted_results = []
            documents = results['documents'][0]
            metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(documents)
            distances = results['distances'][0] if results['distances'] else [0] * len(documents)
            
            for i, (doc, metadata, distance) in enumerate(zip(documents, metadatas, distances), 1):
                # Relevanz-Score (niedrigere Distance = höhere Relevanz)
                relevance = max(0, 1 - distance)
                
                # Nur Ergebnisse mit ausreichender Relevanz
                if relevance > 0.3:  # Schwellwert für deutsche Texte
                    source_info = ""
                    if metadata:
                        source_url = metadata.get('source_url', '')
                        title = metadata.get('title', '')
                        if title:
                            source_info = f" (Quelle: {title})"
                        elif source_url:
                            source_info = f" (Quelle: {source_url})"
                    
                    formatted_results.append(
                        f"📄 **Information {i}**{source_info}:\n{doc.strip()}"
                    )
            
            if not formatted_results:
                return (
                    f"❌ Die gefundenen Informationen zu '{query}' sind nicht "
                    f"relevant genug. Versuchen Sie eine andere Formulierung "
                    f"oder allgemeinere Begriffe."
                )
            
            # Antwort zusammenstellen
            response = (
                f"🎓 **Informationen aus der Universitäts-Wissensdatenbank:**\n\n"
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