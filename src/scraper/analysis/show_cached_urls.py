#!/usr/bin/env python3
"""
Script zum Anzeigen aller gecachten URLs
=========================================

Zeigt alle URLs aus dem URL-Cache in verschiedenen Formaten an.

Usage:
------
# Zeige Statistiken
python show_cached_urls.py

# Liste alle URLs auf (nach Kategorie sortiert)
python show_cached_urls.py --list

# Einfache URL-Liste
python show_cached_urls.py --list --list-format simple

# Detaillierte Liste mit Metadaten
python show_cached_urls.py --list --list-format detailed

# JSON-Export
python show_cached_urls.py --list --list-format json --list-output data/urls.json

# Suche nach URLs
python show_cached_urls.py --search "bachelor"

# Exportiere für andere Tools
python show_cached_urls.py --export csv --output urls.csv

Beispiele:
----------
# Alle URLs nach Kategorie gruppiert speichern
python show_cached_urls.py --list --list-format by-category

# Nur Studium-URLs finden
python show_cached_urls.py --search "studium"

# URLs als JSON für weitere Verarbeitung
python show_cached_urls.py --list --list-format json --list-output discovered_urls.json
"""

import sqlite3
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def show_cache_stats(db_path: str = "data/url_cache.db"):
    """Zeige detaillierte Cache-Statistiken."""
    
    if not Path(db_path).exists():
        print(f"❌ Cache-Datenbank nicht gefunden: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Gesamt-Statistik
    cursor.execute('SELECT COUNT(*) FROM url_cache')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM url_cache WHERE success = 1')
    successful = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM url_cache WHERE success = 0')
    failed = cursor.fetchone()[0]
    
    print("=" * 80)
    print("📊 URL CACHE STATISTIKEN")
    print("=" * 80)
    print(f"Gesamt gecachte URLs:    {total:,}")
    print(f"✅ Erfolgreich:          {successful:,}")
    print(f"❌ Fehlgeschlagen:       {failed:,}")
    print()
    
    # URLs nach Kategorie
    cursor.execute('''
        SELECT category, COUNT(*) as count 
        FROM url_cache 
        GROUP BY category 
        ORDER BY count DESC
    ''')
    
    print("📁 URLs NACH KATEGORIE:")
    print("-" * 80)
    categories = cursor.fetchall()
    for category, count in categories:
        cat_name = category or "unbekannt"
        bar = "█" * (count // 5)  # Visual bar
        print(f"{cat_name:15} {count:4} {bar}")
    print()
    
    # URLs nach Erfolg/Fehler
    print("📈 LETZTE SCRAPING-AKTIVITÄT:")
    print("-" * 80)
    cursor.execute('''
        SELECT url, category, last_scraped, success, status_code
        FROM url_cache 
        ORDER BY last_scraped DESC 
        LIMIT 20
    ''')
    
    for url, category, last_scraped, success, status_code in cursor.fetchall():
        status_icon = "✅" if success else "❌"
        cat_short = (category or "?")[:10].ljust(10)
        url_short = url[:60] + "..." if len(url) > 60 else url
        code_str = str(status_code or "?").rjust(3)
        print(f"{status_icon} [{cat_short}] {code_str} | {url_short}")
    
    conn.close()
    print("=" * 80)


def export_urls(db_path: str = "data/url_cache.db", 
                output_file: str = "data/cached_urls.txt",
                format_type: str = "txt"):
    """
    Exportiere alle URLs in verschiedenen Formaten.
    
    Args:
        db_path: Pfad zur Cache-Datenbank
        output_file: Output-Datei
        format_type: Format (txt, json, csv)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM url_cache ORDER BY category, url')
    rows = cursor.fetchall()
    
    if format_type == "txt":
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Gecachte URLs - {len(rows)} URLs\n")
            f.write(f"# Exportiert am: {Path(output_file).stat().st_mtime}\n\n")
            
            current_category = None
            for row in rows:
                if row['category'] != current_category:
                    current_category = row['category']
                    f.write(f"\n## {current_category or 'Unbekannt'}\n")
                f.write(f"{row['url']}\n")
        
        print(f"✅ URLs exportiert nach: {output_file}")
    
    elif format_type == "json":
        data = []
        for row in rows:
            data.append({
                'url': row['url'],
                'category': row['category'],
                'last_scraped': row['last_scraped'],
                'success': bool(row['success']),
                'status_code': row['status_code']
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ URLs exportiert nach: {output_file}")
    
    elif format_type == "csv":
        import csv
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Category', 'Last Scraped', 'Success', 'Status Code'])
            for row in rows:
                writer.writerow([
                    row['url'],
                    row['category'],
                    row['last_scraped'],
                    row['success'],
                    row['status_code']
                ])
        
        print(f"✅ URLs exportiert nach: {output_file}")
    
    conn.close()


def search_urls(db_path: str = "data/url_cache.db", query: str = ""):
    """Suche URLs im Cache."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT url, category, success, status_code 
        FROM url_cache 
        WHERE url LIKE ? 
        ORDER BY url
    ''', (f'%{query}%',))
    
    results = cursor.fetchall()
    
    print(f"\n🔍 Suchergebnisse für '{query}': {len(results)} URLs gefunden\n")
    print("-" * 80)
    
    for url, category, success, status_code in results:
        status_icon = "✅" if success else "❌"
        cat_short = (category or "?")[:10].ljust(10)
        code_str = str(status_code or "?").rjust(3)
        print(f"{status_icon} [{cat_short}] {code_str} | {url}")
    
    conn.close()


def list_all_urls(db_path: str = "data/url_cache.db", 
                  output_file: str = "data/discovered_urls.txt",
                  format_type: str = "simple"):
    """
    Liste alle URLs auf und speichere sie in eine Datei.
    
    Args:
        db_path: Pfad zur Cache-Datenbank
        output_file: Output-Datei für die URL-Liste
        format_type: Format (simple, detailed, json, by-category)
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM url_cache ORDER BY category, url')
    rows = cursor.fetchall()
    
    print(f"\n📋 Exportiere {len(rows)} URLs nach: {output_file}")
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if format_type == "simple":
        # Einfache Liste - eine URL pro Zeile
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Discovered URLs - {len(rows)} URLs\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for row in rows:
                f.write(f"{row['url']}\n")
        
        print(f"✅ {len(rows)} URLs gespeichert (simple format)")
    
    elif format_type == "detailed":
        # Detaillierte Liste mit Metadaten
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Discovered URLs - Detailed List\n")
            f.write(f"# Total URLs: {len(rows)}\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")
            
            for row in rows:
                status = "✅ SUCCESS" if row['success'] else "❌ FAILED"
                category = row['category'] or "uncategorized"
                f.write(f"URL:      {row['url']}\n")
                f.write(f"Category: {category}\n")
                f.write(f"Status:   {status} (Code: {row['status_code'] or 'N/A'})\n")
                f.write(f"Scraped:  {row['last_scraped']}\n")
                f.write("-" * 100 + "\n\n")
        
        print(f"✅ {len(rows)} URLs gespeichert (detailed format)")
    
    elif format_type == "by-category":
        # Gruppiert nach Kategorie
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# Discovered URLs - Organized by Category\n")
            f.write(f"# Total URLs: {len(rows)}\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 100 + "\n\n")
            
            # Gruppiere nach Kategorie
            by_category = defaultdict(list)
            for row in rows:
                category = row['category'] or "uncategorized"
                by_category[category].append(row['url'])
            
            # Schreibe kategorisiert
            for category in sorted(by_category.keys()):
                urls = by_category[category]
                f.write(f"\n## {category.upper()} ({len(urls)} URLs)\n")
                f.write("-" * 100 + "\n")
                for url in urls:
                    f.write(f"{url}\n")
                f.write("\n")
        
        print(f"✅ {len(rows)} URLs gespeichert (by-category format)")
    
    elif format_type == "json":
        # JSON-Format mit allen Details
        data = {
            'total_urls': len(rows),
            'generated_at': datetime.now().isoformat(),
            'urls': []
        }
        
        for row in rows:
            data['urls'].append({
                'url': row['url'],
                'category': row['category'],
                'success': bool(row['success']),
                'status_code': row['status_code'],
                'last_scraped': row['last_scraped'],
                'content_hash': row['content_hash']
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ {len(rows)} URLs gespeichert (JSON format)")
    
    conn.close()
    
    # Zeige Preview
    print(f"\n📄 Preview von {output_file}:")
    print("-" * 100)
    with open(output_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()[:15]
        for line in lines:
            print(line.rstrip())
        if len(lines) >= 15:
            print("...")
    print("-" * 100)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="URL Cache Viewer - Zeige alle gecachten URLs"
    )
    parser.add_argument('--db', default='data/url_cache.db',
                       help='Pfad zur Cache-Datenbank')
    parser.add_argument('--export', choices=['txt', 'json', 'csv'],
                       help='Exportiere URLs in Format')
    parser.add_argument('--output', default='data/cached_urls.txt',
                       help='Output-Datei für Export')
    parser.add_argument('--search', type=str,
                       help='Suche nach URLs')
    parser.add_argument('--list', action='store_true',
                       help='Liste alle URLs auf und speichere in discovered_urls.txt')
    parser.add_argument('--list-format', 
                       choices=['simple', 'detailed', 'by-category', 'json'],
                       default='by-category',
                       help='Format für --list Option')
    parser.add_argument('--list-output', default='data/discovered_urls.txt',
                       help='Output-Datei für --list Option')
    
    args = parser.parse_args()
    
    if args.list:
        list_all_urls(args.db, args.list_output, args.list_format)
    elif args.search:
        search_urls(args.db, args.search)
    elif args.export:
        export_urls(args.db, args.output, args.export)
    else:
        show_cache_stats(args.db)
