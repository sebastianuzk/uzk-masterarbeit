import sqlite3

conn = sqlite3.connect('data/content_database.db')
cursor = conn.cursor()

# Suche nach Information Systems Modulhandbüchern
query = """
SELECT url, title, category 
FROM documents 
WHERE content_type='pdf' 
AND (
    title LIKE '%Information Systems%' 
    OR title LIKE '%Information%Systems%'
    OR url LIKE '%information%systems%'
    OR url LIKE '%is.pdf%'
    OR url LIKE '%is_%'
    OR url LIKE '%_is.pdf%'
    OR title LIKE '%IS%'
)
ORDER BY title
"""

cursor.execute(query)
results = cursor.fetchall()

print(f'Gefunden: {len(results)} PDFs mit "Information Systems"\n')
print('='*80)

for i, (url, title, category) in enumerate(results, 1):
    print(f'\n{i}. {title}')
    print(f'   Kategorie: {category}')
    print(f'   URL: {url}')

conn.close()
