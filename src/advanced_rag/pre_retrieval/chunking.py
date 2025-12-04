"""
Semantic Chunking für optimale RAG-Performance
==============================================

Teilt Text in semantisch kohärente Chunks basierend auf Embedding-Ähnlichkeit.
Erkennt echte Themenwechsel durch Cosine-Similarity zwischen Sätzen.
"""

import re
import numpy as np
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Echter Semantic Chunker mit Embedding-basierter Segmentierung.
    
    Funktionsweise:
    1. Text in Sätze aufteilen
    2. Embeddings für jeden Satz berechnen
    3. Cosine-Similarity zwischen aufeinanderfolgenden Sätzen messen
    4. Bei niedriger Similarity (Themenwechsel) → neuer Chunk
    5. Chunks zusammenführen bis max_size erreicht
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1800,
        min_chunk_size: int = 400,
        overlap: int = 300,
        similarity_threshold: float = 0.65,
        embedding_model: Optional[Any] = None
    ):
        """
        Initialisiere den Semantic Chunker.
        
        Args:
            max_chunk_size: Maximale Chunk-Größe in Zeichen
            min_chunk_size: Minimale Chunk-Größe in Zeichen
            overlap: Überlappung zwischen Chunks (in Sätzen, nicht Zeichen)
            similarity_threshold: Schwellwert für Themenwechsel (0.0-1.0)
                                  Niedrigerer Wert = mehr Splits
            embedding_model: SentenceTransformer Model (optional, wird lazy geladen)
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.similarity_threshold = similarity_threshold
        self._embedding_model = embedding_model
        
    @property
    def embedding_model(self):
        """Lazy-Loading des Embedding-Modells."""
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            # Verwende das gleiche Modell wie in config/settings.py
            import os
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            try:
                from config.settings import SENTENCE_TRANSFORMER_MODEL
                model_name = SENTENCE_TRANSFORMER_MODEL
            except ImportError:
                model_name = "paraphrase-multilingual-MiniLM-L12-v2"
            
            logger.info(f"Lade Embedding-Modell für Semantic Chunking: {model_name}")
            self._embedding_model = SentenceTransformer(model_name)
        return self._embedding_model
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Teile Text in Sätze auf.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von Sätzen
        """
        # Splitten an Satzenden (. ! ?) gefolgt von Leerzeichen
        # Berücksichtigt auch deutsche Abkürzungen wie "z.B.", "d.h."
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZÄÖÜ])'
        
        # Erst Absätze respektieren
        paragraphs = text.split('\n\n')
        sentences = []
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Teile Absatz in Sätze
            para_sentences = re.split(sentence_pattern, para)
            
            for sent in para_sentences:
                sent = sent.strip()
                if sent and len(sent) > 10:  # Mindestlänge für Sätze
                    sentences.append(sent)
        
        return sentences
    
    def _compute_embeddings(self, sentences: List[str]) -> np.ndarray:
        """
        Berechne Embeddings für alle Sätze.
        
        Args:
            sentences: Liste von Sätzen
            
        Returns:
            numpy Array mit Embeddings (shape: n_sentences x embedding_dim)
        """
        if not sentences:
            return np.array([])
        
        embeddings = self.embedding_model.encode(
            sentences,
            convert_to_numpy=True,
            show_progress_bar=False
        )
        return embeddings
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Berechne Cosine-Similarity zwischen zwei Vektoren."""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _find_breakpoints(self, embeddings: np.ndarray) -> List[int]:
        """
        Finde Breakpoints basierend auf Similarity-Drops.
        
        Args:
            embeddings: Sentence embeddings
            
        Returns:
            Liste von Indizes wo neue Chunks beginnen sollten
        """
        if len(embeddings) <= 1:
            return []
        
        breakpoints = []
        similarities = []
        
        # Berechne Similarity zwischen aufeinanderfolgenden Sätzen
        for i in range(len(embeddings) - 1):
            sim = self._cosine_similarity(embeddings[i], embeddings[i + 1])
            similarities.append(sim)
        
        # Finde Stellen mit niedriger Similarity (= Themenwechsel)
        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                # Index i+1 ist der Start des neuen Themas
                breakpoints.append(i + 1)
                logger.debug(f"Breakpoint bei Satz {i+1}: Similarity={sim:.3f}")
        
        return breakpoints
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Teile Text semantisch basierend auf Embedding-Ähnlichkeit.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von semantisch kohärenten Text-Chunks
        """
        # 1. Text in Sätze aufteilen
        sentences = self._split_into_sentences(text)
        
        if not sentences:
            return []
        
        if len(sentences) == 1:
            return [sentences[0]] if len(sentences[0]) >= self.min_chunk_size else []
        
        # 2. Embeddings berechnen
        logger.debug(f"Berechne Embeddings für {len(sentences)} Sätze...")
        embeddings = self._compute_embeddings(sentences)
        
        # 3. Breakpoints finden (Themenwechsel)
        breakpoints = self._find_breakpoints(embeddings)
        
        # 4. Chunks erstellen basierend auf Breakpoints
        chunks = []
        start_idx = 0
        
        # Füge End-Index hinzu
        all_breaks = breakpoints + [len(sentences)]
        
        for end_idx in all_breaks:
            # Sammle Sätze für diesen Chunk
            chunk_sentences = sentences[start_idx:end_idx]
            chunk_text = ' '.join(chunk_sentences)
            
            # Prüfe Größenbeschränkungen
            if len(chunk_text) > self.max_chunk_size:
                # Chunk ist zu groß - teile ihn weiter auf
                sub_chunks = self._split_large_chunk(chunk_sentences)
                chunks.extend(sub_chunks)
            elif len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
            elif chunks:
                # Zu klein - füge zum vorherigen Chunk hinzu
                chunks[-1] += ' ' + chunk_text
            else:
                # Erster Chunk ist zu klein - speichere trotzdem
                chunks.append(chunk_text)
            
            start_idx = end_idx
        
        # 5. Überlappung hinzufügen (optional)
        if self.overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks, sentences)
        
        logger.info(f"Semantic Chunking: {len(sentences)} Sätze → {len(chunks)} Chunks")
        
        return chunks
    
    def _split_large_chunk(self, sentences: List[str]) -> List[str]:
        """
        Teile einen zu großen Chunk in kleinere Teile.
        
        Args:
            sentences: Liste von Sätzen
            
        Returns:
            Liste von Chunks
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
        Füge Überlappung zwischen Chunks hinzu.
        
        Nimmt die letzten N Zeichen des vorherigen Chunks und fügt sie
        am Anfang des nächsten Chunks hinzu.
        
        Args:
            chunks: Liste von Chunks
            sentences: Original-Sätze (für Kontext)
            
        Returns:
            Chunks mit Überlappung
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]
            
            # Nimm die letzten overlap Zeichen des vorherigen Chunks
            overlap_text = prev_chunk[-self.overlap:] if len(prev_chunk) > self.overlap else prev_chunk
            
            # Füge am Anfang hinzu (mit Trennzeichen)
            overlapped_chunks.append(overlap_text + ' [...] ' + current_chunk)
        
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
        
        # Chunke jede Sektion semantisch
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
        Chunke ein vollständiges Dokument.
        
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


# Fallback für einfaches Paragraph-Chunking (ohne Embeddings)
class ParagraphChunker:
    """
    Einfacher Paragraph-basierter Chunker (ohne Embeddings).
    Für schnelle Verarbeitung wenn semantische Analyse nicht benötigt wird.
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 200,
        overlap: int = 300
    ):
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """Teile Text an Absatzgrenzen."""
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            if para_size > self.max_chunk_size:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Teile großen Absatz
                chunks.extend(self._chunk_large_paragraph(para))
                continue
            
            if current_size + para_size > self.max_chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        if current_chunk:
            final_chunk = '\n\n'.join(current_chunk)
            if len(final_chunk) >= self.min_chunk_size:
                chunks.append(final_chunk)
            elif chunks:
                chunks[-1] += '\n\n' + final_chunk
        
        return chunks
    
    def _chunk_large_paragraph(self, paragraph: str) -> List[str]:
        """Teile einen großen Absatz in Sätze."""
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if current_size + len(sentence) > self.max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = len(sentence)
            else:
                current_chunk.append(sentence)
                current_size += len(sentence)
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
