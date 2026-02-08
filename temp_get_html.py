import sqlite3
import gzip
from pathlib import Path

url = 'https://wiso.uni-koeln.de/de/studium/studienorganisation/faq/bachelor/studienwahl-und-bewerbung'

# HTML Cache Database
html_cache_db = Path('data/html_cache/html_cache.db')

if html_cache_db.exists():
    with sqlite3.connect(html_cache_db) as conn:
        # Suche URL
        cursor = conn.execute("SELECT url, file_path FROM html_cache WHERE url = ?", (url,))
        result = cursor.fetchone()
        if result:
            print(f'Gefunden: {result[0]}')
            print(f'Dateipfad: {result[1]}')
            
            # Korrigiere Pfad (file_path ist bereits relativ zu data/)
            html_file = Path(result[1])
            print(f'Suche Datei: {html_file}')
            
            if html_file.exists():
                # Entpacke gzip
                with gzip.open(html_file, 'rt', encoding='utf-8') as f:
                    html_content = f.read()
                print(f'HTML-Laenge: {len(html_content)} Zeichen')
                
                # Exportiere
                output = Path('data/bewerbung_bachelor_faq.html')
                output.write_text(html_content, encoding='utf-8')
                print(f'✅ HTML gespeichert: {output}')
            else:
                print(f'Datei nicht gefunden: {html_file}')
        else:
            print('URL nicht im html_cache gefunden')
else:
    print('html_cache.db nicht gefunden')
