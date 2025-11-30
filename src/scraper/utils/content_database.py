"""
Content Database für permanente Speicherung
==========================================

Separate Datenbank zur strukturierten Speicherung aller gescrapten 
HTML- und PDF-Inhalte, unabhängig von Cache und Vektordatenbank.

Features:
- Permanente Speicherung von HTML- und PDF-Inhalten
- Strukturierte Metadaten (URL, Titel, Kategorie, Timestamps)
- Volltextsuche über alle Inhalte
- Deduplizierung über Content-Hash
- Kompression zur Speicherplatzoptimierung
"""

import sqlite3
import logging
import gzip
import hashlib
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class StoredDocument:
    """Gespeichertes Dokument mit vollständigen Metadaten."""
    id: Optional[int]
    url: str
    title: str
    content: str
    content_type: str  # 'html' oder 'pdf'
    category: str
    content_hash: str
    content_length: int
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiere zu Dictionary."""
        data = asdict(self)
        data['metadata'] = json.dumps(data['metadata'])
        return data


class ContentDatabase:
    """
    Permanente Datenbank für alle gescrapten Inhalte.
    
    Speichert HTML- und PDF-Dokumente mit vollständigen Metadaten
    in einer strukturierten SQLite-Datenbank, getrennt von Cache 
    und Vektordatenbank.
    """
    
    def __init__(self, db_path: Path):
        """
        Initialisiere Content Database.
        
        Args:
            db_path: Pfad zur Datenbankdatei
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        
        self._init_database()
        logger.info(f"Content Database initialisiert: {self.db_path}")
    
    def _init_database(self):
        """Erstelle Datenbank-Schema."""
        with self.lock:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA cache_size=10000")
                
                # Haupttabelle für Dokumente
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL UNIQUE,
                        title TEXT NOT NULL,
                        content BLOB NOT NULL,
                        content_type TEXT NOT NULL,
                        category TEXT NOT NULL,
                        content_hash TEXT NOT NULL,
                        content_length INTEGER NOT NULL,
                        metadata TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                # Indices für Performance
                conn.execute("CREATE INDEX IF NOT EXISTS idx_url ON documents(url)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON documents(content_hash)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_content_type ON documents(content_type)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON documents(category)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON documents(created_at)")
                
                # Volltextsuche-Index
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts 
                    USING fts5(url, title, content, category, content='documents', content_rowid='id')
                """)
                
                # Trigger für automatische FTS-Updates
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
                        INSERT INTO documents_fts(rowid, url, title, content, category)
                        VALUES (new.id, new.url, new.title, new.content, new.category);
                    END
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS documents_ad AFTER DELETE ON documents BEGIN
                        DELETE FROM documents_fts WHERE rowid = old.id;
                    END
                """)
                
                conn.execute("""
                    CREATE TRIGGER IF NOT EXISTS documents_au AFTER UPDATE ON documents BEGIN
                        UPDATE documents_fts SET 
                            url = new.url, 
                            title = new.title, 
                            content = new.content,
                            category = new.category
                        WHERE rowid = new.id;
                    END
                """)
                
                conn.commit()
    
    def _generate_content_hash(self, content: str) -> str:
        """Generiere SHA256-Hash für Content-Deduplizierung."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _compress_content(self, content: str) -> bytes:
        """Komprimiere Content mit gzip."""
        return gzip.compress(content.encode('utf-8'), compresslevel=6)
    
    def _decompress_content(self, compressed: bytes) -> str:
        """Dekomprimiere Content."""
        return gzip.decompress(compressed).decode('utf-8')
    
    def add_document(
        self,
        url: str,
        title: str,
        content: str,
        content_type: str,
        category: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Füge Dokument zur Datenbank hinzu oder aktualisiere bestehendes.
        
        Args:
            url: URL des Dokuments
            title: Titel
            content: Volltext-Inhalt
            content_type: 'html' oder 'pdf'
            category: Inhaltskategorie
            metadata: Zusätzliche Metadaten
            
        Returns:
            Document ID oder None bei Fehler
        """
        if not content.strip():
            logger.warning(f"Leerer Content für {url}, überspringe")
            return None
        
        with self.lock:
            try:
                content_hash = self._generate_content_hash(content)
                compressed_content = self._compress_content(content)
                now = datetime.now().isoformat()
                
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    # Prüfe ob Dokument bereits existiert
                    cursor = conn.execute(
                        "SELECT id, content_hash FROM documents WHERE url = ?",
                        (url,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        doc_id, existing_hash = existing
                        if existing_hash == content_hash:
                            logger.debug(f"Dokument unverändert: {url}")
                            return doc_id
                        
                        # Update bestehendes Dokument
                        conn.execute("""
                            UPDATE documents 
                            SET title = ?, content = ?, content_type = ?, 
                                category = ?, content_hash = ?, content_length = ?,
                                metadata = ?, updated_at = ?
                            WHERE id = ?
                        """, (
                            title, compressed_content, content_type, category,
                            content_hash, len(content), json.dumps(metadata or {}),
                            now, doc_id
                        ))
                        logger.info(f"Dokument aktualisiert: {url}")
                        return doc_id
                    
                    # Insert neues Dokument
                    cursor = conn.execute("""
                        INSERT INTO documents 
                        (url, title, content, content_type, category, content_hash, 
                         content_length, metadata, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        url, title, compressed_content, content_type, category,
                        content_hash, len(content), json.dumps(metadata or {}),
                        now, now
                    ))
                    
                    conn.commit()
                    doc_id = cursor.lastrowid
                    logger.info(f"Dokument hinzugefügt: {url} (ID: {doc_id})")
                    return doc_id
                    
            except Exception as e:
                logger.error(f"Fehler beim Speichern von {url}: {e}")
                return None
    
    def get_document(self, url: str) -> Optional[StoredDocument]:
        """
        Hole Dokument aus Datenbank.
        
        Args:
            url: URL des Dokuments
            
        Returns:
            StoredDocument oder None
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    cursor = conn.execute("""
                        SELECT id, url, title, content, content_type, category,
                               content_hash, content_length, metadata, created_at, updated_at
                        FROM documents WHERE url = ?
                    """, (url,))
                    
                    row = cursor.fetchone()
                    if not row:
                        return None
                    
                    doc_id, url, title, compressed_content, content_type, category, \
                    content_hash, content_length, metadata_json, created_at, updated_at = row
                    
                    content = self._decompress_content(compressed_content)
                    metadata = json.loads(metadata_json) if metadata_json else {}
                    
                    return StoredDocument(
                        id=doc_id,
                        url=url,
                        title=title,
                        content=content,
                        content_type=content_type,
                        category=category,
                        content_hash=content_hash,
                        content_length=content_length,
                        metadata=metadata,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    
            except Exception as e:
                logger.error(f"Fehler beim Abrufen von {url}: {e}")
                return None
    
    def search(
        self,
        query: str,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100
    ) -> List[StoredDocument]:
        """
        Volltextsuche über alle Dokumente.
        
        Args:
            query: Suchbegriff
            content_type: Filter nach 'html' oder 'pdf'
            category: Filter nach Kategorie
            limit: Max. Anzahl Ergebnisse
            
        Returns:
            Liste von StoredDocuments
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    sql = """
                        SELECT d.id, d.url, d.title, d.content, d.content_type, 
                               d.category, d.content_hash, d.content_length, 
                               d.metadata, d.created_at, d.updated_at
                        FROM documents d
                        JOIN documents_fts fts ON d.id = fts.rowid
                        WHERE documents_fts MATCH ?
                    """
                    params = [query]
                    
                    if content_type:
                        sql += " AND d.content_type = ?"
                        params.append(content_type)
                    
                    if category:
                        sql += " AND d.category = ?"
                        params.append(category)
                    
                    sql += " LIMIT ?"
                    params.append(limit)
                    
                    cursor = conn.execute(sql, params)
                    results = []
                    
                    for row in cursor.fetchall():
                        doc_id, url, title, compressed_content, content_type, category, \
                        content_hash, content_length, metadata_json, created_at, updated_at = row
                        
                        content = self._decompress_content(compressed_content)
                        metadata = json.loads(metadata_json) if metadata_json else {}
                        
                        results.append(StoredDocument(
                            id=doc_id,
                            url=url,
                            title=title,
                            content=content,
                            content_type=content_type,
                            category=category,
                            content_hash=content_hash,
                            content_length=content_length,
                            metadata=metadata,
                            created_at=created_at,
                            updated_at=updated_at
                        ))
                    
                    return results
                    
            except Exception as e:
                logger.error(f"Fehler bei Suche '{query}': {e}")
                return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Hole Statistiken über gespeicherte Dokumente.
        
        Returns:
            Dictionary mit Statistiken
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    stats = {}
                    
                    # Gesamtanzahl
                    cursor = conn.execute("SELECT COUNT(*) FROM documents")
                    stats['total_documents'] = cursor.fetchone()[0]
                    
                    # Nach Content-Type
                    cursor = conn.execute("""
                        SELECT content_type, COUNT(*) 
                        FROM documents 
                        GROUP BY content_type
                    """)
                    stats['by_type'] = dict(cursor.fetchall())
                    
                    # Nach Kategorie
                    cursor = conn.execute("""
                        SELECT category, COUNT(*) 
                        FROM documents 
                        GROUP BY category
                        ORDER BY COUNT(*) DESC
                    """)
                    stats['by_category'] = dict(cursor.fetchall())
                    
                    # Speichergröße
                    cursor = conn.execute("""
                        SELECT SUM(LENGTH(content)) as compressed_size,
                               SUM(content_length) as original_size
                        FROM documents
                    """)
                    compressed, original = cursor.fetchone()
                    stats['storage'] = {
                        'compressed_bytes': compressed or 0,
                        'compressed_mb': round((compressed or 0) / 1024 / 1024, 2),
                        'original_bytes': original or 0,
                        'original_mb': round((original or 0) / 1024 / 1024, 2),
                        'compression_ratio': round(compressed / original * 100, 1) if original else 0
                    }
                    
                    # Zeitliche Verteilung
                    cursor = conn.execute("""
                        SELECT DATE(created_at) as date, COUNT(*) 
                        FROM documents 
                        GROUP BY DATE(created_at)
                        ORDER BY date DESC
                        LIMIT 10
                    """)
                    stats['recent_additions'] = dict(cursor.fetchall())
                    
                    return stats
                    
            except Exception as e:
                logger.error(f"Fehler beim Abrufen der Statistiken: {e}")
                return {}
    
    def list_documents(
        self,
        content_type: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Tuple[int, str, str, str, str]]:
        """
        Liste Dokumente mit Basisinformationen.
        
        Args:
            content_type: Filter nach Typ
            category: Filter nach Kategorie
            limit: Max. Anzahl
            offset: Offset für Pagination
            
        Returns:
            Liste von (id, url, title, content_type, category)
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    sql = "SELECT id, url, title, content_type, category FROM documents WHERE 1=1"
                    params = []
                    
                    if content_type:
                        sql += " AND content_type = ?"
                        params.append(content_type)
                    
                    if category:
                        sql += " AND category = ?"
                        params.append(category)
                    
                    sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                    
                    cursor = conn.execute(sql, params)
                    return cursor.fetchall()
                    
            except Exception as e:
                logger.error(f"Fehler beim Auflisten: {e}")
                return []
    
    def delete_document(self, url: str) -> bool:
        """
        Lösche Dokument aus Datenbank.
        
        Args:
            url: URL des zu löschenden Dokuments
            
        Returns:
            True bei Erfolg
        """
        with self.lock:
            try:
                with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                    conn.execute("DELETE FROM documents WHERE url = ?", (url,))
                    conn.commit()
                    logger.info(f"Dokument gelöscht: {url}")
                    return True
            except Exception as e:
                logger.error(f"Fehler beim Löschen von {url}: {e}")
                return False
    
    def close(self):
        """Schließe Datenbankverbindungen (Cleanup)."""
        logger.info("Content Database geschlossen")
