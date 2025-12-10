"""
Prüfe Schwierigkeiten-Tabelle in Zusammenfassung
"""
import pandas as pd
from pathlib import Path

xlsx_file = Path('src/evaluation/data/Backup/naive_1250_300.xlsx')

# Lade Zusammenfassung
df_summary = pd.read_excel(xlsx_file, sheet_name='Zusammenfassung', header=None)

print('Zusammenfassung-Blatt (alle Zeilen):')
print('=' * 80)
for i, row in df_summary.iterrows():
    row_vals = [str(x)[:25] if pd.notna(x) else '' for x in row[:6]]
    print(f'Zeile {i:2d}: ' + ' | '.join(row_vals))

# Lade Detaillierte Ergebnisse und berechne SOLL-Werte für Schwierigkeiten
print('\n' + '=' * 80)
print('SOLL-Werte für Schwierigkeiten (berechnet aus 116 Fragen):')
print('=' * 80)

df = pd.read_excel(xlsx_file, sheet_name='Detaillierte Ergebnisse')
df_clean = df[~df['id'].isin(['AVG', 'META'])]

for diff in ['easy', 'medium', 'hard']:
    diff_df = df_clean[df_clean['difficulty'] == diff]
    if len(diff_df) > 0:
        print(f'\n{diff.upper()} (n={len(diff_df)}):')
        for metric in ['faithfulness', 'context_recall', 'context_precision', 'gold_doc_rank']:
            if metric in diff_df.columns:
                avg = diff_df[metric].mean()
                print(f'  {metric}: {avg:.6f}')
