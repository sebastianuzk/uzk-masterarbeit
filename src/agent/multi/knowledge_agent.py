"""
Knowledge Agent - Spezialisierter Agent für Wissensabfragen.

Verantwortlich für:
- Web-Suche über DuckDuckGo
"""

from typing import List, Optional

from langchain_core.tools import BaseTool
from langchain_ollama import ChatOllama

from config.logging_config import get_logger
from config.settings import settings
from src.agent.tool_loader import load_tool_safely
from src.tools.duckduckgo_tool import create_duckduckgo_tool

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
            "Spezialisiert auf Web-Suche und aktuelle Informationen. "
            "Nutze diesen Agenten wenn externe oder aktuelle Informationen aus dem Internet benötigt werden."
        )
    
    def _create_tools(self) -> List[BaseTool]:
        """Erstelle alle Wissens-Tools."""
        tools = []
        
        # DuckDuckGo-Suche (nur wenn aktiviert)
        if settings.ENABLE_DUCKDUCKGO:
            ddg_tool = load_tool_safely(create_duckduckgo_tool, "DuckDuckGo")
            if ddg_tool:
                tools.append(ddg_tool)
        else:
            logger.debug("DuckDuckGo-Tool deaktiviert (RAG-Evaluation-Modus)")
        
        return tools
    
    def _get_system_prompt(self) -> str:
        """Erstelle den System-Prompt für den Knowledge-Agenten (dynamisch basierend auf verfügbaren Tools)."""
        # Sammle verfügbare Tool-Namen
        available_tool_names = {tool.name for tool in self.tools}
        
        has_duckduckgo = "duckduckgo_search" in available_tool_names
        
        # Basis-Prompt
        prompt = """Du bist der Wissens-Spezialist, ein KI-Agent für Informationssuche und Wissensabfragen.
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
