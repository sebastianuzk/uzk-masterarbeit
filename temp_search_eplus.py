import pickle
from pathlib import Path

# Pfad zur Checkpoint-Datei
checkpoint_path = Path('src/evaluation/data/responses_checkpoint_validation.pkl')

# Checkpoint laden
with open(checkpoint_path, 'rb') as f:
    data = pickle.load(f)

print('Checkpoint geladen')
print(f'Typ: {type(data)}')

# Gewünschte IDs
target_ids = [1, 8, 11, 17, 20, 30, 33, 34, 64, 65, 84, 89, 91, 97, 110]

if isinstance(data, dict):
    print(f'Keys: {list(data.keys())}')
    
    test_df = data.get('test_df')
    dataset = data.get('dataset')
    response_times = data.get('response_times', [])
    urls_list = data.get('urls_list', [])
    content_types_list = data.get('content_types_list', [])
    
    if test_df is not None:
        print(f'test_df Laenge: {len(test_df)}')
        print(f'Alle IDs: {test_df["id"].tolist()}')
    
    if dataset is not None:
        print(f'Dataset samples: {len(dataset.samples)}')
    
    # Finde Indizes der gewünschten IDs
    if test_df is not None:
        indices_to_keep = []
        for i, row_id in enumerate(test_df['id'].tolist()):
            if row_id in target_ids:
                indices_to_keep.append(i)
        
        print(f'\nIndizes zu behalten: {indices_to_keep}')
        print(f'Anzahl: {len(indices_to_keep)}')
        
        # Filtere test_df
        new_test_df = test_df[test_df['id'].isin(target_ids)].reset_index(drop=True)
        print(f'\nNeue test_df IDs: {new_test_df["id"].tolist()}')
        
        # Filtere samples
        if dataset is not None:
            new_samples = [dataset.samples[i] for i in indices_to_keep]
            print(f'Neue samples Anzahl: {len(new_samples)}')
            
            # Erstelle neues Dataset
            from ragas.dataset_schema import EvaluationDataset
            new_dataset = EvaluationDataset(samples=new_samples)
        
        # Filtere response_times, urls_list, content_types_list
        new_response_times = [response_times[i] for i in indices_to_keep] if response_times else []
        new_urls_list = [urls_list[i] for i in indices_to_keep] if urls_list else []
        new_content_types_list = [content_types_list[i] for i in indices_to_keep] if content_types_list else []
        
        # Neuer Checkpoint
        new_data = {
            'dataset': new_dataset,
            'test_df': new_test_df,
            'response_times': new_response_times,
            'urls_list': new_urls_list,
            'content_types_list': new_content_types_list
        }
        
        # Speichern
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(new_data, f)
        
        print(f'\n✅ Checkpoint aktualisiert mit {len(new_samples)} Eintraegen')
