import pandas as pd

df = pd.read_csv('src/evaluation/data/Testset.CSV', sep=';')
row = df[df['id'] == 26]

print('=== Frage 26 ===')
print('Frage:', row['question'].values[0])
print()
print('Expected Answer Länge:', len(row['expected_answer'].values[0]), 'Zeichen')
print()
print('Category:', row['category'].values[0])
print('Difficulty:', row['difficulty'].values[0])
print()
print('Expected Answer (erste 500 Zeichen):')
print(row['expected_answer'].values[0][:500])
