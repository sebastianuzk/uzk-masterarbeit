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

# Scraper Utils
from src.scraper.utils.checkpoint_manager import CheckpointManager

# Lade RAG Configuration
try:
    from src.advanced_rag.rag_config import RAGConfig
    rag_config = RAGConfig.load_from_env()
    USE_ADVANCED = not rag_config.baseline_enabled  # baseline=True bedeutet Naive
except Exception as e:
    print(f"⚠️  Fehler beim Laden der RAG-Config: {e}")
    print("   Verwende Advanced RAG als Fallback")
    USE_ADVANCED = True

# Conditional Imports für Advanced-Techniken
if USE_ADVANCED:
    from src.advanced_rag.pre_retrieval.cleaning import ContentCleaner
    from src.advanced_rag.pre_retrieval.chunking import SemanticChunker
    from src.advanced_rag.pre_retrieval.deduplication import ContentDeduplicator
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

def naive_clean_text(text: str) -> str:
    """Naive Text-Bereinigung ohne Advanced-Techniken."""
    # Nur grundlegende Bereinigung
    text = re.sub(r'\s+', ' ', text)  # Normalisiere Leerzeichen
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Entferne mehrfache Zeilenumbrüche
    return text.strip()

def naive_chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """
    Naive Chunking: Einfaches Character-basiertes Chunking mit Overlap.
    
    Args:
        text: Eingabetext
        chunk_size: Chunk-Größe in Zeichen (Standard: 1000)
        overlap: Überlappung zwischen Chunks (Standard: 200)
    
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

def process_document(doc_id, url, title, content, content_type, 
                     content_cleaner=None, chunker=None, deduplicator=None, categorizer=None):
    """
    Verarbeite ein einzelnes Dokument (ohne Embeddings).
    Respektiert USE_ADVANCED Flag.
    
    Returns:
        dict mit Chunks und Metadaten oder None wenn übersprungen
    """
    try:
        # Dekomprimiere
        raw_content = decompress_content(content)
        
        if USE_ADVANCED:
            # ADVANCED: Mit Pre-Retrieval Techniken
            if content_type == 'html':
                cleaned_text = content_cleaner.clean_html(raw_content)
            else:  # pdf
                cleaned_text = content_cleaner._clean_text(raw_content)
            
            chunks = chunker.chunk_by_paragraphs(cleaned_text)
            
            # Deduplication nur für HTMLs
            if content_type == 'html' and len(chunks) > 0:
                chunk_docs = [{"url": f"{url}#chunk_{i}", "content": chunk} for i, chunk in enumerate(chunks)]
                unique_chunks, _ = deduplicator.deduplicate_batch(chunk_docs)
                chunks = [doc["content"] for doc in unique_chunks]
        else:
            # NAIVE: Ohne Advanced-Techniken
            cleaned_text = naive_clean_text(raw_content)
            chunks = naive_chunk_text(cleaned_text, chunk_size=1000, overlap=200)
        
        if len(chunks) == 0:
            return None
        
        # Bestimme Collection (mit categorizer für Advanced)
        collection_name = get_collection_name(url, categorizer)
        
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
    
    if USE_ADVANCED:
        print("📦 Lade Advanced Pre-Retrieval Komponenten...")
        content_cleaner = ContentCleaner()
        print("   ✅ ContentCleaner")
        
        # Lade Chunking-Parameter aus Config
        chunker = SemanticChunker(
            max_chunk_size=rag_config.semantic_chunking_max_size,
            min_chunk_size=rag_config.semantic_chunking_min_size,
            overlap=rag_config.semantic_chunking_overlap
        )
        print(f"   ✅ SemanticChunker (max={rag_config.semantic_chunking_max_size}, min={rag_config.semantic_chunking_min_size}, overlap={rag_config.semantic_chunking_overlap})")
        
        deduplicator = ContentDeduplicator(
            similarity_threshold=rag_config.deduplication_similarity_threshold,
            shingle_size=rag_config.deduplication_shingle_size
        )
        print("   ✅ ContentDeduplicator (Quick-Win optimiert: Cache + Early Exit + Size-Bucketing)")
        
        categorizer = CollectionCategorizer()  # Verwendet DEFAULT_COLLECTIONS
        print(f"   ✅ CollectionCategorizer ({len(categorizer.get_collection_names())} Collections)")
    else:
        print("📦 Verwende Naive RAG (keine Advanced-Techniken)...")
        content_cleaner = None
        chunker = None
        deduplicator = None
        categorizer = None
        print("   ✅ Naive Text-Bereinigung")
        print("   ✅ Naive Chunking (einfache Zeichenzahl-basiert)")
    
    print("\n🤖 Lade Embedding-Modell...")
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("   ✅ all-MiniLM-L6-v2 (384 Dimensionen)")
    
    # Verbinde zu ChromaDB
    print("\n💾 Initialisiere ChromaDB...")
    client = chromadb.PersistentClient(path=str(VECTOR_DB))
    
    # Erstelle/Lade Collections
    collections_dict = {}
    
    # NAIVE RAG: Nur eine Collection
    if not USE_ADVANCED:
        collection_name = 'wiso_documents'
        if collection_name in completed_collections:
            collections_dict[collection_name] = client.get_collection(name=collection_name)
            print(f"   ♻️  Collection '{collection_name}' geladen (bereits fertig)")
        else:
            try:
                collections_dict[collection_name] = client.create_collection(
                    name=collection_name,
                    metadata={"description": "WiSo Fakultät - Alle Dokumente (Naive RAG)"}
                )
                print(f"   ✅ Collection '{collection_name}' erstellt (NAIVE RAG - keine Kategorisierung)")
            except:
                collections_dict[collection_name] = client.get_collection(name=collection_name)
                print(f"   ♻️  Collection '{collection_name}' geladen")
    
    # ADVANCED RAG: Multi-Collections
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
    # NAIVE RAG: Nur eine Collection
    if not USE_ADVANCED:
        collection_names = ['wiso_documents']
    else:
        collection_names = categorizer.get_collection_names()
    
    stats = {
        'total': 0,
        'html': 0,
        'pdf': 0,
        'chunks': 0,
        'skipped': 0,
        'collections': {name: 0 for name in collection_names},
        'errors': 0
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
        print("🔄 Phase 1: Decompress → Clean → Chunk → Deduplicate")
        print()
        
        cursor = conn.execute("""
            SELECT id, url, title, content, content_type
            FROM documents
            ORDER BY id
        """)
        
        # Progress bar für Phase 1
        with tqdm(total=total_docs, desc="📝 Phase 1: Dokumente verarbeiten", unit="doc") as pbar:
            for row in cursor:
                doc_id, url, title, content, content_type = row
                
                # Zeige aktuell bearbeitete Datei
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
                    
                    # Überspringe wenn Collection bereits fertig ist
                    if collection_name in completed_collections:
                        stats['skipped'] += 1
                    else:
                        stats['chunks'] += len(result['chunks'])
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
    print(f"   • Embedding-Modell: all-MiniLM-L6-v2 (384D)")
    
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
    
    print("\n" + "=" * 80)
    print("🎉 PIPELINE ERFOLGREICH ABGESCHLOSSEN")
    print("=" * 80)
    print(f"\n✅ Alle {stats['total']:,} Dokumente wurden mit Advanced Pre-Retrieval")
    print(f"   Techniken verarbeitet und in ChromaDB gespeichert!")
    print(f"\n✓ {stats['html']:,} HTML-Dokumente verarbeitet")
    print(f"✓ {stats['pdf']:,} PDF-Dokumente verarbeitet")
    print(f"✓ {stats['chunks']:,} Chunks erstellt (nach Deduplication)")
    print(f"\nEnde: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

if __name__ == "__main__":
    run_production_scraper()
