"""
Visualization Module for Tool Evaluation Results

Generates publication-quality figures for scientific papers.
Uses matplotlib with academic styling.

Part of Master's Thesis: AI-Powered University Assistant Evaluation Framework
"""

import json
from pathlib import Path
from typing import Optional
import sys
import os

# Check for matplotlib availability
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Install with: pip install matplotlib")


# Academic color palette (colorblind-friendly)
COLORS = {
    "primary": "#2E86AB",      # Blue
    "secondary": "#A23B72",    # Purple/Pink
    "tertiary": "#F18F01",     # Orange
    "success": "#C73E1D",      # Red
    "neutral": "#6C757D",      # Gray
    
    # Difficulty colors
    "easy": "#28A745",         # Green
    "medium": "#FFC107",       # Yellow
    "hard": "#DC3545",         # Red
    "multi_step": "#6F42C1",   # Purple
}

# Academic style settings
STYLE_SETTINGS = {
    "font.family": "serif",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 10,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.titlesize": 14,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.spines.top": False,
    "axes.spines.right": False,
}


def apply_style():
    """Apply academic styling to matplotlib."""
    if not HAS_MATPLOTLIB:
        return
    plt.rcParams.update(STYLE_SETTINGS)


def plot_overall_metrics(metrics: dict, save_path: Optional[str] = None) -> Optional[plt.Figure]:
    """
    Create a bar chart of overall evaluation metrics.
    
    Args:
        metrics: AggregatedMetrics as dict
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure object
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for plotting")
        return None
    
    apply_style()
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    metric_names = ["Precision", "Recall", "F1-Score", "Arg. Accuracy", "Exact Match"]
    values = [
        metrics["mean_precision"],
        metrics["mean_recall"],
        metrics["mean_f1"],
        metrics["mean_argument_accuracy"],
        metrics["exact_match_rate"]
    ]
    errors = [
        metrics["std_precision"],
        metrics["std_recall"],
        metrics["std_f1"],
        0,  # No std for arg accuracy
        0   # No std for exact match
    ]
    
    x = np.arange(len(metric_names))
    bars = ax.bar(x, values, yerr=errors, capsize=4, 
                  color=COLORS["primary"], edgecolor="black", linewidth=0.5,
                  error_kw={"elinewidth": 1, "capthick": 1})
    
    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.annotate(f'{val:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)
    
    ax.set_ylabel("Score")
    ax.set_title("Overall Tool Evaluation Metrics")
    ax.set_xticks(x)
    ax.set_xticklabels(metric_names, rotation=15, ha="right")
    ax.set_ylim(0, 1.15)
    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Saved: {save_path}")
    
    return fig


def plot_by_difficulty(metrics: dict, save_path: Optional[str] = None) -> Optional[plt.Figure]:
    """
    Create grouped bar chart comparing metrics across difficulty levels.
    
    Args:
        metrics: AggregatedMetrics as dict
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure object
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for plotting")
        return None
    
    apply_style()
    
    by_diff = metrics["metrics_by_difficulty"]
    difficulties = ["easy", "medium", "hard", "multi_step"]
    difficulties = [d for d in difficulties if d in by_diff]
    
    if not difficulties:
        print("No difficulty data available")
        return None
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(difficulties))
    width = 0.35
    
    f1_scores = [by_diff[d]["mean_f1"] for d in difficulties]
    exact_match = [by_diff[d]["exact_match_rate"] for d in difficulties]
    counts = [by_diff[d]["count"] for d in difficulties]
    
    bars1 = ax.bar(x - width/2, f1_scores, width, label="F1-Score",
                   color=COLORS["primary"], edgecolor="black", linewidth=0.5)
    bars2 = ax.bar(x + width/2, exact_match, width, label="Exact Match Rate",
                   color=COLORS["secondary"], edgecolor="black", linewidth=0.5)
    
    # Add count annotations
    for i, (xi, count) in enumerate(zip(x, counts)):
        ax.annotate(f'n={count}', xy=(xi, 0.02), ha='center', fontsize=8, color='gray')
    
    ax.set_ylabel("Score")
    ax.set_title("Performance by Difficulty Level")
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace("_", " ").title() for d in difficulties])
    ax.set_ylim(0, 1.1)
    ax.legend(loc="upper right")
    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Saved: {save_path}")
    
    return fig


def plot_by_tool(metrics: dict, save_path: Optional[str] = None) -> Optional[plt.Figure]:
    """
    Create horizontal bar chart showing performance by tool.
    
    Args:
        metrics: AggregatedMetrics as dict
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure object
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for plotting")
        return None
    
    apply_style()
    
    by_tool = metrics["metrics_by_tool"]
    
    # Sort by F1 score
    tools = sorted(by_tool.keys(), key=lambda t: by_tool[t]["mean_f1"], reverse=True)
    
    fig, ax = plt.subplots(figsize=(10, max(6, len(tools) * 0.5)))
    
    y = np.arange(len(tools))
    height = 0.35
    
    f1_scores = [by_tool[t]["mean_f1"] for t in tools]
    exact_match = [by_tool[t]["exact_match_rate"] for t in tools]
    
    bars1 = ax.barh(y + height/2, f1_scores, height, label="F1-Score",
                    color=COLORS["primary"], edgecolor="black", linewidth=0.5)
    bars2 = ax.barh(y - height/2, exact_match, height, label="Exact Match Rate",
                    color=COLORS["secondary"], edgecolor="black", linewidth=0.5)
    
    # Add count annotations
    for i, tool in enumerate(tools):
        count = by_tool[tool]["count"]
        ax.annotate(f'n={count}', xy=(0.02, i), va='center', fontsize=8, color='white')
    
    ax.set_xlabel("Score")
    ax.set_title("Performance by Tool")
    ax.set_yticks(y)
    ax.set_yticklabels([t.replace("klips2_", "").replace("_", " ").title() for t in tools])
    ax.set_xlim(0, 1.1)
    ax.legend(loc="lower right")
    ax.axvline(x=1.0, color='gray', linestyle='--', linewidth=0.5, alpha=0.5)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Saved: {save_path}")
    
    return fig


def plot_confusion_matrix(results: list, save_path: Optional[str] = None) -> Optional[plt.Figure]:
    """
    Create a confusion matrix showing expected vs actual tool selection.
    
    Args:
        results: List of ScenarioResult dicts
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure object
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for plotting")
        return None
    
    apply_style()
    
    # Collect all tools
    all_tools = set()
    for r in results:
        all_tools.update(r.get("expected_tools", []))
        all_tools.update(r.get("actual_tools", []))
    
    all_tools = sorted(all_tools)
    n_tools = len(all_tools)
    
    if n_tools == 0:
        print("No tool data available")
        return None
    
    # Build confusion matrix
    matrix = np.zeros((n_tools, n_tools))
    tool_to_idx = {t: i for i, t in enumerate(all_tools)}
    
    for r in results:
        expected = r.get("expected_tools", [])
        actual = r.get("actual_tools", [])
        
        for exp in expected:
            for act in actual:
                if exp in tool_to_idx and act in tool_to_idx:
                    matrix[tool_to_idx[exp], tool_to_idx[act]] += 1
    
    fig, ax = plt.subplots(figsize=(10, 8))
    
    im = ax.imshow(matrix, cmap="Blues")
    
    # Add colorbar
    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Count", rotation=-90, va="bottom")
    
    # Labels
    ax.set_xticks(np.arange(n_tools))
    ax.set_yticks(np.arange(n_tools))
    tool_labels = [t.replace("klips2_", "").replace("_", "\n") for t in all_tools]
    ax.set_xticklabels(tool_labels, rotation=45, ha="right")
    ax.set_yticklabels(tool_labels)
    
    ax.set_xlabel("Actual Tool")
    ax.set_ylabel("Expected Tool")
    ax.set_title("Tool Selection Confusion Matrix")
    
    # Add text annotations
    for i in range(n_tools):
        for j in range(n_tools):
            val = int(matrix[i, j])
            if val > 0:
                color = "white" if matrix[i, j] > matrix.max() / 2 else "black"
                ax.text(j, i, val, ha="center", va="center", color=color, fontsize=8)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Saved: {save_path}")
    
    return fig


def plot_error_analysis(metrics: dict, save_path: Optional[str] = None) -> Optional[plt.Figure]:
    """
    Create pie chart of error types.
    
    Args:
        metrics: AggregatedMetrics as dict
        save_path: Optional path to save figure
    
    Returns:
        matplotlib Figure object
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for plotting")
        return None
    
    apply_style()
    
    # Calculate correct scenarios
    total = metrics["total_scenarios"]
    exact_matches = int(metrics["exact_match_rate"] * total)
    
    labels = []
    sizes = []
    colors = []
    
    if exact_matches > 0:
        labels.append(f"Correct ({exact_matches})")
        sizes.append(exact_matches)
        colors.append(COLORS["easy"])
    
    forbidden = metrics.get("forbidden_tool_violations", 0)
    if forbidden > 0:
        labels.append(f"Forbidden Tool ({forbidden})")
        sizes.append(forbidden)
        colors.append(COLORS["hard"])
    
    missing = metrics.get("missing_tool_count", 0)
    if missing > 0:
        labels.append(f"Missing Tool ({missing})")
        sizes.append(missing)
        colors.append(COLORS["medium"])
    
    extra = metrics.get("extra_tool_count", 0)
    if extra > 0:
        labels.append(f"Extra Tool ({extra})")
        sizes.append(extra)
        colors.append(COLORS["tertiary"])
    
    # Account for remaining errors (argument errors)
    other_errors = total - exact_matches - forbidden - missing - extra
    if other_errors > 0:
        labels.append(f"Argument Errors ({other_errors})")
        sizes.append(other_errors)
        colors.append(COLORS["neutral"])
    
    if not sizes:
        print("No error data available")
        return None
    
    fig, ax = plt.subplots(figsize=(8, 8))
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, colors=colors,
        autopct='%1.1f%%', startangle=90,
        wedgeprops={"edgecolor": "white", "linewidth": 1}
    )
    
    ax.set_title("Error Distribution")
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        print(f"Saved: {save_path}")
    
    return fig


def generate_all_figures(report_path: str, output_dir: str = "data/eval_figures"):
    """
    Generate all figures from a saved evaluation report.
    
    Args:
        report_path: Path to JSON evaluation report
        output_dir: Directory to save figures
    """
    if not HAS_MATPLOTLIB:
        print("matplotlib required for generating figures")
        print("Install with: pip install matplotlib")
        return
    
    # Load report
    with open(report_path, "r", encoding="utf-8") as f:
        report = json.load(f)
    
    metrics = report["aggregated_metrics"]
    results = report.get("individual_results", [])
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    base_name = Path(report_path).stem
    
    print(f"Generating figures for: {base_name}")
    print("-" * 50)
    
    # Generate all figures
    plot_overall_metrics(metrics, output_path / f"{base_name}_overall.pdf")
    plot_overall_metrics(metrics, output_path / f"{base_name}_overall.png")
    
    plot_by_difficulty(metrics, output_path / f"{base_name}_by_difficulty.pdf")
    plot_by_difficulty(metrics, output_path / f"{base_name}_by_difficulty.png")
    
    plot_by_tool(metrics, output_path / f"{base_name}_by_tool.pdf")
    plot_by_tool(metrics, output_path / f"{base_name}_by_tool.png")
    
    if results:
        plot_confusion_matrix(results, output_path / f"{base_name}_confusion.pdf")
        plot_confusion_matrix(results, output_path / f"{base_name}_confusion.png")
    
    plot_error_analysis(metrics, output_path / f"{base_name}_errors.pdf")
    plot_error_analysis(metrics, output_path / f"{base_name}_errors.png")
    
    print("-" * 50)
    print(f"All figures saved to: {output_path}/")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        generate_all_figures(sys.argv[1])
    else:
        print("Usage: python visualize.py <path_to_evaluation_report.json>")
        print()
        print("This script generates publication-quality figures from evaluation results.")
        print()
        print("Available figure types:")
        print("  - Overall metrics bar chart")
        print("  - Performance by difficulty level")
        print("  - Performance by tool")
        print("  - Confusion matrix")
        print("  - Error distribution pie chart")
