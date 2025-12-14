"""
Produktiver Offline-Scraper für die komplette Datenbasis
=========================================================
Verarbeitet alle 2675 Dokumente (2242 HTML + 433 PDF).
Respektiert RAG_NAIVE_SETUP Flag:
- RAG_NAIVE_SETUP=true  → Naive RAG ohne Advanced Pre-Retrieval
- RAG_NAIVE_SETUP=false → Advanced RAG mit Pre-Retrieval Techniken
"""
import sys
import os
# Füge Projekt-Root zum Path hinzu
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

import sqlite3
import gzip
import re
from pathlib import Path
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
import time
from datetime import datetime
import pandas as pd

# Scraper Utils
from src.scraper.utils.checkpoint_manager import CheckpointManager

# Zentrale Konfiguration
from config.settings import SENTENCE_TRANSFORMER_MODEL

# Lade RAG Configuration
try:
    from src.advanced_rag.rag_config import RAGConfig
    rag_config = RAGConfig.load_from_env()
    # Prüfe ob mindestens eine Advanced-Technik aktiv ist
    USE_ADVANCED = not rag_config.baseline_enabled
    # Individuelle Feature-Flags
    USE_SEMANTIC_CHUNKING = rag_config.use_semantic_chunking
    USE_CONTENT_CLEANING = rag_config.use_content_cleaning
    USE_DEDUPLICATION = rag_config.use_deduplication
    USE_MULTI_COLLECTION = rag_config.use_multi_collection_search
except Exception as e:
    print(f"⚠️  Fehler beim Laden der RAG-Config: {e}")
    print("   Verwende Naive RAG als Fallback")
    USE_ADVANCED = False
    USE_SEMANTIC_CHUNKING = False
    USE_CONTENT_CLEANING = False
    USE_DEDUPLICATION = False
    USE_MULTI_COLLECTION = False

# Conditional Imports für Advanced-Techniken (nur wenn benötigt)
if USE_SEMANTIC_CHUNKING:
    from src.advanced_rag.pre_retrieval.chunking import SemanticChunker
if USE_CONTENT_CLEANING:
    from src.advanced_rag.pre_retrieval.cleaning import ContentCleaner
if USE_DEDUPLICATION:
    from src.advanced_rag.pre_retrieval.deduplication import ContentDeduplicator, deduplicate_documents_exact, create_dedup_excel
if USE_MULTI_COLLECTION:
    from src.advanced_rag.pre_retrieval.collection_categorizer import CollectionCategorizer

# Datenbank-Pfade
CONTENT_DB = Path("data/content_database.db")
VECTOR_DB = Path("data/vector_db")

# Initialisiere Checkpoint Manager
checkpoint_mgr = CheckpointManager()

def get_collection_name(url: str, categorizer=None) -> str:
    """
    Bestimme Collection-Name basierend auf URL.
    
    Args:
        url: Dokument-URL
        categorizer: Optional CollectionCategorizer (Advanced RAG)
    
    Returns:
        Collection-Name
    """
    # ADVANCED RAG: Multi-Collection via CollectionCategorizer
    if categorizer is not None:
        return categorizer.get_collection_name(url)
    
    # NAIVE RAG (Standard): Nur eine Collection
    return 'wiso_documents'

def check_existing_progress():
    """Prüfe welche Collections bereits existieren und vollständig sind."""
    print("\n" + "=" * 80)
    print("SCHRITT 1: Prüfe bestehenden Fortschritt")
    print("=" * 80)
    
    if not VECTOR_DB.exists():
        print("✅ Vektordatenbank existiert noch nicht - starte von vorne")
        phase1_data = checkpoint_mgr.load_phase1_checkpoint()
        return set(), phase1_data  # Keine Collections vorhanden, aber evtl. Phase 1 Checkpoint
    
    # Verbinde zu ChromaDB
    client = chromadb.PersistentClient(path=str(VECTOR_DB))
    
    # Prüfe bestehende Collections
    existing_collections = client.list_collections()
    completed_collections = set()
    
    if existing_collections:
        print(f"\n📊 Gefundene Collections:")
        for collection in existing_collections:
            count = collection.count()
            if count > 0:
                completed_collections.add(collection.name)
                print(f"   ✅ {collection.name}: {count:,} Chunks (wird übersprungen)")
            else:
                print(f"   ⚠️  {collection.name}: leer (wird neu verarbeitet)")
        
        if completed_collections:
            print(f"\n🔄 Fortsetzen: {len(completed_collections)} Collections bereits fertig")
    else:
        print("✅ Keine bestehenden Collections - starte von vorne")
    
    # Prüfe Phase 1 Checkpoint
    phase1_data = checkpoint_mgr.load_phase1_checkpoint()
    
    return completed_collections, phase1_data

def decompress_content(compressed_data: bytes) -> str:
    """Dekomprimiere gzip-Content."""
    return gzip.decompress(compressed_data).decode('utf-8')

def naive_extract_text_from_html(html: str) -> str:
    """
    Naive HTML-zu-Text Extraktion mit Strukturerhaltung.
    Konvertiert HTML zu Markdown-ähnlichem Text.
    
    Erhaltene Strukturen:
    - Überschriften (h1-h6) → # Markdown-Überschriften
    - Listen (ul/ol) → - oder 1. Listenelemente
    - Blockquotes → > Zitate
    - Absätze/Divs → Zeilenumbrüche
    
    Entfernt:
    - Script, Style, Head, Meta Tags
    - Navigation, Footer, Aside (Layout-Elemente)
    - Elemente mit menu/nav/sidebar/breadcrumb Klassen
    - UI-Texte wie "Menü schließen"
    - HTML-Tags selbst
    - Übermäßige Whitespaces
    """
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. Entferne unsichtbare Elemente komplett
    for element in soup(['script', 'style', 'head', 'meta', 'link', 'noscript', 'iframe']):
        element.decompose()
    
    # 2. Entferne Layout-Elemente ohne semantischen Inhalt
    for element in soup(['nav', 'footer', 'aside']):
        element.decompose()
    
    # 3. Entferne Elemente mit bestimmten Klassen/IDs (Navigation, Menüs, Sidebars)
    boilerplate_patterns = re.compile(r'menu|nav|sidebar|breadcrumb|cookie|banner|popup|modal', re.IGNORECASE)
    for element in soup.find_all(class_=boilerplate_patterns):
        element.decompose()
    for element in soup.find_all(id=boilerplate_patterns):
        element.decompose()
    
    # 4. Überschriften → Markdown
    for i, tag in enumerate(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        for h in soup.find_all(tag):
            prefix = '#' * (i + 1) + ' '
            h.insert_before('\n\n')
            h.insert_after('\n')
            if h.string:
                h.string = prefix + h.get_text().strip()
            else:
                h.insert_before(prefix)
    
    # 5. Listen → Markdown
    # Nummerierte Listen
    for ol in soup.find_all('ol'):
        ol.insert_before('\n')
        ol.insert_after('\n')
        for i, li in enumerate(ol.find_all('li', recursive=False), 1):
            li.insert_before(f'\n{i}. ')
    
    # Unnummerierte Listen
    for ul in soup.find_all('ul'):
        ul.insert_before('\n')
        ul.insert_after('\n')
        for li in ul.find_all('li', recursive=False):
            li.insert_before('\n- ')
    
    # 6. Blockquotes → Markdown
    for bq in soup.find_all('blockquote'):
        bq.insert_before('\n')
        bq.insert_after('\n')
        # Füge > vor dem Text ein
        text = bq.get_text().strip()
        quoted_lines = '\n'.join('> ' + line for line in text.split('\n'))
        bq.string = quoted_lines
    
    # 7. Block-Elemente → Zeilenumbrüche
    for tag in soup.find_all(['p', 'div', 'br', 'tr', 'article', 'section']):
        tag.insert_before('\n')
        if tag.name != 'br':
            tag.insert_after('\n')
    
    # 8. Tabellenzellen → Tab-getrennt
    for td in soup.find_all(['td', 'th']):
        td.insert_after('\t')
    
    # 9. Extrahiere Text
    text = soup.get_text()
    
    # 10. Entferne typische UI-Texte
    ui_patterns = [
        r'Menü schließen',
        r'Zur Übersichtsseite\s+\w+',
        r'zum Inhalt springen',
        r'Sprache wechseln',
        r'Suchbegriff eingeben',
        r'Abschicken',
        r'Finden',
        r'EnglishEnglish',
        r'Hauptnavigation\..*?anzuspringen\.',
    ]
    for pattern in ui_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # 11. Bereinige Whitespace
    text = re.sub(r'[ \t]+', ' ', text)  # Mehrere Spaces/Tabs zu einem Space
    text = re.sub(r'\n[ \t]+', '\n', text)  # Spaces am Zeilenanfang entfernen
    text = re.sub(r'[ \t]+\n', '\n', text)  # Spaces am Zeilenende entfernen
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 Zeilenumbrüche
    
    return text.strip()

def naive_clean_text(text: str) -> str:
    """Naive Text-Bereinigung für bereits extrahierten Text (z.B. PDFs)."""
    # Nur grundlegende Bereinigung
    text = re.sub(r'\s+', ' ', text)  # Normalisiere Leerzeichen
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Entferne mehrfache Zeilenumbrüche
    return text.strip()

def naive_chunk_text(text: str, chunk_size: int, overlap: int) -> list:
    """
    Naive Chunking: Einfaches Character-basiertes Chunking mit Overlap.
    
    Args:
        text: Eingabetext
        chunk_size: Chunk-Größe in Zeichen (REQUIRED)
        overlap: Überlappung zwischen Chunks (REQUIRED)
    
    Returns:
        Liste von Text-Chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Nur hinzufügen wenn nicht zu klein
        if len(chunk.strip()) > 50:
            chunks.append(chunk.strip())
        
        # Nächster Start mit Overlap
        start = end - overlap
    
    return chunks


def extract_document_text(doc_id, url, title, content, content_type, content_cleaner=None):
    """
    Extrahiere und bereinige Text aus einem Dokument (OHNE Chunking).
    Für Exact-Deduplication auf Dokument-Ebene.
    
    Args:
        doc_id: Dokument-ID
        url: Quell-URL
        title: Dokumenttitel
        content: Komprimierter Inhalt (gzip)
        content_type: 'html' oder 'pdf'
        content_cleaner: Optional ContentCleaner
    
    Returns:
        dict mit doc_id, url, title, content_type, text
        oder None bei Fehler
    """
    try:
        # Dekomprimiere
        raw_content = decompress_content(content)
        
        # Basis-Cleaning: HTML → Markdown-ähnlicher Text
        if content_type == 'html':
            cleaned_text = naive_extract_text_from_html(raw_content)
        else:  # pdf
            cleaned_text = naive_clean_text(raw_content)
        
        # Optional: Erweitertes Content Cleaning
        if USE_CONTENT_CLEANING and content_cleaner is not None:
            cleaned_text = content_cleaner._clean_text(cleaned_text)
        
        if not cleaned_text or len(cleaned_text.strip()) < 50:
            return None
        
        return {
            'doc_id': str(doc_id),
            'url': url,
            'title': title,
            'content_type': content_type,
            'text': cleaned_text
        }
        
    except Exception as e:
        print(f"\n⚠️  Fehler beim Extrahieren von Dokument {doc_id}: {e}")
        return None


def chunk_document(doc_dict, chunker=None, categorizer=None):
    """
    Chunke ein bereits extrahiertes Dokument.
    
    Args:
        doc_dict: Dictionary mit doc_id, url, title, content_type, text
        chunker: Optional SemanticChunker
        categorizer: Optional CollectionCategorizer
    
    Returns:
        dict mit Chunks und Metadaten oder None
    """
    try:
        cleaned_text = doc_dict['text']
        url = doc_dict['url']
        
        # Chunking: Semantic oder Naive
        if USE_SEMANTIC_CHUNKING and chunker is not None:
            chunks = chunker.chunk_by_paragraphs(cleaned_text)
        else:
            chunks = naive_chunk_text(
                cleaned_text, 
                chunk_size=rag_config.naive_chunking_max_size,
                overlap=rag_config.naive_chunking_overlap
            )
        
        if len(chunks) == 0:
            return None
        
        # Bestimme Collection
        collection_name = get_collection_name(url, categorizer if USE_MULTI_COLLECTION else None)
        
        return {
            'doc_id': doc_dict['doc_id'],
            'url': url,
            'title': doc_dict['title'],
            'content_type': doc_dict['content_type'],
            'chunks': chunks,
            'collection_name': collection_name
        }
        
    except Exception as e:
        print(f"\n⚠️  Fehler beim Chunking von Dokument {doc_dict.get('doc_id', '?')}: {e}")
        return None


def process_document(doc_id, url, title, content, content_type, 
                     content_cleaner=None, chunker=None, deduplicator=None, categorizer=None):
    """
    Verarbeite ein einzelnes Dokument (ohne Embeddings).
    Respektiert individuelle Feature-Flags.
    
    Returns:
        dict mit Chunks und Metadaten oder None wenn übersprungen
    """
    try:
        # Dekomprimiere
        raw_content = decompress_content(content)
        
        # Basis-Cleaning für alle Modi: HTML → Markdown-ähnlicher Text
        if content_type == 'html':
            cleaned_text = naive_extract_text_from_html(raw_content)
        else:  # pdf
            cleaned_text = naive_clean_text(raw_content)
        
        # Optional: Erweitertes Content Cleaning
        if USE_CONTENT_CLEANING and content_cleaner is not None:
            cleaned_text = content_cleaner._clean_text(cleaned_text)
        
        # Chunking: Semantic oder Naive
        if USE_SEMANTIC_CHUNKING and chunker is not None:
            chunks = chunker.chunk_by_paragraphs(cleaned_text)
        else:
            # Naive Chunking mit konfigurierbaren Parametern aus rag_config
            chunks = naive_chunk_text(
                cleaned_text, 
                chunk_size=rag_config.naive_chunking_max_size,
                overlap=rag_config.naive_chunking_overlap
            )
        
        # Optional: Deduplication (nur für HTMLs)
        if USE_DEDUPLICATION and deduplicator is not None and content_type == 'html' and len(chunks) > 0:
            chunk_docs = [{"url": f"{url}#chunk_{i}", "content": chunk} for i, chunk in enumerate(chunks)]
            unique_chunks, _ = deduplicator.deduplicate_batch(chunk_docs)
            chunks = [doc["content"] for doc in unique_chunks]
        
        if len(chunks) == 0:
            return None
        
        # Bestimme Collection (Multi-Collection oder Single)
        collection_name = get_collection_name(url, categorizer if USE_MULTI_COLLECTION else None)
        
        return {
            'doc_id': doc_id,
            'url': url,
            'title': title,
            'content_type': content_type,
            'chunks': chunks,
            'collection_name': collection_name
        }
        
    except Exception as e:
        print(f"\n⚠️  Fehler bei Dokument {doc_id}: {e}")
        return None

def run_production_scraper():
    """Führe den produktiven Scraper-Run aus."""
    
    start_time = time.time()
    
    print("=" * 80)
    print("PRODUKTIVER OFFLINE-SCRAPER")
    print("=" * 80)
    print(f"Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Modus: Inkrementelle Verarbeitung mit automatischem Fortsetzen")
    print("=" * 80)
    
    # Prüfe bestehenden Fortschritt
    completed_collections, phase1_checkpoint = check_existing_progress()
    
    # Initialisiere Module
    print("\n" + "=" * 80)
    print("SCHRITT 2: Module initialisieren")
    print("=" * 80)
    
    # Initialisiere Module basierend auf individuellen Feature-Flags
    print("📦 Initialisiere Pre-Retrieval Komponenten...")
    
    # Embedding-Modell zuerst laden (wird von SemanticChunker benötigt)
    print("\n🤖 Lade Embedding-Modell...")
    embedding_model = SentenceTransformer(SENTENCE_TRANSFORMER_MODEL)
    print(f"   ✅ {SENTENCE_TRANSFORMER_MODEL}")
    
    content_cleaner = None
    chunker = None
    deduplicator = None
    categorizer = None
    
    if USE_CONTENT_CLEANING:
        content_cleaner = ContentCleaner()
        print("   ✅ ContentCleaner")
    else:
        print("   ❌ ContentCleaner (deaktiviert)")
    
    if USE_SEMANTIC_CHUNKING:
        chunker = SemanticChunker(
            max_chunk_size=rag_config.semantic_chunking_max_size,
            min_chunk_size=rag_config.semantic_chunking_min_size,
            overlap=rag_config.semantic_chunking_overlap,
            similarity_threshold=rag_config.semantic_chunking_similarity_threshold,
            embedding_model=embedding_model  # Übergebe das bereits geladene Modell
        )
        print(f"   ✅ SemanticChunker (max={rag_config.semantic_chunking_max_size}, min={rag_config.semantic_chunking_min_size}, overlap={rag_config.semantic_chunking_overlap}, threshold={rag_config.semantic_chunking_similarity_threshold})")
    else:
        print(f"   ❌ SemanticChunker (deaktiviert) → Naive Chunking ({rag_config.semantic_chunking_max_size}/{rag_config.semantic_chunking_overlap})")
    
    if USE_DEDUPLICATION:
        deduplicator = ContentDeduplicator(
            similarity_threshold=rag_config.deduplication_similarity_threshold,
            shingle_size=rag_config.deduplication_shingle_size
        )
        print("   ✅ ContentDeduplicator")
    else:
        print("   ❌ ContentDeduplicator (deaktiviert)")
    
    if USE_MULTI_COLLECTION:
        categorizer = CollectionCategorizer()
        print(f"   ✅ CollectionCategorizer ({len(categorizer.get_collection_names())} Collections)")
    else:
        print("   ❌ CollectionCategorizer (deaktiviert) → Single Collection")
    
    # Verbinde zu ChromaDB
    print("\n💾 Initialisiere ChromaDB...")
    client = chromadb.PersistentClient(path=str(VECTOR_DB))
    
    # Erstelle/Lade Collections
    collections_dict = {}
    
    # Single Collection (wenn Multi-Collection deaktiviert)
    if not USE_MULTI_COLLECTION:
        collection_name = 'wiso_documents'
        if collection_name in completed_collections:
            collections_dict[collection_name] = client.get_collection(name=collection_name)
            print(f"   ♻️  Collection '{collection_name}' geladen (bereits fertig)")
        else:
            try:
                collections_dict[collection_name] = client.create_collection(
                    name=collection_name,
                    metadata={"description": "WiSo Fakultät - Alle Dokumente (Single Collection)"}
                )
                print(f"   ✅ Collection '{collection_name}' erstellt")
            except:
                collections_dict[collection_name] = client.get_collection(name=collection_name)
                print(f"   ♻️  Collection '{collection_name}' geladen")
    
    # Multi-Collections
    else:
        collection_names = categorizer.get_collection_names()
        for collection_name in collection_names:
            if collection_name in completed_collections:
                # Collection existiert bereits - lade sie
                collections_dict[collection_name] = client.get_collection(name=collection_name)
                print(f"   ♻️  Collection '{collection_name}' geladen (bereits fertig)")
            else:
                # Neue Collection erstellen
                try:
                    collections_dict[collection_name] = client.create_collection(
                        name=collection_name,
                        metadata={"description": f"WiSo Fakultät - {collection_name}"}
                    )
                    print(f"   ✅ Collection '{collection_name}' erstellt")
                except:
                    # Falls Collection existiert aber leer ist
                    collections_dict[collection_name] = client.get_collection(name=collection_name)
                    print(f"   ♻️  Collection '{collection_name}' geladen")
    
    # Verbinde zur Content Database
    conn = sqlite3.connect(CONTENT_DB)
    
    # Initialisiere Stats und Collections
    # Multi-Collection nur wenn aktiviert UND categorizer vorhanden
    if USE_MULTI_COLLECTION and categorizer is not None:
        collection_names = categorizer.get_collection_names()
    else:
        collection_names = ['wiso_documents']
    
    stats = {
        'total': 0,
        'html': 0,
        'pdf': 0,
        'chunks': 0,
        'skipped': 0,
        'collections': {name: 0 for name in collection_names},
        'errors': 0,
        'chunk_lengths': []  # Sammle alle Chunk-Längen für Statistiken
    }
    
    # Sammle verarbeitete Dokumente nach Collection
    docs_by_collection = {name: [] for name in collection_names}
    
    # Phase 1: Dokumente verarbeiten oder aus Checkpoint laden
    if phase1_checkpoint is not None:
        print("\n" + "=" * 80)
        print("SCHRITT 3: Phase 1 aus Checkpoint wiederherstellen")
        print("=" * 80)
        print("⚡ Überspringe Phase 1 - nutze gespeicherte Daten")
        
        docs_by_collection = phase1_checkpoint
        total_new_docs = sum(len(docs) for docs in docs_by_collection.values())
        stats['chunks'] = sum(sum(len(doc['chunks']) for doc in docs) for docs in docs_by_collection.values())
        # Sammle Chunk-Längen aus Checkpoint
        for docs in docs_by_collection.values():
            for doc in docs:
                stats['chunk_lengths'].extend([len(chunk) for chunk in doc['chunks']])
        
        print(f"\n✅ Phase 1 übersprungen: {total_new_docs:,} Dokumente aus Checkpoint")
        print(f"   📊 {stats['chunks']:,} Chunks bereit für Embedding")
        
        conn.close()
    else:
        # Hole alle Dokumente
        print("\n" + "=" * 80)
        print("SCHRITT 3: Dokumente laden")
        print("=" * 80)
        
        cursor = conn.execute("SELECT COUNT(*) FROM documents")
        total_docs = cursor.fetchone()[0]
        print(f"📊 Gefunden: {total_docs:,} Dokumente")
        
        # Zähle nach Content-Type
        cursor = conn.execute("SELECT content_type, COUNT(*) FROM documents GROUP BY content_type")
        for content_type, count in cursor.fetchall():
            print(f"   • {content_type.upper()}: {count:,}")
        
        # Verarbeite alle Dokumente
        print("\n" + "=" * 80)
        print("SCHRITT 4: Dokumente verarbeiten")
        print("=" * 80)
        if USE_DEDUPLICATION:
            print("🔄 Phase 1a: Decompress → Clean → Text extrahieren")
            print("🔄 Phase 1b: Exact-Deduplication auf Dokument-Ebene")
            print("🔄 Phase 1c: Chunking (nur unique Dokumente)")
        else:
            print("🔄 Phase 1: Decompress → Clean → Chunk")
        print()
        
        cursor = conn.execute("""
            SELECT id, url, title, content, content_type
            FROM documents
            ORDER BY id
        """)
        
        if USE_DEDUPLICATION:
            # ================================================================
            # PHASE 1a: Text extrahieren (für alle Dokumente)
            # ================================================================
            print("📝 Phase 1a: Text extrahieren...")
            all_docs_text = []
            
            with tqdm(total=total_docs, desc="📝 Phase 1a: Text extrahieren", unit="doc") as pbar:
                for row in cursor:
                    doc_id, url, title, content, content_type = row
                    
                    short_title = title[:40] + "..." if len(title) > 40 else title
                    pbar.set_description(f"📝 [{content_type.upper()}] {short_title}")
                    
                    result = extract_document_text(
                        doc_id, url, title, content, content_type, content_cleaner
                    )
                    
                    stats['total'] += 1
                    stats[content_type] += 1
                    
                    if result is not None:
                        all_docs_text.append(result)
                    else:
                        stats['skipped'] += 1
                    
                    pbar.set_postfix({
                        'Extracted': len(all_docs_text),
                        'Skip': stats['skipped']
                    })
                    pbar.update(1)
            
            print(f"\n✅ Phase 1a abgeschlossen: {len(all_docs_text):,} Dokumente extrahiert")
            
            # ================================================================
            # PHASE 1b: Exact-Deduplication
            # ================================================================
            print("\n" + "-" * 80)
            print("🔍 Phase 1b: Exact-Deduplication...")
            print("-" * 80)
            
            unique_docs, removed_docs, dedup_stats = deduplicate_documents_exact(
                all_docs_text, text_key='text', id_key='doc_id'
            )
            
            print(f"   📊 Input:    {dedup_stats['total']:,} Dokumente")
            print(f"   📊 Unique:   {dedup_stats['unique']:,} Dokumente")
            print(f"   📊 Entfernt: {dedup_stats['duplicates_removed']:,} Duplikate")
            print(f"   📊 Gruppen:  {dedup_stats['duplicate_groups']:,} Duplikat-Gruppen")
            print(f"   📊 Reduktion: {dedup_stats['reduction_percent']:.1f}%")
            
            # Speichere Dedup-Stats für späteren Report
            stats['dedup'] = dedup_stats
            
            # Excel-Übersicht für Deduplication erstellen
            create_dedup_excel(unique_docs, removed_docs, dedup_stats)
            
            # ================================================================
            # PHASE 1c: Chunking (nur unique Dokumente)
            # ================================================================
            print("\n" + "-" * 80)
            print(f"✂️  Phase 1c: Chunking ({len(unique_docs):,} unique Dokumente)...")
            print("-" * 80)
            
            with tqdm(total=len(unique_docs), desc="✂️  Phase 1c: Chunking", unit="doc") as pbar:
                for doc_dict in unique_docs:
                    short_title = doc_dict['title'][:40] + "..." if len(doc_dict['title']) > 40 else doc_dict['title']
                    pbar.set_description(f"✂️  [{doc_dict['content_type'].upper()}] {short_title}")
                    
                    result = chunk_document(doc_dict, chunker, categorizer)
                    
                    if result is not None:
                        collection_name = result['collection_name']
                        
                        if collection_name not in completed_collections:
                            stats['chunks'] += len(result['chunks'])
                            stats['chunk_lengths'].extend([len(chunk) for chunk in result['chunks']])
                            docs_by_collection[collection_name].append(result)
                    
                    pbar.set_postfix({
                        'Docs': sum(len(docs) for docs in docs_by_collection.values()),
                        'Chunks': f"{stats['chunks']:,}"
                    })
                    pbar.update(1)
            
            print(f"\n✅ Phase 1c abgeschlossen: {stats['chunks']:,} Chunks erstellt")
            
        else:
            # ================================================================
            # NAIVE MODE: Alle Schritte in einem Durchgang (ohne Dedup)
            # ================================================================
            with tqdm(total=total_docs, desc="📝 Phase 1: Dokumente verarbeiten", unit="doc") as pbar:
                for row in cursor:
                    doc_id, url, title, content, content_type = row
                    
                    short_title = title[:40] + "..." if len(title) > 40 else title
                    pbar.set_description(f"📝 [{content_type.upper()}] {short_title}")
                    
                    result = process_document(
                        doc_id, url, title, content, content_type,
                        content_cleaner, chunker, deduplicator, categorizer
                    )
                    
                    stats['total'] += 1
                    stats[content_type] += 1
                    
                    if result is None:
                        stats['skipped'] += 1
                    else:
                        collection_name = result['collection_name']
                        
                        if collection_name in completed_collections:
                            stats['skipped'] += 1
                        else:
                            stats['chunks'] += len(result['chunks'])
                            stats['chunk_lengths'].extend([len(chunk) for chunk in result['chunks']])
                            docs_by_collection[collection_name].append(result)
                    
                    pbar.set_postfix({
                        'Docs': sum(len(docs) for docs in docs_by_collection.values()),
                        'Chunks': f"{stats['chunks']:,}",
                        'Skip': stats['skipped']
                    })
                    pbar.update(1)
    
        conn.close()
        
        total_new_docs = sum(len(docs) for docs in docs_by_collection.values())
        print(f"\n✅ Phase 1 abgeschlossen: {total_new_docs:,} neue Dokumente, {stats['chunks']:,} Chunks")
        
        if completed_collections:
            print(f"   ♻️  {len(completed_collections)} Collections übersprungen (bereits fertig)")
        
        # Speichere Phase 1 Checkpoint
        checkpoint_mgr.save_phase1_checkpoint(docs_by_collection)
    
    # Phase 2: Batch-Embedding und Speicherung
    print("\n" + "=" * 80)
    print("SCHRITT 5: Embeddings erstellen (BATCH)")
    print("=" * 80)
    print("🚀 Phase 2: Batch-Embedding → Store (inkrementell nach jeder Collection!)")
    print()
    
    # Batch-Größe für Embeddings
    BATCH_SIZE = 128
    
    for collection_name, docs in docs_by_collection.items():
        # Überspringe fertige Collections
        if collection_name in completed_collections:
            continue
        
        if not docs:
            print(f"\n⏭️  Collection '{collection_name}': Keine neuen Dokumente")
            continue
        
        print(f"\n📦 Collection '{collection_name}': {len(docs)} Dokumente")
        collection = collections_dict[collection_name]
        
        # Sammle alle Chunks für Batch-Encoding
        all_chunks = []
        chunk_metadata = []
        
        print(f"   📋 Sammle Chunks aus {len(docs)} Dokumenten...")
        for doc in tqdm(docs, desc=f"   📄 Chunks sammeln", leave=False):
            for i, chunk in enumerate(doc['chunks']):
                all_chunks.append(chunk)
                chunk_metadata.append({
                    'doc_id': doc['doc_id'],
                    'url': doc['url'],
                    'title': doc['title'],
                    'content_type': doc['content_type'],
                    'chunk_index': i,
                    'total_chunks': len(doc['chunks']),
                    'chunk_id': f"{doc['content_type']}_{doc['doc_id']}_chunk_{i}"
                })
        
        print(f"   ✅ {len(all_chunks):,} Chunks gesammelt")
        
        # Batch-Embedding mit Progress Bar
        all_embeddings = []
        with tqdm(total=len(all_chunks), desc=f"   🤖 Embeddings", unit="chunk") as pbar:
            for i in range(0, len(all_chunks), BATCH_SIZE):
                batch = all_chunks[i:i + BATCH_SIZE]
                embeddings = embedding_model.encode(batch, show_progress_bar=False)
                all_embeddings.extend(embeddings.tolist())
                pbar.update(len(batch))
        
        # Batch-Speicherung in ChromaDB (mit Größenlimit)
        # ChromaDB erlaubt max ~5000 Chunks pro add() - wir nutzen 5000 als Limit
        CHROMADB_BATCH_SIZE = 5000
        
        print(f"   💾 Speichere in ChromaDB...")
        
        if len(all_chunks) <= CHROMADB_BATCH_SIZE:
            # Kleine Collection: Alles auf einmal
            collection.add(
                documents=all_chunks,
                embeddings=all_embeddings,
                ids=[meta['chunk_id'] for meta in chunk_metadata],
                metadatas=[{k: v for k, v in meta.items() if k != 'chunk_id'} for meta in chunk_metadata]
            )
        else:
            # Große Collection: In Batches speichern
            num_batches = (len(all_chunks) + CHROMADB_BATCH_SIZE - 1) // CHROMADB_BATCH_SIZE
            with tqdm(total=len(all_chunks), desc=f"   💾 Speichern", unit="chunk") as save_pbar:
                for i in range(0, len(all_chunks), CHROMADB_BATCH_SIZE):
                    end_idx = min(i + CHROMADB_BATCH_SIZE, len(all_chunks))
                    batch_chunks = all_chunks[i:end_idx]
                    batch_embeddings = all_embeddings[i:end_idx]
                    batch_metadata = chunk_metadata[i:end_idx]
                    
                    collection.add(
                        documents=batch_chunks,
                        embeddings=batch_embeddings,
                        ids=[meta['chunk_id'] for meta in batch_metadata],
                        metadatas=[{k: v for k, v in meta.items() if k != 'chunk_id'} for meta in batch_metadata]
                    )
                    save_pbar.update(len(batch_chunks))
        
        stats['collections'][collection_name] = len(all_chunks)
        actual_count = collection.count()
        print(f"   ✅ {len(all_chunks):,} Chunks gespeichert")
        print(f"   🎉 Collection '{collection_name}' abgeschlossen! (Total: {actual_count:,} Chunks)")
    
    # Lösche Phase 1 Checkpoint (alle Collections erfolgreich)
    checkpoint_mgr.delete_phase1_checkpoint()
    
    # Deduplication-Statistiken (nur für Advanced RAG)
    dedup_stats = deduplicator.get_statistics() if deduplicator else None
    
    # Finale Statistiken
    elapsed_time = time.time() - start_time
    minutes = int(elapsed_time // 60)
    seconds = int(elapsed_time % 60)
    
    print("\n" + "=" * 80)
    print("✅ PRODUKTIVER RUN ABGESCHLOSSEN")
    print("=" * 80)
    
    print(f"\n⏱️  Laufzeit: {minutes} Minuten {seconds} Sekunden")
    print(f"📊 Verarbeitete Dokumente: {stats['total']:,}")
    print(f"   • HTML: {stats['html']:,}")
    print(f"   • PDF: {stats['pdf']:,}")
    print(f"   • Übersprungen: {stats['skipped']:,}")
    
    print(f"\n📦 Erstellte Chunks: {stats['chunks']:,}")
    print(f"   • Durchschnitt: {stats['chunks']/stats['total']:.1f} Chunks/Dokument")
    
    print(f"\n🗂️  Collections:")
    for collection_name, chunk_count in stats['collections'].items():
        if chunk_count > 0:
            collection = collections_dict[collection_name]
            actual_count = collection.count()
            print(f"   • {collection_name}: {actual_count:,} Chunks")
    
    if dedup_stats:
        print(f"\n🔍 Deduplication:")
        print(f"   • Unique Chunks: {dedup_stats['total_seen']:,}")
        print(f"   • Similarity Threshold: {dedup_stats['similarity_threshold']}")
        print(f"   • Duplikate entfernt: {stats['chunks'] - dedup_stats['total_seen']:,}")
    else:
        print(f"\n🔍 Deduplication:")
        print(f"   • Naive Setup: Keine Deduplizierung")
    
    print(f"\n💾 Vektordatenbank:")
    print(f"   • Pfad: {VECTOR_DB}")
    print(f"   • Collections: {len([c for c, count in stats['collections'].items() if count > 0])}")
    print(f"   • Embedding-Modell: {SENTENCE_TRANSFORMER_MODEL}")
    
    # Verifikation: Zeige Beispiele aus beiden Content-Types
    print("\n" + "=" * 80)
    print("📋 VERIFIKATION: Beispiel-Chunks aus beiden Content-Types")
    print("=" * 80)
    
    # Sammle Beispiele aus allen Collections
    html_examples = []
    pdf_examples = []
    
    for collection_name, collection in collections_dict.items():
        if stats['collections'].get(collection_name, 0) == 0:
            continue
        
        # Hole alle Chunks dieser Collection
        results = collection.get(include=['metadatas', 'documents'])
        
        for doc, metadata in zip(results['documents'], results['metadatas']):
            if metadata['content_type'] == 'html' and len(html_examples) < 2:
                html_examples.append({
                    'title': metadata['title'],
                    'url': metadata['url'],
                    'collection': collection_name,
                    'chunk_index': metadata['chunk_index'],
                    'total_chunks': metadata['total_chunks'],
                    'content': doc
                })
            elif metadata['content_type'] == 'pdf' and len(pdf_examples) < 2:
                pdf_examples.append({
                    'title': metadata['title'],
                    'url': metadata['url'],
                    'collection': collection_name,
                    'chunk_index': metadata['chunk_index'],
                    'total_chunks': metadata['total_chunks'],
                    'content': doc
                })
            
            if len(html_examples) >= 2 and len(pdf_examples) >= 2:
                break
        
        if len(html_examples) >= 2 and len(pdf_examples) >= 2:
            break
    
    # Zeige HTML-Beispiele
    print(f"\n📄 HTML-Dokumente ({len(html_examples)} Beispiele):")
    for i, example in enumerate(html_examples, 1):
        print(f"\n   Beispiel {i}:")
        print(f"   📍 Quelle: {example['title']}")
        print(f"   🔗 URL: {example['url'][:80]}...")
        print(f"   📦 Collection: {example['collection']}")
        print(f"   📊 Chunk {example['chunk_index']+1}/{example['total_chunks']}")
        print(f"   📝 Inhalt: {example['content'][:150]}...")
    
    # Zeige PDF-Beispiele
    print(f"\n📑 PDF-Dokumente ({len(pdf_examples)} Beispiele):")
    for i, example in enumerate(pdf_examples, 1):
        print(f"\n   Beispiel {i}:")
        print(f"   📍 Quelle: {example['title']}")
        print(f"   🔗 URL: {example['url'][:80]}...")
        print(f"   📦 Collection: {example['collection']}")
        print(f"   📊 Chunk {example['chunk_index']+1}/{example['total_chunks']}")
        print(f"   📝 Inhalt: {example['content'][:150]}...")
    
    # Berechne Gesamtzeit
    end_time = time.time()
    total_time_seconds = end_time - start_time
    total_time_minutes = total_time_seconds / 60
    
    print("\n" + "=" * 80)
    print("🎉 PIPELINE ERFOLGREICH ABGESCHLOSSEN")
    print("=" * 80)
    print(f"\n✅ Alle {stats['total']:,} Dokumente wurden verarbeitet")
    print(f"   und in ChromaDB gespeichert!")
    print(f"\n✓ {stats['html']:,} HTML-Dokumente verarbeitet")
    print(f"✓ {stats['pdf']:,} PDF-Dokumente verarbeitet")
    print(f"✓ {stats['chunks']:,} Chunks erstellt")
    print(f"✓ {stats['skipped']:,} Dokumente übersprungen")
    print(f"✓ {stats['errors']:,} Fehler")
    print(f"\n⏱️  Gesamtzeit: {total_time_minutes:.2f} Minuten ({total_time_seconds:.0f} Sekunden)")
    print(f"\nEnde: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # =========================================================================
    # EXCEL-EXPORT: Scraping-Statistiken
    # =========================================================================
    print("\n📊 Erstelle Scraping-Statistiken Excel...")
    
    # Bestimme RAG-Modus für Dateinamen
    if USE_ADVANCED:
        active_techniques = []
        if USE_SEMANTIC_CHUNKING:
            active_techniques.append("SemanticChunking")
        if USE_CONTENT_CLEANING:
            active_techniques.append("ContentCleaning")
        if USE_DEDUPLICATION:
            active_techniques.append("Deduplication")
        if USE_MULTI_COLLECTION:
            active_techniques.append("MultiCollection")
        
        if active_techniques:
            rag_mode = "_".join(active_techniques)
        else:
            rag_mode = "Advanced_NoTechniques"
    else:
        rag_mode = "Naive"
    
    # Berechne Chunk-Längen-Statistiken
    chunk_lengths = stats['chunk_lengths']
    if chunk_lengths:
        avg_chunk_len = round(sum(chunk_lengths) / len(chunk_lengths), 2)
        min_chunk_len = min(chunk_lengths)
        max_chunk_len = max(chunk_lengths)
    else:
        avg_chunk_len = 0
        min_chunk_len = 0
        max_chunk_len = 0
    
    # Erstelle DataFrame mit Statistiken
    scraping_stats = {
        'Metrik': [
            'RAG Modus',
            'Anzahl Collections',
            'Gesamtdokumente',
            'HTML-Dokumente',
            'PDF-Dokumente',
            'Chunks erstellt',
            'Durchschn. Chunks/Dokument',
            'Durchschn. Chunk-Länge (Zeichen)',
            'Min Chunk-Länge (Zeichen)',
            'Max Chunk-Länge (Zeichen)',
            'Dokumente übersprungen',
            'Fehler',
            'Gesamtzeit (Minuten)',
            'Gesamtzeit (Sekunden)',
            'Dokumente/Sekunde',
            'Startzeit',
            'Endzeit'
        ],
        'Wert': [
            rag_mode,
            len(collection_names),
            stats['total'],
            stats['html'],
            stats['pdf'],
            stats['chunks'],
            round(stats['chunks'] / max(stats['total'], 1), 2),
            avg_chunk_len,
            min_chunk_len,
            max_chunk_len,
            stats['skipped'],
            stats['errors'],
            round(total_time_minutes, 2),
            round(total_time_seconds, 0),
            round(stats['total'] / max(total_time_seconds, 1), 2),
            datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S'),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
    }
    
    df_stats = pd.DataFrame(scraping_stats)
    
    # Erstelle DataFrame mit Chunking-Hyperparametern
    if USE_SEMANTIC_CHUNKING:
        chunking_params = {
            'Parameter': [
                'Chunking-Methode',
                'Max Chunk Size',
                'Min Chunk Size', 
                'Overlap',
                'Similarity Threshold',
                'Embedding Model'
            ],
            'Wert': [
                'Semantic Chunking (Embedding-basiert)',
                rag_config.semantic_chunking_max_size,
                rag_config.semantic_chunking_min_size,
                rag_config.semantic_chunking_overlap,
                rag_config.semantic_chunking_similarity_threshold,
                rag_config.embedding_model_name
            ]
        }
    else:
        chunking_params = {
            'Parameter': [
                'Chunking-Methode',
                'Chunk Size',
                'Overlap'
            ],
            'Wert': [
                'Naive Chunking (Character-basiert)',
                rag_config.naive_chunking_max_size,
                rag_config.naive_chunking_overlap
            ]
        }
    
    df_chunking = pd.DataFrame(chunking_params)
    
    # Erstelle DataFrame mit Collection-Statistiken
    collection_stats = []
    for name in collection_names:
        count = stats['collections'].get(name, 0)
        collection_stats.append({
            'Collection': name,
            'Anzahl Chunks': count,
            'Anteil (%)': round(count / max(stats['chunks'], 1) * 100, 2)
        })
    
    df_collections = pd.DataFrame(collection_stats)
    
    # Speichere als Excel mit mehreren Sheets
    excel_path = Path("src/evaluation/data") / f"scraping_stats_{rag_mode}.xlsx"
    excel_path.parent.mkdir(parents=True, exist_ok=True)
    
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_stats.to_excel(writer, sheet_name='Übersicht', index=False)
        df_chunking.to_excel(writer, sheet_name='Chunking-Parameter', index=False)
        df_collections.to_excel(writer, sheet_name='Collections', index=False)
    
    print(f"   ✅ Statistiken gespeichert: {excel_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_production_scraper()
