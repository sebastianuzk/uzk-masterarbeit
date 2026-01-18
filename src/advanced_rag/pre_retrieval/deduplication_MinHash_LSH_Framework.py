"""
Near-Deduplication mit datasketch Framework (MinHash + LSH)
===========================================================

Dieses Modul implementiert Near-Duplicate-Erkennung unter Verwendung des
etablierten `datasketch` Frameworks, das optimierte Implementierungen von
MinHash und Locality-Sensitive Hashing (LSH) bereitstellt.

Vorteile der Framework-Nutzung:
- Battle-tested Implementierung (seit 2015 entwickelt)
- Optimierte C-Extensions für Performance
- Umfangreiche Dokumentation und Community-Support
- Unterstützung für verschiedene LSH-Varianten

Vergleich zur Custom-Implementierung (deduplication_MinHash_LSH.py):
- datasketch: Schneller durch C-optimierten Code, weniger Kontrolle über Interna
- Custom: Volle Kontrolle, vollständig in Python, besser für Lehrzwecke

Literatur:
- datasketch Dokumentation: https://ekzhu.github.io/datasketch/
- Broder (1997): On the resemblance and containment of documents
- Leskovec et al. (2014): Mining of Massive Datasets, Chapter 3

Autor: Masterarbeit Sebastian - Universität zu Köln
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

# datasketch Framework
from datasketch import MinHash, MinHashLSH

# Lokale Imports
from .deduplication import normalize_text, UnionFind

logger = logging.getLogger(__name__)


# ============================================================================
# KONFIGURATION
# ============================================================================

@dataclass
class DatasketchConfig:
    """
    Konfiguration für datasketch-basierte Near-Deduplication.
    
    Werte werden aus RAGConfig geladen (Single Source of Truth: rag.env).
    Verwende DatasketchConfig.from_rag_config() zur Initialisierung.
    
    Attribute:
        num_perm: Anzahl der Permutationen für MinHash.
        threshold: Jaccard-Schwellwert für LSH.
        shingle_k: Größe der Wort-Shingles (k-grams).
        min_words: Minimale Wortanzahl für Deduplication.
        seed: Random Seed für deterministische MinHash-Permutationen.
        weights: LSH-Gewichtung (optional).
        use_content_type_grouping: HTML und PDF getrennt deduplizieren.
    """
    num_perm: int
    threshold: float
    shingle_k: int
    min_words: int
    seed: int
    weights: Optional[Tuple[float, float]] = None
    use_content_type_grouping: bool = True
    
    def __post_init__(self):
        """Validiere Konfiguration."""
        if not 0 < self.threshold <= 1.0:
            raise ValueError(f"threshold muss zwischen 0 und 1 liegen, ist: {self.threshold}")
        if self.num_perm < 16:
            raise ValueError(f"num_perm sollte mindestens 16 sein, ist: {self.num_perm}")
    
    @classmethod
    def from_rag_config(cls) -> 'DatasketchConfig':
        """
        Erstelle DatasketchConfig aus der globalen RAG-Konfiguration.
        
        Single Source of Truth: rag.env via RAGConfig, RANDOM_SEED aus .env
        
        Returns:
            DatasketchConfig mit Werten aus Config
        """
        from src.advanced_rag.rag_config import get_rag_config
        from config.settings import RANDOM_SEED
        rag_config = get_rag_config()
        
        return cls(
            num_perm=rag_config.near_deduplication_num_perm,
            threshold=rag_config.near_deduplication_similarity_threshold,
            shingle_k=rag_config.near_deduplication_shingle_k,
            min_words=rag_config.near_deduplication_min_words,
            seed=RANDOM_SEED
        )


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def _create_word_shingles(text: str, k: int = 5) -> Set[str]:
    """
    Erstelle Wort-Shingles (k-grams) aus normalisiertem Text.
    
    Args:
        text: Eingabetext
        k: Shingle-Größe (Anzahl Wörter pro Shingle)
        
    Returns:
        Set von Shingle-Strings
    """
    normalized = normalize_text(text)
    words = normalized.split()
    
    if len(words) < k:
        return {" ".join(words)} if words else set()
    
    shingles = set()
    for i in range(len(words) - k + 1):
        shingle = " ".join(words[i:i + k])
        shingles.add(shingle)
    
    return shingles


def _create_minhash(shingles: Set[str], num_perm: int = 128, seed: int = 42) -> MinHash:
    """
    Erstelle MinHash-Signatur für ein Shingle-Set mit datasketch.
    
    WICHTIG: Wir setzen hashfunc=None und permutations um Determinismus zu
    gewährleisten! datasketch verwendet sonst zufällige Permutationen.
    
    Args:
        shingles: Set von Shingle-Strings
        num_perm: Anzahl der Permutationen
        seed: Random Seed für Reproduzierbarkeit
        
    Returns:
        datasketch MinHash-Objekt
    """
    # Erstelle MinHash mit festem Seed für Determinismus
    # Durch Setzen von seed werden die Permutationen deterministisch generiert
    mh = MinHash(num_perm=num_perm, seed=seed)
    
    for shingle in shingles:
        # MinHash.update() erwartet bytes
        mh.update(shingle.encode('utf-8'))
    
    return mh


def _select_canonical_url(documents: List[dict], id_key: str = 'doc_id') -> dict:
    """
    Wähle das "kanonische" Dokument aus einer Gruppe von Near-Duplicates.
    
    Heuristiken (Priorität):
    1. Kürzere URL bevorzugen (oft Hauptseite)
    2. Weniger URL-Parameter bevorzugen
    3. Keine Anker (#) bevorzugen
    4. Bei Gleichheit: Mehr Text bevorzugen (vollständiger)
    
    Args:
        documents: Liste von Dokumenten in der Duplikat-Gruppe
        id_key: Key für die Dokument-ID
        
    Returns:
        Das ausgewählte kanonische Dokument
    """
    if not documents:
        raise ValueError("Leere Dokumentliste")
    
    if len(documents) == 1:
        return documents[0]
    
    def score(doc: dict) -> tuple:
        url = doc.get('url', '')
        text = doc.get('text', '')
        
        url_length = len(url)
        param_count = url.count('?') + url.count('&')
        has_anchor = 1 if '#' in url else 0
        text_length = -len(text)
        
        return (url_length, param_count, has_anchor, text_length)
    
    sorted_docs = sorted(documents, key=score)
    return sorted_docs[0]


# ============================================================================
# HAUPTFUNKTION: DATASKETCH-BASIERTE NEAR-DEDUPLICATION
# ============================================================================

def deduplicate_documents_datasketch(
    documents: List[dict],
    config: Optional[DatasketchConfig] = None,
    text_key: str = 'text',
    id_key: str = 'doc_id'
) -> Tuple[List[dict], List[dict], dict]:
    """
    Dedupliziere Dokumente mittels datasketch MinHash + LSH.
    
    Diese Funktion nutzt das etablierte datasketch-Framework für:
    1. Wort-Shingling für jedes Dokument
    2. MinHash-Signaturen mit datasketch.MinHash
    3. LSH-Index mit datasketch.MinHashLSH
    4. Automatische Kandidaten-Findung
    5. Union-Find Clustering
    6. Canonical Selection pro Cluster
    
    WICHTIG: Die Funktion ist DETERMINISTISCH wenn der gleiche Seed verwendet wird.
    
    Args:
        documents: Liste von Dokumenten (dict mit text_key und id_key)
        config: DatasketchConfig (default: aus RAGConfig/rag.env)
        text_key: Schlüssel für den Text im Dokument
        id_key: Schlüssel für die Dokument-ID
        
    Returns:
        Tuple von:
        - unique_documents: Liste der behaltenen Dokumente
        - removed_documents: Liste der entfernten Near-Duplicates
        - stats: Statistiken über den Deduplication-Prozess
    """
    if config is None:
        config = DatasketchConfig.from_rag_config()
    
    # Ausgabe der Config-Parameter
    print(f"   ⚙️  Config: num_perm={config.num_perm}, threshold={config.threshold}")
    print(f"             shingle_k={config.shingle_k}, min_words={config.min_words}, seed={config.seed}")
    
    logger.info(f"datasketch Near-Deduplication: {len(documents)} Dokumente")
    logger.info(f"   Config: num_perm={config.num_perm}, threshold={config.threshold}, "
                f"shingle_k={config.shingle_k}, seed={config.seed}")
    
    if not documents:
        return [], [], {"total": 0, "unique": 0, "duplicates_removed": 0}
    
    # ================================================================
    # SCHRITT 1: Dokumente nach Content-Type gruppieren (optional)
    # ================================================================
    if config.use_content_type_grouping:
        docs_by_type: Dict[str, List[dict]] = defaultdict(list)
        for doc in documents:
            content_type = doc.get('content_type', 'unknown')
            docs_by_type[content_type].append(doc)
        logger.info(f"   Content-Types: {', '.join(f'{ct}={len(docs)}' for ct, docs in docs_by_type.items())}")
    else:
        docs_by_type = {'all': documents}
    
    # ================================================================
    # SCHRITT 2: Shingles und MinHash-Signaturen berechnen
    # ================================================================
    doc_shingles: Dict[str, Set[str]] = {}
    doc_minhashes: Dict[str, MinHash] = {}
    doc_word_counts: Dict[str, int] = {}
    skipped_docs: Set[str] = set()
    
    for doc in documents:
        doc_id = doc.get(id_key)
        text = doc.get(text_key, '')
        
        # Normalisiere und zähle Wörter
        normalized = normalize_text(text)
        words = normalized.split()
        word_count = len(words)
        doc_word_counts[doc_id] = word_count
        
        # Nur Dokumente mit >= min_words für Vergleich
        if word_count >= config.min_words:
            shingles = _create_word_shingles(text, k=config.shingle_k)
            doc_shingles[doc_id] = shingles
            
            # MinHash mit datasketch erstellen
            mh = _create_minhash(shingles, num_perm=config.num_perm, seed=config.seed)
            doc_minhashes[doc_id] = mh
        else:
            skipped_docs.add(doc_id)
    
    logger.info(f"   {len(doc_minhashes)} MinHash-Signaturen berechnet, {len(skipped_docs)} zu kurz")
    
    # ================================================================
    # SCHRITT 3: LSH-Index aufbauen und Kandidaten finden
    # ================================================================
    all_candidate_pairs: Set[Tuple[str, str]] = set()
    
    for content_type, type_docs in docs_by_type.items():
        # LSH-Index mit datasketch erstellen
        # threshold: automatische Optimierung von Bands/Rows
        lsh_kwargs = {
            'threshold': config.threshold,
            'num_perm': config.num_perm
        }
        # weights nur hinzufügen wenn explizit gesetzt
        if config.weights is not None:
            lsh_kwargs['weights'] = config.weights
        
        lsh = MinHashLSH(**lsh_kwargs)
        
        # Füge alle Dokumente mit MinHash zum Index hinzu
        for doc in type_docs:
            doc_id = doc.get(id_key)
            if doc_id in doc_minhashes:
                lsh.insert(doc_id, doc_minhashes[doc_id])
        
        # Finde Kandidaten für jedes Dokument
        for doc in type_docs:
            doc_id = doc.get(id_key)
            if doc_id not in doc_minhashes:
                continue
            
            # Query gibt alle ähnlichen Dokumente zurück
            candidates = lsh.query(doc_minhashes[doc_id])
            
            for candidate_id in candidates:
                if candidate_id != doc_id:
                    # Sortiere IDs für konsistente Paare
                    if doc_id < candidate_id:
                        all_candidate_pairs.add((doc_id, candidate_id))
                    else:
                        all_candidate_pairs.add((candidate_id, doc_id))
    
    logger.info(f"   {len(all_candidate_pairs):,} LSH-Kandidatenpaare")
    
    # ================================================================
    # SCHRITT 4: Kandidaten verifizieren mit MinHash Jaccard-Schätzung
    # ================================================================
    union_find = UnionFind()
    verified_pairs: List[Tuple[str, str, float]] = []
    
    for doc_id1, doc_id2 in all_candidate_pairs:
        mh1 = doc_minhashes.get(doc_id1)
        mh2 = doc_minhashes.get(doc_id2)
        
        if mh1 is None or mh2 is None:
            continue
        
        # Jaccard-Schätzung mit datasketch (sehr schnell!)
        estimated_jaccard = mh1.jaccard(mh2)
        
        if estimated_jaccard >= config.threshold:
            verified_pairs.append((doc_id1, doc_id2, estimated_jaccard))
            union_find.union(doc_id1, doc_id2)
    
    logger.info(f"   {len(verified_pairs)} verifizierte Near-Duplicate-Paare")
    
    # ================================================================
    # SCHRITT 5: Cluster extrahieren
    # ================================================================
    raw_clusters = union_find.get_clusters()
    duplicate_clusters = {k: v for k, v in raw_clusters.items() if len(v) > 1}
    
    # ================================================================
    # SCHRITT 6: Canonical wählen, Rest als Duplikate markieren
    # ================================================================
    id_to_doc = {doc.get(id_key): doc for doc in documents}
    
    canonical_doc_ids: Set[str] = set()
    removed_doc_ids: Set[str] = set()
    cluster_info: List[dict] = []
    
    for cluster_idx, (root, member_ids) in enumerate(sorted(duplicate_clusters.items()), 1):
        member_docs = [id_to_doc[mid] for mid in member_ids if mid in id_to_doc]
        
        if len(member_docs) < 2:
            continue
        
        # Wähle Canonical
        canonical = _select_canonical_url(member_docs, id_key=id_key)
        canonical_id = canonical.get(id_key)
        canonical_doc_ids.add(canonical_id)
        
        # Rest sind Duplikate
        for doc in member_docs:
            doc_id = doc.get(id_key)
            if doc_id != canonical_id:
                removed_doc_ids.add(doc_id)
                doc['_kept_doc_id'] = canonical_id
                doc['_near_duplicate_of'] = canonical.get('url', '')
        
        cluster_info.append({
            'cluster_idx': cluster_idx,
            'canonical_id': canonical_id,
            'canonical_url': canonical.get('url', ''),
            'member_ids': list(member_ids),
            'size': len(member_docs)
        })
    
    logger.info(f"   {len(duplicate_clusters)} Cluster mit {len(removed_doc_ids)} zu entfernenden Dokumenten")
    
    # ================================================================
    # SCHRITT 7: Unique und Removed Listen erstellen
    # ================================================================
    unique_documents = []
    removed_documents = []
    
    for doc in documents:
        doc_id = doc.get(id_key)
        if doc_id in removed_doc_ids:
            removed_documents.append(doc)
        else:
            unique_documents.append(doc)
    
    # ================================================================
    # SCHRITT 8: Statistiken
    # ================================================================
    stats = {
        "total": len(documents),
        "unique": len(unique_documents),
        "duplicates_removed": len(removed_documents),
        "clusters": len(duplicate_clusters),
        "lsh_candidate_pairs": len(all_candidate_pairs),
        "verified_pairs": len(verified_pairs),
        "skipped_short_docs": len(skipped_docs),
        "reduction_percent": (len(removed_documents) / len(documents) * 100) if documents else 0,
        "config": {
            "framework": "datasketch",
            "version": "1.8.0",
            "num_perm": config.num_perm,
            "threshold": config.threshold,
            "shingle_k": config.shingle_k,
            "min_words": config.min_words,
            "seed": config.seed,
            "weights": config.weights
        },
        "_cluster_info": cluster_info
    }
    
    # Ausgabe der Ergebnisse
    print(f"   📊 Input:    {stats['total']:,} Dokumente")
    print(f"   📊 Unique:   {stats['unique']:,} Dokumente")
    print(f"   📊 Entfernt: {stats['duplicates_removed']:,} Near-Duplicates")
    print(f"   📊 Cluster:  {stats['clusters']:,}")
    print(f"   📊 LSH-Kandidatenpaare: {stats['lsh_candidate_pairs']:,}")
    print(f"   📊 Verifizierte Paare: {stats['verified_pairs']:,}")
    print(f"   📊 Übersprungen (zu kurz): {stats['skipped_short_docs']:,}")
    print(f"   📊 Reduktion: {stats['reduction_percent']:.1f}%")
    
    logger.info(
        f"datasketch: {stats['total']} → {stats['unique']} Dokumente "
        f"({stats['duplicates_removed']} entfernt, {stats['reduction_percent']:.1f}%)"
    )
    
    return unique_documents, removed_documents, stats


# ============================================================================
# EXCEL-EXPORT FÜR NEAR-DEDUPLICATION (MINHASH + LSH)
# ============================================================================

def create_near_dedup_excel_datasketch(
    unique_docs: List[dict], 
    removed_docs: List[dict], 
    stats: dict,
    output_path: str = None
) -> str:
    """
    Erstelle Excel-Übersicht für MinHash+LSH Near-Deduplication.
    
    Diese Funktion nutzt intern die generische create_near_dedup_excel() 
    aus deduplication.py, konvertiert aber die datasketch-spezifischen 
    Stats in das erwartete Format.
    
    Args:
        unique_docs: Liste der behaltenen Dokumente
        removed_docs: Liste der entfernten Near-Duplicates
        stats: Statistiken aus deduplicate_documents_datasketch()
        output_path: Optional: Pfad für Excel-Datei
    
    Returns:
        Pfad zur erstellten Excel-Datei
    """
    from pathlib import Path
    from .deduplication import create_near_dedup_excel
    
    # Konvertiere datasketch-Stats in generisches Format
    stats_for_excel = stats.copy()
    stats_for_excel['candidate_pairs'] = stats.get('lsh_candidate_pairs', 0)
    
    # Config-Werte auf Top-Level für Excel-Funktion
    config = stats.get('config', {})
    stats_for_excel['shingle_k'] = config.get('shingle_k', 5)
    stats_for_excel['similarity_threshold'] = config.get('threshold', 0.85)
    stats_for_excel['min_words'] = config.get('min_words', 120)
    
    # Generiere Dateinamen mit Threshold und Timestamp wenn kein Pfad angegeben
    if output_path is None:
        from datetime import datetime
        threshold = config.get('threshold', 0.85)
        threshold_str = str(threshold).replace('.', '')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"data/deduplication/near_deduplication_minhash_lsh_{threshold_str}_{timestamp}.xlsx"
    
    # Rufe generische Excel-Funktion auf
    return create_near_dedup_excel(
        unique_docs, 
        removed_docs, 
        stats_for_excel, 
        output_path=output_path
    )


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'DatasketchConfig',
    'deduplicate_documents_datasketch',
    'create_near_dedup_excel_datasketch',
]
