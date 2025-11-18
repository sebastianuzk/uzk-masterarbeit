#!/usr/bin/env python3
"""Cache-Ordnerstruktur analysieren"""

from pathlib import Path
import os
import sqlite3

def analyze_cache_structure():
    print('📁 CACHE-ORDNERSTRUKTUR ANALYSE')
    print('=' * 60)
    
    base_path = Path('data')
    
    print('🗂️ GESAMTE STRUKTUR:')
    print('-' * 30)
    
    def show_tree(path, prefix="", max_depth=3, current_depth=0):
        if current_depth >= max_depth:
            return
        
        if not path.exists():
            return
            
        items = sorted(path.iterdir())
        files = [item for item in items if item.is_file()]
        dirs = [item for item in items if item.is_dir()]
        
        # Zeige Dateien
        for i, file in enumerate(files):
            is_last_file = (i == len(files) - 1) and len(dirs) == 0
            connector = "└── " if is_last_file else "├── "
            
            size_mb = file.stat().st_size / (1024*1024)
            print(f"{prefix}{connector}{file.name} ({size_mb:.2f} MB)")
        
        # Zeige Verzeichnisse (begrenzt)
        dirs_to_show = dirs[:5] if current_depth == 0 else dirs[:3]
        remaining = len(dirs) - len(dirs_to_show)
        
        for i, dir in enumerate(dirs_to_show):
            is_last = (i == len(dirs_to_show) - 1) and remaining == 0
            connector = "└── " if is_last else "├── "
            
            # Zähle Inhalte
            try:
                content_count = len(list(dir.iterdir()))
                print(f"{prefix}{connector}{dir.name}/ ({content_count} items)")
                
                # Rekursion für wichtige Verzeichnisse
                if dir.name in ['html_cache', 'vector_db'] and current_depth < 2:
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    show_tree(dir, new_prefix, max_depth, current_depth + 1)
                    
            except PermissionError:
                print(f"{prefix}{connector}{dir.name}/ (access denied)")
        
        if remaining > 0:
            connector = "└── " if len(files) == 0 else "├── "
            print(f"{prefix}{connector}... and {remaining} more directories")
    
    show_tree(base_path)
    
    print('\n📊 CACHE-DATEIEN DETAILS:')
    print('-' * 30)
    
    # HTML Cache
    html_cache_db = base_path / 'html_cache' / 'html_cache.db'
    if html_cache_db.exists():
        size_mb = html_cache_db.stat().st_size / (1024*1024)
        print(f'🗃️  HTML-Cache Datenbank: {html_cache_db}')
        print(f'   📏 Größe: {size_mb:.2f} MB')
        
        # Zeige Inhalt
        try:
            conn = sqlite3.connect(html_cache_db)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM html_cache')
            count = cursor.fetchone()[0]
            print(f'   📊 Einträge: {count:,}')
            conn.close()
        except Exception as e:
            print(f'   ❌ Fehler beim Lesen: {e}')
        
        # WAL und SHM Dateien
        wal_file = html_cache_db.with_suffix('.db-wal')
        shm_file = html_cache_db.with_suffix('.db-shm')
        
        if wal_file.exists():
            wal_size = wal_file.stat().st_size / 1024
            print(f'   📝 WAL-Datei: {wal_size:.1f} KB')
            
        if shm_file.exists():
            shm_size = shm_file.stat().st_size / 1024  
            print(f'   💾 SHM-Datei: {shm_size:.1f} KB')
    
    # HTML Content Files
    html_dir = base_path / 'html_cache' / 'html'
    if html_dir.exists():
        print(f'\n🗂️  HTML-Content Verzeichnis: {html_dir}')
        
        # Zähle HTML-Dateien
        html_files = list(html_dir.rglob('*.html.gz'))
        total_size = sum(f.stat().st_size for f in html_files) / (1024*1024)
        
        print(f'   📄 HTML-Dateien: {len(html_files):,}')
        print(f'   📏 Gesamtgröße: {total_size:.2f} MB')
        print(f'   📁 Ordner-Struktur: Hex-basierte Verteilung (256 Ordner)')
    
    # URL Cache
    url_cache_db = base_path / 'url_cache.db'
    if url_cache_db.exists():
        size_mb = url_cache_db.stat().st_size / (1024*1024)
        print(f'\n🔗 URL-Cache: {url_cache_db}')
        print(f'   📏 Größe: {size_mb:.2f} MB')
    
    # Vector DB
    vector_db_dir = base_path / 'vector_db'
    if vector_db_dir.exists():
        print(f'\n🧠 Vector Database: {vector_db_dir}')
        collections = list(vector_db_dir.iterdir())
        print(f'   📊 Collections: {len(collections)}')
        
        total_vector_size = 0
        for collection in collections:
            if collection.is_dir():
                collection_size = sum(f.stat().st_size for f in collection.rglob('*') if f.is_file())
                total_vector_size += collection_size
                print(f'   📁 {collection.name}: {collection_size/(1024*1024):.1f} MB')
        
        print(f'   📏 Gesamtgröße: {total_vector_size/(1024*1024):.1f} MB')
    
    print('\n💡 ZUSAMMENFASSUNG:')
    print('-' * 30)
    print('• HTML-Cache: SQLite DB + komprimierte HTML-Dateien')
    print('• URL-Cache: SQLite DB für URL-Metadaten')  
    print('• Vector-DB: ChromaDB Collections für RAG')
    print('• Hierarchische Struktur für Performance')

if __name__ == '__main__':
    analyze_cache_structure()