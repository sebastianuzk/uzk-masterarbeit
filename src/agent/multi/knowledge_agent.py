"""
Knowledge Agent - Spezialisierter Agent für Wissensabfragen.

Verantwortlich für:
- RAG-basierte Suche in der Universitäts-Wissensdatenbank
- Web-Suche über DuckDuckGo
- Web-Scraping spezifischer URLs
"""

from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from config.settings import settings
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.web_scraper_tool import create_web_scraper_tool

from .base_agent import BaseSpecializedAgent


class KnowledgeAgent(BaseSpecializedAgent):
    """
    Spezialisierter Agent für Wissensabfragen und Informationssuche.
    
    Dieser Agent bearbeitet alle Anfragen, die Wissen über die
    Universität, Studiengänge, Fristen und allgemeine Informationen
    erfordern.
    """
    
    def __init__(self, shared_llm: Optional[ChatOllama] = None):
        """Initialisiere den Knowledge-Agenten."""
        super().__init__(shared_llm)
        print(f"✅ {self.name} initialisiert mit {len(self.tools)} Tools")
    
    @property
    def name(self) -> str:
        return "Wissens-Agent"
    
    @property
    def description(self) -> str:
        return (
            "Spezialisiert auf Wissensabfragen und Informationssuche: "
            "Universitäts-Wissensdatenbank (RAG), allgemeine Fragen zu Studiengängen, "
            "Fristen, Prüfungen, Web-Suche für aktuelle Informationen, "
            "Web-Scraping für spezifische Webseiten. "
            "Nutze diesen Agenten für Fragen über die Universität, "
            "Studiengänge, Bewerbungsfristen oder wenn externe Informationen benötigt werden."
        )
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle alle Wissens-Tools."""
        tools = []
        
        # RAG-Tool für Universitäts-Wissensdatenbank
        try:
            rag_tool = create_university_rag_tool()
            tools.append(rag_tool)
            print("  ✅ Universitäts-RAG-Tool geladen")
        except Exception as e:
            print(f"  ⚠️  RAG-Tool konnte nicht geladen werden: {e}")
        
        # DuckDuckGo-Suche
        if settings.ENABLE_DUCKDUCKGO:
            try:
                ddg_tool = create_duckduckgo_tool()
                tools.append(ddg_tool)
                print("  ✅ DuckDuckGo-Tool geladen")
            except Exception as e:
                print(f"  ⚠️  DuckDuckGo-Tool konnte nicht geladen werden: {e}")
        
        # Web-Scraper
        if settings.ENABLE_WEB_SCRAPER:
            try:
                scraper_tool = create_web_scraper_tool()
                tools.append(scraper_tool)
                print("  ✅ Web-Scraper-Tool geladen")
            except Exception as e:
                print(f"  ⚠️  Web-Scraper-Tool konnte nicht geladen werden: {e}")
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt für den Knowledge-Agenten."""
        return """Du bist der Wissens-Spezialist, ein KI-Agent für Informationssuche und Wissensabfragen.

## KRITISCHE REGEL: IMMER EIN TOOL AUFRUFEN

⚠️ Du MUSST bei jeder Anfrage mindestens ein Tool aufrufen! Antworte NIEMALS ohne Tool-Aufruf.

## TOOL-AUSWAHL

### 1. duckduckgo_search - NUTZEN BEI EXPLIZITEN SUCH-KEYWORDS:
   Wenn der Nutzer eines dieser Wörter/Phrasen verwendet → duckduckgo_search:
   - Deutsch: "im Internet", "online", "im Web", "google", "such im Netz"
   - Deutsch: "Suche nach", "Such nach", "Suche im Internet"
   - English: "Search for", "search online", "look up", "find online", "google"
   - Aktuelle Infos: "aktuelle Nachrichten", "neuesten News", "current news"
   
### 2. university_knowledge_search (RAG) - STANDARD für Uni-Fragen:
   Für alle anderen Fragen zur Universität:
   - Fragen zur Uni Köln, WiSo-Fakultät, KLIPS2
   - Prüfungsordnungen, Studienablauf, interne Prozesse
   - Studiengänge, Bewerbungen, Fristen
   - DIES IST DAS BEVORZUGTE TOOL wenn keine expliziten Internet-Keywords

### 3. web_scraper - NUR bei konkreten URLs:
   - Wenn eine URL mit http:// oder https:// genannt wird
   - "Inhalt von [URL]", "Lies die Seite [URL]"

## ENTSCHEIDUNGSLOGIK

1. Beginnt mit "Search for" oder "Suche nach/im Internet"? → duckduckgo_search
2. Hat der Nutzer eine URL genannt? → web_scraper  
3. Sonst (Uni-Fragen ohne Such-Keywords) → university_knowledge_search

## BEISPIELE

"Search for University of Cologne requirements" → duckduckgo_search
"Suche im Internet nach Bewerbungsfristen" → duckduckgo_search
"Such online nach Öffnungszeiten" → duckduckgo_search
"Wann sind die Bewerbungsfristen?" → university_knowledge_search
"Wie funktioniert KLIPS?" → university_knowledge_search
"Zeig mir https://example.com" → web_scraper

## SPRACHANPASSUNG
Antworte in der Sprache des Nutzers."""
