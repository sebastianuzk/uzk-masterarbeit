import pandas as pd
from pathlib import Path

# Exakt wie in ragas_evaluation.py load_testset()
full_path = Path('src/evaluation/data/Testset.CSV')

# Versuche verschiedene Encodings (wie im Code)
for encoding in ['utf-8', 'cp1252', 'latin-1']:
    try:
        df = pd.read_csv(full_path, sep=';', encoding=encoding)
        print(f"✅ Erfolgreich mit Encoding: {encoding}")
        break
    except UnicodeDecodeError:
        continue

print(f"   Zeilen: {len(df)}")
print(f"   Spalten: {list(df.columns)}")
print()
print("=== Erste 5 Fragen (wie in Evaluation) ===")
for i, row in df.head(5).iterrows():
    print(f"ID {row['id']}: {row['question'][:80]}...")
    print(f"   Antwort: {str(row['expected_answer'])[:80]}...")
    print()
