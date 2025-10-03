"""
DuckDuckGo Search Tool für den Autonomen Chatbot-Agenten
"""
from ddgs import DDGS
from langchain_core.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
from urllib.parse import urlparse
import re

search_max_k: int = 10  # Maximale Anzahl der Suchergebnisse des DuckDuckGo-Tools
search_max_len: int = 300  # Maximale Länge des Snippets pro Suchergebnis
search_max_tail: int = 200  # Maximale Verlängerung über min_len hinaus, um Satzende zu finden
search_min_len: int = 200  # Minimale Länge des Snippets pro Suchergebnis


class WebSearchResult(BaseModel):
    """Ergebnis einer Web-Suche"""
    titel: str = Field(description="Titel der Website")
    snippet: str = Field(description="Zusammenfassung der Website")
    domain: str = Field(description="Domain der Website")
    url: str = Field(description="URL der Website")
    
    def __str__(self) -> str:
        """String-Repräsentation des Suchergebnisses"""
        return f"**{self.titel}**\n{self.snippet}\nDomain: {self.domain}\nURL: {self.url}\n"


class DuckDuckGoSearchInput(BaseModel):
    """Input für DuckDuckGo-Suche"""
    query: str = Field(description="Suchbegriff für DuckDuckGo Web Search")


class DuckDuckGoTool(BaseTool):
    """Tool für DuckDuckGo Web Search"""
    
    name: str = "duckduckgo_search"
    description: str = ("Nutze dieses Tool, um das Web zu durchsuchen, falls du keine relevanten Informationen zur Beantwortung der Frage findest. "
                        "Bei der Wiedergabe der Suchergebnisse solltest du die relevantesten und vertrauenswürdigsten Quellen priorisieren und immer einen Link zur Quelle angeben. "
                        "Für Quellenangaben verwende bitte die vollständige URLs aus den Suchergebnissen. "
                        "In jedem Fall musst du den Nutzer explizit darauf aufmerksam machen, dass die Informationen möglicherweise nicht von der Universität zu Köln stammen und nicht aktuell sind. "
    )
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput
    
    def _run(self, query: str) -> str:
        """Führe DuckDuckGo-Suche aus"""
        try:
            # Führe Suche aus
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=search_max_k))
            
            if not results:
                return f"Keine Suchergebnisse gefunden für '{query}'"
            
            # Erstelle Liste von WebSearchResult-Objekten
            formatted_results: List[WebSearchResult] = []
            for result in results:
                titel = result.get('title', 'Unbekannter Titel')
                url = result.get('href', '')
                snippet = result.get('body', '')
                domain = result.get('domain', '')


                # Extrahiere Domain aus URL
                try:
                    parsed_url = urlparse(url)
                    if "uni-koeln" in parsed_url.netloc:
                        domain = "Universität zu Köln"
                    else:
                        domain = "Externe Quelle: " + parsed_url.netloc
                except:
                    domain = 'Unknown Domain'
                

                # Begrenze Snippet-Länge
                if len(snippet) > search_max_len:
                    snippet = trim_snippet(snippet)

                                                    
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

def trim_snippet(text: str, min_len: int = search_min_len, max_tail: int = search_max_tail) -> str:
    """
    Schneidet Text so, dass er mindestens min_len umfasst und dann
    bis zum nächsten Satzende (., !, ?, …) verlängert.
    max_tail begrenzt, wie weit wir höchstens weiterlaufen, falls kein Satzende kommt.
    """
    if len(text) <= min_len:
        return text

    # Suche Satzende ab min_len
    # Satzende-Heuristik: ., !, ?, …, ggf. gefolgt von schließenden Anführungszeichen/Klammern
    # und dann Leerraum/Zeilenende.
    pattern = re.compile(r'[\.!?…](?:[\'")\]]+)?(?=\s|$)')
    m = pattern.search(text, pos=min_len, endpos=min(len(text), min_len + max_tail))

    if m:
        return text[:m.end()].rstrip()
    else:
        # Kein eindeutiges Satzende im erlaubten Fenster → hart begrenzen
        return text[:min_len].rstrip() + "…"


def create_duckduckgo_tool() -> DuckDuckGoTool:
    """Factory-Funktion für das DuckDuckGo-Tool"""
    return DuckDuckGoTool()