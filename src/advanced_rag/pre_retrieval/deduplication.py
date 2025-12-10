"""
Content Deduplication für Web Scraping
======================================

Entfernt near-duplicate Dokumente mithilfe von MinHash und Simhash.

Enthält:
- normalize_text(): Text-Normalisierung für Exact-Deduplication
- ContentDeduplicator: Near-Duplicate-Erkennung via Shingling/Jaccard
"""

import hashlib
import re
import unicodedata
from typing import List, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# TEXT-NORMALISIERUNG FÜR EXACT-DEDUPLICATION
# ============================================================================

def normalize_text(text: str) -> str:
    """
    Normalisiere Text für Exact-Deduplication (Hashing).
    
    Diese Funktion bereitet Text so auf, dass Dokumente als gleich erkannt werden,
    wenn sie sich nur in Typografie, Groß-/Kleinschreibung, Whitespace und 
    Aufzählungsmarkern unterscheiden.
    
    Normalisierungsschritte:
    1. Lowercasing
    2. Unicode-Normalisierung (NFKC)
    3. Typografische Vereinheitlichung (Anführungszeichen, Bindestriche, NBSP)
    4. Entfernung von Aufzählungsmarkern am Zeilenanfang
    5. Entfernung dekorativer Sequenzen (----, ====, etc.)
    6. Whitespace-Normalisierung
    
    Was NICHT gemacht wird:
    - Keine Entfernung/Vereinheitlichung von Zahlen und Datumsangaben
    - Kein Stemming oder Lemmatizing
    - Umlaute (ä, ö, ü) und ß bleiben erhalten
    
    Args:
        text: Eingabetext (kann None oder leer sein)
        
    Returns:
        Normalisierter Text für Hashing
    """
    # Robuste Behandlung von None/leerem Input
    if not text:
        return ""
    
    if not isinstance(text, str):
        text = str(text)
    
    # 1. Lowercasing
    text = text.lower()
    
    # 2. Unicode-Normalisierung (NFKC)
    # - Vereinheitlicht Kompatibilitätszeichen (z.B. ﬁ → fi)
    # - Kombiniert diakritische Zeichen
    text = unicodedata.normalize('NFKC', text)
    
    # 3. Typografische Vereinheitlichung
    # 3a. Anführungszeichen → einfaches "
    quote_chars = [
        '"', '"',  # Typografische doppelte Anführungszeichen
        '„', '‟',  # Deutsche Anführungszeichen
        ''', ''',  # Typografische einfache Anführungszeichen
        '‚', '‛',  # Weitere einfache Anführungszeichen
        '«', '»',  # Guillemets
        '‹', '›',  # Einfache Guillemets
    ]
    for char in quote_chars:
        text = text.replace(char, '"')
    
    # 3b. Bindestrich-Varianten → normaler Bindestrich
    dash_chars = [
        '–',  # En-Dash
        '—',  # Em-Dash
        '―',  # Horizontal Bar
        '‐',  # Hyphen
        '‑',  # Non-Breaking Hyphen
        '⁃',  # Hyphen Bullet
    ]
    for char in dash_chars:
        text = text.replace(char, '-')
    
    # 3c. Geschützte/spezielle Leerzeichen → normales Space
    space_chars = [
        '\u00A0',  # Non-Breaking Space
        '\u2007',  # Figure Space
        '\u2008',  # Punctuation Space
        '\u2009',  # Thin Space
        '\u200A',  # Hair Space
        '\u200B',  # Zero-Width Space
        '\u202F',  # Narrow No-Break Space
        '\u205F',  # Medium Mathematical Space
        '\u3000',  # Ideographic Space
    ]
    for char in space_chars:
        text = text.replace(char, ' ')
    
    # 4. Entfernung von Aufzählungsmarkern am Zeilenanfang
    # Arbeite zeilenweise, falls noch Zeilenumbrüche vorhanden sind
    lines = text.split('\n')
    normalized_lines = []
    
    for line in lines:
        # Entferne führende Whitespaces für Pattern-Matching
        stripped = line.lstrip()
        
        # Pattern für Aufzählungsmarker am Zeilenanfang
        # Bullets: -, *, •, +, >, #
        # Nummerierung: 1., 2., 3., ...
        # Buchstaben: a), b), c), ... oder a., b., c., ...
        
        # Bullet-Marker entfernen
        bullet_pattern = r'^[\-\*\•\+\>\#]\s+'
        stripped = re.sub(bullet_pattern, '', stripped)
        
        # Nummerierte Listen: 1. , 2. , etc.
        number_pattern = r'^\d+[\.\)]\s+'
        stripped = re.sub(number_pattern, '', stripped)
        
        # Buchstaben-Listen: a), b), a., b., etc.
        letter_pattern = r'^[a-z][\.\)]\s+'
        stripped = re.sub(letter_pattern, '', stripped)
        
        # Markdown-Überschriften: #, ##, ###, etc.
        heading_pattern = r'^#{1,6}\s+'
        stripped = re.sub(heading_pattern, '', stripped)
        
        normalized_lines.append(stripped)
    
    text = '\n'.join(normalized_lines)
    
    # 5. Entfernung dekorativer Sequenzen
    # Linien aus wiederholten Zeichen: ----, ====, ****, ~~~~, etc.
    decorative_pattern = r'[\-=\*~_]{3,}'
    text = re.sub(decorative_pattern, '', text)
    
    # 6. Whitespace-Normalisierung
    # Alle Whitespace-Arten (Space, Tab, Newline, etc.) auf einzelnes Space
    text = re.sub(r'\s+', ' ', text)
    
    # Führende und trailing Whitespaces entfernen
    text = text.strip()
    
    return text


def compute_normalized_hash(text: str) -> str:
    """
    Berechne Hash für normalisierten Text (für Exact-Dedup).
    
    Kombiniert normalize_text() mit SHA256-Hashing.
    
    Args:
        text: Eingabetext
        
    Returns:
        SHA256-Hash des normalisierten Textes
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def demo_normalization():
    """
    Demonstriert die Normalisierung mit Beispieltexten.
    
    Zeigt Original und normalisierten Text für verschiedene Fälle.
    """
    test_cases = [
        # Typografische Varianten
        ('Anführungszeichen', 
         '„Dies ist ein Test" und «noch einer»'),
        
        # Bindestriche
        ('Bindestriche', 
         'Hin- und Herfahrt – mit Em-Dash — und mehr'),
        
        # Aufzählungen
        ('Bullet-Liste', 
         '- Punkt 1\n* Punkt 2\n• Punkt 3\n+ Punkt 4'),
        
        # Nummerierte Liste
        ('Nummerierte Liste', 
         '1. Erster Punkt\n2. Zweiter Punkt\na) Unterpunkt\nb) Noch einer'),
        
        # Markdown-Überschriften
        ('Markdown-Headings', 
         '# Überschrift 1\n## Überschrift 2\n### Überschrift 3'),
        
        # Dekorative Linien
        ('Dekorative Linien', 
         'Text davor\n--------------------\nText danach\n====================\nEnde'),
        
        # Geschützte Leerzeichen
        ('Geschützte Leerzeichen', 
         'Wort\u00A0mit\u00A0NBSP\u00A0Zeichen'),
        
        # Gemischter Fall
        ('Gemischter Fall', 
         '## „Studienordnung" 2024\n- Punkt 1: Hin- und Rückfahrt\n- Punkt 2: 30 LP erforderlich\n----\nWeiterer Text'),
    ]
    
    print("=" * 80)
    print("DEMO: Text-Normalisierung für Exact-Deduplication")
    print("=" * 80)
    
    for name, original in test_cases:
        normalized = normalize_text(original)
        print(f"\n📝 {name}:")
        print(f"   Original:    {repr(original)}")
        print(f"   Normalisiert: {repr(normalized)}")
    
    print("\n" + "=" * 80)
    print("✅ Demo abgeschlossen")
    print("=" * 80)


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
        
        # Quick-Win Optimierungen
        self.shingle_cache: dict = {}  # Cache für Shingles
        self.chunks_by_size: dict = defaultdict(list)  # Size-Bucketing
        
    def create_shingles(self, text: str) -> Set[str]:
        """
        Erstelle Shingles (n-grams) aus Text mit Caching.
        
        Args:
            text: Eingabetext
            
        Returns:
            Set von Shingles
        """
        # Quick-Win 1: Shingle-Cache
        text_hash = hash(text)
        if text_hash in self.shingle_cache:
            return self.shingle_cache[text_hash]
        
        # Normalisiere Text
        text = text.lower().strip()
        words = text.split()
        
        # Erstelle Wort-Shingles
        shingles = set()
        for i in range(len(words) - self.shingle_size + 1):
            shingle = " ".join(words[i:i + self.shingle_size])
            shingles.add(shingle)
        
        # Cache speichern
        self.shingle_cache[text_hash] = shingles
        return shingles
    
    def compute_content_hash(self, text: str, use_full_normalization: bool = True) -> str:
        """
        Berechne eindeutigen Hash für Inhalt.
        
        Args:
            text: Eingabetext
            use_full_normalization: Wenn True, nutze normalize_text() für robuste Normalisierung.
                                    Wenn False, nur lower().strip() (Legacy-Verhalten).
            
        Returns:
            SHA256-Hash als Hex-String
        """
        if use_full_normalization:
            normalized = normalize_text(text)
        else:
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
        Berechne Jaccard-Ähnlichkeit zwischen zwei Sets mit Early Exit.
        
        Args:
            set1: Erstes Set
            set2: Zweites Set
            
        Returns:
            Ähnlichkeit zwischen 0.0 und 1.0
        """
        if not set1 and not set2:
            return 1.0
        
        # Quick-Win 2: Early Exit - prüfe maximale mögliche Similarity
        min_size = min(len(set1), len(set2))
        max_size = max(len(set1), len(set2))
        
        if max_size > 0:
            max_possible_similarity = min_size / max_size
            if max_possible_similarity < self.similarity_threshold:
                return 0.0  # Kann nie Threshold erreichen
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def is_duplicate(self, text: str, url: str) -> Tuple[bool, str]:
        """
        Prüfe ob Text ein Duplikat ist mit Size-Bucketing.
        
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
        
        # Quick-Win 3: Size-Bucketing - nur ähnlich große Texte vergleichen
        text_size = len(text)
        size_bucket = text_size // 500  # Buckets von 500 Zeichen
        
        # Kandidaten: Aktueller Bucket ± 1
        candidates = []
        for bucket in [size_bucket - 1, size_bucket, size_bucket + 1]:
            candidates.extend(self.chunks_by_size.get(bucket, []))
        
        # Near-duplicates - nur gegen Kandidaten
        shingles = self.create_shingles(text)
        
        for candidate_url in candidates:
            if candidate_url not in self.url_to_fingerprint:
                continue
                
            candidate_text = self.url_to_fingerprint[candidate_url].get('text', '')
            seen_shingles = self.create_shingles(candidate_text)
            
            similarity = self.jaccard_similarity(shingles, seen_shingles)
            
            if similarity >= self.similarity_threshold:
                logger.info(
                    f"Near-duplicate gefunden: {url} ähnlich zu {candidate_url} "
                    f"(Similarity: {similarity:.2f})"
                )
                return True, f"near_duplicate_{similarity:.2f}"
        
        # Kein Duplikat - speichere Fingerprint UND Size-Bucket
        self.seen_fingerprints.add(content_hash)
        self.url_to_fingerprint[url] = {
            'content_hash': content_hash,
            'shingles_hash': self.compute_shingles_hash(shingles),
            'text': text[:5000],
            'word_count': len(text.split())
        }
        self.chunks_by_size[size_bucket].append(url)
        
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


# ============================================================================
# ENTRY POINT FÜR DEMO
# ============================================================================

if __name__ == "__main__":
    demo_normalization()