#!/usr/bin/env python3
"""
Comprehensive Cache Status Report
================================

Analysiert alle Caches des Crawling-Systems:
- HTML-Cache
- PDF-Cache  
- Error-Cache
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import sqlite3
from datetime import datetime
from src.scraper.utils.error_cache import ErrorCache

def format_size(size_bytes):
    """Formatiere Dateigröße in human-readable Format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"

def analyze_html_cache():
    """Analysiere HTML-Cache Status."""
    cache_dir = Path("data/html_cache")
    
    if not cache_dir.exists():
        return {"status": "not_found", "path": str(cache_dir)}
    
    # SQLite-Datei
    db_path = cache_dir / "html_cache.db"
    if not db_path.exists():
        return {"status": "empty", "path": str(cache_dir)}
    
    # Datenbankstatistiken
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Anzahl Einträge
    cursor.execute("SELECT COUNT(*) FROM html_cache")
    total_entries = cursor.fetchone()[0]
    
    # Status-Codes
    cursor.execute("SELECT status_code, COUNT(*) FROM html_cache GROUP BY status_code")
    status_counts = dict(cursor.fetchall())
    
    # Letzte Aktivität
    cursor.execute("SELECT MAX(timestamp) FROM html_cache")
    last_update = cursor.fetchone()[0]
    
    conn.close()
    
    # Dateisystem-Größe
    total_size = sum(f.stat().st_size for f in cache_dir.rglob('*') if f.is_file())
    db_size = db_path.stat().st_size if db_path.exists() else 0
    
    return {
        "status": "active",
        "path": str(cache_dir),
        "total_entries": total_entries,
        "status_codes": status_counts,
        "last_update": last_update,
        "total_size": total_size,
        "db_size": db_size
    }

def analyze_pdf_cache():
    """Analysiere PDF-Cache Status."""
    cache_dir = Path("data/pdf_cache")
    
    if not cache_dir.exists():
        return {"status": "not_found", "path": str(cache_dir)}
    
    # PDF-Dateien zählen
    pdf_files = list(cache_dir.glob("*.pdf"))
    
    if not pdf_files:
        return {"status": "empty", "path": str(cache_dir)}
    
    # Größe berechnen
    total_size = sum(f.stat().st_size for f in pdf_files)
    
    # Letzte Aktualisierung
    last_modified = max(f.stat().st_mtime for f in pdf_files)
    last_update = datetime.fromtimestamp(last_modified).isoformat()
    
    return {
        "status": "active", 
        "path": str(cache_dir),
        "total_pdfs": len(pdf_files),
        "total_size": total_size,
        "last_update": last_update
    }

def analyze_error_cache():
    """Analysiere Error-Cache Status."""
    cache_dir = Path("data/error_cache")
    
    if not cache_dir.exists():
        return {"status": "not_found", "path": str(cache_dir)}
    
    try:
        error_cache = ErrorCache(str(cache_dir))
        stats = error_cache.get_stats()
        
        # Dateigröße
        db_path = cache_dir / "error_cache.db"
        db_size = db_path.stat().st_size if db_path.exists() else 0
        
        return {
            "status": "active",
            "path": str(cache_dir),
            "total_errors": stats['total_errors'],
            "by_status_code": stats['by_status_code'],
            "by_error_type": stats['by_error_type'],
            "db_size": db_size
        }
    except Exception as e:
        return {"status": "error", "path": str(cache_dir), "error": str(e)}

def print_cache_report():
    """Erstelle umfassenden Cache-Report."""
    print("🔍 COMPREHENSIVE CACHE STATUS REPORT")
    print("=" * 60)
    print(f"📅 Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # HTML Cache
    print(f"\n📄 HTML CACHE")
    print("-" * 30)
    html_status = analyze_html_cache()
    
    if html_status["status"] == "not_found":
        print(f"❌ Not Found: {html_status['path']}")
    elif html_status["status"] == "empty":
        print(f"📂 Empty: {html_status['path']}")
    elif html_status["status"] == "active":
        print(f"✅ Active: {html_status['path']}")
        print(f"   📊 Total Entries: {html_status['total_entries']:,}")
        print(f"   📁 Total Size: {format_size(html_status['total_size'])}")
        print(f"   💾 DB Size: {format_size(html_status['db_size'])}")
        if html_status.get('status_codes'):
            print(f"   📈 Status Codes:")
            for code, count in html_status['status_codes'].items():
                print(f"      {code}: {count:,}")
        if html_status.get('last_update'):
            last_update = datetime.fromtimestamp(html_status['last_update'])
            print(f"   ⏰ Last Update: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # PDF Cache  
    print(f"\n📄 PDF CACHE")
    print("-" * 30)
    pdf_status = analyze_pdf_cache()
    
    if pdf_status["status"] == "not_found":
        print(f"❌ Not Found: {pdf_status['path']}")
    elif pdf_status["status"] == "empty":
        print(f"📂 Empty: {pdf_status['path']}")
    elif pdf_status["status"] == "active":
        print(f"✅ Active: {pdf_status['path']}")
        print(f"   📊 Total PDFs: {pdf_status['total_pdfs']:,}")
        print(f"   📁 Total Size: {format_size(pdf_status['total_size'])}")
        if pdf_status.get('last_update'):
            print(f"   ⏰ Last Update: {pdf_status['last_update']}")
    
    # Error Cache
    print(f"\n🚫 ERROR CACHE")
    print("-" * 30)
    error_status = analyze_error_cache()
    
    if error_status["status"] == "not_found":
        print(f"❌ Not Found: {error_status['path']}")
    elif error_status["status"] == "error":
        print(f"⚠️  Error: {error_status['error']}")
    elif error_status["status"] == "active":
        print(f"✅ Active: {error_status['path']}")
        print(f"   📊 Total Errors: {error_status['total_errors']:,}")
        print(f"   💾 DB Size: {format_size(error_status['db_size'])}")
        if error_status.get('by_status_code'):
            print(f"   📈 By Status Code:")
            for code, count in error_status['by_status_code'].items():
                print(f"      {code}: {count:,}")
        if error_status.get('by_error_type'):
            print(f"   📝 By Error Type:")
            for error_type, count in error_status['by_error_type'].items():
                print(f"      {error_type}: {count:,}")
    
    # Gesamtstatistiken
    print(f"\n📊 SUMMARY")
    print("-" * 30)
    
    total_size = 0
    total_items = 0
    
    if html_status["status"] == "active":
        total_size += html_status["total_size"] 
        total_items += html_status["total_entries"]
        
    if pdf_status["status"] == "active":
        total_size += pdf_status["total_size"]
        total_items += pdf_status["total_pdfs"]
        
    if error_status["status"] == "active":
        total_size += error_status["db_size"]
        total_items += error_status["total_errors"]
    
    print(f"   📁 Total Cache Size: {format_size(total_size)}")
    print(f"   📊 Total Cached Items: {total_items:,}")
    
    # Cache-Hit-Ratio-Schätzung
    if html_status["status"] == "active" and pdf_status["status"] == "active":
        success_items = html_status["total_entries"] + pdf_status["total_pdfs"]
        if error_status["status"] == "active":
            failed_items = error_status["total_errors"]
            hit_ratio = (success_items / (success_items + failed_items)) * 100 if (success_items + failed_items) > 0 else 0
            print(f"   📈 Success Rate: {hit_ratio:.1f}%")
    
    print(f"\n✅ Cache analysis completed")

if __name__ == "__main__":
    print_cache_report()