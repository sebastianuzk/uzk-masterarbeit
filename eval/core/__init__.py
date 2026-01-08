"""
Core-Module für das Evaluation Framework.

Enthält:
- evaluation: Gold-Standard-Definitionen und Evaluationslogik
- runner: Szenario-Runner und Ergebnis-Aggregation
"""

from eval.core.evaluation import (
    ToolCall,
    GoldStandard,
    ArgumentMatchMode,
    EvaluationResult,
)
from eval.core.runner import (
    EvaluationScenario,
    Difficulty,
    ScenarioResult,
    EvaluationReport,
    evaluate_scenario,
    aggregate_results,
    save_report,
)

__all__ = [
    "ToolCall",
    "GoldStandard", 
    "ArgumentMatchMode",
    "EvaluationResult",
    "EvaluationScenario",
    "Difficulty",
    "ScenarioResult",
    "EvaluationReport",
    "evaluate_scenario",
    "aggregate_results",
    "save_report",
]
