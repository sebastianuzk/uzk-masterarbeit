"""
Extrahiert HTML-Dateien aus dem Cache anhand ihrer URLs.
"""

import gzip
import sqlite3
from pathlib import Path

# Basis-Pfade
BASE_DIR = Path(__file__).parent
CACHE_DB = BASE_DIR / "data" / "html_cache" / "html_cache.db"
OUTPUT_DIR = BASE_DIR / "data"

# URLs die extrahiert werden sollen
URLS_TO_EXTRACT = [
    "https://wiso.uni-koeln.de/en/praxis/veranstaltungen/veranstaltungen-vergangener-semester/sose-2020",
    "https://wiso.uni-koeln.de/en/praxis/wiso-career-service/funcmenu/departments-a-z",
]


def extract_html_files():
    """Extrahiert HTML-Dateien aus dem Cache."""
    
    # Verbindung zur Datenbank
    conn = sqlite3.connect(CACHE_DB)
    cursor = conn.cursor()
    
    for url in URLS_TO_EXTRACT:
        print(f"\n🔍 Suche: {url}")
        
        # Suche in der Datenbank
        cursor.execute("SELECT url, file_path FROM html_cache WHERE url = ?", (url,))
        result = cursor.fetchone()
        
        if not result:
            print(f"   ❌ Nicht gefunden!")
            continue
        
        db_url, rel_path = result
        
        # Vollständiger Pfad zur gz-Datei
        gz_path = BASE_DIR / rel_path
        
        if not gz_path.exists():
            print(f"   ❌ Datei existiert nicht: {gz_path}")
            continue
        
        # Output-Dateiname aus URL generieren
        # z.B. "sose-2020.html" oder "departments-a-z.html"
        filename = url.rstrip("/").split("/")[-1] + ".html"
        output_path = OUTPUT_DIR / filename
        
        # Dekomprimieren und speichern
        with gzip.open(gz_path, 'rt', encoding='utf-8') as f_in:
            content = f_in.read()
        
        with open(output_path, 'w', encoding='utf-8') as f_out:
            f_out.write(content)
        
        print(f"   ✅ Gespeichert: {output_path}")
        print(f"   📄 Größe: {len(content):,} Zeichen")
    
    conn.close()
    print("\n✅ Fertig!")


if __name__ == "__main__":
    extract_html_files()
