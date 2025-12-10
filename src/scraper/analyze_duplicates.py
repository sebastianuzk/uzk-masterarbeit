"""
Analysiere die Detaillierten Ergebnisse auf Duplikate
"""
import pandas as pd
from pathlib import Path

xlsx_file = Path('src/evaluation/data/Backup/naive_1250_300.xlsx')
df = pd.read_excel(xlsx_file, sheet_name='Detaillierte Ergebnisse')

print(f'Anzahl Zeilen: {len(df)}')
print(f'Spalten: {list(df.columns)}')
print()

# Prüfe auf Duplikate
if 'id' in df.columns:
    print(f'Unique IDs: {df["id"].nunique()}')
    print(f'Duplikate: {len(df) - df["id"].nunique()}')
    
    # Zeige Duplikate
    duplicates = df[df.duplicated(subset=['id'], keep=False)]
    if len(duplicates) > 0:
        print(f'\nDuplizierte IDs (erste 10):')
        for id_val in sorted(duplicates['id'].unique())[:10]:
            count = len(df[df['id'] == id_val])
            print(f'  ID {id_val}: {count}x')

if 'user_input' in df.columns:
    print(f'\nUnique Fragen (user_input): {df["user_input"].nunique()}')
    
# Zeige erste paar Zeilen
print('\nErste 5 Zeilen:')
print(df[['id', 'category', 'difficulty']].head(10).to_string())
