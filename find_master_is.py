import sqlite3
import sys

# Fix encoding for Windows terminal
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

db_path = 'data/content_database.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Suche nach Master Information Systems Modulhandbüchern
query = '''
    SELECT id, url, title
    FROM documents
    WHERE content_type = 'pdf'
    AND (url LIKE '%Master%' OR url LIKE '%m_mhb%' OR url LIKE '%m_module%')
    AND (url LIKE '%is%' OR url LIKE '%Information%Systems%')
    ORDER BY url
'''

cursor.execute(query)
results = cursor.fetchall()

print(f'\n{"="*100}')
print(f'Gefundene Master Information Systems Modulhandbücher: {len(results)}')
print(f'{"="*100}\n')

for id, url, title in results:
    filename = url.split('/')[-1]
    print(f'ID: {id}')
    print(f'Titel: {title}')
    print(f'Dateiname: {filename}')
    print(f'{"-"*100}\n')

conn.close()
