"""
Backup-Script: Erstellt ein vollständiges Backup des aktuellen Projektstandes
"""
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime
import json

def create_backup():
    """Erstellt ein timestamped Backup aller wichtigen Daten."""
    
    # Timestamp für Backup-Ordner
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/backup_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("BACKUP ERSTELLEN")
    print("=" * 80)
    print(f"\nBackup-Verzeichnis: {backup_dir}")
    print()
    
    backup_info = {
        "timestamp": timestamp,
        "datetime": datetime.now().isoformat(),
        "files": []
    }
    
    # 1. Content Database (SQLite mit RAW-HTML + PDFs)
    print("1. Sichere Content Database...")
    content_db = Path("data/content_database.db")
    if content_db.exists():
        shutil.copy2(content_db, backup_dir / "content_database.db")
        size_mb = content_db.stat().st_size / (1024 * 1024)
        print(f"   ✅ content_database.db ({size_mb:.1f} MB)")
        
        # Statistiken
        with sqlite3.connect(content_db) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT content_type, COUNT(*) FROM documents GROUP BY content_type")
            by_type = dict(cursor.fetchall())
        
        backup_info["files"].append({
            "name": "content_database.db",
            "size_mb": round(size_mb, 2),
            "total_documents": total_docs,
            "by_type": by_type
        })
    else:
        print("   ⚠️ content_database.db nicht gefunden")
    
    # 2. HTML Cache Database
    print("\n2. Sichere HTML Cache Database...")
    html_cache_db = Path("data/html_cache/html_cache.db")
    if html_cache_db.exists():
        cache_backup_dir = backup_dir / "html_cache"
        cache_backup_dir.mkdir(exist_ok=True)
        shutil.copy2(html_cache_db, cache_backup_dir / "html_cache.db")
        size_mb = html_cache_db.stat().st_size / (1024 * 1024)
        print(f"   ✅ html_cache.db ({size_mb:.1f} MB)")
        
        backup_info["files"].append({
            "name": "html_cache/html_cache.db",
            "size_mb": round(size_mb, 2)
        })
    else:
        print("   ⚠️ html_cache.db nicht gefunden")
    
    # 3. PDF Cache Database
    print("\n3. Sichere PDF Cache Database...")
    pdf_cache_db = Path("data/pdf_cache/pdf_cache.db")
    if pdf_cache_db.exists():
        pdf_backup_dir = backup_dir / "pdf_cache"
        pdf_backup_dir.mkdir(exist_ok=True)
        shutil.copy2(pdf_cache_db, pdf_backup_dir / "pdf_cache.db")
        size_mb = pdf_cache_db.stat().st_size / (1024 * 1024)
        print(f"   ✅ pdf_cache.db ({size_mb:.1f} MB)")
        
        backup_info["files"].append({
            "name": "pdf_cache/pdf_cache.db",
            "size_mb": round(size_mb, 2)
        })
    else:
        print("   ⚠️ pdf_cache.db nicht gefunden")
    
    # 4. Vector Database (ChromaDB - produktiv)
    print("\n4. Sichere Vector Database (ChromaDB)...")
    vector_db_dir = Path("data/vector_db")
    if vector_db_dir.exists():
        vector_backup_dir = backup_dir / "vector_db"
        shutil.copytree(vector_db_dir, vector_backup_dir, dirs_exist_ok=True)
        
        # Berechne Gesamtgröße
        total_size = sum(f.stat().st_size for f in vector_backup_dir.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"   ✅ vector_db/ ({size_mb:.1f} MB)")
        
        # Sammle Collection-Statistiken
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(vector_db_dir))
            
            collections_info = {}
            for collection_name in ['wiso_studium', 'wiso_services', 'wiso_forschung', 'wiso_allgemein']:
                try:
                    collection = client.get_collection(collection_name)
                    count = collection.count()
                    
                    # Content-Type Statistiken
                    results = collection.get(include=['metadatas'])
                    html_count = sum(1 for meta in results['metadatas'] if meta.get('content_type') == 'html')
                    pdf_count = sum(1 for meta in results['metadatas'] if meta.get('content_type') == 'pdf')
                    
                    collections_info[collection_name] = {
                        'total_chunks': count,
                        'html_chunks': html_count,
                        'pdf_chunks': pdf_count
                    }
                    print(f"      • {collection_name}: {count:,} Chunks (HTML: {html_count:,}, PDF: {pdf_count:,})")
                except Exception as e:
                    print(f"      ⚠️ {collection_name}: Fehler beim Auslesen ({e})")
            
            backup_info["files"].append({
                "name": "vector_db/",
                "size_mb": round(size_mb, 2),
                "collections": collections_info,
                "total_chunks": sum(info['total_chunks'] for info in collections_info.values()),
                "embedding_model": "all-MiniLM-L6-v2",
                "embedding_dimensions": 384
            })
        except Exception as e:
            print(f"      ⚠️ Fehler beim Sammeln der Statistiken: {e}")
            backup_info["files"].append({
                "name": "vector_db/",
                "size_mb": round(size_mb, 2)
            })
    else:
        print("   ⚠️ Vector Database nicht gefunden")
    
    # 5. Checkpoints (falls vorhanden)
    print("\n5. Prüfe Checkpoints...")
    checkpoints_dir = Path("checkpoints")
    if checkpoints_dir.exists():
        checkpoints_backup_dir = backup_dir / "checkpoints"
        shutil.copytree(checkpoints_dir, checkpoints_backup_dir, dirs_exist_ok=True)
        
        total_size = sum(f.stat().st_size for f in checkpoints_backup_dir.rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        print(f"   ✅ checkpoints/ ({size_mb:.1f} MB)")
        
        backup_info["files"].append({
            "name": "checkpoints/",
            "size_mb": round(size_mb, 2)
        })
    else:
        print("   ℹ️ Keine Checkpoints vorhanden")
    
    # 6. Wichtige Config-Dateien
    print("\n6. Sichere Konfigurationsdateien...")
    config_files = [
        "config/settings.py",
        "requirements.txt",
        "README.md",
        "hyperparameter_documentation.md",
        "src/scraper/hyperparameters.py",
        "run_production_scraper.py"
    ]
    
    config_backup_dir = backup_dir / "config"
    config_backup_dir.mkdir(exist_ok=True)
    
    for config_file in config_files:
        src = Path(config_file)
        if src.exists():
            dest = config_backup_dir / src.name
            shutil.copy2(src, dest)
            print(f"   ✅ {src.name}")
            backup_info["files"].append({"name": config_file})
    
    # 7. Wichtige Source-Dateien
    print("\n7. Sichere wichtige Source-Dateien...")
    source_files = [
        "src/scraper/tools/import_to_content_db.py",
        "src/advanced_rag/pre_retrieval/cleaning.py",
        "src/advanced_rag/pre_retrieval/chunking.py",
        "src/advanced_rag/pre_retrieval/deduplication.py",
        "test_offline_scraper.py",
        "test_optimized_scraper.py",
        "verify_content_types.py"
    ]
    
    source_backup_dir = backup_dir / "source_files"
    source_backup_dir.mkdir(exist_ok=True)
    
    for source_file in source_files:
        src = Path(source_file)
        if src.exists():
            dest = source_backup_dir / src.name
            shutil.copy2(src, dest)
            print(f"   ✅ {src.name}")
            backup_info["files"].append({"name": source_file})
    
    # Speichere Backup-Info als JSON
    info_file = backup_dir / "backup_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(backup_info, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Backup-Info gespeichert: backup_info.json")
    
    # Zusammenfassung
    total_size = sum(f.stat().st_size for f in backup_dir.rglob('*') if f.is_file())
    total_size_mb = total_size / (1024 * 1024)
    
    print("\n" + "=" * 80)
    print("BACKUP ABGESCHLOSSEN")
    print("=" * 80)
    print(f"\n📁 Backup-Verzeichnis: {backup_dir}")
    print(f"📊 Gesamtgröße: {total_size_mb:.1f} MB")
    print(f"📄 Anzahl Dateien: {len(list(backup_dir.rglob('*')))}")
    
    print("\n📋 Gesicherte Komponenten:")
    for file_info in backup_info["files"]:
        name = file_info.get("name", "unknown")
        if "size_mb" in file_info:
            size = file_info["size_mb"]
            if "total_documents" in file_info:
                docs = file_info["total_documents"]
                by_type = file_info.get("by_type", {})
                print(f"   • {name}: {size} MB ({docs} Dokumente: {by_type})")
            elif "total_chunks" in file_info:
                chunks = file_info["total_chunks"]
                model = file_info.get("embedding_model", "N/A")
                print(f"   • {name}: {size} MB ({chunks:,} Chunks, Model: {model})")
                if "collections" in file_info:
                    for coll_name, coll_info in file_info["collections"].items():
                        print(f"      → {coll_name}: {coll_info['total_chunks']:,} Chunks")
            else:
                print(f"   • {name}: {size} MB")
        else:
            print(f"   • {name}")
    
    print(f"\n✅ Backup erfolgreich erstellt!")
    print(f"   Zum Wiederherstellen: Kopiere Dateien aus {backup_dir} zurück")
    print("=" * 80)
    
    return backup_dir

if __name__ == "__main__":
    create_backup()
