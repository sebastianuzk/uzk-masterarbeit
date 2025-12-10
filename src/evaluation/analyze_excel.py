"""
Analysiere und aktualisiere Excel-Dateien mit gold_doc_rank
"""
import pandas as pd
from pathlib import Path
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows

# Erste Analyse: Zeige Struktur
xlsx_file = Path('src/evaluation/data/Backup/naive_1250_300.xlsx')
df = pd.read_excel(xlsx_file, sheet_name='Zusammenfassung', header=None)

print('Struktur des Zusammenfassung-Blattes:')
print('=' * 80)
for i, row in df.iterrows():
    row_str = ' | '.join([str(x)[:20] if pd.notna(x) else '' for x in row[:5]])
    print(f'Zeile {i:2d}: {row_str}')
