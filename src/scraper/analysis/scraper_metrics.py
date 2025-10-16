"""
Scraper Metrics & Analytics
===========================

Sammelt detaillierte Metriken während des Scrapings für Monitoring und Optimierung.
"""

import time
from typing import Dict, Any, List
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ScraperMetrics:
    """
    Sammelt und analysiert Scraping-Metriken.
    
    Tracked:
    - Erfolgsraten
    - Response Times
    - Content-Größen
    - Fehler nach Typ
    - Kategorien-Verteilung
    """
    
    def __init__(self):
        """Initialisiere Metrics-Collector."""
        self.start_time = datetime.now()
        
        self.metrics = {
            'urls_crawled': 0,
            'urls_successful': 0,
            'urls_failed': 0,
            'pdfs_found': 0,
            'pdfs_extracted': 0,
            'pdfs_failed': 0,
            'duplicates_removed': 0,
            'response_times': [],
            'content_sizes': [],
            'errors': defaultdict(int),
            'categories': defaultdict(int),
            'status_codes': defaultdict(int),
            'pdf_extraction_methods': defaultdict(int),
        }
        
        self.url_details = []
        
    def record_url(
        self,
        url: str,
        success: bool,
        status_code: int = None,
        response_time: float = None,
        content_size: int = None,
        category: str = None,
        error: str = None
    ):
        """
        Zeichne URL-Zugriff auf.
        
        Args:
            url: Zugegriffene URL
            success: Ob erfolgreich
            status_code: HTTP-Status-Code
            response_time: Response-Zeit in Sekunden
            content_size: Größe des Inhalts in Bytes
            category: Kategorie des Inhalts
            error: Fehlermeldung falls vorhanden
        """
        self.metrics['urls_crawled'] += 1
        
        if success:
            self.metrics['urls_successful'] += 1
        else:
            self.metrics['urls_failed'] += 1
        
        if status_code:
            self.metrics['status_codes'][status_code] += 1
        
        if response_time is not None:
            self.metrics['response_times'].append(response_time)
        
        if content_size is not None:
            self.metrics['content_sizes'].append(content_size)
        
        if category:
            self.metrics['categories'][category] += 1
        
        if error:
            self.metrics['errors'][error] += 1
        
        # Detaillierte URL-Info speichern
        self.url_details.append({
            'url': url,
            'success': success,
            'status_code': status_code,
            'response_time': response_time,
            'content_size': content_size,
            'category': category,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
    
    def record_pdf(
        self,
        url: str,
        success: bool,
        extraction_method: str = None,
        num_pages: int = None,
        file_size: int = None,
        error: str = None
    ):
        """
        Zeichne PDF-Extraktion auf.
        
        Args:
            url: PDF-URL
            success: Ob erfolgreich extrahiert
            extraction_method: Verwendete Extraktionsmethode
            num_pages: Anzahl der Seiten
            file_size: Dateigröße in Bytes
            error: Fehlermeldung falls vorhanden
        """
        self.metrics['pdfs_found'] += 1
        
        if success:
            self.metrics['pdfs_extracted'] += 1
            if extraction_method:
                self.metrics['pdf_extraction_methods'][extraction_method] += 1
        else:
            self.metrics['pdfs_failed'] += 1
            if error:
                self.metrics['errors'][f"pdf_{error}"] += 1
    
    def record_duplicate(self, url: str, reason: str):
        """
        Zeichne Duplikat auf.
        
        Args:
            url: Duplikat-URL
            reason: Grund für Duplikat
        """
        self.metrics['duplicates_removed'] += 1
        self.metrics['errors'][f"duplicate_{reason}"] += 1
    
    def calculate_success_rate(self) -> float:
        """
        Berechne Erfolgsrate.
        
        Returns:
            Erfolgsrate zwischen 0.0 und 1.0
        """
        total = self.metrics['urls_crawled']
        if total == 0:
            return 0.0
        return self.metrics['urls_successful'] / total
    
    def get_avg_response_time(self) -> float:
        """
        Berechne durchschnittliche Response-Zeit.
        
        Returns:
            Durchschnitt in Sekunden
        """
        times = self.metrics['response_times']
        if not times:
            return 0.0
        return sum(times) / len(times)
    
    def get_avg_content_size(self) -> int:
        """
        Berechne durchschnittliche Content-Größe.
        
        Returns:
            Durchschnitt in Bytes
        """
        sizes = self.metrics['content_sizes']
        if not sizes:
            return 0
        return int(sum(sizes) / len(sizes))
    
    def get_total_content_size(self) -> int:
        """
        Berechne Gesamt-Content-Größe.
        
        Returns:
            Summe in Bytes
        """
        return sum(self.metrics['content_sizes'])
    
    def get_elapsed_time(self) -> float:
        """
        Berechne verstrichene Zeit seit Start.
        
        Returns:
            Zeit in Sekunden
        """
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_crawl_rate(self) -> float:
        """
        Berechne Crawl-Rate (URLs pro Sekunde).
        
        Returns:
            Rate als Float
        """
        elapsed = self.get_elapsed_time()
        if elapsed == 0:
            return 0.0
        return self.metrics['urls_crawled'] / elapsed
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Erhalte umfassende Statistiken.
        
        Returns:
            Dictionary mit allen Statistiken
        """
        success_rate = (self.metrics['urls_successful'] / self.metrics['urls_crawled'] * 100 
                       if self.metrics['urls_crawled'] > 0 else 0)
        
        return {
            'urls_crawled': self.metrics['urls_crawled'],
            'urls_successful': self.metrics['urls_successful'],
            'urls_failed': self.metrics['urls_failed'],
            'success_rate': success_rate,
            'avg_response_time': self.get_avg_response_time(),
            'avg_content_size': self.get_avg_content_size(),
            'total_content_size': self.get_total_content_size(),
            'elapsed_time': self.get_elapsed_time(),
            'crawl_rate': self.get_crawl_rate(),
            'categories': dict(self.metrics['categories']),
            'status_codes': dict(self.metrics['status_codes']),
            'error_summary': dict(self.metrics['errors'])
        }
    
    def format_categories(self) -> str:
        """
        Formatiere Kategorien-Verteilung.
        
        Returns:
            Formatierter String
        """
        if not self.metrics['categories']:
            return "  Keine Kategorien"
        
        lines = []
        for category, count in sorted(
            self.metrics['categories'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            percentage = (count / self.metrics['urls_successful']) * 100
            lines.append(f"  - {category}: {count} ({percentage:.1f}%)")
        
        return '\n'.join(lines)
    
    def format_errors(self) -> str:
        """
        Formatiere Fehler-Übersicht.
        
        Returns:
            Formatierter String
        """
        if not self.metrics['errors']:
            return "  Keine Fehler"
        
        lines = []
        for error, count in sorted(
            self.metrics['errors'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]:  # Top 10 Fehler
            lines.append(f"  - {error}: {count}")
        
        return '\n'.join(lines)
    
    def export_report(self, filepath: Path = None) -> str:
        """
        Generiere detaillierten Text-Bericht.
        
        Args:
            filepath: Optional - Pfad zum Speichern des Reports als JSON
        
        Returns:
            Formatierter Bericht
        """
        elapsed = self.get_elapsed_time()
        
        # Wenn Filepath angegeben, exportiere als JSON
        if filepath:
            stats = self.get_statistics()
            stats['start_time'] = self.start_time.isoformat()
            stats['url_details'] = self.url_details[-100:]  # Nur letzte 100
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Metriken exportiert nach {filepath}")
        
        # Generiere Text-Report
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║              SCRAPING METRIKEN BERICHT                       ║
╚══════════════════════════════════════════════════════════════╝

🕐 Zeitinformationen
  Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
  Dauer: {elapsed:.1f}s ({elapsed/60:.1f} Minuten)
  Crawl-Rate: {self.get_crawl_rate():.2f} URLs/s

📊 URL-Statistiken
  Gesamt gecrawlt: {self.metrics['urls_crawled']}
  Erfolgreich: {self.metrics['urls_successful']}
  Fehlgeschlagen: {self.metrics['urls_failed']}
  Erfolgsrate: {self.calculate_success_rate():.1%}
  Duplikate entfernt: {self.metrics['duplicates_removed']}

📄 PDF-Statistiken
  Gefunden: {self.metrics['pdfs_found']}
  Erfolgreich extrahiert: {self.metrics['pdfs_extracted']}
  Fehlgeschlagen: {self.metrics['pdfs_failed']}

⚡ Performance
  Ø Response-Zeit: {self.get_avg_response_time():.2f}s
  Ø Content-Größe: {self.get_avg_content_size() / 1024:.1f} KB
  Gesamt-Content: {self.get_total_content_size() / (1024*1024):.1f} MB

📁 Kategorien-Verteilung
{self.format_categories()}

❌ Top Fehler
{self.format_errors()}

🔧 HTTP Status Codes
"""
        
        for code, count in sorted(self.metrics['status_codes'].items()):
            report += f"  - {code}: {count}\n"
        
        if self.metrics['pdf_extraction_methods']:
            report += "\n📚 PDF Extraktions-Methoden\n"
            for method, count in self.metrics['pdf_extraction_methods'].items():
                report += f"  - {method}: {count}\n"
        
        report += "\n" + "="*64 + "\n"
        
        return report
    
    def export_json(self, filepath: Path):
        """
        Exportiere Metriken als JSON.
        
        Args:
            filepath: Ziel-Dateipfad
        """
        data = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'elapsed_seconds': self.get_elapsed_time(),
            'summary': {
                'urls_crawled': self.metrics['urls_crawled'],
                'urls_successful': self.metrics['urls_successful'],
                'urls_failed': self.metrics['urls_failed'],
                'success_rate': self.calculate_success_rate(),
                'pdfs_found': self.metrics['pdfs_found'],
                'pdfs_extracted': self.metrics['pdfs_extracted'],
                'duplicates_removed': self.metrics['duplicates_removed'],
                'avg_response_time': self.get_avg_response_time(),
                'avg_content_size': self.get_avg_content_size(),
                'total_content_size': self.get_total_content_size(),
                'crawl_rate': self.get_crawl_rate(),
            },
            'categories': dict(self.metrics['categories']),
            'errors': dict(self.metrics['errors']),
            'status_codes': dict(self.metrics['status_codes']),
            'pdf_extraction_methods': dict(self.metrics['pdf_extraction_methods']),
            'url_details': self.url_details
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metriken exportiert nach {filepath}")
