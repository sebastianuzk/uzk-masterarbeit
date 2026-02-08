#!/usr/bin/env python3
"""
Analyse der URL-Level in der Content-Database

Dieses Script analysiert, wie viele Seiten auf DEMSELBEN LEVEL enden
wie eine gegebene Beispiel-URL.

Beispiel: Für "studium" (also https://wiso.uni-koeln.de/de/studium)
werden alle URLs gefunden, die auf derselben Tiefe enden:
- /de/studium
- /de/praxis  
- /de/forschung
- etc.

Usage:
    python scripts/analyze_url_levels.py [level]
    
    level: Das Beispiel-Level (z.B. "studium" für /de/studium)
           Default: "studium"
"""

import sqlite3
import sys
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

# Projekt-Root finden
PROJECT_ROOT = Path(__file__).parent.parent
DB_PATH = PROJECT_ROOT / "data" / "content_database.db"


def get_all_urls(db_path: Path) -> list:
    """Hole alle URLs aus der Datenbank."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Hole URLs aus documents Tabelle
    cursor.execute("SELECT DISTINCT url FROM documents WHERE url IS NOT NULL")
    urls = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    return urls


def get_url_depth(url: str, base_domain: str = "wiso.uni-koeln.de") -> tuple:
    """
    Ermittle die Tiefe einer URL und ihre Pfadteile.
    
    Returns:
        tuple: (depth, path_parts, last_segment)
    """
    if not url:
        return (0, [], "")
    
    parsed = urlparse(url)
    
    # Prüfe ob es eine wiso-URL ist
    if base_domain not in parsed.netloc.lower():
        return (0, [], "")
    
    path = parsed.path.strip("/").lower()
    parts = [p for p in path.split("/") if p]
    
    # Entferne Dateiendungen (.html, .pdf, etc.) vom letzten Teil
    if parts:
        last = parts[-1]
        for ext in ['.html', '.htm', '.pdf', '.php']:
            if last.endswith(ext):
                last = last[:-len(ext)]
                parts[-1] = last
                break
    
    depth = len(parts)
    last_segment = parts[-1] if parts else ""
    
    return (depth, parts, last_segment)


def analyze_same_level(urls: list, example_level: str) -> dict:
    """
    Finde alle URLs die auf DEMSELBEN LEVEL enden wie das Beispiel.
    
    Args:
        urls: Liste aller URLs
        example_level: Beispiel-Pfad (z.B. "studium" für /de/studium)
        
    Returns:
        dict mit allen URLs auf diesem Level
    """
    # Normalisiere example_level
    example_level = example_level.strip("/").lower()
    example_parts = [p for p in example_level.split("/") if p]
    
    # Bestimme die Ziel-Tiefe basierend auf dem Beispiel
    # "studium" -> /de/studium -> Tiefe 2
    # "studium/master" -> /de/studium/master -> Tiefe 3
    target_depth = len(example_parts) + 1  # +1 für "de" Prefix
    
    print(f"   Beispiel: '{example_level}' -> Ziel-Tiefe: {target_depth}")
    
    # Sammle alle URLs auf dieser Tiefe
    urls_at_level = defaultdict(list)
    
    for url in urls:
        depth, parts, last_segment = get_url_depth(url)
        
        if depth == target_depth:
            # Gruppiere nach dem letzten Pfad-Segment
            urls_at_level[last_segment].append(url)
    
    return dict(urls_at_level)


def count_urls_below_level(urls: list, example_level: str) -> dict:
    """
    Zähle wie viele URLs UNTERHALB jedes Endpunkts auf dem gegebenen Level liegen.
    
    Args:
        urls: Liste aller URLs
        example_level: Beispiel-Pfad (z.B. "studium" für /de/studium)
        
    Returns:
        dict: {endpunkt: {"count": anzahl, "urls": [liste]}}
    """
    # Normalisiere example_level
    example_level = example_level.strip("/").lower()
    example_parts = [p for p in example_level.split("/") if p]
    
    # Bestimme die Ziel-Tiefe
    target_depth = len(example_parts) + 1  # +1 für "de"/"en" Prefix
    
    # Sammle alle URLs die UNTERHALB eines Endpunkts auf target_depth liegen
    urls_below = defaultdict(list)
    
    for url in urls:
        depth, parts, last_segment = get_url_depth(url)
        
        # URL muss tiefer sein als target_depth
        if depth > target_depth and len(parts) > target_depth:
            # Der Endpunkt ist das Element an Position target_depth - 1
            # z.B. für /de/studium/master ist "studium" an Position 1 (0-indexed)
            endpoint = parts[target_depth - 1]  # -1 weil 0-indexed
            urls_below[endpoint].append(url)
    
    # Konvertiere zu dict mit count
    result = {}
    for endpoint, url_list in urls_below.items():
        unique_urls = list(set(url_list))
        result[endpoint] = {
            "count": len(unique_urls),
            "urls": unique_urls
        }
    
    return result


def main():
    # Argument parsen
    example_level = sys.argv[1] if len(sys.argv) > 1 else "studium"
    
    print("=" * 70)
    print(f"🔍 URL-LEVEL ANALYSE: Seiten auf gleichem Level wie '{example_level}'")
    print("=" * 70)
    print()
    
    # Prüfe ob DB existiert
    if not DB_PATH.exists():
        print(f"❌ Datenbank nicht gefunden: {DB_PATH}")
        sys.exit(1)
    
    print(f"📂 Datenbank: {DB_PATH}")
    
    # URLs laden
    urls = get_all_urls(DB_PATH)
    print(f"📊 Gesamt URLs in DB: {len(urls)}")
    print()
    
    # Level analysieren
    print("=" * 70)
    print(f"🎯 SEITEN AUF GLEICHEM LEVEL WIE: '/de/{example_level}'")
    print("=" * 70)
    
    urls_at_level = analyze_same_level(urls, example_level)
    
    # URLs unterhalb jedes Endpunkts zählen
    urls_below = count_urls_below_level(urls, example_level)
    
    # Sortiere nach Anzahl der URLs pro Segment
    sorted_segments = sorted(urls_at_level.items(), key=lambda x: (-len(x[1]), x[0]))
    
    print(f"\n📌 Anzahl verschiedener Endpunkte auf diesem Level: {len(urls_at_level)}")
    print(f"📊 Gesamt URLs auf diesem Level: {sum(len(v) for v in urls_at_level.values())}")
    print()
    
    print("📋 Alle Seiten auf diesem Level + Unterseiten:")
    print("-" * 90)
    print(f"{'Endpunkt':<35} {'Auf Level':>12} {'Unterseiten':>15} {'Gesamt':>12}")
    print("-" * 90)
    
    total_at_level = 0
    total_below = 0
    
    for segment, segment_urls in sorted_segments:
        # Zeige nur unique URLs (ohne Duplikate)
        unique_at_level = len(set(segment_urls))
        below_count = urls_below.get(segment, {}).get("count", 0)
        total = unique_at_level + below_count
        
        total_at_level += unique_at_level
        total_below += below_count
        
        print(f"{segment:<35} {unique_at_level:>12} {below_count:>15} {total:>12}")
    
    # Zeige auch Endpunkte die NUR Unterseiten haben (nicht auf dem Level selbst)
    only_below = set(urls_below.keys()) - set(urls_at_level.keys())
    for segment in sorted(only_below, key=lambda x: -urls_below[x]["count"]):
        below_count = urls_below[segment]["count"]
        total_below += below_count
        print(f"{segment:<35} {0:>12} {below_count:>15} {below_count:>12}")
    
    print("-" * 90)
    print(f"{'GESAMT':<35} {total_at_level:>12} {total_below:>15} {total_at_level + total_below:>12}")
    print()
    
    # Detailierte Unterseiten-Statistik
    print("=" * 70)
    print("📊 UNTERSEITEN PRO ENDPUNKT (sortiert nach Anzahl)")
    print("=" * 70)
    
    all_endpoints = set(urls_at_level.keys()) | set(urls_below.keys())
    sorted_by_below = sorted(all_endpoints, key=lambda x: -urls_below.get(x, {}).get("count", 0))
    
    for segment in sorted_by_below[:20]:  # Top 20
        at_level = len(set(urls_at_level.get(segment, [])))
        below = urls_below.get(segment, {})
        below_count = below.get("count", 0)
        
        if below_count > 0 or at_level > 0:
            print(f"\n🔹 {segment}:")
            print(f"   Auf Level: {at_level} URL(s)")
            print(f"   Unterseiten: {below_count} URL(s)")
            
            # Zeige ein paar Beispiel-Unterseiten
            if below_count > 0:
                example_urls = below.get("urls", [])[:3]
                print(f"   Beispiele:")
                for url in example_urls:
                    print(f"      • {url[:80]}...")
    
    print()


if __name__ == "__main__":
    main()
