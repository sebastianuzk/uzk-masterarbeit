import sqlite3
import gzip

conn = sqlite3.connect('data/content_database.db')

# Hole alle Bachelor_Begruessung PDFs
cursor = conn.execute("""
    SELECT id, url, title, content 
    FROM documents 
    WHERE url LIKE '%Bachelor_Begruessung%'
    ORDER BY id
""")
results = cursor.fetchall()
conn.close()

print('Bachelor_Begruessung PDFs in Content-DB:')
print('=' * 80)

texts = {}
for doc_id, url, title, content in results:
    try:
        text = gzip.decompress(content).decode('utf-8')
        text_len = len(text)
        texts[doc_id] = text
    except:
        text_len = 0
        texts[doc_id] = ""
    
    # Kurzer Dateiname aus URL
    filename = url.split('/')[-1][:60]
    print(f'ID {doc_id}: {title[:35]:35s} | {text_len:5d} chars | {filename}')

# Vergleiche Texte auf Ähnlichkeit
print()
print('=' * 80)
print('Textvergleich (erste 200 Zeichen):')
print('=' * 80)

for doc_id, text in texts.items():
    print(f'\nID {doc_id}:')
    # Entferne Page-Marker und zeige ersten relevanten Text
    clean_text = text.replace('--- Page 1 ---', '').replace('--- Page 2 ---', '').strip()
    print(f'  {clean_text[:200]}...')
