"""Quick Fix: Ersetze 'Context' → 'Document' in TSV-Headern."""
import csv
from pathlib import Path

tsv_path = Path(__file__).parent / "data" / "ares_unlabeled_evaluation.tsv"

# Lese alle Zeilen
with open(tsv_path, 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

# Ersetze Header
lines[0] = lines[0].replace('Context\t', 'Document\t')

# Schreibe zurück
with open(tsv_path, 'w', encoding='utf-8-sig') as f:
    f.writelines(lines)

print(f"✓ Header aktualisiert: {tsv_path.name}")
print(f"  Neue erste Zeile: {lines[0][:100]}...")
