import sqlite3

conn = sqlite3.connect('data/content_database.db')
cursor = conn.cursor()

print('=== HTML Dokumente ===')
cursor.execute("SELECT id, url, title, length(content) FROM documents WHERE content_type = 'html' AND length(content) > 3000 ORDER BY length(content) DESC LIMIT 5")
for r in cursor.fetchall():
    print(f'ID {r[0]}: {r[3]} bytes - {r[2][:50]}')

print()
print('=== PDF Dokumente ===')
cursor.execute("SELECT id, url, title, length(content) FROM documents WHERE content_type = 'pdf' AND length(content) > 3000 ORDER BY length(content) DESC LIMIT 5")
for r in cursor.fetchall():
    print(f'ID {r[0]}: {r[3]} bytes - {r[2][:50]}')

conn.close()
