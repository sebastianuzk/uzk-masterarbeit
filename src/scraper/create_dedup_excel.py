"""
Erstelle verbesserte Excel-Übersicht für Duplikate mit vollständigen PDF-URLs
"""
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

# Lade alle Dokumente
removed_path = Path('data/deduplication/dedup_stage3_removed.jsonl')
unique_path = Path('data/deduplication/dedup_stage3_unique.jsonl')

removed_docs = []
with open(removed_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            removed_docs.append(json.loads(line))

unique_docs = []
with open(unique_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            unique_docs.append(json.loads(line))

# Zeige PDF-Beispiele
print("=== PDF-Duplikate (vollständige URLs) ===")
pdf_docs = [d for d in removed_docs if d['content_type'] == 'pdf']
print(f"Anzahl PDF-Duplikate: {len(pdf_docs)}\n")
for doc in pdf_docs:
    print(f"Doc {doc['doc_id']}:")
    print(f"  URL: {doc['source']}")
    print()

# Hash-zu-Original Mapping
hash_to_original = {}
for doc in unique_docs:
    h = doc.get('normalized_hash', '')
    if h:
        hash_to_original[h] = doc

# Gruppiere nach Hash
hash_groups = defaultdict(list)
for doc in removed_docs:
    hash_groups[doc.get('normalized_hash', '')].append(doc)

# Sortiere Hashes nach Gruppengröße
sorted_hashes = sorted(hash_groups.keys(), key=lambda h: len(hash_groups[h]), reverse=True)
hash_to_group_nr = {h: i+1 for i, h in enumerate(sorted_hashes)}

# Erstelle DataFrame mit VOLLSTÄNDIGEN URLs
rows = []
for doc in removed_docs:
    doc_hash = doc.get('normalized_hash', '')
    original = hash_to_original.get(doc_hash, {})
    group_nr = hash_to_group_nr.get(doc_hash, 0)
    group_size = len(hash_groups.get(doc_hash, [])) + 1  # +1 für Original
    
    rows.append({
        'Gruppe': group_nr,
        'Gruppengroesse': group_size,
        'Entfernt_ID': doc['doc_id'],
        'Entfernt_Typ': doc['content_type'].upper(),
        'Entfernt_URL': doc['source'],  # VOLLSTÄNDIGE URL
        'Entfernt_Titel': doc.get('title') or '',
        'Behalten_ID': original.get('doc_id', ''),
        'Behalten_URL': original.get('source', ''),  # VOLLSTÄNDIGE URL
        'Behalten_Titel': original.get('title') or '',
        'Zeichen': doc.get('char_count', 0),
    })

df = pd.DataFrame(rows)
df = df.sort_values(['Gruppe', 'Entfernt_ID'])

# Excel mit openpyxl für bessere Formatierung
output_path = Path('data/deduplication/duplikate_uebersicht_vollstaendig.xlsx')

with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Entfernte Duplikate')
    
    # Spaltenbreiten anpassen
    worksheet = writer.sheets['Entfernte Duplikate']
    worksheet.column_dimensions['A'].width = 8   # Gruppe
    worksheet.column_dimensions['B'].width = 14  # Gruppengroesse
    worksheet.column_dimensions['C'].width = 12  # Entfernt_ID
    worksheet.column_dimensions['D'].width = 8   # Typ
    worksheet.column_dimensions['E'].width = 100 # Entfernt_URL (breit für vollständige URLs)
    worksheet.column_dimensions['F'].width = 50  # Entfernt_Titel
    worksheet.column_dimensions['G'].width = 12  # Behalten_ID
    worksheet.column_dimensions['H'].width = 100 # Behalten_URL (breit für vollständige URLs)
    worksheet.column_dimensions['I'].width = 50  # Behalten_Titel
    worksheet.column_dimensions['J'].width = 12  # Zeichen

print("=" * 80)
print(f'Excel erstellt: {output_path}')
print(f'Anzahl Einträge: {len(df)}')
print(f'  - HTML: {len([r for r in rows if r["Entfernt_Typ"] == "HTML"])}')
print(f'  - PDF:  {len([r for r in rows if r["Entfernt_Typ"] == "PDF"])}')
print(f'Anzahl Duplikat-Gruppen: {len(hash_groups)}')
print()
print('Spalten:')
print('  - Gruppe: Nummer der Duplikat-Gruppe (1 = größte Gruppe)')
print('  - Gruppengroesse: Anzahl identischer Dokumente (inkl. behaltenes)')
print('  - Entfernt_*: Das gelöschte Duplikat (VOLLSTÄNDIGE URL)')
print('  - Behalten_*: Das behaltene Original (VOLLSTÄNDIGE URL)')
print('  - Zeichen: Textlänge des Dokuments')
