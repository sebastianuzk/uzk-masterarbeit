"""
Evaluierungs-Runner für Tool-Nutzungsanalyse

Dieses Modul führt Evaluierungsszenarien gegen ein LLM aus und sammelt Metriken
für die wissenschaftliche Analyse der Tool-Auswahlgenauigkeit.

Gesammelte Metriken:
- Precision: Korrekt aufgerufene Tools / Gesamt aufgerufene Tools
- Recall: Korrekt aufgerufene Tools / Erwartete Tools
- F1-Score: Harmonisches Mittel aus Precision und Recall
- Exact Match Rate: Szenarien mit perfekter Tool-Auswahl
- Argument Accuracy: Korrekte Argumente / Erwartete Argumente

Teil der Masterarbeit: KI-gestützter Universitätsassistent - Evaluierungsframework
"""

import csv
import json
import re
import time
import inspect
import importlib.util
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from io import StringIO
from pathlib import Path
from typing import Optional
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from eval.core.evaluation import (
    ToolCall,
    GoldStandard,
    EvaluationResult,
    ArgumentMatchMode,
    evaluate_tool_run,
)


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    MULTI_STEP = "multi_step"


@dataclass
class EvaluationScenario:
    """Ein einzelnes Evaluierungsszenario mit Prompt und erwartetem Ergebnis."""
    id: str
    tool: str  # Primäres Tool, das getestet wird
    difficulty: Difficulty
    user_prompt: str
    gold_standard: GoldStandard
    description: str = ""
    category: str = ""  # z.B. "registration", "application", "search"
    short_id: str = ""  # Kurz-ID wie s1, s2, s3...


@dataclass
class ScenarioResult:
    """Ergebnis eines einzelnen Szenario-Durchlaufs."""
    scenario_id: str
    short_id: str  # Kurz-ID wie s1, s2, s3...
    tool: str
    difficulty: str
    category: str
    user_prompt: str  # Die tatsächliche Frage/Anfrage
    
    # Tool-Auswahlmetriken
    expected_tools: list[str]
    actual_tools: list[str]
    correct_tools: list[str]
    forbidden_tools_called: list[str]
    
    # Argument-Metriken
    expected_arguments: dict
    actual_arguments: dict
    correct_arguments: dict
    missing_arguments: dict
    
    # Bewertungen
    tool_precision: float
    tool_recall: float
    tool_f1: float
    argument_accuracy: float
    exact_match: bool
    
    # Meta
    latency_ms: float
    error: Optional[str] = None
    
    # Token-Tracking (geschätzt)
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class AggregatedMetrics:
    """Aggregierte Metriken über alle Szenarien."""
    total_scenarios: int
    
    # Gesamtbewertungen (erforderlich)
    mean_precision: float
    mean_recall: float
    mean_f1: float
    mean_argument_accuracy: float
    exact_match_rate: float
    
    # Standardabweichungen (erforderlich)
    std_precision: float
    std_recall: float
    std_f1: float
    
    # Nach Schwierigkeit/Tool/Kategorie (erforderlich)
    metrics_by_difficulty: dict
    metrics_by_tool: dict
    metrics_by_category: dict
    
    # Fehleranalyse (erforderlich)
    total_errors: int
    forbidden_tool_violations: int
    missing_tool_count: int
    extra_tool_count: int
    
    # Token- und Zeitstatistiken (optional, mit Standardwerten)
    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    avg_tokens_per_scenario: float = 0.0
    total_time_seconds: float = 0.0
    avg_latency_ms: float = 0.0


@dataclass 
class EvaluationReport:
    """Vollständiger Evaluierungsbericht für wissenschaftliche Präsentation."""
    # Meta-Informationen
    timestamp: str
    model_name: str
    model_version: str
    total_scenarios: int
    total_duration_seconds: float
    
    # Ergebnisse
    individual_results: list[ScenarioResult]
    aggregated_metrics: AggregatedMetrics
    
    # Configuration
    evaluation_config: dict = field(default_factory=dict)


def calculate_precision_recall_f1(expected: set, actual: set) -> tuple[float, float, float]:
    """Calculate precision, recall, and F1 score."""
    if not actual:
        precision = 1.0 if not expected else 0.0
    else:
        precision = len(expected & actual) / len(actual)
    
    if not expected:
        recall = 1.0 if not actual else 0.0
    else:
        recall = len(expected & actual) / len(expected)
    
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * (precision * recall) / (precision + recall)
    
    return precision, recall, f1


def calculate_argument_accuracy(expected_args: dict, actual_args: dict, 
                                match_mode: ArgumentMatchMode) -> tuple[float, dict, dict]:
    """
    Calculate argument accuracy and identify correct/missing arguments.
    
    Returns: (accuracy, correct_args, missing_args)
    """
    if not expected_args:
        return 1.0, {}, {}
    
    correct = {}
    missing = {}
    
    for tool, args in expected_args.items():
        correct[tool] = {}
        missing[tool] = {}
        actual_tool_args = actual_args.get(tool, {})
        
        for arg_name, expected_value in args.items():
            actual_value = actual_tool_args.get(arg_name)
            
            if actual_value is None:
                missing[tool][arg_name] = expected_value
            elif match_mode == ArgumentMatchMode.EXACT:
                if actual_value == expected_value:
                    correct[tool][arg_name] = actual_value
                else:
                    missing[tool][arg_name] = expected_value
            elif match_mode == ArgumentMatchMode.NORMALIZED:
                if str(actual_value).lower().strip() == str(expected_value).lower().strip():
                    correct[tool][arg_name] = actual_value
                else:
                    missing[tool][arg_name] = expected_value
            else:  # SEMANTIC - more lenient matching
                # For semantic, we consider it correct if there's reasonable overlap
                if str(expected_value).lower() in str(actual_value).lower() or \
                   str(actual_value).lower() in str(expected_value).lower():
                    correct[tool][arg_name] = actual_value
                else:
                    missing[tool][arg_name] = expected_value
    
    total_args = sum(len(args) for args in expected_args.values())
    correct_count = sum(len(args) for args in correct.values())
    
    accuracy = correct_count / total_args if total_args > 0 else 1.0
    
    return accuracy, correct, missing


def evaluate_scenario(
    scenario: EvaluationScenario,
    actual_tool_calls: list[ToolCall],
    latency_ms: float = 0.0
) -> ScenarioResult:
    """
    Evaluate a single scenario against actual LLM tool calls.
    
    Args:
        scenario: The evaluation scenario with gold standard
        actual_tool_calls: List of ToolCall objects from the LLM
        latency_ms: Response latency in milliseconds
    
    Returns:
        ScenarioResult with all metrics
    """
    gold = scenario.gold_standard
    
    # Extract tool names
    expected_tools = set(gold.required_tools)
    actual_tools = set(tc.name for tc in actual_tool_calls)
    correct_tools = expected_tools & actual_tools
    
    # Check forbidden tools
    forbidden_called = []
    if gold.forbidden_tools:
        forbidden_called = list(gold.forbidden_tools & actual_tools)
    
    # Calculate tool metrics
    precision, recall, f1 = calculate_precision_recall_f1(expected_tools, actual_tools)
    
    # Extract actual arguments
    actual_arguments = {}
    for tc in actual_tool_calls:
        actual_arguments[tc.name] = tc.arguments
    
    # Calculate argument accuracy
    arg_accuracy, correct_args, missing_args = calculate_argument_accuracy(
        gold.required_arguments,
        actual_arguments,
        gold.argument_match_mode
    )
    
    # Exact match: all expected tools called, no forbidden tools, all arguments correct
    exact_match = (
        expected_tools == actual_tools and
        len(forbidden_called) == 0 and
        arg_accuracy == 1.0
    )
    
    return ScenarioResult(
        scenario_id=scenario.id,
        short_id=scenario.short_id,
        tool=scenario.tool,
        difficulty=scenario.difficulty.value,
        category=scenario.category,
        user_prompt=scenario.user_prompt,
        expected_tools=list(expected_tools),
        actual_tools=list(actual_tools),
        correct_tools=list(correct_tools),
        forbidden_tools_called=forbidden_called,
        expected_arguments=gold.required_arguments,
        actual_arguments=actual_arguments,
        correct_arguments=correct_args,
        missing_arguments=missing_args,
        tool_precision=precision,
        tool_recall=recall,
        tool_f1=f1,
        argument_accuracy=arg_accuracy,
        exact_match=exact_match,
        latency_ms=latency_ms
    )


def aggregate_results(results: list[ScenarioResult]) -> AggregatedMetrics:
    """Aggregate individual results into summary metrics."""
    import statistics
    
    if not results:
        return AggregatedMetrics(
            total_scenarios=0,
            mean_precision=0, mean_recall=0, mean_f1=0,
            mean_argument_accuracy=0, exact_match_rate=0,
            std_precision=0, std_recall=0, std_f1=0,
            metrics_by_difficulty={}, metrics_by_tool={}, metrics_by_category={},
            total_errors=0, forbidden_tool_violations=0,
            missing_tool_count=0, extra_tool_count=0
        )
    
    precisions = [r.tool_precision for r in results]
    recalls = [r.tool_recall for r in results]
    f1s = [r.tool_f1 for r in results]
    arg_accs = [r.argument_accuracy for r in results]
    
    # Group by difficulty
    by_difficulty = {}
    for diff in Difficulty:
        diff_results = [r for r in results if r.difficulty == diff.value]
        if diff_results:
            by_difficulty[diff.value] = {
                "count": len(diff_results),
                "mean_f1": statistics.mean([r.tool_f1 for r in diff_results]),
                "exact_match_rate": sum(1 for r in diff_results if r.exact_match) / len(diff_results),
                "mean_argument_accuracy": statistics.mean([r.argument_accuracy for r in diff_results])
            }
    
    # Group by tool
    by_tool = {}
    tools = set(r.tool for r in results)
    for tool in tools:
        tool_results = [r for r in results if r.tool == tool]
        by_tool[tool] = {
            "count": len(tool_results),
            "mean_f1": statistics.mean([r.tool_f1 for r in tool_results]),
            "exact_match_rate": sum(1 for r in tool_results if r.exact_match) / len(tool_results),
            "mean_argument_accuracy": statistics.mean([r.argument_accuracy for r in tool_results])
        }
    
    # Group by category
    by_category = {}
    categories = set(r.category for r in results if r.category)
    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        by_category[cat] = {
            "count": len(cat_results),
            "mean_f1": statistics.mean([r.tool_f1 for r in cat_results]),
            "exact_match_rate": sum(1 for r in cat_results if r.exact_match) / len(cat_results)
        }
    
    # Error analysis
    forbidden_violations = sum(1 for r in results if r.forbidden_tools_called)
    missing_tools = sum(
        len(set(r.expected_tools) - set(r.actual_tools)) 
        for r in results
    )
    extra_tools = sum(
        len(set(r.actual_tools) - set(r.expected_tools)) 
        for r in results
    )
    errors = sum(1 for r in results if r.error)
    
    # Token and time statistics
    total_input_tokens = sum(r.input_tokens for r in results)
    total_output_tokens = sum(r.output_tokens for r in results)
    total_tokens = sum(r.total_tokens for r in results)
    total_time_ms = sum(r.latency_ms for r in results)
    
    return AggregatedMetrics(
        total_scenarios=len(results),
        # Token and time stats
        total_tokens=total_tokens,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        avg_tokens_per_scenario=total_tokens / len(results) if results else 0,
        total_time_seconds=total_time_ms / 1000,
        avg_latency_ms=total_time_ms / len(results) if results else 0,
        # Scores
        mean_precision=statistics.mean(precisions),
        mean_recall=statistics.mean(recalls),
        mean_f1=statistics.mean(f1s),
        mean_argument_accuracy=statistics.mean(arg_accs),
        exact_match_rate=sum(1 for r in results if r.exact_match) / len(results),
        std_precision=statistics.stdev(precisions) if len(precisions) > 1 else 0,
        std_recall=statistics.stdev(recalls) if len(recalls) > 1 else 0,
        std_f1=statistics.stdev(f1s) if len(f1s) > 1 else 0,
        metrics_by_difficulty=by_difficulty,
        metrics_by_tool=by_tool,
        metrics_by_category=by_category,
        total_errors=errors,
        forbidden_tool_violations=forbidden_violations,
        missing_tool_count=missing_tools,
        extra_tool_count=extra_tools
    )


def generate_latex_table(metrics: AggregatedMetrics) -> str:
    """Generate LaTeX table for the results."""
    latex = r"""
\begin{table}[h]
\centering
\caption{Tool Selection Evaluation Results}
\label{tab:tool_eval_results}
\begin{tabular}{lcccc}
\toprule
\textbf{Metric} & \textbf{Mean} & \textbf{Std Dev} \\
\midrule
Precision & %.3f & %.3f \\
Recall & %.3f & %.3f \\
F1-Score & %.3f & %.3f \\
Argument Accuracy & %.3f & -- \\
Exact Match Rate & %.3f & -- \\
\bottomrule
\end{tabular}
\end{table}
""" % (
        metrics.mean_precision, metrics.std_precision,
        metrics.mean_recall, metrics.std_recall,
        metrics.mean_f1, metrics.std_f1,
        metrics.mean_argument_accuracy,
        metrics.exact_match_rate
    )
    
    # Add by-difficulty table
    latex += r"""
\begin{table}[h]
\centering
\caption{Results by Difficulty Level}
\label{tab:results_by_difficulty}
\begin{tabular}{lccc}
\toprule
\textbf{Difficulty} & \textbf{N} & \textbf{F1} & \textbf{Exact Match} \\
\midrule
"""
    for diff, data in sorted(metrics.metrics_by_difficulty.items()):
        latex += "%s & %d & %.3f & %.3f \\\\\n" % (
            diff.capitalize(), data["count"], data["mean_f1"], data["exact_match_rate"]
        )
    
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    
    # Add by-tool table
    latex += r"""
\begin{table}[h]
\centering
\caption{Results by Tool}
\label{tab:results_by_tool}
\begin{tabular}{lccc}
\toprule
\textbf{Tool} & \textbf{N} & \textbf{F1} & \textbf{Exact Match} \\
\midrule
"""
    for tool, data in sorted(metrics.metrics_by_tool.items()):
        tool_display = tool.replace("_", r"\_")
        latex += "%s & %d & %.3f & %.3f \\\\\n" % (
            tool_display, data["count"], data["mean_f1"], data["exact_match_rate"]
        )
    
    latex += r"""\bottomrule
\end{tabular}
\end{table}
"""
    
    return latex


def generate_markdown_report(report: EvaluationReport) -> str:
    """Generate a Markdown report for quick viewing."""
    m = report.aggregated_metrics
    
    md = f"""# Tool Evaluation Report

**Generated:** {report.timestamp}  
**Model:** {report.model_name} ({report.model_version})  
**Total Scenarios:** {report.total_scenarios}  
**Duration:** {report.total_duration_seconds:.2f}s

---

## Overall Metrics

| Metric | Value | Std Dev |
|--------|-------|---------|
| Precision | {m.mean_precision:.3f} | ±{m.std_precision:.3f} |
| Recall | {m.mean_recall:.3f} | ±{m.std_recall:.3f} |
| F1-Score | {m.mean_f1:.3f} | ±{m.std_f1:.3f} |
| Argument Accuracy | {m.mean_argument_accuracy:.3f} | - |
| **Exact Match Rate** | **{m.exact_match_rate:.1%}** | - |

---

## Results by Difficulty

| Difficulty | N | F1 | Exact Match |
|------------|---|-----|-------------|
"""
    
    for diff, data in sorted(m.metrics_by_difficulty.items()):
        md += f"| {diff.capitalize()} | {data['count']} | {data['mean_f1']:.3f} | {data['exact_match_rate']:.1%} |\n"
    
    md += """
---

## Results by Tool

| Tool | N | F1 | Exact Match | Arg Accuracy |
|------|---|-----|-------------|--------------|
"""
    
    for tool, data in sorted(m.metrics_by_tool.items()):
        md += f"| `{tool}` | {data['count']} | {data['mean_f1']:.3f} | {data['exact_match_rate']:.1%} | {data['mean_argument_accuracy']:.3f} |\n"
    
    md += f"""
---

## Error Analysis

| Error Type | Count |
|------------|-------|
| Forbidden Tool Violations | {m.forbidden_tool_violations} |
| Missing Tools | {m.missing_tool_count} |
| Extra Tools Called | {m.extra_tool_count} |
| Runtime Errors | {m.total_errors} |

---

## Failed Scenarios

"""
    
    failed = [r for r in report.individual_results if not r.exact_match]
    if failed:
        md += "| Short ID | Scenario ID | Tool | Difficulty | Expected | Actual | Issue |\n"
        md += "|----------|-------------|------|------------|----------|--------|-------|\n"
        for r in failed[:20]:  # Limit to first 20
            expected = ", ".join(r.expected_tools) or "none"
            actual = ", ".join(r.actual_tools) or "none"
            issue = []
            if r.forbidden_tools_called:
                issue.append(f"forbidden: {r.forbidden_tools_called}")
            if set(r.expected_tools) - set(r.actual_tools):
                issue.append("missing tools")
            if set(r.actual_tools) - set(r.expected_tools):
                issue.append("extra tools")
            if r.argument_accuracy < 1.0:
                issue.append(f"arg acc: {r.argument_accuracy:.0%}")
            md += f"| {r.short_id} | {r.scenario_id} | {r.tool} | {r.difficulty} | {expected} | {actual} | {'; '.join(issue)} |\n"
        
        if len(failed) > 20:
            md += f"\n*... and {len(failed) - 20} more failed scenarios*\n"
    else:
        md += "*All scenarios passed!*\n"
    
    return md


def generate_csv_results(results: list[ScenarioResult]) -> str:
    """
    Generate CSV with individual scenario results.
    
    Columns optimized for statistical analysis in R/Python/SPSS.
    """
    output = StringIO()
    
    fieldnames = [
        # Identifiers
        "short_id",
        "scenario_id",
        "tool",
        "difficulty",
        "category",
        "user_prompt",
        # Tool selection metrics
        "n_expected_tools",
        "n_actual_tools",
        "n_correct_tools",
        "n_forbidden_called",
        "tool_precision",
        "tool_recall",
        "tool_f1",
        # Argument metrics
        "argument_accuracy",
        # Overall
        "exact_match",
        "latency_ms",
        # Token usage
        "input_tokens",
        "output_tokens",
        "total_tokens",
        # Detailed (for debugging)
        "expected_tools",
        "actual_tools",
        "error",
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for r in results:
        # Clean prompt: collapse whitespace for CSV compatibility
        clean_prompt = " ".join(r.user_prompt.split())
        writer.writerow({
            "short_id": r.short_id,
            "scenario_id": r.scenario_id,
            "tool": r.tool,
            "difficulty": r.difficulty,
            "category": r.category,
            "user_prompt": clean_prompt,
            "n_expected_tools": len(r.expected_tools),
            "n_actual_tools": len(r.actual_tools),
            "n_correct_tools": len(r.correct_tools),
            "n_forbidden_called": len(r.forbidden_tools_called),
            "tool_precision": round(r.tool_precision, 4),
            "tool_recall": round(r.tool_recall, 4),
            "tool_f1": round(r.tool_f1, 4),
            "argument_accuracy": round(r.argument_accuracy, 4),
            "exact_match": 1 if r.exact_match else 0,  # Binary for stats
            "latency_ms": round(r.latency_ms, 2),
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "total_tokens": r.total_tokens,
            "expected_tools": ";".join(r.expected_tools),
            "actual_tools": ";".join(r.actual_tools),
            "error": r.error or "",
        })
    
    return output.getvalue()


def generate_csv_summary(metrics: AggregatedMetrics, model_name: str = "") -> str:
    """
    Generate CSV with aggregated summary metrics.
    
    One row per evaluation run - useful for comparing models.
    """
    output = StringIO()
    
    fieldnames = [
        "model",
        "timestamp",
        "n_scenarios",
        "precision_mean",
        "precision_std",
        "recall_mean", 
        "recall_std",
        "f1_mean",
        "f1_std",
        "argument_accuracy_mean",
        "exact_match_rate",
        "n_forbidden_violations",
        "n_missing_tools",
        "n_extra_tools",
        "n_errors",
        # Token and time statistics
        "total_time_seconds",
        "avg_latency_ms",
        "total_tokens",
        "total_input_tokens",
        "total_output_tokens",
        "avg_tokens_per_scenario",
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    writer.writerow({
        "model": model_name,
        "timestamp": datetime.now().isoformat(),
        "n_scenarios": metrics.total_scenarios,
        "precision_mean": round(metrics.mean_precision, 4),
        "precision_std": round(metrics.std_precision, 4),
        "recall_mean": round(metrics.mean_recall, 4),
        "recall_std": round(metrics.std_recall, 4),
        "f1_mean": round(metrics.mean_f1, 4),
        "f1_std": round(metrics.std_f1, 4),
        "argument_accuracy_mean": round(metrics.mean_argument_accuracy, 4),
        "exact_match_rate": round(metrics.exact_match_rate, 4),
        "n_forbidden_violations": metrics.forbidden_tool_violations,
        "n_missing_tools": metrics.missing_tool_count,
        "n_extra_tools": metrics.extra_tool_count,
        "n_errors": metrics.total_errors,
        # Token and time statistics
        "total_time_seconds": round(metrics.total_time_seconds, 2),
        "avg_latency_ms": round(metrics.avg_latency_ms, 2),
        "total_tokens": metrics.total_tokens,
        "total_input_tokens": metrics.total_input_tokens,
        "total_output_tokens": metrics.total_output_tokens,
        "avg_tokens_per_scenario": round(metrics.avg_tokens_per_scenario, 1),
    })
    
    return output.getvalue()


def sanitize_model_name(model_name: str) -> str:
    """
    Sanitize model name for use as directory name.
    
    Removes/replaces characters that are problematic for file systems.
    """
    # Replace colons, slashes, and other problematic chars
    sanitized = model_name.replace(":", "_").replace("/", "_").replace("\\", "_")
    sanitized = sanitized.replace(" ", "_").replace(".", "_")
    # Remove any remaining problematic characters
    sanitized = re.sub(r'[<>"|?*]', '', sanitized)
    return sanitized


def save_report(report: EvaluationReport, output_dir: str = "data/eval_results"):
    """
    Save evaluation report in multiple formats.
    
    Directory structure:
        {output_dir}/
            {model_name}_{agent_type}/
                tools/
                    results.json
                    results.csv
                    summary.csv
                    report.md
                    tables.tex
    """
    # Sanitize model name for directory
    model_dir_name = sanitize_model_name(report.model_name)
    
    # Agent-Typ aus evaluation_config holen
    agent_type = report.evaluation_config.get('agent_type', 'single')
    
    # Create model+agent-specific directory with tools/ subfolder
    model_path = Path(output_dir) / f"{model_dir_name}_{agent_type}"
    tools_path = model_path / "tools"
    tools_path.mkdir(parents=True, exist_ok=True)
    
    # Save JSON (complete data)
    json_path = tools_path / "results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False, default=str)
    
    # Save Markdown report
    md_path = tools_path / "report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(generate_markdown_report(report))
    
    # Save LaTeX tables
    latex_path = tools_path / "tables.tex"
    with open(latex_path, "w", encoding="utf-8") as f:
        f.write(generate_latex_table(report.aggregated_metrics))
    
    # Save CSV - individual results (for statistical analysis)
    csv_results_path = tools_path / "results.csv"
    with open(csv_results_path, "w", encoding="utf-8", newline="") as f:
        f.write(generate_csv_results(report.individual_results))
    
    # Save CSV - summary for this run
    csv_summary_path = tools_path / "summary.csv"
    with open(csv_summary_path, "w", encoding="utf-8", newline="") as f:
        f.write(generate_csv_summary(report.aggregated_metrics, report.model_name))
    
    print(f"Reports saved to {tools_path}/")
    print(f"  - results.json (complete data)")
    print(f"  - results.csv (individual results for R/Python)")
    print(f"  - summary.csv (run summary)")
    print(f"  - report.md (readable report)")
    print(f"  - tables.tex (LaTeX tables)")
    
    return model_path


# ============================================================================
# SZENARIO-LOADING UND AUSFÜHRUNG
# ============================================================================

def load_scenarios_from_tests() -> list[EvaluationScenario]:
    """
    Lädt alle Evaluierungsszenarien aus den Test-Dateien in eval/scenarios/.
    
    Scannt die Szenario-Dateien und extrahiert EvaluationScenario-Objekte
    aus allen Testklassen und -methoden.
    
    Returns:
        Liste aller gefundenen Evaluierungsszenarien
    """
    from pathlib import Path
    import importlib.util
    import inspect
    
    scenarios = []
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    
    # Durchsuche alle Python-Testdateien
    for test_file in scenarios_dir.rglob("test_*.py"):
        # Lade Modul dynamisch
        spec = importlib.util.spec_from_file_location(test_file.stem, test_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                print(f"⚠️  Konnte {test_file} nicht laden: {e}")
                continue
            
            # Suche nach Testklassen
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.startswith("Test"):
                    # Suche nach Testmethoden
                    for method_name, method in inspect.getmembers(obj, inspect.isfunction):
                        if method_name.startswith("test_"):
                            # Versuche Szenario aus Docstring zu parsen
                            try:
                                scenario = _parse_scenario_from_method(
                                    obj, method_name, method, test_file
                                )
                                if scenario:
                                    scenarios.append(scenario)
                            except Exception as e:
                                print(f"⚠️  Fehler bei {name}.{method_name}: {e}")
    
    # Sortiere nach ID
    scenarios.sort(key=lambda s: s.id)
    
    # Vergebe kurze IDs
    for i, scenario in enumerate(scenarios, 1):
        scenario.short_id = f"s{i}"
    
    return scenarios


def _parse_scenario_from_method(
    cls, method_name: str, method, test_file: Path
) -> Optional[EvaluationScenario]:
    """
    Extrahiert ein EvaluationScenario aus einer Testmethode.
    
    Parst den Docstring und Methodeninhalt, um die Szenario-Details zu extrahieren.
    """
    import ast
    import re
    
    docstring = method.__doc__ or ""
    
    # Extrahiere Difficulty aus Klassennamen
    class_name = cls.__name__
    if "Easy" in class_name:
        difficulty = Difficulty.EASY
    elif "Medium" in class_name:
        difficulty = Difficulty.MEDIUM
    elif "Hard" in class_name:
        difficulty = Difficulty.HARD
    elif "Multi" in class_name:
        difficulty = Difficulty.MULTI_STEP
    else:
        difficulty = Difficulty.MEDIUM
    
    # Extrahiere Tool aus Verzeichnisname oder Dateiname
    parent_dir = test_file.parent.name
    if parent_dir == "klips":
        tool = _extract_tool_from_filename(test_file.stem)
    elif parent_dir == "tools":
        tool = _extract_tool_from_filename(test_file.stem)
    else:
        tool = "unknown"
    
    # Extrahiere user_prompt aus dem Methodencode
    try:
        source = inspect.getsource(method)
        
        # Suche nach user_prompt = """...""" (mehrzeilige Triple-Quotes)
        prompt_match = re.search(
            r'(?:prompt|user_prompt)\s*=\s*"""(.*?)"""',
            source, re.DOTALL
        )
        if not prompt_match:
            # Fallback: user_prompt = '''...'''
            prompt_match = re.search(
                r"(?:prompt|user_prompt)\s*=\s*'''(.*?)'''",
                source, re.DOTALL
            )
        if not prompt_match:
            # Fallback: einzeilige Strings user_prompt = "..."
            prompt_match = re.search(
                r'(?:prompt|user_prompt)\s*=\s*["\'](.+?)["\']',
                source, re.DOTALL
            )
        
        if prompt_match:
            user_prompt = prompt_match.group(1).strip()
        else:
            # Letzter Fallback: Docstring verwenden
            user_prompt = docstring.split("\n")[0] if docstring else f"Test: {method_name}"
        
        # Suche nach GoldStandard(...) - auch mehrzeilig
        gold_match = re.search(r'GoldStandard\s*\((.*?)\)', source, re.DOTALL)
        if gold_match:
            gold_content = gold_match.group(1)
            
            # Extrahiere required_tools
            tools_match = re.search(r'required_tools\s*=\s*\[(.*?)\]', gold_content, re.DOTALL)
            required_tools = []
            if tools_match:
                tools_str = tools_match.group(1)
                required_tools = re.findall(r'["\'](\w+)["\']', tools_str)
            
            # Extrahiere forbidden_tools (für negative Tests) - kann [] oder {} sein
            forbidden_match = re.search(r'forbidden_tools\s*=\s*[\[{](.*?)[\]}]', gold_content, re.DOTALL)
            forbidden_tools = set()
            if forbidden_match:
                forbidden_str = forbidden_match.group(1)
                forbidden_tools = set(re.findall(r'["\'](\w+)["\']', forbidden_str))
            
            # Erstelle GoldStandard - negative Tests haben required_tools=[] aber forbidden_tools
            gold_standard = GoldStandard(
                required_tools=required_tools,
                forbidden_tools=forbidden_tools,
                argument_match_mode=ArgumentMatchMode.NORMALIZED
            )
        else:
            # Fallback: leerer GoldStandard mit Tool aus Dateiname
            gold_standard = GoldStandard(required_tools=[tool])
        
    except Exception as e:
        print(f"⚠️  Parsing-Fehler: {e}")
        user_prompt = docstring.split("\n")[0] if docstring else method_name
        gold_standard = GoldStandard(required_tools=[tool])
    
    # Erstelle Szenario-ID
    scenario_id = f"{cls.__name__}_{method_name}"
    
    # Kategorie aus Verzeichnis
    category = parent_dir
    
    return EvaluationScenario(
        id=scenario_id,
        tool=tool if tool != "unknown" else (
            required_tools[0] if gold_standard.required_tools else "unknown"
        ),
        difficulty=difficulty,
        user_prompt=user_prompt,
        gold_standard=gold_standard,
        description=docstring.strip(),
        category=category
    )


def _extract_tool_from_filename(filename: str) -> str:
    """Extrahiert Toolnamen aus Dateinamen wie test_register.py -> klips2_register"""
    name = filename.replace("test_", "")
    
    tool_mapping = {
        "register": "klips2_register",
        "apply": "klips2_apply_study",
        "address": "klips2_change_address",
        "password": "klips2_change_password",
        "courses": "klips2_get_course_details",
        "duckduckgo": "duckduckgo_search",
        "email": "send_email",
        "multi_negative": "multi_tool",
    }
    
    return tool_mapping.get(name, name)


def run_single_scenario(agent, scenario: EvaluationScenario) -> ScenarioResult:
    """
    Führt ein einzelnes Szenario mit dem gegebenen Agenten aus.
    
    WICHTIG: Diese Funktion testet nur die Tool-AUSWAHL, nicht die Tool-AUSFÜHRUNG!
    Wir rufen das LLM direkt mit gebundenen Tools auf, um zu sehen welche Tools
    es auswählen würde, ohne sie tatsächlich auszuführen.
    
    Args:
        agent: Der zu testende Agent (ReactAgent, MultiAgentSystem, etc.)
        scenario: Das auszuführende Szenario
    
    Returns:
        ScenarioResult mit allen Metriken
    """
    import time
    from langchain_core.messages import HumanMessage
    
    # Clear agent memory für frischen Start
    if hasattr(agent, 'clear_memory'):
        agent.clear_memory()
    
    start_time = time.time()
    tool_calls = []
    error = None
    input_tokens, output_tokens, total_tokens = 0, 0, 0
    
    try:
        # Prüfe ob es ein Multi-Agent System ist
        is_multi_agent = not hasattr(agent, 'llm')
        
        if is_multi_agent:
            # Für Multi-Agent: get_tool_selection nutzen (falls vorhanden)
            if hasattr(agent, 'get_tool_selection'):
                tool_selection = agent.get_tool_selection(scenario.user_prompt)
                for tc in tool_selection:
                    tool_calls.append(ToolCall(
                        name=tc.get("name", ""),
                        arguments=tc.get("args", {})
                    ))
            else:
                # Fallback: Agent ausführen (mit Tool-Ausführung)
                response = agent.run(scenario.user_prompt)
                # Keine Tool-Calls extrahierbar
                tool_calls = []
            
            # Token-Schätzung für Multi-Agent
            input_tokens = len(scenario.user_prompt.split()) * 2
            output_tokens = len(tool_calls) * 10
            total_tokens = input_tokens + output_tokens
            
        else:
            # Für Single-Agent (ReactAgent): LLM DIREKT mit Tools aufrufen
            # Das gibt uns die Tool-Calls OHNE die Tools auszuführen!
            
            # LLM mit gebundenen Tools holen
            llm_with_tools = agent.llm.bind_tools(agent.tools)
            
            # Message-Liste erstellen
            messages = [
                agent.system_message,
                HumanMessage(content=scenario.user_prompt)
            ]
            
            # LLM aufrufen um Tool-Auswahl zu bekommen (OHNE Ausführung)
            response = llm_with_tools.invoke(messages)
            
            # Tool-Calls aus der AIMessage extrahieren
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append(ToolCall(
                        name=tc.get("name", ""),
                        arguments=tc.get("args", {})
                    ))
            
            # Token-Usage aus Response extrahieren
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                if isinstance(usage, dict):
                    input_tokens = usage.get('input_tokens', 0)
                    output_tokens = usage.get('output_tokens', 0)
                    total_tokens = usage.get('total_tokens', input_tokens + output_tokens)
            elif hasattr(response, 'response_metadata') and response.response_metadata:
                meta = response.response_metadata
                if isinstance(meta, dict):
                    input_tokens = meta.get('prompt_eval_count', 0)
                    output_tokens = meta.get('eval_count', 0)
                    total_tokens = input_tokens + output_tokens
        
    except Exception as e:
        error = str(e)
    
    latency_ms = (time.time() - start_time) * 1000
    
    # Evaluiere das Ergebnis
    result = evaluate_scenario(scenario, tool_calls, latency_ms)
    
    # Token-Counts hinzufügen
    result.input_tokens = input_tokens
    result.output_tokens = output_tokens
    result.total_tokens = total_tokens
    
    if error:
        result.error = error
    
    return result


def _extract_tool_calls(response) -> list[ToolCall]:
    """
    Extrahiert ToolCall-Objekte aus einer Agent-Antwort.
    
    Unterstützt verschiedene Response-Formate (LangGraph, LangChain, etc.)
    """
    tool_calls = []
    
    # LangGraph-Format: dict mit messages
    if isinstance(response, dict) and "messages" in response:
        for msg in response["messages"]:
            # AIMessage mit tool_calls Attribut (LangGraph Standard)
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                for tc in msg.tool_calls:
                    # tc ist ein dict mit 'name', 'args', 'id'
                    if isinstance(tc, dict):
                        tool_calls.append(ToolCall(
                            name=tc.get("name", ""),
                            arguments=tc.get("args", {})
                        ))
            
            # ToolMessage - hat 'name' Attribut für das Tool das aufgerufen wurde
            if hasattr(msg, 'name') and msg.name:
                # Prüfe ob es eine ToolMessage ist (nicht AIMessage)
                msg_type = type(msg).__name__
                if msg_type == 'ToolMessage':
                    # ToolMessage enthält das Ergebnis eines Tool-Aufrufs
                    # Wir sammeln hier nur den Namen - Args kommen von der AIMessage
                    pass  # Tool wurde bereits über AIMessage.tool_calls erfasst
            
            # Fallback: additional_kwargs (OpenAI-Format)
            if hasattr(msg, 'additional_kwargs'):
                for tc in msg.additional_kwargs.get('tool_calls', []):
                    func = tc.get('function', {})
                    if func.get('name'):
                        tool_calls.append(ToolCall(
                            name=func.get('name', ''),
                            arguments=func.get('arguments', {})
                        ))
    
    # Direkte Tool-Aufrufe (Liste von dicts)
    elif isinstance(response, list):
        for item in response:
            if isinstance(item, dict) and 'tool' in item:
                tool_calls.append(ToolCall(
                    name=item['tool'],
                    arguments=item.get('arguments', {})
                ))
    
    return tool_calls


# Example usage for running evaluation
if __name__ == "__main__":
    # This is a demonstration of how to use the evaluation runner
    # In practice, you would integrate this with your agent
    
    print("Evaluation Runner - Demo Mode")
    print("=" * 50)
    print()
    print("To run actual evaluation, integrate with your agent:")
    print()
    print("```python")
    print("from tests.eval.runner import (")
    print("    EvaluationScenario, Difficulty, evaluate_scenario,")
    print("    aggregate_results, EvaluationReport, save_report")
    print(")")
    print()
    print("# Load scenarios from test files")
    print("scenarios = load_scenarios()")
    print()
    print("# Run each scenario through your agent")
    print("results = []")
    print("for scenario in scenarios:")
    print("    tool_calls = agent.run(scenario.user_prompt)")
    print("    result = evaluate_scenario(scenario, tool_calls)")
    print("    results.append(result)")
    print()
    print("# Generate report")
    print("metrics = aggregate_results(results)")
    print("report = EvaluationReport(...)")
    print("save_report(report)")
    print("```")
