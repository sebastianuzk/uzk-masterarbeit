"""
Resilient Scraper mit Retry-Logik
==================================

Robustes Scraping mit exponential backoff und intelligenter Fehlerbehandlung.
"""

import asyncio
import aiohttp
from typing import Optional, Callable, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Konfiguration für Retry-Logik."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


class ResilientScraper:
    """
    Robuster Scraper mit intelligenter Retry-Logik.
    
    Features:
    - Exponential backoff
    - Jitter für verteilte Retries
    - Fehlerklassifizierung
    - Retry-Queue für failed requests
    """
    
    def __init__(self, retry_config: RetryConfig = None):
        """
        Initialisiere Resilient Scraper.
        
        Args:
            retry_config: Retry-Konfiguration
        """
        self.config = retry_config or RetryConfig()
        self.retry_queue = []
        self.failed_urls = []
        self.error_stats = {}
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Berechne Delay für Retry-Versuch.
        
        Args:
            attempt: Versuchs-Nummer (0-based)
            
        Returns:
            Delay in Sekunden
        """
        # Exponential backoff
        delay = min(
            self.config.initial_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        # Optional: Jitter hinzufügen
        if self.config.jitter:
            import random
            delay = delay * (0.5 + random.random())
        
        return delay
    
    def is_retryable_error(self, error: Exception) -> bool:
        """
        Prüfe ob Fehler retry-fähig ist.
        
        Args:
            error: Exception
            
        Returns:
            True wenn retry sinnvoll
        """
        # Netzwerk-Fehler -> retry
        if isinstance(error, (
            aiohttp.ClientConnectionError,
            aiohttp.ClientTimeout,
            asyncio.TimeoutError
        )):
            return True
        
        # Server-Fehler (5xx) -> retry
        if isinstance(error, aiohttp.ClientResponseError):
            return 500 <= error.status < 600
        
        # Rate limiting (429) -> retry
        if isinstance(error, aiohttp.ClientResponseError):
            return error.status == 429
        
        # Andere Fehler -> kein retry
        return False
    
    def classify_error(self, error: Exception) -> str:
        """
        Klassifiziere Fehlertyp.
        
        Args:
            error: Exception
            
        Returns:
            Fehler-Kategorie
        """
        if isinstance(error, aiohttp.ClientConnectionError):
            return "connection_error"
        elif isinstance(error, aiohttp.ClientTimeout):
            return "timeout"
        elif isinstance(error, asyncio.TimeoutError):
            return "timeout"
        elif isinstance(error, aiohttp.ClientResponseError):
            if error.status == 404:
                return "not_found"
            elif error.status == 403:
                return "forbidden"
            elif error.status == 429:
                return "rate_limited"
            elif 500 <= error.status < 600:
                return "server_error"
            else:
                return f"http_{error.status}"
        else:
            return "unknown_error"
    
    async def scrape_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        scraper: 'BatchScraper'
    ) -> Optional[Any]:
        """
        Scrape URL mit automatischen Retries.
        
        Args:
            session: aiohttp ClientSession
            url: Zu scrapende URL
            scraper: BatchScraper-Instanz
            
        Returns:
            ScrapedContent oder None
        """
        last_error = None
        
        for attempt in range(self.config.max_retries):
            try:
                # Versuche zu scrapen mit BatchScraper
                content = await scraper.scrape_single(session, url)
                
                # Erfolg!
                if attempt > 0:
                    logger.info(f"✓ Erfolgreich nach {attempt + 1} Versuchen: {url}")
                
                return content
                
            except Exception as e:
                last_error = e
                error_type = self.classify_error(e)
                
                # Statistik updaten
                self.error_stats[error_type] = self.error_stats.get(error_type, 0) + 1
                
                # Prüfe ob retry sinnvoll
                if not self.is_retryable_error(e):
                    logger.warning(
                        f"✗ Nicht-retry-fähiger Fehler für {url}: "
                        f"{error_type} - {str(e)}"
                    )
                    self.failed_urls.append((url, error_type, str(e)))
                    # Gib ein fehlgeschlagenes ScrapedContent zurück
                    from .batch_scraper import ScrapedContent
                    from datetime import datetime
                    return ScrapedContent(
                        url=url,
                        title="",
                        content="",
                        metadata={},
                        success=False,
                        error_message=str(e),
                        timestamp=datetime.now().isoformat()
                    )
                
                # Letzter Versuch?
                if attempt == self.config.max_retries - 1:
                    logger.error(
                        f"✗ Alle {self.config.max_retries} Versuche fehlgeschlagen für {url}: "
                        f"{error_type}"
                    )
                    self.failed_urls.append((url, error_type, str(e)))
                    # Gib ein fehlgeschlagenes ScrapedContent zurück
                    from .batch_scraper import ScrapedContent
                    from datetime import datetime
                    return ScrapedContent(
                        url=url,
                        title="",
                        content="",
                        metadata={},
                        success=False,
                        error_message=str(e),
                        timestamp=datetime.now().isoformat()
                    )
                
                # Berechne Delay und warte
                delay = self.calculate_delay(attempt)
                logger.warning(
                    f"⚠ Versuch {attempt + 1}/{self.config.max_retries} fehlgeschlagen "
                    f"für {url}: {error_type}. Retry in {delay:.1f}s..."
                )
                
                await asyncio.sleep(delay)
        
        # Sollte nicht erreicht werden, aber Fallback
        from .batch_scraper import ScrapedContent
        from datetime import datetime
        return ScrapedContent(
            url=url,
            title="",
            content="",
            metadata={},
            success=False,
            error_message="Max retries exceeded",
            timestamp=datetime.now().isoformat()
        )
    
    async def scrape_batch_with_retry(
        self,
        urls: list,
        scrape_func: Callable,
        progress_callback: Optional[Callable] = None,
        **kwargs
    ) -> list:
        """
        Scrape mehrere URLs mit Retry-Logik.
        
        Args:
            urls: Liste von URLs
            scrape_func: Scraping-Funktion
            progress_callback: Optional progress callback
            **kwargs: Zusätzliche Argumente für scrape_func
            
        Returns:
            Liste von Ergebnissen
        """
        results = []
        
        for i, url in enumerate(urls, 1):
            result = await self.scrape_with_retry(url, scrape_func, **kwargs)
            
            if result is not None:
                results.append(result)
                if progress_callback:
                    progress_callback(url, True, None)
            else:
                if progress_callback:
                    progress_callback(url, False, "All retries failed")
            
            # Progress-Log
            if i % 10 == 0:
                logger.info(f"Fortschritt: {i}/{len(urls)} URLs verarbeitet")
        
        return results
    
    def get_retry_queue(self) -> list:
        """
        Erhalte URLs die erneut versucht werden sollten.
        
        Returns:
            Liste von URLs
        """
        return self.retry_queue
    
    def get_failed_urls(self) -> list:
        """
        Erhalte endgültig fehlgeschlagene URLs.
        
        Returns:
            Liste von (url, error_type, error_message) Tuples
        """
        return self.failed_urls
    
    def get_error_statistics(self) -> dict:
        """
        Erhalte Fehler-Statistiken.
        
        Returns:
            Dictionary mit Fehler-Counts
        """
        return self.error_stats
    
    def export_failed_urls(self, filepath: str):
        """
        Exportiere fehlgeschlagene URLs in Datei.
        
        Args:
            filepath: Ziel-Dateipfad
        """
        import json
        from pathlib import Path
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'failed_count': len(self.failed_urls),
            'error_statistics': self.error_stats,
            'failed_urls': [
                {
                    'url': url,
                    'error_type': error_type,
                    'error_message': error_msg
                }
                for url, error_type, error_msg in self.failed_urls
            ]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Fehlgeschlagene URLs exportiert nach {filepath}")
