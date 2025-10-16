"""
Intelligent Content Cleaning
============================

Entfernt Boilerplate-Inhalte und verbessert die Qualität extrahierter Texte.
"""

import re
from typing import List, Set
from bs4 import BeautifulSoup, Comment
import logging

logger = logging.getLogger(__name__)


class ContentCleaner:
    """
    Intelligenter Content Cleaner zur Verbesserung der Textqualität.
    
    Entfernt:
    - Navigationsmenüs
    - Footer-Inhalte
    - Cookie-Banner
    - Wiederholte Boilerplate-Texte
    - Übermäßige Leerzeichen
    """
    
    def __init__(self):
        """Initialisiere den Content Cleaner."""
        # Boilerplate-Patterns für deutsche Universitäts-Websites
        self.boilerplate_patterns = [
            r'Cookie[s]?[\s-]*(Richtlinie|Policy|Hinweis|Notice)',
            r'Datenschutz[\s-]*(erklärung|hinweis|bestimmungen)?',
            r'Impressum',
            r'©\s*\d{4}.*Universität',
            r'Alle Rechte vorbehalten',
            r'Diese Seite verwendet Cookies',
            r'Um unsere Webseite.*zu verbessern',
            r'Kontakt\s*\|\s*Impressum\s*\|\s*Datenschutz',
        ]
        
        # CSS-Selektoren für zu entfernende Elemente
        self.remove_selectors = [
            'nav', 'footer', 'header',
            '.navigation', '.nav', '.menu',
            '.cookie-banner', '.cookie-notice', '.cookie-consent',
            '.breadcrumb', '.breadcrumbs',
            '.sidebar', '.aside',
            '.advertisement', '.ads', '.ad',
            '.social-media', '.social-links',
            '.share-buttons', '.sharing',
            'script', 'style', 'noscript',
        ]
        
        # Mindestlänge für sinnvollen Content
        self.min_content_length = 100
        
    def clean_html(self, html: str) -> str:
        """
        Bereinige HTML und extrahiere Hauptinhalt.
        
        Args:
            html: Roher HTML-String
            
        Returns:
            Gereinigter Text-Inhalt
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # Entferne Kommentare
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()
        
        # Entferne unerwünschte Elemente
        for selector in self.remove_selectors:
            for element in soup.select(selector):
                element.decompose()
        
        # Extrahiere Hauptinhalt
        main_content = self._extract_main_content(soup)
        
        # Bereinige Text
        cleaned_text = self._clean_text(main_content)
        
        return cleaned_text
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extrahiere Hauptinhalt aus HTML.
        
        Args:
            soup: BeautifulSoup-Objekt
            
        Returns:
            Hauptinhalt als Text
        """
        # Versuche main-Tags zu finden
        main_tags = ['main', 'article', '[role="main"]']
        
        for tag in main_tags:
            main_element = soup.select_one(tag)
            if main_element:
                return main_element.get_text(separator='\n', strip=True)
        
        # Fallback: Extrahiere aus body
        body = soup.find('body')
        if body:
            return body.get_text(separator='\n', strip=True)
        
        # Letzter Fallback: Gesamter Text
        return soup.get_text(separator='\n', strip=True)
    
    def _clean_text(self, text: str) -> str:
        """
        Bereinige extrahierten Text.
        
        Args:
            text: Roher Text
            
        Returns:
            Gereinigter Text
        """
        # Entferne Boilerplate-Patterns
        for pattern in self.boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Normalisiere Leerzeichen
        text = re.sub(r'\s+', ' ', text)
        
        # Entferne mehrfache Zeilenumbrüche
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Entferne führende/nachfolgende Leerzeichen
        text = text.strip()
        
        return text
    
    def remove_duplicated_lines(self, text: str, min_occurrences: int = 3) -> str:
        """
        Entferne Zeilen, die zu oft wiederholt werden (Boilerplate).
        
        Args:
            text: Eingabetext
            min_occurrences: Minimale Anzahl an Wiederholungen für Entfernung
            
        Returns:
            Text ohne wiederholte Zeilen
        """
        lines = text.split('\n')
        line_counts = {}
        
        # Zähle Zeilen
        for line in lines:
            stripped = line.strip()
            if len(stripped) > 10:  # Ignoriere sehr kurze Zeilen
                line_counts[stripped] = line_counts.get(stripped, 0) + 1
        
        # Identifiziere Boilerplate-Zeilen
        boilerplate_lines = {
            line for line, count in line_counts.items()
            if count >= min_occurrences
        }
        
        # Filtere Boilerplate-Zeilen
        filtered_lines = [
            line for line in lines
            if line.strip() not in boilerplate_lines
        ]
        
        if boilerplate_lines:
            logger.debug(f"Entfernte {len(boilerplate_lines)} Boilerplate-Zeilen")
        
        return '\n'.join(filtered_lines)
    
    def is_substantial_content(self, text: str) -> bool:
        """
        Prüfe ob Text substantiellen Inhalt hat.
        
        Args:
            text: Zu prüfender Text
            
        Returns:
            True wenn Text substantiell ist
        """
        # Längenprüfung
        if len(text) < self.min_content_length:
            return False
        
        # Wortanzahl-Prüfung
        words = text.split()
        if len(words) < 20:
            return False
        
        # Durchschnittliche Wortlänge (zu kurz = meist Navigation)
        avg_word_length = sum(len(word) for word in words) / len(words)
        if avg_word_length < 3:
            return False
        
        return True
    
    def clean_document(self, content: dict) -> dict:
        """
        Bereinige ein vollständiges Dokument.
        
        Args:
            content: Dictionary mit 'content' und optional 'html' Keys
            
        Returns:
            Gereinigtes Dokument
        """
        cleaned = content.copy()
        
        # Bereinige Text-Inhalt
        if 'content' in cleaned:
            text = cleaned['content']
            text = self._clean_text(text)
            text = self.remove_duplicated_lines(text)
            cleaned['content'] = text
            
            # Füge Quality-Indikatoren hinzu
            cleaned['is_substantial'] = self.is_substantial_content(text)
            cleaned['word_count'] = len(text.split())
            cleaned['char_count'] = len(text)
        
        return cleaned
