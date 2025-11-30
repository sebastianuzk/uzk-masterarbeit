#!/usr/bin/env python3
"""
Content Cache Management Tool
=============================

Verwalte und durchsuche den gespeicherten Website-Content.
"""

import argparse
import json
import sys

from src.scraper.utils.full_content_cache import FullContentCache


def cmd_stats(args):
    """Zeige Cache-Statistiken."""
    cache = FullContentCache(args.database)
    
    try:
        stats = cache.get_cached_content_stats()
        
        print("📊 Content Cache Statistiken")
        print("=" * 50)
        print(f"Gespeicherte Seiten: {stats['total_pages']:,}")
        print(f"Original-Größe: {stats['total_original_size'] / 1024 / 1024:.1f} MB")
        print(f"Komprimierte Größe: {stats['total_compressed_size'] / 1024 / 1024:.1f} MB")
        print(f"Kompressionsrate: {stats['compression_ratio']}")
        print(f"Durchschnittliche Seitengröße: {stats['avg_page_size'] / 1024:.1f} KB")
        print(f"Erstes Datum: {stats['first_stored']}")
        print(f"Letztes Datum: {stats['last_stored']}")
        
        print(f"\n📂 Nach Kategorien:")
        for category, data in stats['by_category'].items():
            size_mb = data['total_size'] / 1024 / 1024
            print(f"  {category}: {data['count']:,} Seiten ({size_mb:.1f} MB)")
        
        print(f"\n🔝 Größte Seiten:")
        for page in stats['largest_pages']:
            size_kb = page['size'] / 1024
            title = page['title'][:60] + "..." if len(page['title']) > 60 else page['title']
            print(f"  {title}: {size_kb:.1f} KB")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1
    
    finally:
        cache.close()


def cmd_search(args):
    """Durchsuche Content."""
    cache = FullContentCache(args.database)
    
    try:
        search_fields = []
        if args.title:
            search_fields.append('title')
        if args.content:
            search_fields.append('cleaned_text')
        if args.meta:
            search_fields.append('meta_description')
        
        if not search_fields:
            search_fields = ['title', 'cleaned_text', 'meta_description']
        
        results = cache.search_content(
            query=args.query,
            search_in=search_fields,
            limit=args.limit
        )
        
        print(f"🔍 Suchergebnisse für '{args.query}'")
        print("=" * 50)
        print(f"Gefunden: {len(results)} Seiten")
        print()
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['title'] or 'Untitled'}")
            print(f"   URL: {result['url']}")
            print(f"   Kategorie: {result['category']}")
            print(f"   Größe: {result['file_size'] / 1024:.1f} KB")
            print(f"   Zuletzt: {result['last_scraped']}")
            print(f"   Relevanz: {result['relevance_score']}")
            
            if result['meta_description']:
                desc = result['meta_description'][:100] + "..." if len(result['meta_description']) > 100 else result['meta_description']
                print(f"   Beschreibung: {desc}")
            print()
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1
    
    finally:
        cache.close()


def cmd_export(args):
    """Exportiere Content."""
    cache = FullContentCache(args.database)
    
    try:
        if args.url:
            # Einzelne URL exportieren
            success = cache.export_content(args.url, args.output)
            if success:
                print(f"✅ Content exportiert: {args.url} → {args.output}")
            else:
                print(f"❌ Export fehlgeschlagen für {args.url}")
                return 1
        else:
            # Bulk-Export
            count = cache.bulk_export(args.output, args.category)
            print(f"✅ {count} Dateien nach {args.output} exportiert")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1
    
    finally:
        cache.close()


def cmd_get(args):
    """Hole Content für URL."""
    cache = FullContentCache(args.database)
    
    try:
        content = cache.get_full_content(args.url)
        
        if not content:
            print(f"❌ Kein Content gefunden für: {args.url}")
            return 1
        
        if args.format == 'json':
            # JSON-Output (ohne raw_html für Lesbarkeit)
            output = content.copy()
            output['raw_html'] = f"<HTML content ({len(content['raw_html'])} bytes)>"
            print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
        
        elif args.format == 'html':
            # HTML-Output
            print(content['raw_html'])
        
        elif args.format == 'text':
            # Text-Output
            print(content['cleaned_text'] or "Kein bereinigter Text verfügbar")
        
        else:  # summary
            print(f"📄 Content für: {args.url}")
            print("=" * 50)
            print(f"Titel: {content['title'] or 'Untitled'}")
            print(f"Meta-Description: {content['meta_description'] or 'Keine'}")
            print(f"Kategorie: {content['category']}")
            print(f"Zuletzt gescraped: {content['last_scraped']}")
            print(f"Original-Größe: {content['file_size'] / 1024:.1f} KB")
            print(f"Komprimiert: {content['compressed_size'] / 1024:.1f} KB")
            print(f"Links: {len(content['links'])}")
            print(f"Bilder: {len(content['images'])}")
            
            if content['extraction_metadata']:
                print(f"\n📊 Extraktion-Metadaten:")
                for key, value in content['extraction_metadata'].items():
                    print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1
    
    finally:
        cache.close()


def cmd_cleanup(args):
    """Bereinige alten Content."""
    cache = FullContentCache(args.database)
    
    try:
        if args.confirm or input(f"Wirklich Content älter als {args.days} Tage löschen? (y/N): ").lower() == 'y':
            deleted = cache.cleanup_old_content(args.days)
            print(f"✅ {deleted} alte Content-Einträge gelöscht")
        else:
            print("❌ Abgebrochen")
    
    except Exception as e:
        print(f"❌ Fehler: {e}")
        return 1
    
    finally:
        cache.close()


def main():
    """Hauptfunktion."""
    parser = argparse.ArgumentParser(
        description="Verwalte und durchsuche gespeicherten Website-Content"
    )
    
    parser.add_argument(
        '--database', '-d',
        default='data/full_content_cache.db',
        help='Pfad zur Cache-Datenbank'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Verfügbare Befehle')
    
    # Stats Command
    subparsers.add_parser('stats', help='Zeige Cache-Statistiken')
    
    # Search Command  
    search_parser = subparsers.add_parser('search', help='Durchsuche Content')
    search_parser.add_argument('query', help='Suchbegriff')
    search_parser.add_argument('--title', action='store_true', help='Nur in Titeln suchen')
    search_parser.add_argument('--content', action='store_true', help='Nur in Inhalten suchen')
    search_parser.add_argument('--meta', action='store_true', help='Nur in Meta-Descriptions suchen')
    search_parser.add_argument('--limit', type=int, default=20, help='Max. Anzahl Ergebnisse')
    
    # Export Command
    export_parser = subparsers.add_parser('export', help='Exportiere Content')
    export_parser.add_argument('output', help='Ausgabe-Pfad/Verzeichnis')
    export_parser.add_argument('--url', help='Spezifische URL exportieren')
    export_parser.add_argument('--category', help='Nur bestimmte Kategorie exportieren')
    
    # Get Command
    get_parser = subparsers.add_parser('get', help='Hole Content für URL')
    get_parser.add_argument('url', help='URL')
    get_parser.add_argument('--format', choices=['summary', 'json', 'html', 'text'], 
                           default='summary', help='Ausgabe-Format')
    
    # Cleanup Command
    cleanup_parser = subparsers.add_parser('cleanup', help='Bereinige alten Content')
    cleanup_parser.add_argument('--days', type=int, default=180, 
                               help='Lösche Content älter als X Tage')
    cleanup_parser.add_argument('--confirm', action='store_true', 
                               help='Bestätigung nicht erfragen')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Führe entsprechenden Befehl aus
    if args.command == 'stats':
        return cmd_stats(args)
    elif args.command == 'search':
        return cmd_search(args)
    elif args.command == 'export':
        return cmd_export(args)
    elif args.command == 'get':
        return cmd_get(args)
    elif args.command == 'cleanup':
        return cmd_cleanup(args)


if __name__ == '__main__':
    sys.exit(main() or 0)