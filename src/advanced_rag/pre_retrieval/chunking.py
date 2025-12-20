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
    6. Overlap am Anfang jedes Chunks (außer dem ersten) hinzufügen
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1800,
        min_chunk_size: int = 400,
        overlap: int = 300,
        similarity_threshold: float = 0.65,
        embedding_model: Optional[Any] = None,
        debug_overlap: bool = False
    ):
        """
        Initialisiere den Semantic Chunker.
        
        Args:
            max_chunk_size: Maximale Chunk-Größe in Zeichen (nicht Tokens!).
                           Empfohlen: 1500-2000 für die meisten Embedding-Modelle.
            min_chunk_size: Minimale Chunk-Größe in Zeichen.
                           Chunks unter diesem Wert werden mit dem vorherigen
                           zusammengeführt (sofern max_size nicht überschritten wird).
            overlap: Überlappung zwischen Chunks in Zeichen.
                    Die letzten N Zeichen des vorherigen Chunks werden am Anfang
                    des nächsten Chunks wiederholt (am Satz-/Wortgrenze geschnitten).
            similarity_threshold: Schwellwert für Themenwechsel (Wertebereich 0.0-1.0).
                                 Wenn die Cosine-Similarity zwischen zwei aufeinander-
                                 folgenden Sätzen UNTER diesem Wert liegt, wird eine
                                 Chunk-Grenze gesetzt. Niedrigerer Wert = weniger Splits,
                                 höherer Wert = mehr/kleinere Chunks.
                                 Empfohlen: 0.5-0.7 je nach Domäne.
            embedding_model: SentenceTransformer Model (optional).
                            Wird lazy geladen wenn nicht angegeben.
            debug_overlap: Wenn True, wird '[...]' als Marker zwischen Overlap
                          und Chunk-Inhalt eingefügt (für Debugging).
                          Wenn False (Standard), nahtloser Übergang.
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.overlap = overlap
        self.similarity_threshold = similarity_threshold
        self._embedding_model = embedding_model
        self.debug_overlap = debug_overlap
        
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
                from config.settings import SENTENCE_TRANSFORMER_MODEL, EMBEDDING_MAX_SEQ_LENGTH
                model_name = SENTENCE_TRANSFORMER_MODEL
            except ImportError:
                model_name = "BAAI/bge-m3"
                EMBEDDING_MAX_SEQ_LENGTH = 1024
            
            logger.info(f"Lade Embedding-Modell für Semantic Chunking: {model_name}")
            self._embedding_model = SentenceTransformer(model_name, trust_remote_code=True)
            self._embedding_model.max_seq_length = EMBEDDING_MAX_SEQ_LENGTH
        return self._embedding_model
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Teile Text in Sätze auf.
        
        Verwendet ein pragmatisches Regex-basiertes Splitting. Erkennt Satzenden
        an Punkt, Ausrufezeichen oder Fragezeichen, gefolgt von Leerzeichen und
        einem typischen Satzanfang (Großbuchstabe, Ziffer, Klammer, Bindestrich).
        
        HINWEIS: Abkürzungen wie "z.B.", "d.h." werden NICHT perfekt behandelt.
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von Sätzen. Gibt niemals leere Liste zurück wenn text nicht leer ist.
        """
        # Pragmatisches Regex-basiertes Satz-Splitting:
        # Satzende (. ! ?) gefolgt von Leerzeichen und typischem Satzanfang
        # (Großbuchstabe, Ziffer, Klammer, Bindestrich)
        # HINWEIS: Deckt nicht alle Sonderfälle perfekt ab.
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZÄÖÜ0-9\(\-])'
        
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
                # Minimale Schwelle: nur völlig leere Strings ausschließen
                if sent and len(sent) > 0:
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
        
        Für jedes Paar aufeinanderfolgender Sätze wird die Cosine-Similarity
        berechnet. Wenn sim < self.similarity_threshold, wird ein Breakpoint
        gesetzt (= Themenwechsel erkannt, neuer Chunk beginnt).
        
        Args:
            embeddings: Sentence embeddings (shape: n_sentences x embedding_dim)
            
        Returns:
            Liste von Indizes wo neue Chunks beginnen sollten.
            Index i bedeutet: Satz i ist der erste Satz eines neuen Chunks.
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
        
        Analysiert die Cosine-Similarity zwischen aufeinanderfolgenden Sätzen
        und setzt Chunk-Grenzen bei Themenwechseln (sim < similarity_threshold).
        Chunks werden auf max_chunk_size begrenzt und bei Bedarf zusammengeführt
        wenn sie unter min_chunk_size liegen.
        
        Falls aktiviert (overlap > 0), werden die letzten overlap Zeichen des
        vorherigen Chunks am Anfang des nächsten wiederholt (zeichenbasiert,
        an Satz-/Wortgrenzen geschnitten).
        
        GARANTIE: Gibt niemals leere Liste zurück wenn der Input-Text nicht
        leer ist. Text geht nicht verloren.
        
        Args:
            text: Eingabetext (beliebiger String)
            
        Returns:
            Liste von semantisch kohärenten Text-Chunks.
            Jeder Chunk hat maximal max_chunk_size Zeichen.
        """
        # 1. Text in Sätze aufteilen
        sentences = self._split_into_sentences(text)
        
        # Fallback: Wenn kein Satz gefunden wurde, verwende den gesamten Text
        # Damit geht kein Text verloren, nur weil das Satz-Splitting nichts findet
        if not sentences:
            text_stripped = text.strip()
            if not text_stripped:
                return []  # Wirklich leerer Text
            sentences = [text_stripped]
        
        # Falls nur ein "Satz" gefunden wurde, prüfe ob er zu groß ist
        if len(sentences) == 1:
            single_sentence = sentences[0]
            if len(single_sentence) > self.max_chunk_size:
                # Zu groß - teile hart auf
                return self._hard_split_text(single_sentence)
            else:
                # Einzelsatz immer behalten - lieber zu kurz als Information verlieren
                return [single_sentence]
        
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
                # Validiere jeden sub_chunk
                for sub_chunk in sub_chunks:
                    if len(sub_chunk) <= self.max_chunk_size:
                        chunks.append(sub_chunk)
                    else:
                        # Fallback: hart teilen
                        chunks.extend(self._hard_split_text(sub_chunk))
            elif len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
            elif chunks:
                # Zu klein - füge zum vorherigen Chunk hinzu, ABER nur wenn dieser nicht zu groß wird
                combined_size = len(chunks[-1]) + len(chunk_text) + 1
                if combined_size <= self.max_chunk_size:
                    chunks[-1] += ' ' + chunk_text
                else:
                    # Vorheriger Chunk würde zu groß - starte neuen Chunk trotz min_size
                    chunks.append(chunk_text)
            else:
                # Erster Chunk ist zu klein - speichere trotzdem
                chunks.append(chunk_text)
            
            start_idx = end_idx
        
        # 5. Überlappung hinzufügen (optional)
        if self.overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks)
        
        # 6. FINALE VALIDIERUNG: Stelle sicher, dass KEIN Chunk max_size überschreitet
        validated_chunks = []
        for chunk in chunks:
            if len(chunk) <= self.max_chunk_size:
                validated_chunks.append(chunk)
            else:
                # Sollte nicht passieren, aber als Fallback hart teilen
                logger.warning(f"Chunk mit {len(chunk)} Zeichen überschreitet max_size, teile hart...")
                validated_chunks.extend(self._hard_split_text(chunk))
        
        # Aussagekräftiges Logging mit Statistiken
        if validated_chunks:
            avg_len = int(np.mean([len(c) for c in validated_chunks]))
            min_len = min(len(c) for c in validated_chunks)
            max_len = max(len(c) for c in validated_chunks)
            logger.info(
                f"Semantic Chunking: {len(sentences)} Sätze → {len(validated_chunks)} Chunks "
                f"(Ø {avg_len}, min {min_len}, max {max_len} Zeichen)"
            )
        else:
            logger.info(f"Semantic Chunking: {len(sentences)} Sätze → 0 Chunks")
        
        return validated_chunks
    
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
            
            # Falls ein einzelner Satz bereits zu groß ist, teile ihn hart auf
            if sentence_size > self.max_chunk_size:
                # Speichere bisherigen Chunk
                if current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    # Prüfe nochmal die tatsächliche Größe
                    if len(chunk_text) <= self.max_chunk_size:
                        chunks.append(chunk_text)
                    else:
                        # Sollte nicht passieren, aber als Fallback
                        chunks.extend(self._hard_split_text(chunk_text))
                    current_chunk = []
                    current_size = 0
                
                # Teile den zu langen Satz in Stücke
                sub_chunks = self._hard_split_text(sentence)
                chunks.extend(sub_chunks)
                continue
            
            # Berechne die tatsächliche Größe nach dem Join
            # +1 für das Leerzeichen zwischen Sätzen (wenn current_chunk nicht leer)
            space_needed = 1 if current_chunk else 0
            projected_size = current_size + space_needed + sentence_size
            
            if projected_size > self.max_chunk_size and current_chunk:
                chunk_text = ' '.join(current_chunk)
                # Finale Validierung der Größe
                if len(chunk_text) <= self.max_chunk_size:
                    chunks.append(chunk_text)
                else:
                    # Fallback: hart teilen
                    chunks.extend(self._hard_split_text(chunk_text))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size = projected_size
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                if len(chunk_text) <= self.max_chunk_size:
                    chunks.append(chunk_text)
                else:
                    chunks.extend(self._hard_split_text(chunk_text))
            elif chunks:
                # Nur zusammenfügen wenn max_size nicht überschritten wird
                combined_size = len(chunks[-1]) + len(chunk_text) + 1
                if combined_size <= self.max_chunk_size:
                    chunks[-1] += ' ' + chunk_text
                else:
                    # Chunk trotz Untergröße separat speichern
                    chunks.append(chunk_text)
            else:
                chunks.append(chunk_text)  # Lieber zu klein als verloren
        
        return chunks
    
    def _hard_split_text(self, text: str) -> List[str]:
        """
        Teile einen zu langen Text hart an Wortgrenzen auf.
        
        Wird verwendet wenn ein einzelner "Satz" bereits max_chunk_size überschreitet.
        
        Args:
            text: Zu langer Text
            
        Returns:
            Liste von Chunks mit max. max_chunk_size Zeichen
        """
        chunks = []
        words = text.split()
        current_chunk = []
        current_size = 0
        
        for word in words:
            word_size = len(word)
            
            # Falls ein einzelnes Wort zu lang ist (sehr selten)
            if word_size > self.max_chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                # Teile das Wort in Stücke
                for i in range(0, word_size, self.max_chunk_size - 100):
                    chunks.append(word[i:i + self.max_chunk_size - 100])
                continue
            
            if current_size + word_size + 1 > self.max_chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
                current_size = word_size
            else:
                current_chunk.append(word)
                current_size += word_size + 1
        
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if len(chunk_text) >= self.min_chunk_size:
                chunks.append(chunk_text)
            elif chunks:
                # Prüfe ob zusammenfügen max_size überschreiten würde
                combined_size = len(chunks[-1]) + len(chunk_text) + 1
                if combined_size <= self.max_chunk_size:
                    chunks[-1] += ' ' + chunk_text
                else:
                    # Lieber zu kurz als zu lang
                    chunks.append(chunk_text)
            else:
                chunks.append(chunk_text)  # Lieber zu kurz als verloren
        
        # Finale Validierung: Alle Chunks müssen <= max_size sein
        validated = []
        for chunk in chunks:
            if len(chunk) <= self.max_chunk_size:
                validated.append(chunk)
            else:
                # Rekursiv weiter teilen (sollte sehr selten passieren)
                # Um Endlosrekursion zu vermeiden, teile am Zeichen-Index
                for i in range(0, len(chunk), self.max_chunk_size - 50):
                    sub = chunk[i:i + self.max_chunk_size - 50]
                    # Schneide an Wortgrenze wenn möglich
                    if i + self.max_chunk_size - 50 < len(chunk):
                        last_space = sub.rfind(' ')
                        if last_space > len(sub) - 200:  # Nicht zu viel abschneiden
                            sub = sub[:last_space]
                    validated.append(sub.strip())
        
        return validated
    
    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """
        Füge Überlappung zwischen Chunks hinzu.
        
        Nimmt die letzten N Zeichen (self.overlap) des vorherigen Chunks
        und fügt sie am Anfang des nächsten Chunks hinzu.
        Der Schnitt erfolgt an Satz- oder Wortgrenzen, nicht mitten im Wort.
        
        WICHTIG: Respektiert max_chunk_size - kürzt den Overlap wenn nötig!
        
        Args:
            chunks: Liste von Chunks ohne Overlap
            
        Returns:
            Chunks mit Überlappung (außer dem ersten Chunk)
        """
        if len(chunks) <= 1:
            return chunks
        
        overlapped_chunks = [chunks[0]]
        
        # Separator nur im Debug-Modus
        if self.debug_overlap:
            separator = ' [...] '
        else:
            separator = ' '
        separator_len = len(separator)
        
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]
            
            # Berechne verfügbaren Platz für Overlap
            available_space = self.max_chunk_size - len(current_chunk) - separator_len
            
            # Wenn kein Platz für Overlap, füge Chunk ohne Overlap hinzu
            if available_space <= 50:  # Mindestens 50 Zeichen sinnvoll
                overlapped_chunks.append(current_chunk)
                continue
            
            # Begrenze Overlap auf verfügbaren Platz
            actual_overlap = min(self.overlap, available_space)
            
            # Nimm die letzten overlap Zeichen des vorherigen Chunks
            # ABER: Schneide am Satzanfang, nicht mitten im Satz!
            if len(prev_chunk) > actual_overlap:
                overlap_text = prev_chunk[-actual_overlap:]
                # Finde letzten Satzanfang (nach . ! ? gefolgt von typischem Satzanfang)
                # Nutzt globales re-Modul (am Modulanfang importiert)
                matches = list(re.finditer(r'[.!?]\s+[A-ZÄÖÜ0-9\(\-]', overlap_text))
                if matches:
                    # Nimm den letzten Satzanfang
                    last_match = matches[-1]
                    # Starte nach dem Satzzeichen und Leerzeichen (beim Großbuchstaben)
                    overlap_text = overlap_text[last_match.end() - 1:]
                else:
                    # Kein Satzanfang gefunden - schneide an Wortgrenze
                    first_space = overlap_text.find(' ')
                    if first_space > 0 and first_space < len(overlap_text) - 10:
                        overlap_text = overlap_text[first_space + 1:]
            else:
                overlap_text = prev_chunk
            
            # Finale Größenprüfung vor dem Zusammenfügen
            combined = overlap_text + separator + current_chunk
            while len(combined) > self.max_chunk_size:
                # Kürze overlap_text weiter
                excess = len(combined) - self.max_chunk_size
                if len(overlap_text) > excess + 20:
                    overlap_text = overlap_text[excess:]
                    # Schneide an Wortgrenze
                    first_space = overlap_text.find(' ')
                    if first_space > 0:
                        overlap_text = overlap_text[first_space + 1:]
                    combined = overlap_text + separator + current_chunk
                else:
                    # Kein sinnvoller Overlap möglich - verwende nur current_chunk
                    combined = current_chunk
                    break
            
            overlapped_chunks.append(combined)
        
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
    
    HINWEIS: Diese Klasse implementiert KEIN Overlap zwischen Chunks.
    Für Overlap-Funktionalität verwende SemanticChunker.
    """
    
    def __init__(
        self,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 200
    ):
        """
        Args:
            max_chunk_size: Maximale Chunk-Größe in Zeichen
            min_chunk_size: Minimale Chunk-Größe in Zeichen
        """
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
    
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
