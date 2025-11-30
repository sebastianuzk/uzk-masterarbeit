"""
WISO Faculty Web Crawler
=======================

This module implements a focused web crawler for the WiSo faculty website.
It discovers and extracts all relevant URLs while respecting common crawling
etiquette and robots.txt rules.

Features:
- Focused crawling of WiSo faculty domain
- Respects robots.txt and crawl delays
- Filters for relevant content pages
- Integrates with batch scraper
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict, Optional
import re
import logging
from pathlib import Path
import json
import time
import random
import robotexclusionrulesparser
from dataclasses import dataclass
from datetime import datetime
from src.scraper.utils.error_cache import ErrorCache

logger = logging.getLogger(__name__)

@dataclass
class CrawlerConfig:
    """Configuration for the WiSo crawler."""
    seed_url: str = "https://wiso.uni-koeln.de/de/"
    allowed_domains: Set[str] = None
    max_pages: int = 6000
    crawl_delay: float = 2.0  # Erhöht von 1.0 auf 2.0 - verhindert Blockierung
    max_depth: int = 5
    concurrent_requests: int = 5  # Reduziert von 10 auf 5 - weniger aggressiv
    
    # Retry-Konfiguration für garantierten Erfolg
    max_retries_per_attempt: int = 3      # Retries pro crawl_page Aufruf
    infinite_retries: bool = True         # Nie aufgeben - URLs immer wieder versuchen
    initial_retry_delay: float = 15.0     # Initial delay für 429-Fehler
    max_retry_delay: float = 300.0        # Max delay
    exponential_base: float = 2.0
    jitter: bool = True
    
    # Anti-Rate-Limiting Strategien
    randomize_delays: bool = True         # Zufällige Delays zwischen Requests
    vary_user_agents: bool = True         # Wechselnde User Agents
    session_rotation: bool = True         # Session-Rotation alle X Requests
    session_rotation_interval: int = 20   # Alle 20 Requests neue Session (sehr häufig)
    
    # Request-Verhalten
    min_delay: float = 10.0              # Minimum delay zwischen Requests
    max_delay: float = 30.0              # Maximum delay zwischen Requests
    respect_server_load: bool = True     # Längere Pausen bei Server-Stress
    
    # Logging-Konfiguration
    log_url_max_length: int = 80         # Maximale URL-Länge in Logs
    
    def __post_init__(self):
        if self.allowed_domains is None:
            self.allowed_domains = {
                "wiso.uni-koeln.de",
                #"verwaltung.uni-koeln.de"
            }

class WisoCrawler:
    """Crawler implementation for WiSo faculty website."""
    
    def __init__(self, config: CrawlerConfig, html_cache=None):
        self.config = config
        self.visited_urls: Set[str] = set()
        self.queue: Set[str] = {config.seed_url}
        self.found_urls: Set[str] = set()
        self.pdf_urls: Set[str] = set()  # Separate collection for PDFs
        
        # Caches
        self.html_cache = html_cache
        self.error_cache = ErrorCache()  # Separate cache for failed URLs (404, 403, etc.)
        self.robots_parser = robotexclusionrulesparser.RobotFileParserLookalike()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # HTML Content Cache
        self.html_cache = html_cache
        
        # Retry-Management für garantierten Erfolg
        self.retry_queue: List[Dict] = []  # URLs die wiederholt werden müssen
        self.failed_urls: List[tuple] = []  # Temporäre Fehler-Liste
        self.retry_stats = {
            'total_requests': 0,
            'successful_first_try': 0,
            'successful_after_retry': 0,
            'retry_rounds': 0,
            'max_attempts_per_url': 0,
            'rate_limit_errors': 0,
            'server_errors': 0,
            'server_error_errors': 0,  # HTTP 500, 502, 503, 504 Fehler
            'timeout_errors': 0,
            'connection_errors': 0,
            'not_found_404_errors': 0,
            'other_errors': 0
        }
        
        # Anti-Rate-Limiting
        self.request_count = 0
        self.last_request_time = 0
        self.session_cookies = {}  # Session-Cookie simulation
        self.browsing_session_start = time.time()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
    
    def format_url_for_log(self, url: str, force_full: bool = False) -> str:
        """
        Format URL for logging with configurable length.
        
        Args:
            url: URL to format
            force_full: If True, always show full URL (for error cases)
            
        Returns:
            Formatted URL string
        """
        if force_full:
            return url  # Vollständige URL bei Fehlern
            
        max_length = self.config.log_url_max_length
        if len(url) <= max_length:
            return url
        return f"{url[:max_length]}..."
        
    async def init_session(self):
        """Initialize aiohttp session and robots.txt parser."""
        if self.session is None:
            # Wähle zufälligen User Agent
            user_agent = random.choice(self.user_agents) if self.config.vary_user_agents else self.user_agents[0]
            
            # Add realistic headers to avoid being blocked
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'no-cache',
                'DNT': '1',  # Do Not Track
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            }
            
            # Add timeout and connector settings for better stability
            # Disable SSL verification to avoid handshake issues
            timeout = aiohttp.ClientTimeout(total=30, connect=10, sock_read=20)
            connector = aiohttp.TCPConnector(
                limit=2,  # Noch weniger concurrent connections
                limit_per_host=1,  # Nur 1 connection pro Host
                ssl=False,  # Disable SSL verification
                force_close=True,  # Close connections after each request
                enable_cleanup_closed=True,  # Cleanup closed connections
                ttl_dns_cache=300,  # DNS Cache TTL
                use_dns_cache=True,
            )
            
            # Cookie Jar für Session-Simulation
            cookie_jar = aiohttp.CookieJar()
            
            self.session = aiohttp.ClientSession(
                headers=headers, 
                timeout=timeout,
                connector=connector,
                cookie_jar=cookie_jar  # Automatische Cookie-Verwaltung
            )
            
        # Fetch and parse robots.txt
        try:
            robots_url = urljoin(self.config.seed_url, "/robots.txt")
            async with self.session.get(robots_url) as response:
                if response.status == 200:
                    robots_content = await response.text()
                    self.robots_parser.parse(robots_content.splitlines())
        except Exception as e:
            logger.warning(f"Could not fetch robots.txt: {e}")

    async def close(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
            self.session = None

    def calculate_retry_delay(self, attempt: int) -> float:
        """Berechne Delay für Retry mit exponential backoff."""
        delay = min(
            self.config.initial_retry_delay * (self.config.exponential_base ** attempt),
            self.config.max_retry_delay
        )
        if self.config.jitter:
            delay = delay * (0.5 + random.random())
        return delay

    def is_retryable_error(self, error: Exception, status_code: Optional[int] = None) -> bool:
        """Prüfe ob Fehler retry-fähig ist."""
        if status_code == 429 or (status_code and 500 <= status_code < 600):
            return True
        # 404 könnte temporär sein (Server-Überlastung, temporäre Nichtverfügbarkeit)
        # Deshalb 1-2 Retries erlauben, aber nicht unendlich
        if status_code == 404:
            return True
        return isinstance(error, (
            aiohttp.ClientConnectionError,
            aiohttp.ClientTimeout,
            asyncio.TimeoutError,
            aiohttp.ServerTimeoutError
        ))

    def classify_error(self, error: Exception, status_code: Optional[int] = None) -> str:
        """Klassifiziere Fehler für Statistiken."""
        if status_code == 429:
            return "rate_limit"
        elif status_code == 404:
            return "not_found_404"
        elif status_code and 500 <= status_code < 600:
            return "server_error"
        elif isinstance(error, (aiohttp.ClientTimeout, asyncio.TimeoutError)):
            return "timeout"
        elif isinstance(error, aiohttp.ClientConnectionError):
            return "connection"
        else:
            return "other"

    def add_to_retry_queue(self, url: str, error: Exception, attempt_count: int, status_code: int = None):
        """Füge URL zur Retry-Queue hinzu oder cache permanente Fehler."""
        if status_code is None:
            status_code = getattr(error, 'status', None)
            
        # Prüfe auf permanente Fehler und cache diese separat
        if status_code and self.error_cache.is_permanent_error(status_code):
            self.error_cache.add(
                url=url,
                status_code=status_code,
                error_type="http_error",
                error_message=str(error),
                attempt_count=attempt_count
            )
            logger.warning(f"🚫 Permanent error cached: {status_code} {self.format_url_for_log(url)}")
            return
            
        retry_delay = self.calculate_retry_delay(attempt_count)
        error_type = self.classify_error(error, status_code)
        
        # Begrenzte Retries für temporäre Fehler
        if attempt_count >= self.config.max_retries_per_attempt:
            logger.warning(f"🚫 Max retries reached for {self.format_url_for_log(url)} nach {attempt_count} Versuchen")
            self.failed_urls.append((url, error_type, f"Max retries nach {attempt_count} Versuchen"))
            return
        
        # Check if URL already in retry_queue
        for entry in self.retry_queue:
            if entry['url'] == url:
                entry['attempt_count'] = attempt_count + 1
                entry['next_retry_time'] = time.time() + retry_delay
                entry['last_error'] = str(error)
                entry['error_type'] = error_type
                return
        
        # Add new entry
        self.retry_queue.append({
            'url': url,
            'attempt_count': attempt_count + 1,
            'next_retry_time': time.time() + retry_delay,
            'last_error': str(error),
            'error_type': error_type,
            'first_attempt_time': time.time()
        })

    async def process_retry_queue(self) -> int:
        """Bearbeite URLs in der Retry-Queue. Returns: Anzahl erfolgreicher URLs."""
        if not self.retry_queue:
            return 0
            
        current_time = time.time()
        ready_urls = [entry for entry in self.retry_queue if entry['next_retry_time'] <= current_time]
        
        if not ready_urls:
            return 0
        
        self.retry_stats['retry_rounds'] += 1
        logger.info(f"🔄 Retry Round {self.retry_stats['retry_rounds']}: Processing {len(ready_urls)} URLs...")
        
        successful_count = 0
        
        for entry in ready_urls:
            self.retry_queue.remove(entry)
            url = entry['url']
            attempt_count = entry['attempt_count']
            
            self.retry_stats['max_attempts_per_url'] = max(
                self.retry_stats['max_attempts_per_url'], attempt_count
            )
            
            # Versuche URL erneut zu crawlen
            new_links = await self.crawl_page(url)
            
            if url in self.found_urls:
                successful_count += 1
                # Add new links to main queue (PDFs now included!)
                for link in new_links:
                    if link not in self.visited_urls:
                        self.queue.add(link)
        
        if successful_count > 0:
            logger.info(f"✅ {successful_count}/{len(ready_urls)} URLs erfolgreich aus Retry-Queue verarbeitet")
        
        return successful_count

    def is_allowed_url(self, url: str) -> bool:
        """Check if URL should be crawled based on domain and robots.txt."""
        try:
            parsed = urlparse(url)
        except ValueError as e:
            # Handle invalid URL formats (e.g., malformed IPv6) - SHOW FULL URL FOR DEBUGGING
            logger.warning(f"Invalid URL format: {self.format_url_for_log(url, force_full=True)} - {e}")
            return False
        
        # Check domain
        if parsed.netloc not in self.config.allowed_domains:
            return False
            
        # Check robots.txt
        if not self.robots_parser.is_allowed("*", url):
            return False
                        
        # Filter out non-HTML resources and certain patterns (but keep PDFs!)
        excluded_patterns = [
            r'\.(jpg|jpeg|png|gif|css|js|ico|xml)$',  # Removed pdf from here
            r'(calendar|print|rss|feed)',
            r'/(de|en)/api/',
        ]
        
        url_lower = url.lower()
        return not any(re.search(pattern, url_lower) for pattern in excluded_patterns)

    async def extract_links(self, url: str, html: str) -> Set[str]:
        """Extract and normalize links from HTML content."""
        links = set()
        soup = BeautifulSoup(html, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            try:
                absolute_url = urljoin(url, href)
                
                # Normalize URL
                parsed = urlparse(absolute_url)
                normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if parsed.query:
                    normalized_url += f"?{parsed.query}"
                
                # 🔧 WICHTIG: Trim whitespace from URL (häufiges Problem bei HTML-Links)
                normalized_url = normalized_url.strip()
                
                # Check if it's a PDF
                if normalized_url.lower().endswith('.pdf'):
                    # Add to PDF collection AND to links for crawling!
                    if parsed.netloc in self.config.allowed_domains:
                        self.pdf_urls.add(normalized_url)
                        logger.info(f"📄 Found PDF: {normalized_url}")  # 🔧 INFO statt DEBUG!
                        links.add(normalized_url)  # 🔥 WICHTIG: PDFs werden auch zu links hinzugefügt für Queue-Verarbeitung!
                elif self.is_allowed_url(normalized_url):
                    links.add(normalized_url)
                    
            except ValueError as e:
                # Handle invalid URL formats (e.g., malformed IPv6, invalid href values) - SHOW FULL URL FOR DEBUGGING
                logger.debug(f"Skipping invalid URL from {self.format_url_for_log(url, force_full=True)}: href='{href}' - {e}")
                continue
            except Exception as e:
                # Handle any other URL processing errors - SHOW FULL URL FOR DEBUGGING
                logger.warning(f"Unexpected error processing URL from {self.format_url_for_log(url, force_full=True)}: href='{href}' - {e}")
                continue
                
        return links

    async def _handle_pdf_url(self, url: str) -> Set[str]:
        """
        Handle PDF URLs with caching and download functionality.
        Similar to HTML processing but for PDFs.
        """
        import os
        from pathlib import Path
        import hashlib
        
        logger.info(f"🔍 Crawling PDF: {self.format_url_for_log(url)}")
        
        # PDF-Cache Pfad erstellen
        pdf_cache_dir = Path("data/pdf_cache")
        pdf_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # URL als Dateiname verwenden (für eindeutige Zuordnung)
        # URL bereinigen: illegale Zeichen für Dateinamen entfernen/ersetzen
        safe_url = re.sub(r'[<>:"|?*\\\/]', '_', url)  # Windows/Linux-illegale Zeichen ersetzen
        safe_url = re.sub(r'https?_', '', safe_url)  # http/https Prefix entfernen
        
        # PDF-Extension nur hinzufügen falls noch nicht vorhanden
        if not safe_url.endswith('.pdf'):
            safe_filename = f"{safe_url}.pdf"
        else:
            safe_filename = safe_url
        
        # Falls der Name zu lang wird, kürzen (Windows Limit: 260 Zeichen)
        if len(safe_filename) > 200:  # Puffer für Pfad
            safe_filename = safe_filename[:200] + "....pdf"
            
        pdf_file_path = pdf_cache_dir / safe_filename
        
        # PDF Cache Check
        if pdf_file_path.exists():
            logger.info(f"📄 PDF Cache HIT: {self.format_url_for_log(url)}")
            file_size = pdf_file_path.stat().st_size
            logger.info(f"📁 Cached PDF: {safe_filename} ({file_size:,} bytes)")
            
            # Zu PDF-Collection hinzufügen
            if url not in self.pdf_urls:
                self.pdf_urls.add(url)
                logger.info(f"📄 Found PDF: {url}")
            
            # Auch zu found_urls hinzufügen (für einheitliches Success-Tracking)
            self.found_urls.add(url)
            
            self.retry_stats['successful_first_try'] += 1
            return set()  # PDFs return no links
        
        # PDF Cache MISS - Download erforderlich
        logger.info(f"📄 PDF Cache MISS: {self.format_url_for_log(url)}")
        
        try:
            logger.info(f"🌐 HTTP Request (PDF): {self.format_url_for_log(url)}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    pdf_content = await response.read()
                    file_size = len(pdf_content)
                    
                    logger.info(f"📡 Response: HTTP {response.status} | PDF Size: {file_size:,} bytes")
                    
                    # PDF speichern
                    with open(pdf_file_path, 'wb') as f:
                        f.write(pdf_content)
                    
                    logger.info(f"💾 PDF saved: {safe_filename} ({file_size:,} bytes)")
                    
                    # Zu PDF-Collection hinzufügen
                    if url not in self.pdf_urls:
                        self.pdf_urls.add(url)
                        logger.info(f"📄 Found PDF: {url}")
                    
                    # Auch zu found_urls hinzufügen (für einheitliches Success-Tracking)
                    self.found_urls.add(url)
                    
                    self.retry_stats['successful_first_try'] += 1
                    return set()  # PDFs return no links
                    
                else:
                    # Permanente Fehler in Error-Cache speichern
                    if self.error_cache.is_permanent_error(response.status):
                        self.error_cache.add(
                            url=url,
                            status_code=response.status,
                            error_type="http_error",
                            error_message=f"PDF Download failed: HTTP {response.status}"
                        )
                        logger.warning(f"🚫 PDF permanent error cached: {response.status} {self.format_url_for_log(url)}")
                    else:
                        logger.warning(f"❌ PDF Download failed: HTTP {response.status} for {self.format_url_for_log(url)}")
                    return set()
                    
        except Exception as e:
            # Prüfe ob es ein permanenter HTTP-Fehler ist
            status_code = getattr(e, 'status', None)
            if status_code and self.error_cache.is_permanent_error(status_code):
                self.error_cache.add(
                    url=url,
                    status_code=status_code,
                    error_type="http_error",
                    error_message=f"PDF Error: {str(e)}"
                )
                logger.warning(f"🚫 PDF permanent error cached: {status_code} {self.format_url_for_log(url)}")
            else:
                logger.error(f"❌ Error downloading PDF {self.format_url_for_log(url)}: {e}")
            return set()

    async def crawl_page(self, url: str) -> Set[str]:
        """Crawl a single page and extract links."""
        if not self.session:
            await self.init_session()

        # Prüfe Error-Cache für permanente Fehler
        if self.error_cache.contains(url):
            error_entry = self.error_cache.get(url)
            logger.debug(f"Skipping permanently failed URL: {self.format_url_for_log(url)} (Error: {error_entry.status_code})")
            return set()

        # 📄 PDF-DETECTION UND VERARBEITUNG
        if url.lower().endswith('.pdf'):
            # Prüfe Error-Cache auch für PDFs
            if self.error_cache.contains(url):
                error_entry = self.error_cache.get(url)
                logger.debug(f"Skipping permanently failed PDF: {self.format_url_for_log(url)} (Error: {error_entry.status_code})")
                return set()
            return await self._handle_pdf_url(url)

        # Prüfe HTML-Cache zuerst
        if self.html_cache and self.html_cache.contains(url):
            cached_entry = self.html_cache.get(url)
            if cached_entry and cached_entry.status_code == 200:
                logger.info(f"📄 HTML Cache HIT: {self.format_url_for_log(url)}")
                links = await self.extract_links(url, cached_entry.content)
                self.found_urls.add(url)
                self.retry_stats['successful_first_try'] += 1
                return links  # SOFORTIGER RETURN - KEIN DELAY BEI CACHE HITS!
            else:
                logger.info(f"📄 HTML Cache MISS (stale): {self.format_url_for_log(url)}")
        else:
            logger.info(f"📄 HTML Cache MISS: {self.format_url_for_log(url)}")        # Nur bei echten HTTP-Requests: Delays und Rate-Limiting
        self.retry_stats['total_requests'] += 1
        self.request_count += 1
        
        # Session-Rotation prüfen
        await self.rotate_session_if_needed()
        
        # Adaptive Delay berechnen
        delay = self.get_adaptive_delay()
        
        # Adaptive Backoff wenn Server überlastet
        await self.adaptive_back_off()
        
        # Respektiere Rate-Limiting
        current_time = time.time()
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            if time_since_last < delay:
                wait_time = delay - time_since_last
                await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        
        last_error = None
        last_status = None
        
        # Versuche mehrmals innerhalb eines crawl_page Aufrufs
        for attempt in range(self.config.max_retries_per_attempt):
            try:
                # Log HTTP Request
                if attempt == 0:
                    logger.info(f"🌐 HTTP Request: {self.format_url_for_log(url)}")
                else:
                    logger.info(f"🔄 Retry {attempt+1}/{self.config.max_retries_per_attempt}: {self.format_url_for_log(url)}")
                
                # Dynamische Headers
                extra_headers = self.get_current_headers()
                
                async with self.session.get(url, allow_redirects=True, headers=extra_headers) as response:
                    # Messe sowohl Header-Size als auch tatsächliche Size
                    header_size = response.headers.get('content-length', 'unknown')
                    
                    if response.status == 200:
                        # Check if this is a PDF URL (crawler should not process PDF content)
                        content_type = response.content_type or ''
                        if url.lower().endswith('.pdf') or 'application/pdf' in content_type.lower():
                            # PDF URLs should be added to pdf_urls set, not processed as HTML
                            logger.info(f"📡 Response: HTTP {response.status} | PDF detected: {url}")
                            if url not in self.pdf_urls:
                                self.pdf_urls.add(url)
                                logger.info(f"📄 Found PDF during crawling: {url}")  # 🔧 INFO statt DEBUG!
                            # ❌ NICHT zu found_urls hinzufügen - PDFs sind separate!
                            # self.found_urls.add(url)  # ← ENTFERNT: PDFs gehören NICHT in found_urls!
                            
                            # Erfolgs-Statistik
                            if attempt == 0:
                                self.retry_stats['successful_first_try'] += 1
                            else:
                                self.retry_stats['successful_after_retry'] += 1
                                logger.info(f"✅ PDF erfolgreich nach {attempt + 1} Versuchen: {url}")
                            
                            return set()  # PDFs return no links to extract
                        
                        # Regular HTML processing
                        html = await response.text()
                        actual_size = len(html.encode('utf-8')) if html else 0
                        
                        # Intelligente Größenanzeige
                        if header_size != 'unknown':
                            logger.info(f"📡 Response: HTTP {response.status} | Size: {header_size} bytes")
                        else:
                            logger.info(f"📡 Response: HTTP {response.status} | Size: {actual_size} bytes (measured)")
                        
                        # HTML-Content cachen
                        if self.html_cache and html and html.strip():
                            response_headers = dict(response.headers)
                            self.html_cache.put(
                                url=url,
                                content=html,
                                content_type=response.content_type or 'text/html',
                                status_code=response.status,
                                headers=response_headers,
                                encoding=response.charset or 'utf-8'
                            )
                            logger.debug(f"💾 HTML gecacht: {url} ({len(html)} chars)")
                        
                        links = await self.extract_links(url, html)
                        self.found_urls.add(url)
                        
                        # Erfolgs-Statistik
                        if attempt == 0:
                            self.retry_stats['successful_first_try'] += 1
                        else:
                            self.retry_stats['successful_after_retry'] += 1
                            logger.info(f"✅ Erfolgreich nach {attempt + 1} Versuchen: {url}")
                        
                        return links
                    else:
                        last_status = response.status
                        
                        # 🔧 OPTIMIZATION: Check for permanent errors immediately
                        if self.error_cache and self.error_cache.is_permanent_error(response.status):
                            # Cache permanent errors immediately without retrying
                            error_msg = f"HTTP {response.status}"
                            error_type = self.classify_error(None, response.status)
                            logger.warning(f"🚫 Permanent error detected for {self.format_url_for_log(url)}: {error_msg}")
                            
                            # Add to error cache with correct parameters
                            self.error_cache.add(
                                url=url,
                                status_code=response.status,
                                error_type=error_type,
                                error_message=error_msg,
                                attempt_count=attempt + 1
                            )
                            
                            # Track statistics
                            self.retry_stats[f"{error_type}_errors"] += 1
                            self.failed_urls.append((url, f"HTTP_{response.status}", error_msg))
                            
                            return set()  # Exit immediately for permanent errors
                        
                        # Spezielle Behandlung für verschiedene Status Codes (nur temporary)
                        if response.status == 429:
                            # Rate Limit - intelligente Pipeline-Pause
                            rate_limit_delay = random.uniform(60, 180)  # 1-3 Minuten
                            logger.warning(f"🚫 Rate Limited! Pausiere Pipeline für {rate_limit_delay:.0f}s...")
                            
                            # Check for pause flag
                            pause_flag = Path("data/pipeline_pause.flag")
                            if pause_flag.exists():
                                logger.warning("⏸️ Pipeline pause flag detected - waiting for resume...")
                                while pause_flag.exists():
                                    await asyncio.sleep(10)
                                logger.info("▶️ Pipeline resumed")
                            else:
                                await asyncio.sleep(rate_limit_delay)
                        elif response.status in [503, 502, 504]:
                            # Server überlastet - moderate Pause
                            server_delay = random.uniform(15, 45)
                            logger.warning(f"🔧 Server überlastet ({response.status}), warte {server_delay:.0f}s...")
                            await asyncio.sleep(server_delay)
                        
                        raise aiohttp.ClientResponseError(
                            request_info=response.request_info,
                            history=response.history,
                            status=response.status,
                            message=f"HTTP {response.status}"
                        )
                        
            except Exception as e:
                last_error = e
                last_status = getattr(e, 'status', last_status)
                error_type = self.classify_error(e, last_status)
                self.retry_stats[f"{error_type}_errors"] += 1
                
                # Prüfe ob retry sinnvoll
                if not self.is_retryable_error(e, last_status):
                    logger.warning(f"❌ Nicht-retry-fähiger Fehler für {url}: {error_type}")
                    self.failed_urls.append((url, error_type, str(e)))
                    break
                
                # Letzter Versuch in diesem crawl_page Aufruf?
                if attempt == self.config.max_retries_per_attempt - 1:
                    break
                
                # Kurzer Delay zwischen Versuchen
                short_delay = self.calculate_retry_delay(attempt) / 4  # Kürzerer Delay innerhalb crawl_page
                logger.warning(f"⚠️ Versuch {attempt + 1}/{self.config.max_retries_per_attempt} fehlgeschlagen für {url}: {error_type}. Retry in {short_delay:.1f}s...")
                await asyncio.sleep(short_delay)
        
        # Alle sofortigen Versuche fehlgeschlagen
        if self.config.infinite_retries and last_error and self.is_retryable_error(last_error, last_status):
            # Zur Retry-Queue hinzufügen für späteren Versuch
            self.add_to_retry_queue(url, last_error, self.config.max_retries_per_attempt - 1)
            logger.warning(f"🔄 {url} zur Retry-Queue hinzugefügt. Queue-Größe: {len(self.retry_queue)}")
        else:
            # 🔧 NOTE: Permanent errors are now handled immediately in the response section above
            # This section only handles temporary errors that exhausted retries
            if last_status and last_status not in {400, 401, 403, 404, 405, 410, 418, 451}:
                # Non-permanent errors that exhausted retries
                logger.error(f"❌ URL fehlgeschlagen nach allen Versuchen: {self.format_url_for_log(url, force_full=True)} - {last_status}")
                self.failed_urls.append((url, f"HTTP_{last_status}", f"HTTP-Fehler {last_status}"))
            # Permanent errors are already handled above and cached immediately
            
        return set()

    async def crawl(self) -> List[str]:
        """Main crawling loop."""
        try:
            await self.init_session()
            start_time = time.time()
            
            logger.info(f"🕷️ Starting WiSo Crawler with guaranteed success mode:")
            logger.info(f"   • Infinite retries: {self.config.infinite_retries}")
            logger.info(f"   • Max retries per attempt: {self.config.max_retries_per_attempt}")
            logger.info(f"   • Initial retry delay: {self.config.initial_retry_delay}s")
            logger.info(f"   • Max pages: {self.config.max_pages}")
            
            # Hauptschleife: URLs aus der normalen Queue
            while self.queue and len(self.found_urls) < self.config.max_pages:
                # Get next URL to crawl
                url = self.queue.pop()
                if url in self.visited_urls:
                    continue
                    
                self.visited_urls.add(url)
                
                # Log aktuelle URL für bessere Sichtbarkeit
                logger.info(f"🔍 Crawling [{len(self.found_urls)+1}/{self.config.max_pages}]: {url}")
                
                # Crawl page and extract links
                new_links = await self.crawl_page(url)
                
                # Log Erfolg/Misserfolg der aktuellen URL
                if url in self.found_urls:
                    logger.info(f"✅ Erfolgreich: {len(new_links)} neue Links gefunden | Queue: {len(self.queue)} | Retry: {len(self.retry_queue)}")
                else:
                    logger.warning(f"❌ Fehlgeschlagen, aber in Retry-Queue | Queue: {len(self.queue)} | Retry: {len(self.retry_queue)}")
                
                # Add new links to queue (PDFs now included for crawling!)
                for link in new_links:
                    if link not in self.visited_urls:
                        self.queue.add(link)  # 🔥 PDFs werden jetzt auch zur Queue hinzugefügt!
                
                # Detaillierte Progress-Logs alle 10 URLs
                if len(self.found_urls) % 10 == 0 and len(self.found_urls) > 0:
                    success_rate = (self.retry_stats['successful_first_try'] + self.retry_stats['successful_after_retry']) / max(self.retry_stats['total_requests'], 1) * 100
                    logger.info(f"📊 STATUS: {len(self.found_urls)}/{self.config.max_pages} URLs | Queue: {len(self.queue)} | Retry: {len(self.retry_queue)} | Success: {success_rate:.1f}%")
                
                # Gelegentlich Retry-Queue bearbeiten
                if len(self.found_urls) % 25 == 0 and self.retry_queue:
                    await self.process_retry_queue()
            
            # Hauptcrawling abgeschlossen - jetzt fokussiert auf Retry-Queue
            if self.config.infinite_retries:
                logger.info(f"\n🔄 Hauptcrawling abgeschlossen. Bearbeite Retry-Queue...")
                
                max_retry_rounds = 50  # Sicherheitsgrenze
                retry_round = 0
                
                while self.retry_queue and retry_round < max_retry_rounds:
                    retry_round += 1
                    successful = await self.process_retry_queue()
                    
                    if successful == 0:
                        # Warte bis URLs bereit sind
                        if self.retry_queue:
                            current_time = time.time()
                            next_retry_times = [entry['next_retry_time'] for entry in self.retry_queue]
                            min_wait_time = min(next_retry_times) - current_time
                            
                            if min_wait_time > 0:
                                wait_time = min(min_wait_time, 60)  # Max 60s warten
                                logger.info(f"⏳ Warte {wait_time:.1f}s auf nächste Retry-Möglichkeit... (Queue: {len(self.retry_queue)})")
                                await asyncio.sleep(wait_time)
                    
                    # Progress
                    if retry_round % 5 == 0:
                        success_rate = (self.retry_stats['successful_first_try'] + self.retry_stats['successful_after_retry']) / max(self.retry_stats['total_requests'], 1) * 100
                        logger.info(f"🔄 Retry Round {retry_round}: {len(self.retry_queue)} URLs remaining | Success Rate: {success_rate:.1f}%")
            
            # Finale Statistiken
            duration = time.time() - start_time
            total_successful = self.retry_stats['successful_first_try'] + self.retry_stats['successful_after_retry']
            success_rate = (total_successful / max(self.retry_stats['total_requests'], 1)) * 100
            
            logger.info(f"\n🎯 Crawling abgeschlossen in {duration:.1f}s:")
            logger.info(f"   • Gefundene URLs: {len(self.found_urls)}")
            logger.info(f"   • PDF-Dokumente: {len(self.pdf_urls)}")
            logger.info(f"   • Erfolgsrate (gesamt): {success_rate:.1f}%")
            logger.info(f"   • Erfolg beim ersten Versuch: {self.retry_stats['successful_first_try']}")
            logger.info(f"   • Erfolg nach Retry: {self.retry_stats['successful_after_retry']}")
            logger.info(f"   • Verbleibende Retry-Queue: {len(self.retry_queue)}")
            logger.info(f"   • Max Versuche pro URL: {self.retry_stats['max_attempts_per_url']}")
            
            if self.retry_queue:
                logger.warning(f"⚠️ {len(self.retry_queue)} URLs konnten trotz Retries nicht verarbeitet werden")
                
            # 🔥 KRITISCH: Nur HTML-URLs zurückgeben, PDFs sind in separater pdf_urls Collection!
            html_urls = [url for url in self.found_urls if not url.lower().endswith('.pdf')]
            logger.info(f"📊 FINALE TRENNUNG:")
            logger.info(f"   • HTML-URLs: {len(html_urls)} (werden für Scraping zurückgegeben)")
            logger.info(f"   • PDF-URLs: {len(self.pdf_urls)} (separate Collection)")
            
            return html_urls  # ← Nur HTML-URLs für Scraping!
            
        finally:
            await self.close()

    def get_retry_statistics(self) -> Dict:
        """Erhalte detaillierte Retry-Statistiken."""
        total = self.retry_stats['total_requests']
        if total == 0:
            return self.retry_stats
        
        stats = self.retry_stats.copy()
        stats['success_rate_total'] = ((stats['successful_first_try'] + stats['successful_after_retry']) / total) * 100
        stats['retry_rate'] = (stats['successful_after_retry'] / total) * 100
        stats['pending_retries'] = len(self.retry_queue)
        
        return stats

    def export_retry_report(self, filepath: str):
        """Exportiere detaillierten Retry-Report."""
        data = {
            'timestamp': datetime.now().isoformat(),
            'configuration': {
                'infinite_retries': self.config.infinite_retries,
                'max_retries_per_attempt': self.config.max_retries_per_attempt,
                'initial_retry_delay': self.config.initial_retry_delay,
                'max_retry_delay': self.config.max_retry_delay
            },
            'statistics': self.get_retry_statistics(),
            'pending_retries': [
                {
                    'url': entry['url'],
                    'attempt_count': entry['attempt_count'],
                    'error_type': entry['error_type'],
                    'last_error': entry['last_error'],
                    'time_since_first_attempt': time.time() - entry['first_attempt_time']
                }
                for entry in self.retry_queue
            ],
            'successful_urls': list(self.found_urls),
            'total_discovered': {
                'html_pages': len(self.found_urls),
                'pdf_documents': len(self.pdf_urls)
            }
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_adaptive_delay(self) -> float:
        """Berechne adaptiven Delay basierend auf Serververhalten."""
        base_delay = self.config.crawl_delay
        
        if self.config.randomize_delays:
            # Simuliere menschliche Lesezeit mit exponentieller Verteilung
            # Die meisten Menschen lesen 5-15s, manche länger
            reading_time = random.expovariate(1/12.0)  # Durchschnitt 12s
            reading_time = max(5.0, min(reading_time, 60.0))  # 5s - 60s Bereich
            
            # Grundlegende Navigation-Zeit (Zeit zum Finden des nächsten Links)
            navigation_time = random.uniform(2.0, 8.0)
            
            # Gesamtzeit = Lesezeit + Navigation
            delay = reading_time + navigation_time
            
            # Gelegentlich längere Pausen (Nutzer wird abgelenkt)
            if random.random() < 0.15:  # 15% der Zeit
                distraction_time = random.uniform(20, 40)  # 20s - 40s
                delay += distraction_time
                logger.info(f"🧠 Simuliere Ablenkung: +{distraction_time:.0f}s")
        else:
            delay = base_delay
        
        # Verlängere Delay bei vielen Rate Limit Fehlern
        rate_limit_ratio = self.retry_stats['rate_limit_errors'] / max(self.retry_stats['total_requests'], 1)
        if rate_limit_ratio > 0.1:  # Mehr als 10% Rate Limit Fehler
            delay *= (1 + rate_limit_ratio * 3)  # Bis zu 4x längerer Delay
            logger.info(f"🐌 Adaptive Delay: {delay:.1f}s (Rate Limit Ratio: {rate_limit_ratio:.2%})")
        
        return delay

    async def rotate_session_if_needed(self):
        """Rotiere Session alle X Requests."""
        if (self.config.session_rotation and 
            self.request_count > 0 and 
            self.request_count % self.config.session_rotation_interval == 0):
            
            logger.info(f"🔄 Session-Rotation nach {self.request_count} Requests...")
            await self.close()
            await asyncio.sleep(random.uniform(5, 15))  # Kurze Pause
            await self.init_session()

    def should_back_off(self) -> bool:
        """Prüfe ob längere Pause nötig ist."""
        if not self.config.respect_server_load:
            return False
        
        # Bei vielen Server-Fehlern -> längere Pause
        server_error_ratio = self.retry_stats['server_errors'] / max(self.retry_stats['total_requests'], 1)
        return server_error_ratio > 0.15  # Mehr als 15% Server-Fehler

    async def adaptive_back_off(self):
        """Intelligente Backoff-Strategie."""
        if self.should_back_off():
            backoff_time = random.uniform(60, 180)  # 1-3 Minuten
            logger.info(f"🛑 Server unter Last - Adaptive Backoff: {backoff_time:.0f}s")
            await asyncio.sleep(backoff_time)

    def get_current_headers(self) -> dict:
        """Erhalte realistische Browser-Headers für Request."""
        if not self.config.vary_user_agents:
            return {}
        
        headers = {}
        
        # Wechsle User Agent gelegentlich
        if self.request_count % 50 == 0:
            new_user_agent = random.choice(self.user_agents)
            headers['User-Agent'] = new_user_agent
        
        # Simuliere echtes Browser-Verhalten
        if self.config.vary_user_agents:
            # Sec-Fetch Headers (moderne Browser)
            headers.update({
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': random.choice(['same-origin', 'cross-site', 'none']),
                'Sec-Fetch-User': '?1',
            })
            
            # Cache-Control (echte Browser senden das)
            if random.random() < 0.4:  # 40% der Zeit
                headers['Cache-Control'] = random.choice([
                    'max-age=0',
                    'no-cache',
                    'no-store, no-cache, must-revalidate'
                ])
            
            # Realistic Accept Header (vollständiger)
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7'
            
            # Accept-Encoding mit modernen Formaten
            headers['Accept-Encoding'] = 'gzip, deflate, br, zstd'
            
            # Referer simulation (sehr wichtig!)
            if random.random() < 0.7 and len(self.found_urls) > 0:  # 70% der Zeit
                # Wähle zufällige bereits besuchte URL als Referer
                headers['Referer'] = random.choice(list(self.found_urls))
        
        return headers

    def get_failed_urls(self) -> List[tuple]:
        """
        Erhalte Liste der fehlgeschlagenen URLs.
        
        Returns:
            Liste von (url, error_type, error_message) Tuples
        """
        return self.failed_urls.copy()

    def export_failed_urls(self, filepath: str):
        """
        Exportiere fehlgeschlagene URLs in JSON-Datei.
        
        Args:
            filepath: Ziel-Dateipfad
        """
        from pathlib import Path
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'crawler_type': 'WisoCrawler',
            'timestamp': datetime.now().isoformat(),
            'failed_count': len(self.failed_urls),
            'retry_stats': self.retry_stats,
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
        
        logger.info(f"📄 Fehlgeschlagene URLs exportiert nach {filepath} ({len(self.failed_urls)} URLs)")

async def crawl_wiso_faculty() -> List[str]:
    """Helper function to run the crawler with default configuration."""
    config = CrawlerConfig()
    crawler = WisoCrawler(config)
    return await crawler.crawl()

def save_urls_to_file(urls: List[str], output_file: str):
    """Save discovered URLs to a JSON file."""
    data = {
        "timestamp": datetime.now().isoformat(),
        "total_urls": len(urls),
        "urls": urls
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Run crawler
    urls = asyncio.run(crawl_wiso_faculty())
    
    # Save results
    output_file = Path(__file__).parent / "discovered_urls.json"
    save_urls_to_file(urls, str(output_file))
    print(f"Discovered {len(urls)} URLs. Results saved to {output_file}")