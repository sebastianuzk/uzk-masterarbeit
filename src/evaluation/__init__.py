"""
Evaluation Module für RAG-System

Dieses Modul stellt verschiedene Evaluation-Tools für das RAG-System bereit:

1. RAGAS-basierte Evaluation (rag_evaluation.py)
   - Standard-Metriken: Context Precision, Context Recall, Faithfulness, Answer Relevancy
   - Wissenschaftlich validierte Bewertungsmethoden
   - Automatisierte Ground Truth Generierung

2. Erweiterte RAG-Evaluation (extended_rag_evaluation.py)  
   - Universitätsspezifische Metriken
   - Response Time Analyse
   - Domain Coverage Tests
   - Konsistenz-Evaluation
   - Quellenqualitäts-Analyse

Verwendung:
---------

Für RAGAS-Evaluation:
```python
from src.evaluation.rag_evaluation import RAGEvaluator
import asyncio

evaluator = RAGEvaluator()
results = await evaluator.run_evaluation()
evaluator.print_summary()
```

Für erweiterte Evaluation:
```python
from src.evaluation.extended_rag_evaluation import ExtendedRAGEvaluator

evaluator = ExtendedRAGEvaluator()
results = evaluator.run_full_evaluation()
evaluator.print_extended_summary(results)
```

Terminal-Ausführung:
------------------

RAGAS-Evaluation:
python src/evaluation/rag_evaluation.py

Erweiterte Evaluation:
python src/evaluation/extended_rag_evaluation.py

Abhängigkeiten:
--------------
pip install ragas datasets

Ausgaben:
--------
- JSON-Dateien mit detaillierten Ergebnissen
- Konsolen-Zusammenfassungen mit Scores und Empfehlungen
- Zeitstempel-basierte Dateinamen für Vergleichbarkeit
"""

__version__ = "1.0.0"
__author__ = "Autonomer Chatbot-Agent Team"

from .rag_evaluation import RAGEvaluator
from .extended_rag_evaluation import ExtendedRAGEvaluator

__all__ = [
    'RAGEvaluator',
    'ExtendedRAGEvaluator'
]