"""
Semantic Chunking für optimale RAG-Performance
==============================================

Teilt Text in semantisch kohärente Chunks statt nur nach Zeichenzahl.
"""

import re
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SemanticChunker:
    """
    Semantic Chunker für intelligente Text-Segmentierung.
    
    Teilt Text basierend auf:
    - Absatzgrenzen
    - Überschriften
    - Semantischer Kohärenz
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 200,
        overlap: int = 300
    ):
        """
        Initialisiere den Semantic Chunker.
        
        Args:
            max_chunk_size: Maximale Chunk-Größe in Zeichen
            min_chunk_size: Minimale Chunk-Größe in Zeichen
            overlap: Überlappung zwischen Chunks
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """
        Teile Text an natürlichen Absatzgrenzen.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von Text-Chunks
        """
        # Teile in Absätze
        paragraphs = re.split(r'\n\s*\n', text)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            para_size = len(para)
            
            # Wenn dieser Absatz allein zu groß ist, teile ihn
            if para_size > self.max_chunk_size:
                # Speichere aktuellen Chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                
                # Teile großen Absatz in Sätze
                sentence_chunks = self._chunk_large_paragraph(para)
                chunks.extend(sentence_chunks)
                continue
            
            # Prüfe ob Absatz in aktuellen Chunk passt
            if current_size + para_size > self.max_chunk_size and current_chunk:
                # Speichere aktuellen Chunk
                chunks.append('\n\n'.join(current_chunk))
                
                # Starte neuen Chunk mit Überlappung
                if self.overlap > 0 and current_chunk:
                    # Füge letzten Teil des vorherigen Chunks hinzu
                    last_para = current_chunk[-1]
                    overlap_text = last_para[-self.overlap:] if len(last_para) > self.overlap else last_para
                    current_chunk = [overlap_text, para]
                    current_size = len(overlap_text) + para_size
                else:
                    current_chunk = [para]
                    current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size
        
        # Füge letzten Chunk hinzu
        if current_chunk:
            final_chunk = '\n\n'.join(current_chunk)
            # Nur hinzufügen wenn groß genug
            if len(final_chunk) >= self.min_chunk_size:
                chunks.append(final_chunk)
            elif chunks:
                # Zu klein - füge zu letztem Chunk hinzu
                chunks[-1] += '\n\n' + final_chunk
        
        return chunks
    
    def _chunk_large_paragraph(self, paragraph: str) -> List[str]:
        """
        Teile einen großen Absatz in kleinere Chunks.
        
        Args:
            paragraph: Zu teilender Absatz
            
        Returns:
            Liste von Chunks
        """
        # Teile in Sätze
        sentences = re.split(r'(?<=[.!?])\s+', paragraph)
        
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_size = len(sentence)
            
            if current_size + sentence_size > self.max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                
                # Überlappung
                if self.overlap > 0:
                    last_sentence = current_chunk[-1]
                    overlap_text = last_sentence[-self.overlap:] if len(last_sentence) > self.overlap else last_sentence
                    current_chunk = [overlap_text, sentence]
                    current_size = len(overlap_text) + sentence_size
                else:
                    current_chunk = [sentence]
                    current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
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
        
        # Chunke jede Sektion
        chunks = []
        for section in sections:
            content = '\n'.join(section['content']).strip()
            
            if not content:
                continue
            
            # Chunke Inhalt
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
    
    def get_optimal_chunk_size(self, text: str) -> int:
        """
        Berechne optimale Chunk-Größe für gegebenen Text.
        
        Args:
            text: Eingabetext
            
        Returns:
            Empfohlene Chunk-Größe
        """
        text_length = len(text)
        
        # Sehr kurze Texte
        if text_length < 1000:
            return text_length
        
        # Mittlere Texte
        if text_length < 5000:
            return 1000
        
        # Lange Texte
        return 1500
