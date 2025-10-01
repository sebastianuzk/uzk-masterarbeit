"""
Web Scraper Tool für den Autonomen Chatbot-Agenten
"""
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class WebScraperInput(BaseModel):
    """Input für Web Scraping"""
    url: str = Field(description="URL der Webseite, die gescrapt werden soll")


class WebScraperTool(BaseTool):
    """Tool für Web Scraping"""
    
    name: str = "web_scraper"
    description: str = """Nützlich zum Extrahieren von Textinhalten aus Webseiten.
    Verwende dieses Tool, wenn du Inhalte von einer spezifischen URL lesen musst."""
    args_schema: Type[BaseModel] = WebScraperInput
    
    def _run(self, url: str) -> str:
        """Führe Web Scraping aus"""
        try:
            # HTTP-Request senden
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # HTML parsen
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Entferne Script und Style Elemente
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extrahiere Text
            text = soup.get_text()
            
            # Bereinige den Text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Begrenze die Textlänge
            if len(text) > 2000:
                text = text[:2000] + "... (Text gekürzt)"
            
            return f"Inhalt von {url}:\n\n{text}"
            
        except requests.exceptions.RequestException as e:
            return f"Fehler beim Abrufen der URL {url}: {str(e)}"
            
        except Exception as e:
            return f"Fehler beim Parsen der Webseite: {str(e)}"
    
    async def _arun(self, url: str) -> str:
        """Asynchrone Ausführung (nicht implementiert)"""
        raise NotImplementedError("Asynchrone Ausführung nicht unterstützt")


def create_web_scraper_tool() -> WebScraperTool:
    """Factory-Funktion für das Web Scraper Tool"""
    return WebScraperTool()