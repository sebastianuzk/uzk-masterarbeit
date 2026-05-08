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

from config.logging_config import get_logger
from config.settings import settings
from src.agent.tool_loader import load_tool_safely
from src.tools.duckduckgo_tool import create_duckduckgo_tool
from src.tools.rag_tool import create_university_rag_tool
from src.tools.web_scraper_tool import create_web_scraper_tool

from .base_agent import BaseSpecializedAgent

logger = get_logger(__name__)


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
        logger.info(f"✅ {self.name} initialisiert mit {len(self.tools)} Tools")
    
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
        rag_tool = load_tool_safely(create_university_rag_tool, "Universitäts-RAG") if settings.ENABLE_RAG_TOOL else None
        if rag_tool:
            tools.append(rag_tool)
        
        # DuckDuckGo-Suche (nur wenn aktiviert)
        if settings.ENABLE_DUCKDUCKGO:
            ddg_tool = load_tool_safely(create_duckduckgo_tool, "DuckDuckGo")
            if ddg_tool:
                tools.append(ddg_tool)
        else:
            logger.debug("DuckDuckGo-Tool deaktiviert (RAG-Evaluation-Modus)")
        
        # Web-Scraper (nur wenn aktiviert)
        if settings.ENABLE_WEB_SCRAPER:
            scraper_tool = load_tool_safely(create_web_scraper_tool, "Web-Scraper")
            if scraper_tool:
                tools.append(scraper_tool)
        else:
            logger.debug("Web-Scraper-Tool deaktiviert (RAG-Evaluation-Modus)")
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt für den Knowledge-Agenten (dynamisch basierend auf verfügbaren Tools)."""
        # Sammle verfügbare Tool-Namen
        available_tool_names = {tool.name for tool in self.tools}
        
        has_rag = "university_knowledge_search" in available_tool_names
        has_duckduckgo = "duckduckgo_search" in available_tool_names
        has_scraper = "web_scraper" in available_tool_names
        
        # Basis-Prompt
        prompt = """Du bist der Wissens-Spezialist, ein KI-Agent für Informationssuche und Wissensabfragen.

## KRITISCHE REGEL: IMMER EIN TOOL AUFRUFEN

⚠️ Du MUSST bei jeder Anfrage mindestens ein Tool aufrufen! Antworte NIEMALS ohne Tool-Aufruf.

## TOOL-AUSWAHL
"""
        
        # Dynamische Tool-Beschreibungen basierend auf verfügbaren Tools
        tool_count = 1
        examples = []
        decision_logic = []
        
        if has_duckduckgo:
            prompt += f"""
### {tool_count}. duckduckgo_search - NUTZEN BEI EXPLIZITEN SUCH-KEYWORDS:
   Wenn der Nutzer eines dieser Wörter/Phrasen verwendet → duckduckgo_search:
   - Deutsch: "im Internet", "online", "im Web", "google", "such im Netz"
   - Deutsch: "Suche nach", "Such nach", "Suche im Internet"
   - English: "Search for", "search online", "look up", "find online", "google"
   - Aktuelle Infos: "aktuelle Nachrichten", "neuesten News", "current news"
"""
            tool_count += 1
            examples.extend([
                '"Search for University of Cologne requirements" → duckduckgo_search',
                '"Suche im Internet nach Bewerbungsfristen" → duckduckgo_search',
                '"Such online nach Öffnungszeiten" → duckduckgo_search',
            ])
            decision_logic.append('1. Beginnt mit "Search for" oder "Suche nach/im Internet"? → duckduckgo_search')
        
        if has_rag:
            prompt += f"""
### {tool_count}. university_knowledge_search (RAG) - {"STANDARD für Uni-Fragen" if not has_duckduckgo else "Für Uni-Fragen"}:
   Für alle {"" if has_duckduckgo else ""}Fragen zur Universität:
   - Fragen zur Uni Köln, WiSo-Fakultät, KLIPS2
   - Prüfungsordnungen, Studienablauf, interne Prozesse
   - Studiengänge, Bewerbungen, Fristen
   {"- DIES IST DAS BEVORZUGTE TOOL wenn keine expliziten Internet-Keywords" if has_duckduckgo else ""}
"""
            tool_count += 1
            examples.extend([
                '"Wann sind die Bewerbungsfristen?" → university_knowledge_search',
                '"Wie funktioniert KLIPS?" → university_knowledge_search',
            ])
            if has_scraper:
                decision_logic.append(f'{len(decision_logic)+1}. Hat der Nutzer eine URL genannt? → web_scraper')
            decision_logic.append(f'{len(decision_logic)+1}. Sonst (Uni-Fragen{" ohne Such-Keywords" if has_duckduckgo else ""}) → university_knowledge_search')
        
        if has_scraper:
            prompt += f"""
### {tool_count}. web_scraper - NUR bei konkreten URLs:
   - Wenn eine URL mit http:// oder https:// genannt wird
   - "Inhalt von [URL]", "Lies die Seite [URL]"
"""
            examples.append('"Zeig mir https://example.com" → web_scraper')
            if not has_rag:  # Only add to decision logic if not already added above
                decision_logic.append(f'{len(decision_logic)+1}. Hat der Nutzer eine URL genannt? → web_scraper')
        
        # Füge Entscheidungslogik hinzu
        if decision_logic:
            prompt += "\n## ENTSCHEIDUNGSLOGIK\n\n"
            prompt += "\n".join(decision_logic)
        
        # Füge Beispiele hinzu
        if examples:
            prompt += "\n\n## BEISPIELE\n\n"
            prompt += "\n".join(examples)
        
        prompt += "\n\n## SPRACHANPASSUNG\nPreserve all characters exactly as they appear in the user message, including umlauts: ä ö ü Ä Ö Ü ß\n\nAntworte in der Sprache des Nutzers."
        
        return prompt
