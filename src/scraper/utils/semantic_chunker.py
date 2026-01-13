"""
Semantic Chunking für optimale RAG-Performance
==============================================

Echter Semantic Chunker der Embeddings nutzt um semantische Grenzen zu erkennen.
Verwendet das gleiche Embedding-Modell wie die Vektordatenbank (BAAI/bge-m3).

Basiert auf der Idee: Sätze mit hoher semantischer Ähnlichkeit gehören zusammen,
ein starker Ähnlichkeitsabfall markiert eine Chunk-Grenze.
"""

import re
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from sentence_transformers import SentenceTransformer

# Import zentrales Embedding-Modell aus Settings
try:
    from config.settings import SENTENCE_TRANSFORMER_MODEL
except ImportError:
    SENTENCE_TRANSFORMER_MODEL = "BAAI/bge-m3"

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Echter Semantic Chunker mit Embedding-basierter Grenzenerkennung.
    
    Funktionsweise:
    1. Teile Text in Sätze
    2. Berechne Embeddings für jeden Satz
    3. Berechne Kosinus-Ähnlichkeit zwischen aufeinanderfolgenden Sätzen
    4. Erkenne Chunk-Grenzen bei starkem Ähnlichkeitsabfall
    5. Gruppiere Sätze zu semantisch kohärenten Chunks
    
    Verwendet das gleiche Modell wie die Vektordatenbank für Konsistenz.
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 200,
        overlap: int = 2,
        similarity_threshold: float = 0.5,
        breakpoint_percentile: int = 90,
        embedding_model: str = None
    ):
        """
        Initialisiere den Semantic Chunker.
        
        Args:
            max_chunk_size: Maximale Chunk-Größe in Zeichen
            min_chunk_size: Minimale Chunk-Größe in Zeichen
            overlap: Anzahl Sätze die überlappen (0 = keine Überlappung)
            similarity_threshold: Absolute Schwelle für semantische Ähnlichkeit (0-1)
            breakpoint_percentile: Perzentil für Breakpoint-Erkennung (höher = weniger Breaks)
            embedding_model: Name des SentenceTransformer Modells
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.similarity_threshold = similarity_threshold
        self.breakpoint_percentile = breakpoint_percentile
        
        # Lade Embedding-Modell (lazy loading)
        self._model = None
        self._model_name = embedding_model or SENTENCE_TRANSFORMER_MODEL
        
    @property
    def model(self) -> SentenceTransformer:
        """Lazy-Load des Embedding-Modells."""
        if self._model is None:
            from config.settings import EMBEDDING_MAX_SEQ_LENGTH
            logger.info(f"Lade Embedding-Modell: {self._model_name}")
            self._model = SentenceTransformer(self._model_name, trust_remote_code=True)
            self._model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH
        return self._model
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Teile Text in Sätze.
        
        Verwendet robuste Regex-basierte Satzerkennung die mit
        deutschen Texten gut funktioniert.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von Sätzen
        """
        # Normalisiere Whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Teile an Satzgrenzen (., !, ?, sowie deutsche Anführungszeichen)
        # Berücksichtige Abkürzungen wie "z.B.", "bzw.", "etc."
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])|(?<=[.!?])\s*$'
        
        # Einfachere Alternative: Teile an .!? gefolgt von Leerzeichen und Großbuchstaben
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filtere leere Sätze und normalisiere
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _compute_embeddings(self, sentences: List[str]) -> np.ndarray:
        """
        Berechne Embeddings für alle Sätze.
        
        Args:
            sentences: Liste von Sätzen
            
        Returns:
            NumPy Array mit Embeddings (n_sentences x embedding_dim)
        """
        if not sentences:
            return np.array([])
        
        embeddings = self.model.encode(sentences, show_progress_bar=False)
        return embeddings
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Berechne Kosinus-Ähnlichkeit zwischen zwei Vektoren.
        
        Args:
            a: Erster Vektor
            b: Zweiter Vektor
            
        Returns:
            Kosinus-Ähnlichkeit (0-1)
        """
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return np.dot(a, b) / (norm_a * norm_b)
    
    def _find_breakpoints(
        self, 
        embeddings: np.ndarray
    ) -> List[int]:
        """
        Finde semantische Breakpoints basierend auf Ähnlichkeitsabfall.
        
        Methode:
        1. Berechne Ähnlichkeit zwischen aufeinanderfolgenden Sätzen
        2. Berechne "Distanzen" (1 - Ähnlichkeit)
        3. Finde Breakpoints wo Distanz über dem Perzentil-Schwellwert liegt
        
        Args:
            embeddings: Satz-Embeddings
            
        Returns:
            Liste von Indizes wo Chunks getrennt werden sollen
        """
        if len(embeddings) < 2:
            return []
        
        # Berechne Ähnlichkeiten zwischen aufeinanderfolgenden Sätzen
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)
        
        # Berechne "Distanzen" (Unähnlichkeit)
        distances = [1 - sim for sim in similarities]
        
        if not distances:
            return []
        
        # Berechne Schwellwert basierend auf Perzentil
        threshold = np.percentile(distances, self.breakpoint_percentile)
        
        # Finde Breakpoints (hohe Distanz = semantischer Bruch)
        breakpoints = []
        for i, dist in enumerate(distances):
            # Breakpoint wenn Distanz über Schwellwert ODER unter absoluter Ähnlichkeit
            if dist > threshold or similarities[i] < self.similarity_threshold:
                breakpoints.append(i + 1)  # +1 weil wir NACH dem Satz trennen
        
        return breakpoints
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Semantisches Chunking basierend auf Embedding-Ähnlichkeit.
        
        Dies ist die Hauptmethode für semantisches Chunking.
        Kompatibel mit der API des alten Chunkers.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von semantisch kohärenten Text-Chunks
        """
        # Teile in Sätze
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return []
        
        # Für sehr kurze Texte: Keine Aufteilung nötig
        if len(sentences) <= 2:
            return [text.strip()] if len(text.strip()) >= self.min_chunk_size else []
        
        # Berechne Embeddings
        embeddings = self._compute_embeddings(sentences)
        
        # Finde semantische Breakpoints
        breakpoints = self._find_breakpoints(embeddings)
        
        # Gruppiere Sätze zu Chunks
        chunks = []
        start_idx = 0
        
        for bp in breakpoints:
            chunk_sentences = sentences[start_idx:bp]
            chunk_text = ' '.join(chunk_sentences)
            
            # Prüfe Größenbeschränkungen
            if len(chunk_text) >= self.min_chunk_size:
                # Wenn zu groß, teile weiter auf
                if len(chunk_text) > self.max_chunk_size:
                    sub_chunks = self._split_large_chunk(chunk_sentences)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_text)
            elif chunks:
                # Zu klein: Füge zu letztem Chunk hinzu
                chunks[-1] += ' ' + chunk_text
            
            start_idx = bp
        
        # Letzter Chunk
        if start_idx < len(sentences):
            chunk_sentences = sentences[start_idx:]
            chunk_text = ' '.join(chunk_sentences)
            
            if len(chunk_text) >= self.min_chunk_size:
                if len(chunk_text) > self.max_chunk_size:
                    sub_chunks = self._split_large_chunk(chunk_sentences)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_text)
            elif chunks:
                chunks[-1] += ' ' + chunk_text
        
        # Überlappung hinzufügen (optional)
        if self.overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks, sentences)
        
        return chunks
    
    def _split_large_chunk(self, sentences: List[str]) -> List[str]:
        """
        Teile einen zu großen Chunk in kleinere Teile.
        
        Args:
            sentences: Sätze des Chunks
            
        Returns:
            Liste kleinerer Chunks
        """
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size + 1  # +1 für Leerzeichen
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
            elif chunks:
                chunks[-1] += ' ' + chunk_text
        
        return chunks
    
    def _add_overlap(self, chunks: List[str], sentences: List[str]) -> List[str]:
        """
        Füge Satz-Überlappung zwischen Chunks hinzu.
        
        Args:
            chunks: Liste von Chunks
            sentences: Original-Sätze
            
        Returns:
            Chunks mit Überlappung
        """
        # Finde Satz-Grenzen für jeden Chunk
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            # Finde letzte Sätze des vorherigen Chunks
            prev_chunk = chunks[i - 1]
            prev_sentences = self._split_into_sentences(prev_chunk)
            
            # Nimm die letzten N Sätze als Überlappung
            overlap_sentences = prev_sentences[-self.overlap:]
            overlap_text = ' '.join(overlap_sentences)
            
            # Füge Überlappung am Anfang hinzu
            overlapped_chunks.append(overlap_text + ' ' + chunks[i])
        
        return overlapped_chunks
    
    def chunk_with_headers(self, text: str) -> List[Dict[str, Any]]:
        """
        Teile Text und behalte Header-Kontext.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von Chunks mit Metadaten
        """
        # Erkenne Überschriften (Markdown-Style)
        header_pattern = r'^(#+)\s+(.+)$'
        
        lines = text.split('\n')
        sections = []
        current_section = {
            'header': None,
            'level': 0,
            'content': []
        }
        
        for line in lines:
            match = re.match(header_pattern, line)
            if match:
                # Speichere vorherige Sektion
                if current_section['content']:
                    sections.append(current_section)
                
                # Neue Sektion
                level = len(match.group(1))
                header = match.group(2)
                current_section = {
                    'header': header,
                    'level': level,
                    'content': []
                }
            else:
                current_section['content'].append(line)
        
        # Speichere letzte Sektion
        if current_section['content']:
            sections.append(current_section)
        
        # Chunke jede Sektion mit semantischem Chunking
        chunks = []
        for section in sections:
            content = '\n'.join(section['content']).strip()
            
            if not content:
                continue
            
            # Semantisches Chunking für Inhalt
            section_chunks = self.chunk_by_paragraphs(content)
            
            # Füge Metadaten hinzu
            for i, chunk in enumerate(section_chunks):
                chunks.append({
                    'text': chunk,
                    'header': section['header'],
                    'header_level': section['level'],
                    'chunk_index': i,
                    'total_chunks_in_section': len(section_chunks)
                })
        
        return chunks
    
    def chunk_document(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        preserve_headers: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Chunke ein vollständiges Dokument mit semantischer Analyse.
        
        Args:
            text: Dokumenttext
            metadata: Zusätzliche Metadaten
            preserve_headers: Ob Header-Kontext behalten werden soll
            
        Returns:
            Liste von Chunk-Dictionaries
        """
        if preserve_headers:
            chunks = self.chunk_with_headers(text)
        else:
            text_chunks = self.chunk_by_paragraphs(text)
            chunks = [
                {
                    'text': chunk,
                    'chunk_index': i,
                    'total_chunks': len(text_chunks)
                }
                for i, chunk in enumerate(text_chunks)
            ]
        
        # Füge globale Metadaten hinzu
        if metadata:
            for chunk in chunks:
                chunk['metadata'] = metadata
        
        logger.debug(f"Dokument in {len(chunks)} semantische Chunks aufgeteilt")
        
        return chunks
    
    def get_chunk_statistics(self, chunks: List[str]) -> Dict[str, Any]:
        """
        Berechne Statistiken über die erstellten Chunks.
        
        Args:
            chunks: Liste von Chunks
            
        Returns:
            Dictionary mit Statistiken
        """
        if not chunks:
            return {
                'num_chunks': 0,
                'avg_size': 0,
                'min_size': 0,
                'max_size': 0,
                'total_size': 0
            }
        
        sizes = [len(c) for c in chunks]
        
        return {
            'num_chunks': len(chunks),
            'avg_size': sum(sizes) / len(sizes),
            'min_size': min(sizes),
            'max_size': max(sizes),
            'total_size': sum(sizes),
            'model': self._model_name
        }
