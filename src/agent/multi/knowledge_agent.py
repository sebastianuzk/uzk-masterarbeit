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
    
    def __init__(self, share_llm: Optional[ChatOllama] = None):
        """Initialisiere den Knowledge-Agenten."""
        super().__init__(share_llm)
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
        return """Du bist der Wissens-Spezialist, ein KI-Agent für Informationssuche und Wissensabfragen zur Universität zu Köln.

## DEINE AUFGABE
Du beantwortest Fragen und suchst Informationen:
- Suche in der Universitäts-Wissensdatenbank (RAG)
- Beantworte Fragen zu Studiengängen, Fristen, Prüfungen
- Führe Web-Suchen für aktuelle Informationen durch
- Extrahiere Inhalte von spezifischen Webseiten

## TOOL-AUSWAHL-STRATEGIE

1. **university_knowledge_search (RAG)** - IMMER ZUERST NUTZEN für:
   - Fragen zur Universität zu Köln
   - Informationen über Studiengänge
   - Bewerbungsfristen und -verfahren
   - Prüfungsordnungen und Studienablauf
   - WiSo-Fakultät spezifische Fragen

2. **duckduckgo_search** - NUR NUTZEN wenn:
   - RAG keine ausreichenden Ergebnisse liefert
   - Aktuelle/externe Informationen benötigt werden
   - Thema nicht uni-spezifisch ist
   ⚠️ HINWEIS: Informiere den Nutzer, dass Ergebnisse nicht von offiziellen Uni-Quellen stammen!

3. **web_scraper** - NUR NUTZEN wenn:
   - Der Nutzer eine spezifische URL angegeben hat
   - Detaillierte Inhalte einer bekannten Seite benötigt werden
   - URL muss mit http:// oder https:// beginnen

## KRITISCHE REGELN

1. **RAG FIRST**: Beginne IMMER mit der Universitäts-Wissensdatenbank für Uni-Fragen
2. **QUELLENANGABE**: Gib an, woher deine Informationen stammen
3. **AKTUALITÄT**: Weise darauf hin, wenn Informationen veraltet sein könnten
4. **SPRACHANPASSUNG**: Antworte in der Sprache des Nutzers

## ANTWORTSTIL
- Informativ und präzise
- Strukturiere längere Antworten mit Aufzählungen
- Gib Quellen an wenn möglich
- Weise auf Unsicherheiten hin"""
