"""Debug-Skript: Inspiziere LangSmith Retriever-Run Outputs"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import json
from langsmith import Client
from config.settings import settings

client = Client(
    api_key=settings.LANGSMITH_API_KEY,
    api_url="https://api.smith.langchain.com"
)

# Hole einen der Traces
session_id = "ares_eval_1_5972682229965597105"

# Finde Root-Run
root_runs = list(client.list_runs(
    project_name=settings.LANGSMITH_PROJECT,
    is_root=True,
    limit=20
))

matching_root = None
for run in root_runs:
    if hasattr(run, 'metadata') and run.metadata and run.metadata.get('session_id') == session_id:
        matching_root = run
        break

if matching_root:
    print(f"✓ Root-Run gefunden: {matching_root.id}")
    trace_id = matching_root.trace_id if hasattr(matching_root, 'trace_id') else matching_root.id
    
    # Hole alle Runs
    all_runs = list(client.list_runs(
        project_name=settings.LANGSMITH_PROJECT,
        trace_id=trace_id
    ))
    
    # Finde Retriever-Runs
    for run in all_runs:
        if hasattr(run, 'run_type') and run.run_type == 'retriever':
            print(f"\n{'='*80}")
            print(f"RETRIEVER RUN gefunden:")
            print(f"  ID: {run.id}")
            print(f"  Name: {run.name if hasattr(run, 'name') else 'N/A'}")
            print(f"  Run Type: {run.run_type}")
            print(f"\n{'='*80}")
            print(f"OUTPUTS:")
            print(f"  Type: {type(run.outputs)}")
            
            if run.outputs:
                # Pretty-print JSON
                print(f"  Content:\n{json.dumps(run.outputs, indent=2, default=str)}")
            else:
                print(f"  KEINE OUTPUTS!")
            
            print(f"\n{'='*80}")
            print(f"INPUTS:")
            if hasattr(run, 'inputs'):
                print(f"  {json.dumps(run.inputs, indent=2, default=str)}")
            else:
                print(f"  Keine Inputs")
            
            break
else:
    print(f"✗ Kein Root-Run gefunden für session_id: {session_id}")
