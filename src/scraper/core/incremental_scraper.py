"""
Incremental Scraping System
============================

Ermöglicht inkrementelles Scraping - nur neue oder geänderte Inhalte werden erfasst.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import json
import logging

from src.scraper.utils.url_cache import URLCache

logger = logging.getLogger(__name__)


class IncrementalScraper:
    """
    Inkrementelles Scraping-System.
    
    Features:
    - Change Detection
    - Intelligente Re-Scraping-Strategien
    - Priority-basiertes Scheduling
    - Diff-Tracking
    """
    
    def __init__(self, cache: URLCache = None):
        """
        Initialisiere Incremental Scraper.
        
        Args:
            cache: URL-Cache-Instanz
        """
        self.cache = cache or URLCache()
        self.changes_detected = []
        self.skipped_urls = []
    
    def should_rescrape(
        self,
        url: str,
        category: str = None,
        force: bool = False
    ) -> tuple[bool, str]:
        """
        Entscheide ob URL erneut gescraped werden soll.
        
        Args:
            url: URL
            category: Content-Kategorie
            force: Erzwinge Scraping
            
        Returns:
            Tuple von (should_scrape, reason)
        """
        if force:
            return True, "forced"
        
        # Nicht im Cache -> scrapen
        cached = self.cache.get(url)
        if not cached:
            return True, "new_url"
        
        # Letzter Scrape war nicht erfolgreich -> erneut versuchen
        if not cached.success:
            return True, "previous_failure"
        
        # Bestimme Freshness basierend auf Content-Typ
        url_lower = url.lower()
        
        # News/Aktuelles: Täglich
        if '/news/' in url_lower or '/aktuelles/' in url_lower:
            max_age = timedelta(days=1)
            priority = "high"
        
        # Veranstaltungen: Täglich
        elif '/event/' in url_lower or '/veranstaltung' in url_lower:
            max_age = timedelta(days=1)
            priority = "high"
        
        # Prüfungsordnungen: Semesterly (90 Tage)
        elif 'pruefungsordnung' in url_lower or '/po-' in url_lower:
            max_age = timedelta(days=90)
            priority = "low"
        
        # Modulhandbücher: Semesterly
        elif 'modulhandbuch' in url_lower:
            max_age = timedelta(days=90)
            priority = "low"
        
        # Kontakte: Alle 3 Monate
        elif '/kontakt' in url_lower or '/contact' in url_lower:
            max_age = timedelta(days=90)
            priority = "low"
        
        # Forschung: Monatlich
        elif '/forschung' in url_lower or '/research' in url_lower:
            max_age = timedelta(days=30)
            priority = "medium"
        
        # Statische Seiten: Monatlich
        else:
            max_age = timedelta(days=30)
            priority = "medium"
        
        # Prüfe Alter
        age = datetime.now() - cached.last_scraped
        
        if age < max_age:
            self.skipped_urls.append({
                'url': url,
                'age_days': age.days,
                'max_age_days': max_age.days,
                'priority': priority
            })
            return False, f"fresh_cache_{age.days}d"
        
        return True, f"expired_cache_{age.days}d"
    
    def filter_urls_for_scraping(
        self,
        urls: List[str],
        categories: Dict[str, str] = None,
        force: bool = False
    ) -> Dict[str, List[str]]:
        """
        Filtere URLs und kategorisiere nach Scraping-Bedarf.
        
        Args:
            urls: Liste von URLs
            categories: Mapping von URL zu Kategorie
            force: Erzwinge Scraping aller URLs
            
        Returns:
            Dictionary mit kategorisierten URLs
        """
        categories = categories or {}
        
        result = {
            'to_scrape': [],
            'skipped': [],
            'new': [],
            'expired': [],
            'failed_before': []
        }
        
        for url in urls:
            category = categories.get(url)
            should_scrape, reason = self.should_rescrape(url, category, force)
            
            if should_scrape:
                result['to_scrape'].append(url)
                
                if reason == "new_url":
                    result['new'].append(url)
                elif reason == "previous_failure":
                    result['failed_before'].append(url)
                elif reason.startswith("expired"):
                    result['expired'].append(url)
            else:
                result['skipped'].append(url)
        
        logger.info(
            f"URL-Filterung: {len(result['to_scrape'])} zu scrapen, "
            f"{len(result['skipped'])} übersprungen"
        )
        
        return result
    
    def detect_changes(
        self,
        url: str,
        new_content: str
    ) -> Dict[str, Any]:
        """
        Erkenne Änderungen im Content.
        
        Args:
            url: URL
            new_content: Neuer Inhalt
            
        Returns:
            Dictionary mit Change-Informationen
        """
        cached = self.cache.get(url)
        
        if not cached:
            return {
                'changed': True,
                'change_type': 'new',
                'details': 'URL war nicht im Cache'
            }
        
        # Content-Hash-Vergleich
        new_hash = self.cache.compute_content_hash(new_content)
        
        if new_hash == cached.content_hash:
            return {
                'changed': False,
                'change_type': 'identical',
                'details': 'Inhalt unverändert'
            }
        
        # Inhalt hat sich geändert
        old_word_count = cached.metadata.get('word_count', 0)
        new_word_count = len(new_content.split())
        
        word_diff = new_word_count - old_word_count
        word_diff_pct = (word_diff / old_word_count * 100) if old_word_count > 0 else 0
        
        change_info = {
            'changed': True,
            'change_type': 'modified',
            'details': {
                'old_hash': cached.content_hash,
                'new_hash': new_hash,
                'word_count_old': old_word_count,
                'word_count_new': new_word_count,
                'word_count_diff': word_diff,
                'word_count_diff_pct': word_diff_pct,
                'last_scraped': cached.last_scraped.isoformat()
            }
        }
        
        self.changes_detected.append({
            'url': url,
            'detected_at': datetime.now().isoformat(),
            **change_info
        })
        
        logger.info(
            f"Änderung erkannt für {url}: "
            f"{word_diff:+d} Wörter ({word_diff_pct:+.1f}%)"
        )
        
        return change_info
    
    def prioritize_urls(
        self,
        urls: List[str],
        categories: Dict[str, str] = None
    ) -> List[tuple[str, int]]:
        """
        Priorisiere URLs basierend auf Wichtigkeit und Aktualität.
        
        Args:
            urls: Liste von URLs
            categories: Mapping von URL zu Kategorie
            
        Returns:
            Liste von (url, priority) Tuples, sortiert nach Priorität
        """
        categories = categories or {}
        priorities = []
        
        for url in urls:
            priority_score = self._calculate_priority(url, categories.get(url))
            priorities.append((url, priority_score))
        
        # Sortiere nach Priorität (höher zuerst)
        priorities.sort(key=lambda x: x[1], reverse=True)
        
        return priorities
    
    def _calculate_priority(self, url: str, category: str = None) -> int:
        """
        Berechne Prioritäts-Score für URL.
        
        Args:
            url: URL
            category: Content-Kategorie
            
        Returns:
            Priorität (0-100, höher = wichtiger)
        """
        url_lower = url.lower()
        score = 50  # Basis-Score
        
        # News/Aktuelles: Höchste Priorität
        if '/news/' in url_lower or '/aktuelles/' in url_lower:
            score = 90
        
        # Veranstaltungen: Hohe Priorität
        elif '/event/' in url_lower or '/veranstaltung' in url_lower:
            score = 85
        
        # Bewerbung/Admission: Hohe Priorität
        elif '/bewerbung' in url_lower or '/application' in url_lower or '/admission' in url_lower:
            score = 80
        
        # Studium: Mittel-hohe Priorität
        elif '/studium' in url_lower or '/studies' in url_lower:
            score = 70
        
        # Prüfungen: Mittel-hohe Priorität
        elif '/pruefung' in url_lower or '/exam' in url_lower:
            score = 70
        
        # Forschung: Mittlere Priorität
        elif '/forschung' in url_lower or '/research' in url_lower:
            score = 60
        
        # Fakultät/Faculty: Mittlere Priorität
        elif '/fakultaet' in url_lower or '/faculty' in url_lower:
            score = 55
        
        # Kontakt: Niedrige Priorität
        elif '/kontakt' in url_lower or '/contact' in url_lower:
            score = 40
        
        # Prüfungsordnungen: Niedrige Priorität (selten geändert)
        elif 'pruefungsordnung' in url_lower:
            score = 30
        
        # Prüfe Cache-Alter für Bonus
        cached = self.cache.get(url)
        if cached:
            age_days = (datetime.now() - cached.last_scraped).days
            
            # Bonus für lange nicht gescraped
            if age_days > 90:
                score += 20
            elif age_days > 30:
                score += 10
            
            # Malus für kürzlich gescraped
            if age_days < 7:
                score -= 20
        else:
            # Neu -> hoher Bonus
            score += 30
        
        return min(100, max(0, score))
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Erhalte Statistiken über inkrementelles Scraping.
        
        Returns:
            Dictionary mit Statistiken
        """
        return {
            'changes_detected': len(self.changes_detected),
            'urls_skipped': len(self.skipped_urls),
            'cache_stats': self.cache.get_statistics() if self.cache else {}
        }
    
    def export_changes_report(self, filepath: Path):
        """
        Exportiere Änderungs-Report.
        
        Args:
            filepath: Ziel-Dateipfad
        """
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'changes_detected': self.changes_detected,
            'skipped_urls': self.skipped_urls
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Änderungs-Report exportiert nach {filepath}")
