"""
Vector Database Backup Script
==============================
Erstellt ein Backup der ChromaDB Vektordatenbank vor dem Neu-Befüllen.
"""
import shutil
from pathlib import Path
from datetime import datetime
import json
import sqlite3

def backup_vector_database():
    """Erstellt ein timestamped Backup der Vektordatenbank."""
    
    # Timestamp für Backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backups/vector_db_backup_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 80)
    print("VECTOR DATABASE BACKUP")
    print("=" * 80)
    print(f"\nBackup-Verzeichnis: {backup_dir}")
    print()
    
    backup_info = {
        "timestamp": timestamp,
        "datetime": datetime.now().isoformat(),
        "description": "Backup der ChromaDB Vektordatenbank vor Neu-Befüllung",
        "files": []
    }
    
    # Pfad zur Vektordatenbank (beide mögliche Orte prüfen)
    vector_db_paths = [
        Path("data/vector_db"),
        Path("src/scraper/vector_db")
    ]
    
    vector_db_path = None
    for path in vector_db_paths:
        if path.exists():
            vector_db_path = path
            print(f"✅ Vektordatenbank gefunden: {path}")
            break
    
    if vector_db_path is None:
        print("❌ Keine Vektordatenbank gefunden")
        print("   Geprüfte Pfade:")
        for path in vector_db_paths:
            print(f"      - {path}")
        print("   Es gibt nichts zu sichern.")
        print("=" * 80)
        return None
    
    # Prüfe ob Datenbank leer ist
    chroma_db = vector_db_path / "chroma.sqlite3"
    if chroma_db.exists():
        # Prüfe Anzahl der Collections und Embeddings
        try:
            with sqlite3.connect(chroma_db) as conn:
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                # Prüfe embeddings Tabelle
                if 'embeddings' in tables:
                    cursor = conn.execute("SELECT COUNT(*) FROM embeddings")
                    num_embeddings = cursor.fetchone()[0]
                    print(f"📊 Gefunden: {num_embeddings:,} Embeddings in der Datenbank")
                    backup_info["num_embeddings"] = num_embeddings
                    
                    if num_embeddings == 0:
                        print("   ⚠️ Datenbank ist leer - trotzdem sichern? (Struktur wird gesichert)")
                else:
                    print("   ℹ️ Keine embeddings Tabelle gefunden")
        except Exception as e:
            print(f"   ⚠️ Konnte Statistiken nicht lesen: {e}")
    
    print(f"\n1. Kopiere Vektordatenbank...")
    
    # Kopiere gesamtes Verzeichnis
    try:
        shutil.copytree(vector_db_path, backup_dir / "vector_db")
        
        # Berechne Größe
        total_size = sum(f.stat().st_size for f in (backup_dir / "vector_db").rglob('*') if f.is_file())
        size_mb = total_size / (1024 * 1024)
        
        # Liste alle Dateien auf
        files_list = list((backup_dir / "vector_db").rglob('*'))
        num_files = len([f for f in files_list if f.is_file()])
        
        print(f"   ✅ {num_files} Dateien kopiert ({size_mb:.2f} MB)")
        
        # Zeige wichtigste Dateien
        print(f"\n   Gesicherte Dateien:")
        for file_path in sorted((backup_dir / "vector_db").rglob('*')):
            if file_path.is_file():
                rel_path = file_path.relative_to(backup_dir / "vector_db")
                file_size = file_path.stat().st_size / 1024  # KB
                if file_size > 10:  # Zeige nur Dateien > 10 KB
                    print(f"      • {rel_path} ({file_size:.1f} KB)")
        
        backup_info["files"].append({
            "path": "vector_db/",
            "num_files": num_files,
            "size_mb": round(size_mb, 2)
        })
        
    except Exception as e:
        print(f"   ❌ Fehler beim Kopieren: {e}")
        return None
    
    # Speichere Backup-Info
    info_file = backup_dir / "backup_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump(backup_info, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Backup-Info gespeichert: backup_info.json")
    
    # Zusammenfassung
    print("\n" + "=" * 80)
    print("BACKUP ABGESCHLOSSEN")
    print("=" * 80)
    print(f"\n📁 Backup-Verzeichnis: {backup_dir}")
    print(f"📊 Gesamtgröße: {size_mb:.2f} MB")
    print(f"📄 Anzahl Dateien: {num_files}")
    
    if "num_embeddings" in backup_info:
        print(f"🔢 Embeddings: {backup_info['num_embeddings']:,}")
    
    print(f"\n✅ Vektordatenbank erfolgreich gesichert!")
    print(f"   Zum Wiederherstellen:")
    print(f"   1. Lösche src/scraper/vector_db/")
    print(f"   2. Kopiere {backup_dir / 'vector_db'} nach src/scraper/")
    print("=" * 80)
    
    return backup_dir

if __name__ == "__main__":
    backup_vector_database()
