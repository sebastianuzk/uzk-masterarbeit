"""
Evaluation Framework für den WiSo-Chatbot

Dieses Modul enthält das komplette Evaluierungsframework für die Masterarbeit:
- Tool-Evaluation: Prüft korrekte Tool-Auswahl und -Argumente
- RAGAS-Evaluation: Bewertet RAG-Qualität (Faithfulness, Context Recall/Precision)
- Kombinierte Evaluation: Führt beide Evaluationen automatisch für mehrere Modelle durch

Verwendung:
    # Komplette Evaluation für ein Modell
    python -m eval.run_full_evaluation --model llama3.1:8b --mode all
    
    # Nur Tool-Evaluation
    python -m eval.run_full_evaluation --model llama3.1:8b --mode tools
    
    # Nur RAGAS-Evaluation  
    python -m eval.run_full_evaluation --model llama3.1:8b --mode rag
    
    # Alle konfigurierten Modelle
    python -m eval.run_full_evaluation --all-models

Ergebnisse werden unter data/eval/final/<modell>/ gespeichert.
"""
