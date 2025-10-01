"""
Wikipedia Tool für den Autonomen Chatbot-Agenten
"""
import wikipedia
from langchain_core.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class WikipediaSearchInput(BaseModel):
    """Input für Wikipedia-Suche"""
    query: str = Field(description="Suchbegriff für Wikipedia")


class WikipediaTool(BaseTool):
    """Tool für Wikipedia-Suchen"""
    
    name: str = "wikipedia_search"
    description: str = """Nützlich für die Suche nach aktuellen Informationen in Wikipedia.
    Verwende dieses Tool, wenn du Fakten, Definitionen oder allgemeine Informationen 
    zu einem Thema benötigst."""
    args_schema: Type[BaseModel] = WikipediaSearchInput
    
    def _run(self, query: str) -> str:
        """Führe Wikipedia-Suche aus"""
        try:
            # Setze die Sprache auf Deutsch
            wikipedia.set_lang("de")
            
            # Suche nach dem Begriff
            summary = wikipedia.summary(query, sentences=3)
            return f"Wikipedia-Zusammenfassung für '{query}':\n{summary}"
            
        except wikipedia.exceptions.DisambiguationError as e:
            # Wenn mehrere Optionen verfügbar sind, verwende die erste
            try:
                summary = wikipedia.summary(e.options[0], sentences=3)
                return f"Wikipedia-Zusammenfassung für '{e.options[0]}':\n{summary}"
            except:
                return f"Mehrere Optionen gefunden für '{query}': {', '.join(e.options[:5])}"
                
        except wikipedia.exceptions.PageError:
            return f"Keine Wikipedia-Seite gefunden für '{query}'"
            
        except Exception as e:
            return f"Fehler bei der Wikipedia-Suche: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Asynchrone Ausführung (nicht implementiert)"""
        raise NotImplementedError("Asynchrone Ausführung nicht unterstützt")


def create_wikipedia_tool() -> WikipediaTool:
    """Factory-Funktion für das Wikipedia-Tool"""
    return WikipediaTool()