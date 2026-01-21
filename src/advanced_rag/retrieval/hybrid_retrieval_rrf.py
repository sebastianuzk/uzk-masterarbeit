"""
Hybrid Retrieval mit BM25 Sparse Index und RRF Fusion
======================================================

Dieses Modul implementiert:
1. BM25SparseIndex: Sparse Index für lexikalische Suche (Pre-Retrieval)
2. RRF Fusion: Reciprocal Rank Fusion für Hybrid Retrieval (später)

Verwendet einfache wortbasierte Tokenisierung (keine Subwords) für BM25,
da BM25 auf exakten Wortübereinstimmungen basiert.

Verwendung im Scraper:
    from src.advanced_rag.retrieval.hybrid_retrieval_rrf import BM25SparseIndex
    
    # Index erstellen
    sparse_index = BM25SparseIndex(collection_name="wiso_documents")
    sparse_index.add_documents(chunks)  # List[dict] mit 'chunk_id', 'text'
    sparse_index.save(checkpoint_dir)
    
    # Index laden
    sparse_index = BM25SparseIndex.load(checkpoint_dir, collection_name="wiso_documents")
"""

import os
import pickle
import logging
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

# BM25 Implementierung
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


# ============================================================================
# BM25 Sparse Index Klasse
# ============================================================================
@dataclass
class BM25SparseIndex:
    """
    BM25-basierter Sparse Index für lexikalische Suche.
    
    Unterstützt multilingualen Korpus (Deutsch + Englisch) mit:
    - Kombinierte Stoppwortlisten
    - Dualer Stemming-Ansatz (deutsch + englisch)
    - Inkrementelles Hinzufügen von Dokumenten
    - Persistierung via Pickle
    
    Attributes:
        collection_name: Name der zugehörigen ChromaDB-Collection
        index_dir: Verzeichnis für persistierten Index
        tokenized_corpus: Liste der tokenisierten Dokumente
        chunk_ids: Mapping Index-Position → chunk_id
        bm25: BM25Okapi Instanz (lazy initialized)
    """
    collection_name: str = "wiso_documents"
    index_dir: str = "data/sparse_index"
    
    # Interne Datenstrukturen (nach __init__ initialisiert)
    tokenized_corpus: List[List[str]] = field(default_factory=list)
    chunk_ids: List[str] = field(default_factory=list)
    _bm25: Optional[BM25Okapi] = field(default=None, repr=False)
    _is_dirty: bool = field(default=False, repr=False)  # Index geändert seit letztem Build?
    
    def __post_init__(self):
        """Initialisierung nach dataclass __init__."""
        # Erstelle Index-Verzeichnis wenn nötig
        self._index_path = Path(self.index_dir) / self.collection_name
        self._index_path.mkdir(parents=True, exist_ok=True)
    
    # ============================================================================
    # Tokenisierung (Einfache wortbasierte Tokenisierung für BM25)
    # ============================================================================
    def tokenize(self, text: str) -> List[str]:
        """
        Einfache wortbasierte Tokenisierung für BM25.
        
        BM25 basiert auf exakten Wortübereinstimmungen, daher:
        - Keine Subword-Tokenisierung (wie bei BGE-M3)
        - Keine Stoppwortentfernung
        - Kein Stemming
        
        Schritte:
        1. Lowercase
        2. Entferne Sonderzeichen (behalte Umlaute)
        3. Whitespace-basierte Tokenisierung in ganze Wörter
        
        Args:
            text: Eingabetext
            
        Returns:
            Liste von Wörtern (lowercase, keine Subwords)
        """
        if not text or not isinstance(text, str):
            return []
        
        # 1. Lowercase
        text = text.lower()
        
        # 2. Entferne Sonderzeichen, behalte Umlaute und Buchstaben
        # Erlaubt: a-z, äöüß, Ziffern (für Jahreszahlen, Ordnungsnummern etc.)
        text = re.sub(r'[^a-zäöüß0-9\s]', ' ', text)
        
        # 3. Whitespace-basierte Tokenisierung (ganze Wörter, keine Subwords)
        tokens = text.split()
        
        # Behalte alle Tokens (keine Stoppwortfilterung, kein Stemming)
        # Filtere nur leere Strings
        tokens = [t for t in tokens if t]
        
        return tokens
    
    # ============================================================================
    # Dokumente hinzufügen
    # ============================================================================
    def add_documents(self, chunks: List[Dict[str, Any]], show_progress: bool = True) -> int:
        """
        Füge Chunks zum Sparse Index hinzu.
        
        Args:
            chunks: Liste von Dicts mit mindestens 'chunk_id' und 'text' Keys
                    Kann auch das Format aus run_production_scraper.py verwenden:
                    {'chunk_id': str, 'text': str} oder
                    direkt den Chunk-Text wenn chunk_ids separat übergeben werden
            show_progress: Zeige Fortschrittsanzeige
            
        Returns:
            Anzahl hinzugefügter Dokumente
        """
        if not chunks:
            logger.warning("Keine Chunks zum Hinzufügen übergeben")
            return 0
        
        added_count = 0
        
        # Progress-Anzeige optional
        if show_progress:
            try:
                from tqdm import tqdm
                chunk_iter = tqdm(chunks, desc="   🔤 Tokenisiere für BM25", leave=False)
            except ImportError:
                chunk_iter = chunks
        else:
            chunk_iter = chunks
        
        for chunk in chunk_iter:
            # Unterstütze verschiedene Formate
            if isinstance(chunk, dict):
                chunk_id = chunk.get('chunk_id', chunk.get('id', ''))
                text = chunk.get('text', chunk.get('document', chunk.get('content', '')))
            else:
                # Falls direkt Text übergeben wird
                logger.warning("Chunk ohne ID übergeben - überspringe")
                continue
            
            if not chunk_id or not text:
                continue
            
            # Prüfe auf Duplikate
            if chunk_id in self.chunk_ids:
                continue
            
            # Tokenisiere und hinzufügen
            tokens = self.tokenize(text)
            if tokens:  # Nur nicht-leere Tokenisierungen
                self.tokenized_corpus.append(tokens)
                self.chunk_ids.append(chunk_id)
                added_count += 1
        
        if added_count > 0:
            self._is_dirty = True
            logger.info(f"✅ {added_count} Chunks zum BM25-Index hinzugefügt")
        
        return added_count
    
    def add_documents_batch(self, 
                           chunk_ids: List[str], 
                           texts: List[str], 
                           show_progress: bool = True) -> int:
        """
        Batch-Variante: Füge Chunks direkt mit separaten Listen hinzu.
        
        Effizienter wenn IDs und Texte bereits als separate Listen vorliegen.
        
        Args:
            chunk_ids: Liste der Chunk-IDs
            texts: Liste der Chunk-Texte (gleiche Reihenfolge)
            show_progress: Zeige Fortschrittsanzeige
            
        Returns:
            Anzahl hinzugefügter Dokumente
        """
        if len(chunk_ids) != len(texts):
            raise ValueError(f"chunk_ids ({len(chunk_ids)}) und texts ({len(texts)}) müssen gleiche Länge haben")
        
        added_count = 0
        existing_ids = set(self.chunk_ids)
        
        # Progress-Anzeige optional
        if show_progress:
            try:
                from tqdm import tqdm
                pairs = tqdm(zip(chunk_ids, texts), 
                           total=len(chunk_ids),
                           desc="   🔤 Tokenisiere für BM25", 
                           leave=False)
            except ImportError:
                pairs = zip(chunk_ids, texts)
        else:
            pairs = zip(chunk_ids, texts)
        
        for chunk_id, text in pairs:
            if chunk_id in existing_ids:
                continue
            
            tokens = self.tokenize(text)
            if tokens:
                self.tokenized_corpus.append(tokens)
                self.chunk_ids.append(chunk_id)
                existing_ids.add(chunk_id)
                added_count += 1
        
        if added_count > 0:
            self._is_dirty = True
            logger.info(f"✅ {added_count} Chunks zum BM25-Index hinzugefügt (Batch)")
        
        return added_count
    
    # ============================================================================
    # BM25 Index aufbauen
    # ============================================================================
    def build_index(self) -> None:
        """
        Baue BM25-Index aus dem tokenisierten Korpus.
        
        Muss aufgerufen werden nach add_documents() und vor search().
        Wird automatisch bei save() aufgerufen wenn dirty.
        """
        if not self.tokenized_corpus:
            logger.warning("Keine Dokumente im Korpus - Index leer")
            self._bm25 = None
            return
        
        logger.info(f"🔨 Baue BM25-Index mit {len(self.tokenized_corpus)} Dokumenten...")
        self._bm25 = BM25Okapi(self.tokenized_corpus)
        self._is_dirty = False
        logger.info(f"✅ BM25-Index gebaut")
    
    @property
    def bm25(self) -> Optional[BM25Okapi]:
        """Lazy-Build des BM25-Index."""
        if self._bm25 is None and self.tokenized_corpus:
            self.build_index()
        return self._bm25
    
    # ============================================================================
    # Suche (für spätere RRF-Fusion)
    # ============================================================================
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Suche im BM25-Index.
        
        Args:
            query: Suchanfrage
            top_k: Anzahl der Top-Ergebnisse
            
        Returns:
            Liste von (chunk_id, score) Tupeln, sortiert nach Score (absteigend)
        """
        if not self.bm25:
            logger.warning("BM25-Index nicht initialisiert")
            return []
        
        # Tokenisiere Query
        query_tokens = self.tokenize(query)
        if not query_tokens:
            return []
        
        # BM25 Scores berechnen
        scores = self.bm25.get_scores(query_tokens)
        
        # Top-K Ergebnisse (sortiert nach Score, absteigend)
        top_indices = scores.argsort()[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Nur relevante Ergebnisse
                results.append((self.chunk_ids[idx], float(scores[idx])))
        
        return results
    
    # ============================================================================
    # Persistierung
    # ============================================================================
    def save(self, checkpoint_dir: Optional[str] = None) -> str:
        """
        Speichere BM25-Index auf Disk.
        
        Args:
            checkpoint_dir: Optionales Verzeichnis (default: self.index_dir)
            
        Returns:
            Pfad zur gespeicherten Index-Datei
        """
        if checkpoint_dir:
            save_path = Path(checkpoint_dir) / self.collection_name
        else:
            save_path = self._index_path
        
        save_path.mkdir(parents=True, exist_ok=True)
        
        # Baue Index wenn dirty
        if self._is_dirty or self._bm25 is None:
            self.build_index()
        
        # Speichere als Pickle
        index_file = save_path / "bm25_index.pkl"
        
        data = {
            'collection_name': self.collection_name,
            'tokenized_corpus': self.tokenized_corpus,
            'chunk_ids': self.chunk_ids,
            'bm25': self._bm25,
            'version': '1.0'
        }
        
        with open(index_file, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"💾 BM25-Index gespeichert: {index_file} ({len(self.chunk_ids)} Dokumente)")
        return str(index_file)
    
    @classmethod
    def load(cls, checkpoint_dir: str, collection_name: str = "wiso_documents") -> 'BM25SparseIndex':
        """
        Lade BM25-Index von Disk.
        
        Args:
            checkpoint_dir: Verzeichnis mit dem Index
            collection_name: Name der Collection
            
        Returns:
            Geladene BM25SparseIndex Instanz
        """
        index_file = Path(checkpoint_dir) / collection_name / "bm25_index.pkl"
        
        if not index_file.exists():
            logger.warning(f"Kein BM25-Index gefunden: {index_file}")
            return cls(collection_name=collection_name, index_dir=checkpoint_dir)
        
        with open(index_file, 'rb') as f:
            data = pickle.load(f)
        
        instance = cls(
            collection_name=data.get('collection_name', collection_name),
            index_dir=checkpoint_dir,
            tokenized_corpus=data.get('tokenized_corpus', []),
            chunk_ids=data.get('chunk_ids', [])
        )
        instance._bm25 = data.get('bm25')
        instance._is_dirty = False
        
        logger.info(f"📂 BM25-Index geladen: {index_file} ({len(instance.chunk_ids)} Dokumente)")
        return instance
    
    @classmethod
    def exists(cls, checkpoint_dir: str, collection_name: str = "wiso_documents") -> bool:
        """Prüfe ob ein gespeicherter Index existiert."""
        index_file = Path(checkpoint_dir) / collection_name / "bm25_index.pkl"
        return index_file.exists()
    
    # ============================================================================
    # Utility-Methoden
    # ============================================================================
    def get_index_size(self) -> int:
        """Anzahl der indexierten Dokumente."""
        return len(self.chunk_ids)
    
    def clear(self) -> None:
        """Lösche den Index."""
        self.tokenized_corpus = []
        self.chunk_ids = []
        self._bm25 = None
        self._is_dirty = False
        logger.info("🗑️  BM25-Index geleert")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Statistiken über den Index."""
        if not self.tokenized_corpus:
            return {
                'total_documents': 0,
                'avg_tokens_per_doc': 0,
                'total_tokens': 0,
                'unique_terms': 0
            }
        
        total_tokens = sum(len(doc) for doc in self.tokenized_corpus)
        unique_terms = len(set(token for doc in self.tokenized_corpus for token in doc))
        
        return {
            'total_documents': len(self.chunk_ids),
            'avg_tokens_per_doc': total_tokens / len(self.tokenized_corpus),
            'total_tokens': total_tokens,
            'unique_terms': unique_terms
        }
    
    def export_summary(self, output_path: Optional[str] = None) -> str:
        """
        Exportiere einen Überblick über den Sparse-Index als Excel-Datei.
        
        Erstellt eine Excel-Datei mit mehreren Sheets:
        - Übersicht: Allgemeine Statistiken
        - Top Terme: Top-500 häufigste Terme mit Frequenzen
        - Beispiel-Dokumente: Erste 20 Dokumente mit Tokens
        - Längen-Verteilung: Dokument-Längen-Statistiken
        
        Args:
            output_path: Optionaler Pfad für die Ausgabedatei.
                        Default: {index_dir}/{collection_name}/sparse_index_summary.xlsx
        
        Returns:
            Pfad zur erstellten Excel-Datei
        """
        from collections import Counter
        from datetime import datetime
        import pandas as pd
        
        if output_path:
            summary_file = Path(output_path)
        else:
            summary_file = self._index_path / "sparse_index_summary.xlsx"
        
        summary_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Statistiken berechnen
        stats = self.get_statistics()
        
        # Term-Frequenzen berechnen
        term_counter = Counter()
        for doc in self.tokenized_corpus:
            term_counter.update(doc)
        
        # Dokument-Längen-Verteilung
        doc_lengths = [len(doc) for doc in self.tokenized_corpus]
        if doc_lengths:
            min_len = min(doc_lengths)
            max_len = max(doc_lengths)
            median_len = sorted(doc_lengths)[len(doc_lengths) // 2]
            q1_len = sorted(doc_lengths)[len(doc_lengths) // 4]
            q3_len = sorted(doc_lengths)[3 * len(doc_lengths) // 4]
        else:
            min_len = max_len = median_len = q1_len = q3_len = 0
        
        # Excel Writer
        with pd.ExcelWriter(summary_file, engine='openpyxl') as writer:
            # Sheet 1: Übersicht
            overview_data = {
                'Metrik': [
                    'Collection',
                    'Index-Verzeichnis',
                    'Erstellt am',
                    '',
                    'Anzahl Dokumente',
                    'Einzigartige Terme',
                    'Gesamt Tokens',
                    'Durchschn. Tokens/Dokument',
                    '',
                    'Min. Dokumentlänge',
                    'Max. Dokumentlänge',
                    'Median Dokumentlänge',
                    '25% Quantil',
                    '75% Quantil',
                    '',
                    'Tokenisierung',
                    'Lowercase',
                    'Stemming',
                    'Stoppwörter entfernt',
                    'Umlaute (äöüß)',
                ],
                'Wert': [
                    self.collection_name,
                    str(self.index_dir),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    '',
                    f"{stats['total_documents']:,}",
                    f"{stats['unique_terms']:,}",
                    f"{stats['total_tokens']:,}",
                    f"{stats['avg_tokens_per_doc']:.2f}",
                    '',
                    f"{min_len:,}",
                    f"{max_len:,}",
                    f"{median_len:,}",
                    f"{q1_len:,}",
                    f"{q3_len:,}",
                    '',
                    'Einfache wortbasierte Tokenisierung',
                    'Ja',
                    'Nein',
                    'Nein',
                    'Beibehalten',
                ]
            }
            df_overview = pd.DataFrame(overview_data)
            df_overview.to_excel(writer, sheet_name='Übersicht', index=False)
            
            # Sheet 2: Top Terme
            top_terms_data = {
                'Rang': list(range(1, min(501, len(term_counter) + 1))),
                'Term': [term for term, _ in term_counter.most_common(500)],
                'Frequenz': [freq for _, freq in term_counter.most_common(500)],
            }
            df_terms = pd.DataFrame(top_terms_data)
            df_terms.to_excel(writer, sheet_name='Top 500 Terme', index=False)
            
            # Sheet 3: Beispiel-Dokumente
            example_docs = []
            for i, (chunk_id, tokens) in enumerate(zip(self.chunk_ids[:20], self.tokenized_corpus[:20])):
                preview = ' '.join(tokens[:50])
                if len(tokens) > 50:
                    preview += "..."
                example_docs.append({
                    'Nr': i + 1,
                    'Chunk ID': chunk_id,
                    'Anzahl Tokens': len(tokens),
                    'Token-Preview (erste 50)': preview
                })
            df_examples = pd.DataFrame(example_docs)
            df_examples.to_excel(writer, sheet_name='Beispiel-Dokumente', index=False)
            
            # Sheet 4: Längen-Verteilung (Histogramm-Daten)
            # Gruppiere Dokumente nach Längen-Buckets
            buckets = [0, 50, 100, 150, 200, 250, 300, 400, 500, 750, 1000, float('inf')]
            bucket_labels = ['0-50', '51-100', '101-150', '151-200', '201-250', 
                           '251-300', '301-400', '401-500', '501-750', '751-1000', '>1000']
            bucket_counts = [0] * (len(buckets) - 1)
            
            for length in doc_lengths:
                for i in range(len(buckets) - 1):
                    if buckets[i] < length <= buckets[i + 1]:
                        bucket_counts[i] += 1
                        break
            
            df_lengths = pd.DataFrame({
                'Tokens-Bereich': bucket_labels,
                'Anzahl Dokumente': bucket_counts,
                'Prozent': [f"{100 * c / len(doc_lengths):.1f}%" if doc_lengths else "0%" for c in bucket_counts]
            })
            df_lengths.to_excel(writer, sheet_name='Längen-Verteilung', index=False)
        
        logger.info(f"📊 Sparse-Index-Summary exportiert: {summary_file}")
        return str(summary_file)


# ============================================================================
# Helper-Funktion für run_production_scraper.py
# ============================================================================
def build_sparse_index_from_chunks(
    chunk_ids: List[str],
    texts: List[str],
    collection_name: str = "wiso_documents",
    index_dir: str = "data/sparse_index",
    show_progress: bool = True
) -> BM25SparseIndex:
    """
    Convenience-Funktion zum Aufbau eines BM25-Index aus Chunks.
    
    Verwendung in run_production_scraper.py:
        from src.advanced_rag.retrieval.hybrid_retrieval_rrf import build_sparse_index_from_chunks
        
        if USE_HYBRID_RETRIEVAL:
            sparse_index = build_sparse_index_from_chunks(
                chunk_ids=[meta['chunk_id'] for meta in chunk_metadata],
                texts=all_chunks,
                collection_name=collection_name
            )
            sparse_index.save()
    
    Args:
        chunk_ids: Liste der Chunk-IDs
        texts: Liste der Chunk-Texte
        collection_name: Name der Collection
        index_dir: Verzeichnis für den Index
        show_progress: Zeige Fortschrittsanzeige
        
    Returns:
        Fertig gebauter und gespeicherter BM25SparseIndex
    """
    sparse_index = BM25SparseIndex(
        collection_name=collection_name,
        index_dir=index_dir
    )
    
    sparse_index.add_documents_batch(chunk_ids, texts, show_progress=show_progress)
    sparse_index.build_index()
    sparse_index.save()
    
    return sparse_index
