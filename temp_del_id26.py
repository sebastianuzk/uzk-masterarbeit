import pickle
from pathlib import Path
from ragas.dataset_schema import EvaluationDataset

checkpoint_path = Path('src/evaluation/data/responses_checkpoint_20260117_080357.pkl')

with open(checkpoint_path, 'rb') as f:
    data = pickle.load(f)

print('Vorher:')
ids = sorted(data['test_df']['id'].tolist())
print(f'  Samples: {len(data["dataset"].samples)}, IDs: {ids}')

# Finde Index von ID 26
test_df = data['test_df']
idx_list = test_df[test_df['id'] == 26].index.tolist()

if idx_list:
    idx = idx_list[0]
    
    # Entferne aus allen Listen
    samples = list(data['dataset'].samples)
    del samples[idx]
    
    for key in ['response_times', 'urls_list', 'content_types_list', 'token_usage_list']:
        lst = data.get(key, [])
        if len(lst) > idx:
            del lst[idx]
        data[key] = lst
    
    # Entferne aus DataFrame
    test_df = test_df[test_df['id'] != 26].reset_index(drop=True)
    
    # Speichere
    data['dataset'] = EvaluationDataset(samples=samples)
    data['test_df'] = test_df
    
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(data, f)
    
    print('Nachher:')
    print(f'  Samples: {len(samples)}, IDs: {sorted(test_df["id"].tolist())}')
    print('✅ ID 26 entfernt!')
else:
    print('⚠️ ID 26 nicht gefunden!')
