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
search_max_len: int = 500  # Maximale Länge des Snippets pro Suchergebnis
search_max_tail: int = 300  # Maximale Verlängerung über min_len hinaus, um Satzende zu finden
search_min_len: int = 300  # Minimale Länge des Snippets pro Suchergebnis


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
    description: str = ("Nutze dieses Tool, um nicht-spezifische Fragen über die Universität zu Köln zu beantworten. "
                        "Das Tool durchsucht das Internet nach relevanten und aktuellen Informationen zu deiner Anfrage. "
                        "Bei der Wiedergabe der Suchergebnisse priorisiere die relevantesten und vertrauenswürdigsten Quellen. "
                        "Gib immer die vollständigen URLs aus den Suchergebnissen als Quellenangaben an. "
                        "Wichtig: Weise den Nutzer darauf hin, dass externe Informationen möglicherweise nicht von der Universität zu Köln stammen.")
    args_schema: Type[BaseModel] = DuckDuckGoSearchInput
    
    def _run(self, query: str) -> str:
        """Führe DuckDuckGo-Suche aus"""
        try:
            # Führe Suche aus
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=search_max_k, safesearch="off"))
            
            print(f"\n🔍 DUCKDUCKGO TOOL DEBUG:")
            print(f"📝 Query: '{query}'")
            print(f"📊 Raw Results Count: {len(results)}")
            
            if not results:
                print("❌ Keine Suchergebnisse erhalten")
                return f"Keine Suchergebnisse gefunden für '{query}'"
            
            # Debug: Zeige erste raw results
            print(f"\n📋 First Raw Result Sample:")
            if results:
                first_result = results[0]
                print(f"  Title: {first_result.get('title', 'N/A')[:100]}")
                print(f"  URL: {first_result.get('href', 'N/A')}")
                print(f"  Body Length: {len(first_result.get('body', ''))}")
                print(f"  Body Sample: {first_result.get('body', '')[:150]}...")
            
            # Erstelle Liste von WebSearchResult-Objekten
            formatted_results: List[WebSearchResult] = []
            for i, result in enumerate(results):
                titel = result.get('title', 'Unbekannter Titel')
                url = result.get('href', '')
                snippet = result.get('body', '')
                
                # Debug für jeden Result
                if i < 3:  # Zeige Details für die ersten 3 Results
                    print(f"\n🔄 Processing Result {i+1}:")
                    print(f"  Original Title: {titel[:80]}")
                    print(f"  Original Snippet Length: {len(snippet)}")
                    print(f"  URL: {url}")
                
                # Extrahiere Domain aus URL
                try:
                    parsed_url = urlparse(url)
                    if "uni-koeln" in parsed_url.netloc:
                        domain = "Universität zu Köln"
                    else:
                        domain = "Externe Quelle: " + parsed_url.netloc
                except Exception:
                    domain = 'Unknown Domain'
                

                # Begrenze Snippet-Länge
                original_snippet_len = len(snippet)
                if len(snippet) > search_max_len:
                    snippet = trim_snippet(snippet)

                # Debug für Snippet-Verarbeitung
                if i < 3:
                    print(f"  Domain: {domain}")
                    print(f"  Snippet: {original_snippet_len} -> {len(snippet)} chars")
                    print(f"  Processed Snippet: {snippet[:100]}...")
                                                    
                # Erstelle WebSearchResult-Objekt
                search_result = WebSearchResult(
                    titel=titel,
                    url=url,
                    snippet=snippet,
                    domain=domain
                )
                formatted_results.append(search_result)
            
            # Formatiere Ausgabe
            print(f"\n✅ FINAL RESULTS:")
            print(f"📊 Formatted Results Count: {len(formatted_results)}")
            print(f"📏 Total Output Length: {sum(len(str(result)) for result in formatted_results)} chars")
            
            result_strings = [str(result) for result in formatted_results]
            final_output = f"DuckDuckGo-Suchergebnisse für '{query}':\n\n" + "\n".join(result_strings)
            
            print(f"🎯 Final Output Length: {len(final_output)} chars")
            print(f"🔚 DEBUG END\n")
            
            return final_output
            
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