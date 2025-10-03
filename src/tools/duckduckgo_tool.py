"""
DuckDuckGo Search Tool für den Autonomen Chatbot-Agenten
"""
from ddgs import DDGS
from langchain_core.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
from urllib.parse import urlparse


class WebSearchResult(BaseModel):
    """Ergebnis einer Web-Suche"""
    titel: str = Field(description="Titel der Website")
    url: str = Field(description="URL der Website")
    snippet: str = Field(description="Zusammenfassung der Website")
    domain: str = Field(description="Domain der Website")
    
    def __str__(self) -> str:
        """String-Repräsentation des Suchergebnisses"""
        return f"**{self.titel}**\n{self.snippet}\nDomain: {self.domain}\nQuelle: {self.url}\n"


class DuckDuckGoSearchInput(BaseModel):
    """Input für DuckDuckGo-Suche"""
    query: str = Field(description="Suchbegriff für DuckDuckGo Web Search")


class DuckDuckGoTool(BaseTool):
    """Tool für DuckDuckGo Web Search"""
    
    name: str = "duckduckgo_search"
    description: str = """Nutze dieses Tool, um das Web zu durchsuchen und aktuelle Informationen zur Universität zu Köln, oder einer ihrer Fakultäten zu finden. 
    Achte dabei darauf, dass nur Seiten welche 'uni-koeln.de' enthalten tatsächlich hierfür relevant sein könnten.
    
    Falls du keine relevanten Informationen zur Beantwortung der Frage findest, kannst du auch andere Webseiten hinzuziehen.
    Allerdings musst du in diesem Fall den Nutzer darauf aufmerksam machen, dass die Informationen nicht von der Universität zu Köln stammen.
    
    In jedem Fall sollen nur Informationen genutzt werden, welche tatsächlich zur Beantwortung der Frage relevant sind"""
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput
    
    def _run(self, query: str) -> str:
        """Führe DuckDuckGo-Suche aus"""
        try:
            # Führe Suche aus
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            
            if not results:
                return f"Keine Suchergebnisse gefunden für '{query}'"
            
            # Erstelle Liste von WebSearchResult-Objekten
            formatted_results: List[WebSearchResult] = []
            for result in results:
                print("Result: ", result.keys())
                titel = result.get('title', 'Unbekannter Titel')
                url = result.get('href', '')
                snippet = result.get('body', '')
                domain = result.get('domain', '')
                
                # Begrenze Snippet-Länge
                if len(snippet) > 300:
                    snippet = snippet[:300] + "..."
                
                
                # Erstelle WebSearchResult-Objekt
                search_result = WebSearchResult(
                    titel=titel,
                    url=url,
                    snippet=snippet,
                    domain=domain,
                    safesearch="on"
                )
                formatted_results.append(search_result)
            
            # Formatiere Ausgabe
            result_strings = [str(result) for result in formatted_results]
            return f"DuckDuckGo-Suchergebnisse für '{query}':\n\n" + "\n".join(result_strings)
            
        except Exception as e:
            return f"Fehler bei der DuckDuckGo-Suche: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Asynchrone Ausführung (nicht implementiert)"""
        raise NotImplementedError("Asynchrone Ausführung nicht unterstützt")


def create_duckduckgo_tool() -> DuckDuckGoTool:
    """Factory-Funktion für das DuckDuckGo-Tool"""
    return DuckDuckGoTool()