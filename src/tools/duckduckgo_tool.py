"""
DuckDuckGo Search Tool für den Autonomen Chatbot-Agenten
"""
from duckduckgo_search import DDGS
from langchain_core.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class DuckDuckGoSearchInput(BaseModel):
    """Input für DuckDuckGo-Suche"""
    query: str = Field(description="Suchbegriff für DuckDuckGo Web Search")


class DuckDuckGoTool(BaseTool):
    """Tool für DuckDuckGo Web Search"""
    
    name: str = "duckduckgo_search"
    description: str = """Nützlich für die Suche nach aktuellen Informationen im Internet.
    Verwende dieses Tool für aktuelle Nachrichten, Ereignisse oder wenn Wikipedia 
    nicht ausreichend ist. Vollständig Open Source und privatsphärefreundlich."""
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput
    
    def _run(self, query: str) -> str:
        """Führe DuckDuckGo-Suche aus"""
        try:
            # Führe Suche aus
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
            
            if not results:
                return f"Keine Suchergebnisse gefunden für '{query}'"
            
            # Formatiere Ergebnisse
            formatted_results = []
            for result in results:
                title = result.get('title', 'Unbekannter Titel')
                body = result.get('body', '')
                href = result.get('href', '')
                
                # Begrenze Inhalt
                if len(body) > 300:
                    body = body[:300] + "..."
                
                formatted_results.append(f"**{title}**\n{body}\nQuelle: {href}\n")
            
            return f"DuckDuckGo-Suchergebnisse für '{query}':\n\n" + "\n".join(formatted_results)
            
        except Exception as e:
            return f"Fehler bei der DuckDuckGo-Suche: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Asynchrone Ausführung (nicht implementiert)"""
        raise NotImplementedError("Asynchrone Ausführung nicht unterstützt")


def create_duckduckgo_tool() -> DuckDuckGoTool:
    """Factory-Funktion für das DuckDuckGo-Tool"""
    return DuckDuckGoTool()