"""
Content Deduplication für Web Scraping
======================================

Entfernt near-duplicate Dokumente mithilfe von MinHash und Simhash.
"""

import hashlib
from typing import List, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ContentFingerprint:
    """Fingerprint eines Dokuments für Deduplication"""
    url: str
    content_hash: str
    shingles_hash: str
    word_count: int


class ContentDeduplicator:
    """
    Dedupliziert Inhalte basierend auf Similarity-Hashing.
    
    Verwendet Shingling und MinHash für effiziente near-duplicate Erkennung.
    """
    
    def __init__(self, similarity_threshold: float = 0.85, shingle_size: int = 3):
        """
        Initialisiere den Deduplicator.
        
        Args:
            similarity_threshold: Schwellwert für Ähnlichkeit (0.0-1.0)
            shingle_size: Größe der Shingles für Vergleich
        """
        self.similarity_threshold = similarity_threshold
        self.shingle_size = shingle_size
        self.seen_fingerprints: Set[str] = set()
        self.url_to_fingerprint: dict = {}
        
    def create_shingles(self, text: str) -> Set[str]:
        """
        Erstelle Shingles (n-grams) aus Text.
        
        Args:
            text: Eingabetext
            
        Returns:
            Set von Shingles
        """
        # Normalisiere Text
        text = text.lower().strip()
        words = text.split()
        
        # Erstelle Wort-Shingles
        shingles = set()
        for i in range(len(words) - self.shingle_size + 1):
            shingle = " ".join(words[i:i + self.shingle_size])
            shingles.add(shingle)
        
        return shingles
    
    def compute_content_hash(self, text: str) -> str:
        """
        Berechne eindeutigen Hash für Inhalt.
        
        Args:
            text: Eingabetext
            
        Returns:
            SHA256-Hash als Hex-String
        """
        normalized = text.lower().strip()
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
    
    def compute_shingles_hash(self, shingles: Set[str]) -> str:
        """
        Berechne Hash für Shingles-Set.
        
        Args:
            shingles: Set von Shingles
            
        Returns:
            Hash-Repräsentation
        """
        # Sortiere für konsistenten Hash
        sorted_shingles = sorted(shingles)
        combined = "".join(sorted_shingles)
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def jaccard_similarity(self, set1: Set[str], set2: Set[str]) -> float:
        """
        Berechne Jaccard-Ähnlichkeit zwischen zwei Sets.
        
        Args:
            set1: Erstes Set
            set2: Zweites Set
            
        Returns:
            Ähnlichkeit zwischen 0.0 und 1.0
        """
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def is_duplicate(self, text: str, url: str) -> Tuple[bool, str]:
        """
        Prüfe ob Text ein Duplikat ist.
        
        Args:
            text: Zu prüfender Text
            url: URL des Dokuments
            
        Returns:
            Tuple von (ist_duplikat, grund)
        """
        # Exakte Duplikate
        content_hash = self.compute_content_hash(text)
        if content_hash in self.seen_fingerprints:
            return True, "exact_duplicate"
        
        # Near-duplicates
        shingles = self.create_shingles(text)
        
        # Prüfe gegen alle gesehenen Dokumente
        for seen_url, fingerprint in self.url_to_fingerprint.items():
            seen_shingles = self.create_shingles(
                self.url_to_fingerprint[seen_url].get('text', '')
            )
            
            similarity = self.jaccard_similarity(shingles, seen_shingles)
            
            if similarity >= self.similarity_threshold:
                logger.info(
                    f"Near-duplicate gefunden: {url} ähnlich zu {seen_url} "
                    f"(Similarity: {similarity:.2f})"
                )
                return True, f"near_duplicate_{similarity:.2f}"
        
        # Kein Duplikat - speichere Fingerprint
        self.seen_fingerprints.add(content_hash)
        self.url_to_fingerprint[url] = {
            'content_hash': content_hash,
            'shingles_hash': self.compute_shingles_hash(shingles),
            'text': text[:5000],  # Speichere nur Anfang für Vergleiche
            'word_count': len(text.split())
        }
        
        return False, "unique"
    
    def deduplicate_batch(self, documents: List[dict]) -> Tuple[List[dict], List[dict]]:
        """
        Dedupliziere eine Batch von Dokumenten.
        
        Args:
            documents: Liste von Dokumenten mit 'url' und 'content' Keys
            
        Returns:
            Tuple von (unique_documents, duplicate_documents)
        """
        unique = []
        duplicates = []
        
        for doc in documents:
            url = doc.get('url', '')
            content = doc.get('content', '')
            
            is_dup, reason = self.is_duplicate(content, url)
            
            if is_dup:
                doc['duplicate_reason'] = reason
                duplicates.append(doc)
            else:
                unique.append(doc)
        
        logger.info(
            f"Deduplication: {len(unique)} unique, {len(duplicates)} duplicates "
            f"von {len(documents)} gesamt"
        )
        
        return unique, duplicates
    
    def get_statistics(self) -> dict:
        """
        Erhalte Statistiken über gesehene Dokumente.
        
        Returns:
            Dictionary mit Statistiken
        """
        return {
            'total_seen': len(self.seen_fingerprints),
            'unique_urls': len(self.url_to_fingerprint),
            'similarity_threshold': self.similarity_threshold,
            'shingle_size': self.shingle_size
        }
