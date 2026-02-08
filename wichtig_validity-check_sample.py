import random
import pandas as pd
from pathlib import Path

# Setzen des Seeds für Reproduzierbarkeit
random.seed(42)

# Testset laden
csv_path = Path(__file__).parent / "src" / "evaluation" / "data" / "Testset.CSV"
df = pd.read_csv(csv_path, sep=';', encoding='utf-8')

print(f"Gesamte Fragen: {len(df)}")
print(f"\nVerteilung nach Schwierigkeit:")
print(df['difficulty'].value_counts())

# 5 Fragen pro Schwierigkeitsgrad auswählen
selected_ids = []
for difficulty in ['easy', 'medium', 'hard']:
    diff_df = df[df['difficulty'] == difficulty]
    sample_size = min(5, len(diff_df))
    sampled = diff_df.sample(n=sample_size, random_state=42)
    selected_ids.extend(sampled['id'].tolist())
    print(f"\n{difficulty.upper()} ({sample_size} Fragen):")
    for _, row in sampled.iterrows():
        print(f"  ID {row['id']}: {row['question'][:60]}...")

print(f"\n\nAusgewählte IDs (15 Fragen, je 5 pro Schwierigkeit):")
print(f"  EASY:   {sorted([id for id in selected_ids[:5]])}")
print(f"  MEDIUM: {sorted([id for id in selected_ids[5:10]])}")
print(f"  HARD:   {sorted([id for id in selected_ids[10:15]])}")
print(f"\nAlle IDs sortiert: {sorted(selected_ids)}")
