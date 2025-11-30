#!/usr/bin/env python3
"""
HTML Cache Management Tool
=========================

Command-line tool für die Verwaltung des HTML-Content-Cache.
Ermöglicht Inspektion, Cleanup, Export und weitere Operationen.
"""

import argparse
import logging
from pathlib import Path
from datetime import datetime
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scraper.utils.html_cache import HTMLContentCache

def setup_logging(level='INFO'):
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def format_size(bytes_size):
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def print_cache_info(cache_dir: Path):
    """Print detailed cache information."""
    if not cache_dir.exists():
        print(f"❌ Cache directory does not exist: {cache_dir}")
        return
    
    cache = HTMLContentCache(cache_dir)
    stats = cache.get_statistics()
    
    print("📄 HTML Content Cache Information")
    print("=" * 50)
    print(f"Cache Directory: {stats['cache_dir']}")
    print(f"Total Entries: {stats['total_entries']:,}")
    print(f"Unique Content: {stats['unique_content']:,}")
    print(f"Total Content Size: {format_size(stats['total_content_size'])}")
    print(f"Compressed Size: {format_size(stats['compressed_size'])}")
    print(f"Compression Ratio: {stats['compression_ratio']}")
    print(f"Hit Rate: {stats['hit_rate']}")
    print(f"Cache Hits: {stats['hits']:,}")
    print(f"Cache Misses: {stats['misses']:,}")
    print(f"Saves: {stats['saves']:,}")
    print(f"Deduplicated: {stats['deduplicated']:,}")

def list_cached_urls(cache_dir: Path, pattern: str = None, limit: int = 50):
    """List cached URLs with optional filtering."""
    if not cache_dir.exists():
        print(f"❌ Cache directory does not exist: {cache_dir}")
        return
    
    cache = HTMLContentCache(cache_dir)
    
    import sqlite3
    db_path = cache_dir / "html_cache.db"
    
    if not db_path.exists():
        print("❌ No cache database found")
        return
    
    with sqlite3.connect(db_path) as conn:
        if pattern:
            cursor = conn.execute(
                "SELECT url, content_length, timestamp FROM html_cache WHERE url LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{pattern}%", limit)
            )
        else:
            cursor = conn.execute(
                "SELECT url, content_length, timestamp FROM html_cache ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
        
        results = cursor.fetchall()
        
        if not results:
            print("📭 No cached URLs found")
            return
        
        print(f"📋 Cached URLs (showing {len(results)} of {cache.get_statistics()['total_entries']})")
        print("-" * 80)
        
        for url, content_length, timestamp in results:
            cached_date = datetime.fromtimestamp(timestamp)
            print(f"{cached_date.strftime('%Y-%m-%d %H:%M')} | {format_size(content_length):>8} | {url}")

def export_cache(cache_dir: Path, output_file: Path):
    """Export entire cache to JSON file."""
    if not cache_dir.exists():
        print(f"❌ Cache directory does not exist: {cache_dir}")
        return
    
    cache = HTMLContentCache(cache_dir)
    
    print(f"📤 Exporting cache to {output_file}...")
    exported_count = cache.export_all(output_file)
    
    if exported_count > 0:
        print(f"✅ Successfully exported {exported_count:,} entries")
        print(f"   File size: {format_size(output_file.stat().st_size)}")
    else:
        print("❌ Export failed or no entries found")

def cleanup_cache(cache_dir: Path, max_age_days: int = None):
    """Clean up old cache entries."""
    if not cache_dir.exists():
        print(f"❌ Cache directory does not exist: {cache_dir}")
        return
    
    cache = HTMLContentCache(cache_dir, max_age_days=max_age_days or 30)
    
    print(f"🧹 Cleaning up cache entries older than {max_age_days or 30} days...")
    deleted_count = cache.cleanup_old_entries()
    
    if deleted_count > 0:
        print(f"✅ Cleaned up {deleted_count:,} old entries")
    else:
        print("✅ No old entries found to clean up")

def clear_cache(cache_dir: Path, confirm: bool = False):
    """Clear entire cache."""
    if not cache_dir.exists():
        print(f"❌ Cache directory does not exist: {cache_dir}")
        return
    
    cache = HTMLContentCache(cache_dir)
    stats = cache.get_statistics()
    
    if not confirm:
        print(f"⚠️  This will delete {stats['total_entries']:,} cached entries")
        print(f"   Total size: {format_size(stats['total_content_size'])}")
        response = input("Are you sure? (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("❌ Operation cancelled")
            return
    
    print("🗑️  Clearing cache...")
    deleted_count = cache.clear_all()
    
    print(f"✅ Cleared {deleted_count:,} entries from cache")

def get_url_content(cache_dir: Path, url: str):
    """Get cached content for a specific URL."""
    if not cache_dir.exists():
        print(f"❌ Cache directory does not exist: {cache_dir}")
        return
    
    cache = HTMLContentCache(cache_dir)
    entry = cache.get(url)
    
    if not entry:
        print(f"❌ URL not found in cache: {url}")
        return
    
    print(f"📄 Cached content for: {url}")
    print("=" * 80)
    print(f"Status Code: {entry.status_code}")
    print(f"Content Type: {entry.content_type}")
    print(f"Content Length: {format_size(entry.content_length)}")
    print(f"Encoding: {entry.encoding}")
    print(f"Cached At: {datetime.fromtimestamp(entry.timestamp)}")
    if entry.etag:
        print(f"ETag: {entry.etag}")
    if entry.last_modified:
        print(f"Last Modified: {entry.last_modified}")
    print("-" * 80)
    
    # Show first 500 characters of content
    content_preview = entry.content[:500]
    if len(entry.content) > 500:
        content_preview += "..."
    
    print(content_preview)

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="HTML Cache Management Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("data/html_cache"),
        help="Path to HTML cache directory (default: data/html_cache)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help="Set logging level (default: INFO)"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Info command
    subparsers.add_parser('info', help='Show cache information')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List cached URLs')
    list_parser.add_argument('--pattern', help='Filter URLs by pattern')
    list_parser.add_argument('--limit', type=int, default=50, help='Limit number of results (default: 50)')
    
    # Export command
    export_parser = subparsers.add_parser('export', help='Export cache to JSON file')
    export_parser.add_argument('output_file', type=Path, help='Output JSON file path')
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser('cleanup', help='Clean up old cache entries')
    cleanup_parser.add_argument('--max-age-days', type=int, default=30, help='Maximum age in days (default: 30)')
    
    # Clear command
    clear_parser = subparsers.add_parser('clear', help='Clear entire cache')
    clear_parser.add_argument('--confirm', action='store_true', help='Skip confirmation prompt')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get cached content for URL')
    get_parser.add_argument('url', help='URL to retrieve from cache')
    
    args = parser.parse_args()
    
    setup_logging(args.log_level)
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'info':
            print_cache_info(args.cache_dir)
        elif args.command == 'list':
            list_cached_urls(args.cache_dir, args.pattern, args.limit)
        elif args.command == 'export':
            export_cache(args.cache_dir, args.output_file)
        elif args.command == 'cleanup':
            cleanup_cache(args.cache_dir, args.max_age_days)
        elif args.command == 'clear':
            clear_cache(args.cache_dir, args.confirm)
        elif args.command == 'get':
            get_url_content(args.cache_dir, args.url)
            
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.log_level == 'DEBUG':
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()