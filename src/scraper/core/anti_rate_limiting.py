"""
Anti-Rate-Limiting Strategien für Web Scraper
=============================================

Verschiedene ethische Ansätze um Serverbegrenzungen respektvoll zu umgehen.
"""

import asyncio
import random
import time
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class BypassStrategy(Enum):
    """Verschiedene Umgehungsstrategien."""
    CONSERVATIVE = "conservative"    # Sehr respektvoll, langsam aber sicher
    ADAPTIVE = "adaptive"           # Passt sich an Serververhalten an
    STEALTH = "stealth"            # Simuliert normales Browser-Verhalten
    AGGRESSIVE = "aggressive"      # Schneller, höheres Blockierung-Risiko
    
@dataclass
class AntiRateLimitConfig:
    """Konfiguration für Anti-Rate-Limiting."""
    strategy: BypassStrategy = BypassStrategy.ADAPTIVE
    
    # Timing-Strategien
    min_delay: float = 10.0
    max_delay: float = 30.0
    randomize_timing: bool = True
    
    # Session-Management
    rotate_sessions: bool = True
    session_lifetime_requests: int = 100
    session_break_duration: tuple = (10, 30)  # Min, Max Sekunden
    
    # Header-Strategien
    rotate_user_agents: bool = True
    simulate_browser_behavior: bool = True
    add_realistic_headers: bool = True
    
    # Adaptive Verhalten
    monitor_error_rates: bool = True
    auto_adjust_delays: bool = True
    backoff_on_errors: bool = True
    max_error_threshold: float = 0.15  # 15% Fehlerrate
    
    # Respekt vor Server
    respect_robots_txt: bool = True
    honor_retry_after: bool = True
    detect_server_load: bool = True

class AntiRateLimiter:
    """Anti-Rate-Limiting Engine."""
    
    def __init__(self, config: AntiRateLimitConfig):
        self.config = config
        self.stats = {
            'total_requests': 0,
            'success_rate': 0.0,
            'avg_response_time': 0.0,
            'rate_limit_hits': 0,
            'server_errors': 0,
            'current_delay': config.min_delay
        }
        self.last_request_time = 0
        self.session_request_count = 0
        
        # User Agent Pool für verschiedene Browser
        self.user_agent_pool = [
            # Chrome auf Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            # Firefox auf Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
            # Safari auf macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
            # Chrome auf macOS
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Edge auf Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
            # Chrome auf Linux
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]

    def get_strategy_config(self) -> Dict:
        """Erhalte spezifische Konfiguration basierend auf gewählter Strategie."""
        if self.config.strategy == BypassStrategy.CONSERVATIVE:
            return {
                'min_delay': 30.0,
                'max_delay': 60.0,
                'session_lifetime': 50,
                'concurrent_limit': 1,
                'aggressive_retries': False
            }
        elif self.config.strategy == BypassStrategy.STEALTH:
            return {
                'min_delay': 15.0,
                'max_delay': 45.0,
                'session_lifetime': 150,
                'concurrent_limit': 1,
                'simulate_human': True
            }
        elif self.config.strategy == BypassStrategy.ADAPTIVE:
            return {
                'min_delay': 10.0,
                'max_delay': 30.0,
                'session_lifetime': 100,
                'concurrent_limit': 2,
                'auto_adjust': True
            }
        elif self.config.strategy == BypassStrategy.AGGRESSIVE:
            return {
                'min_delay': 5.0,
                'max_delay': 15.0,
                'session_lifetime': 200,
                'concurrent_limit': 3,
                'fast_retries': True
            }
        else:
            return self.get_strategy_config_adaptive()

    def calculate_optimal_delay(self, error_rate: float = 0.0) -> float:
        """Berechne optimalen Delay basierend auf aktueller Situation."""
        base_delay = random.uniform(self.config.min_delay, self.config.max_delay)
        
        if self.config.auto_adjust_delays:
            # Verlängere Delay bei hoher Fehlerrate
            if error_rate > self.config.max_error_threshold:
                multiplier = 1 + (error_rate * 3)  # Bis zu 4x längerer Delay
                base_delay *= multiplier
                logger.info(f"🐌 Adaptive Delay Increase: {base_delay:.1f}s (Error Rate: {error_rate:.2%})")
        
        return base_delay

    def get_realistic_headers(self) -> Dict[str, str]:
        """Generiere realistische Browser-Headers."""
        if not self.config.add_realistic_headers:
            return {}
        
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
        }
        
        if self.config.rotate_user_agents:
            headers['User-Agent'] = random.choice(self.user_agent_pool)
        
        # Simuliere echtes Browser-Verhalten
        if self.config.simulate_browser_behavior:
            # Füge gelegentlich Cache-Control hinzu
            if random.random() < 0.3:
                headers['Cache-Control'] = random.choice(['no-cache', 'max-age=0'])
            
            # Füge gelegentlich Referer hinzu (nur für dieselbe Domain)
            if random.random() < 0.2:
                headers['Referer'] = 'https://wiso.uni-koeln.de/de/'
        
        return headers

    async def wait_for_next_request(self, last_error_type: Optional[str] = None) -> None:
        """Warte angemessene Zeit vor nächstem Request."""
        current_time = time.time()
        
        # Spezielle Behandlung für verschiedene Fehlertypen
        if last_error_type == 'rate_limit':
            # Rate Limit -> längere Pause
            delay = random.uniform(30, 90)
            logger.warning(f"🚫 Rate Limit detected - waiting {delay:.0f}s")
        elif last_error_type in ['server_error', 'timeout']:
            # Server-Probleme -> moderate Pause
            delay = random.uniform(15, 45)
            logger.warning(f"🔧 Server issues - waiting {delay:.0f}s")
        else:
            # Normaler Delay
            error_rate = self.stats.get('rate_limit_hits', 0) / max(self.stats.get('total_requests', 1), 1)
            delay = self.calculate_optimal_delay(error_rate)
        
        # Respektiere Minimum-Intervall
        if self.last_request_time > 0:
            time_since_last = current_time - self.last_request_time
            if time_since_last < delay:
                wait_time = delay - time_since_last
                await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()

    def should_rotate_session(self) -> bool:
        """Prüfe ob Session rotiert werden sollte."""
        if not self.config.rotate_sessions:
            return False
        
        return self.session_request_count >= self.config.session_lifetime_requests

    async def rotate_session_break(self) -> None:
        """Pause zwischen Session-Rotationen."""
        if self.config.session_break_duration:
            min_break, max_break = self.config.session_break_duration
            break_time = random.uniform(min_break, max_break)
            logger.info(f"🔄 Session rotation break: {break_time:.0f}s")
            await asyncio.sleep(break_time)

    def update_stats(self, success: bool, response_time: float, error_type: Optional[str] = None):
        """Aktualisiere Performance-Statistiken."""
        self.stats['total_requests'] += 1
        self.session_request_count += 1
        
        # Success Rate
        if success:
            old_avg = self.stats['avg_response_time']
            old_count = self.stats['total_requests'] - 1
            self.stats['avg_response_time'] = (old_avg * old_count + response_time) / self.stats['total_requests']
        
        # Error Tracking
        if error_type == 'rate_limit':
            self.stats['rate_limit_hits'] += 1
        elif error_type in ['server_error', 'timeout']:
            self.stats['server_errors'] += 1
        
        # Success Rate berechnen
        success_count = self.stats['total_requests'] - self.stats['rate_limit_hits'] - self.stats['server_errors']
        self.stats['success_rate'] = success_count / self.stats['total_requests']

    def get_performance_report(self) -> Dict:
        """Erhalte Performance-Report."""
        return {
            'strategy': self.config.strategy.value,
            'total_requests': self.stats['total_requests'],
            'success_rate': f"{self.stats['success_rate']:.2%}",
            'avg_response_time': f"{self.stats['avg_response_time']:.2f}s",
            'rate_limit_hits': self.stats['rate_limit_hits'],
            'server_errors': self.stats['server_errors'],
            'current_session_requests': self.session_request_count,
            'recommendations': self._get_recommendations()
        }

    def _get_recommendations(self) -> List[str]:
        """Erhalte Empfehlungen basierend auf Performance."""
        recommendations = []
        
        if self.stats['rate_limit_hits'] / max(self.stats['total_requests'], 1) > 0.1:
            recommendations.append("Erhöhe Delays - zu viele Rate Limits")
        
        if self.stats['server_errors'] / max(self.stats['total_requests'], 1) > 0.2:
            recommendations.append("Server unter Last - nutze CONSERVATIVE Strategie")
        
        if self.stats['success_rate'] < 0.7:
            recommendations.append("Niedrige Success Rate - überprüfe Strategie")
        
        if not recommendations:
            recommendations.append("Performance OK - aktuelle Strategie beibehalten")
        
        return recommendations

# Vordefinierte Strategiekonfigurationen
STRATEGY_CONFIGS = {
    BypassStrategy.CONSERVATIVE: AntiRateLimitConfig(
        strategy=BypassStrategy.CONSERVATIVE,
        min_delay=30.0,
        max_delay=60.0,
        session_lifetime_requests=50,
        session_break_duration=(20, 40)
    ),
    BypassStrategy.STEALTH: AntiRateLimitConfig(
        strategy=BypassStrategy.STEALTH,
        min_delay=15.0,
        max_delay=45.0,
        session_lifetime_requests=150,
        simulate_browser_behavior=True,
        randomize_timing=True
    ),
    BypassStrategy.ADAPTIVE: AntiRateLimitConfig(
        strategy=BypassStrategy.ADAPTIVE,
        min_delay=10.0,
        max_delay=30.0,
        auto_adjust_delays=True,
        monitor_error_rates=True
    ),
    BypassStrategy.AGGRESSIVE: AntiRateLimitConfig(
        strategy=BypassStrategy.AGGRESSIVE,
        min_delay=5.0,
        max_delay=15.0,
        session_lifetime_requests=200,
        respect_robots_txt=False  # Nur für Testzwecke!
    )
}