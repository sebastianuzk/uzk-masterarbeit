#!/usr/bin/env python3
"""
Vollständiges Evaluierungsskript für den WiSo-Chatbot

Führt Tool- und/oder RAGAS-Evaluation für verschiedene Modelle durch.
Unterstützt sowohl lokale Ollama-Modelle als auch OpenAI API-Modelle.

Verwendung:
    # Einzelnes Modell, beide Evaluationen (Ollama)
    python -m eval.run_full_evaluation --model llama3.1:8b
    
    # OpenAI-Modell verwenden
    python -m eval.run_full_evaluation --model gpt-4o-mini --provider openai
    
    # Nur Tool-Evaluation
    python -m eval.run_full_evaluation --model llama3.1:8b --mode tools
    
    # Nur RAGAS-Evaluation
    python -m eval.run_full_evaluation --model llama3.1:8b --mode rag
    
    # Alle konfigurierten Modelle
    python -m eval.run_full_evaluation --all-models
    
    # Mit bestimmtem Agent-Typ
    python -m eval.run_full_evaluation --model llama3.1:8b --agent single
    
    # OpenAI mit spezifischem Agent
    python -m eval.run_full_evaluation --model gpt-4o --provider openai --agent single

Ergebnisse: data/eval/final/<modell>/
"""

import argparse
import json
import os
import sys
import time
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Projekt-Root zum Pfad hinzufügen
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.logging_config import get_logger, setup_logging
from config.settings import settings
from eval.utils.formatting import format_duration

logger = get_logger(__name__)

# ============================================================================
# KONFIGURATION
# ============================================================================

# Verfügbare LLM-Provider
LLM_PROVIDERS = ["ollama", "openai", "anthropic"]

# Verfügbare Modelle: zentral definiert in config/settings.py
from config.settings import AVAILABLE_MODELS

# Agent-Typen
AGENT_TYPES = ["single", "multi", "constrained", "confirmation"]

# Ausgabe-Verzeichnis
OUTPUT_BASE = PROJECT_ROOT / "data" / "eval" / "final"

# Default-Limits für Evaluation
DEFAULT_RAG_LIMIT = 100  # Standard: 100 Fragen für RAGAS (116 total verfügbar)
DEFAULT_TOOL_LIMIT = None  # Alle 100 Tool-Szenarien (None = alle)


# ============================================================================
# HILFSFUNKTIONEN
# ============================================================================

def _generate_ragas_reports(
    results_df: pd.DataFrame,
    test_df: pd.DataFrame,
    summary: Dict[str, Any],
    output_dir: Path,
    model: str,
    agent_type: str,
    judge_provider: Optional[str],
    judge_model: Optional[str],
    judge_workers: int
) -> None:
    """
    Generiert detaillierte README und HTML Reports für RAGAS-Evaluation.
    
    Args:
        results_df: DataFrame mit RAGAS-Ergebnissen
        test_df: DataFrame mit Testfragen
        summary: Summary-Dictionary
        output_dir: Ausgabeverzeichnis
        model: Agent-Modellname
        agent_type: Agent-Typ
        judge_provider: RAGAS Judge Provider
        judge_model: RAGAS Judge Modell
        judge_workers: Anzahl Workers
    """
    import pandas as pd
    
    # Add category and difficulty to results
    results_df['category'] = test_df['category'].values[:len(results_df)]
    results_df['difficulty'] = test_df['difficulty'].values[:len(results_df)]
    
    # Bestimme Judge-Info
    judge_info = f"{judge_model or 'qwen2.5:7b'} ({judge_provider or 'ollama'})"
    
    # Generate README.md
    readme_content = f"""# RAGAS Evaluation Report

## Configuration

| Parameter | Value |
|-----------|-------|
| **Agent Model** | {model} |
| **Agent Type** | {agent_type} |
| **Judge** | {judge_info} |
| **Workers** | {judge_workers} |
| **Questions** | {summary['total_questions']} |
| **Duration** | {format_duration(summary['duration_seconds'])} |
| **Date** | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## Overall Metrics

| Metric | Mean | Std Dev | Min | Max |
|--------|------|---------|-----|-----|
"""
    
    for metric, values in summary['metrics'].items():
        readme_content += f"| **{metric.replace('_', ' ').title()}** | {values['mean']:.3f} | {values['std']:.3f} | {values['min']:.3f} | {values['max']:.3f} |\n"
    
    # By Category
    readme_content += "\n## Metrics by Category\n\n"
    categories = results_df['category'].dropna().unique()
    
    for category in sorted(categories):
        cat_df = results_df[results_df['category'] == category]
        readme_content += f"\n### {category} ({len(cat_df)} questions)\n\n"
        readme_content += "| Metric | Mean | Std Dev |\n"
        readme_content += "|--------|------|---------|\n"
        
        for metric in ['faithfulness', 'context_recall', 'context_precision']:
            if metric in cat_df.columns:
                mean_val = cat_df[metric].mean()
                std_val = cat_df[metric].std()
                readme_content += f"| {metric.replace('_', ' ').title()} | {mean_val:.3f} | {std_val:.3f} |\n"
    
    # By Difficulty
    readme_content += "\n## Metrics by Difficulty\n\n"
    difficulties = ['easy', 'medium', 'hard']
    
    for difficulty in difficulties:
        diff_df = results_df[results_df['difficulty'] == difficulty]
        if len(diff_df) > 0:
            readme_content += f"\n### {difficulty.upper()} ({len(diff_df)} questions)\n\n"
            readme_content += "| Metric | Mean | Std Dev |\n"
            readme_content += "|--------|------|---------|\n"
            
            for metric in ['faithfulness', 'context_recall', 'context_precision']:
                if metric in diff_df.columns:
                    mean_val = diff_df[metric].mean()
                    std_val = diff_df[metric].std()
                    readme_content += f"| {metric.replace('_', ' ').title()} | {mean_val:.3f} | {std_val:.3f} |\n"
    
    # Distribution
    readme_content += "\n## Score Distribution\n\n"
    for metric in ['faithfulness', 'context_recall', 'context_precision']:
        if metric in results_df.columns:
            readme_content += f"\n### {metric.replace('_', ' ').title()}\n\n"
            
            # Bins
            bins = [0, 0.2, 0.4, 0.6, 0.8, 1.0]
            labels = ['0.0-0.2', '0.2-0.4', '0.4-0.6', '0.6-0.8', '0.8-1.0']
            results_df[f'{metric}_bin'] = pd.cut(results_df[metric], bins=bins, labels=labels, include_lowest=True)
            
            distribution = results_df[f'{metric}_bin'].value_counts().sort_index()
            
            readme_content += "| Range | Count | Percentage |\n"
            readme_content += "|-------|-------|------------|\n"
            
            total = len(results_df)
            for label in labels:
                count = distribution.get(label, 0)
                percentage = (count / total * 100) if total > 0 else 0
                readme_content += f"| {label} | {count} | {percentage:.1f}% |\n"
    
    readme_content += f"\n## Files\n\n- **CSV Results**: `ragas_results.csv`\n- **JSON Summary**: `ragas_summary.json`\n- **HTML Report**: `ragas_report.html`\n"
    
    # Save README
    readme_path = output_dir / "README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    # Generate HTML Report
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAGAS Evaluation Report - {model}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .metric-card {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            margin: 10px;
            border-radius: 8px;
            min-width: 250px;
        }}
        .metric-card h3 {{
            margin: 0;
            color: white;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-details {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .config-table {{
            background-color: #ecf0f1;
        }}
        .category-section {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }}
        .score-excellent {{ background-color: #27ae60; color: white; }}
        .score-good {{ background-color: #f39c12; color: white; }}
        .score-poor {{ background-color: #e74c3c; color: white; }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 RAGAS Evaluation Report</h1>
        
        <h2>📋 Configuration</h2>
        <table class="config-table">
            <tr><th>Parameter</th><th>Value</th></tr>
            <tr><td><strong>Agent Model</strong></td><td>{model}</td></tr>
            <tr><td><strong>Agent Type</strong></td><td>{agent_type}</td></tr>
            <tr><td><strong>Judge</strong></td><td>{judge_info}</td></tr>
            <tr><td><strong>Workers</strong></td><td>{judge_workers}</td></tr>
            <tr><td><strong>Questions</strong></td><td>{summary['total_questions']}</td></tr>
            <tr><td><strong>Duration</strong></td><td>{format_duration(summary['duration_seconds'])}</td></tr>
            <tr><td><strong>Date</strong></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        </table>
        
        <h2>📊 Overall Metrics</h2>
        <div style="text-align: center;">
"""
    
    # Metric cards
    for metric, values in summary['metrics'].items():
        score_class = "score-excellent" if values['mean'] >= 0.7 else ("score-good" if values['mean'] >= 0.5 else "score-poor")
        html_content += f"""
            <div class="metric-card {score_class}">
                <h3>{metric.replace('_', ' ').title()}</h3>
                <div class="metric-value">{values['mean']:.3f}</div>
                <div class="metric-details">
                    ± {values['std']:.3f} | Min: {values['min']:.3f} | Max: {values['max']:.3f}
                </div>
            </div>
"""
    
    html_content += """
        </div>
        
        <h2>📁 Metrics by Category</h2>
"""
    
    # By Category
    for category in sorted(categories):
        cat_df = results_df[results_df['category'] == category]
        html_content += f"""
        <div class="category-section">
            <h3>{category} <span class="badge">{len(cat_df)} questions</span></h3>
            <table>
                <tr><th>Metric</th><th>Mean</th><th>Std Dev</th></tr>
"""
        for metric in ['faithfulness', 'context_recall', 'context_precision']:
            if metric in cat_df.columns:
                mean_val = cat_df[metric].mean()
                std_val = cat_df[metric].std()
                html_content += f"<tr><td>{metric.replace('_', ' ').title()}</td><td>{mean_val:.3f}</td><td>{std_val:.3f}</td></tr>\n"
        
        html_content += """
            </table>
        </div>
"""
    
    html_content += """
        <h2>⚡ Metrics by Difficulty</h2>
"""
    
    # By Difficulty
    for difficulty in difficulties:
        diff_df = results_df[results_df['difficulty'] == difficulty]
        if len(diff_df) > 0:
            html_content += f"""
        <div class="category-section">
            <h3>{difficulty.upper()} <span class="badge">{len(diff_df)} questions</span></h3>
            <table>
                <tr><th>Metric</th><th>Mean</th><th>Std Dev</th></tr>
"""
            for metric in ['faithfulness', 'context_recall', 'context_precision']:
                if metric in diff_df.columns:
                    mean_val = diff_df[metric].mean()
                    std_val = diff_df[metric].std()
                    html_content += f"<tr><td>{metric.replace('_', ' ').title()}</td><td>{mean_val:.3f}</td><td>{std_val:.3f}</td></tr>\n"
            
            html_content += """
            </table>
        </div>
"""
    
    html_content += """
    </div>
</body>
</html>
"""
    
    # Save HTML
    html_path = output_dir / "ragas_report.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)


def get_model_safe_name(model: str) -> str:
    """Konvertiert Modellname zu sicherem Verzeichnisnamen für Hauptordner."""
    # Nur : und / ersetzen, . beibehalten für Lesbarkeit
    return model.replace(":", "-").replace("/", "-")


def get_model_folder_name(model: str) -> str:
    """Konvertiert Modellname zu sicherem Namen für Unterordner (ohne Sonderzeichen)."""
    # Alle Sonderzeichen ersetzen für konsistente Unterordner-Namen
    sanitized = model.replace(":", "_").replace("/", "_").replace("\\", "_")
    sanitized = sanitized.replace(" ", "_").replace(".", "_")
    return sanitized


def generate_combined_report(base_dir: Path, model: str) -> None:
    """
    Generiert einen kombinierten HTML und Markdown Report für alle Agenten.
    
    Args:
        base_dir: Basis-Verzeichnis (z.B. llama3.1-8b/20260108_205727/)
        model: Modellname (z.B. "llama3.1:8b")
    """
    logger.info("=" * 80)
    logger.info("GENERIERE KOMBINIERTEN REPORT")
    logger.info("=" * 80)
    print("\n" + "=" * 80)
    print("📊 GENERIERE KOMBINIERTEN REPORT")
    print("=" * 80)
    
    # Sammle alle Agent-Ergebnisse
    agent_results = []
    model_folder = get_model_folder_name(model)
    
    for agent_type in AGENT_TYPES:
        agent_dir = base_dir / f"{model_folder}_{agent_type}"
        summary_path = agent_dir / "summary.json"
        
        if summary_path.exists():
            with open(summary_path, 'r') as f:
                data = json.load(f)
                agent_results.append(data)
                logger.info(f"{agent_type}: Daten geladen")
                print(f"   ✅ {agent_type}: Daten geladen")
        else:
            logger.warning(f"{agent_type}: Keine Daten gefunden")
            print(f"   ⚠️  {agent_type}: Keine Daten gefunden")
    
    if not agent_results:
        logger.error("Keine Evaluationsergebnisse gefunden!")
        print("   ❌ Keine Evaluationsergebnisse gefunden!")
        return
    
    # Generiere Markdown
    md_content = _generate_markdown_report(agent_results, model)
    md_path = base_dir / "evaluation_report.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    logger.info(f"Markdown: {md_path}")
    print(f"   ✅ Markdown: {md_path}")
    
    # Generiere HTML
    html_content = _generate_html_report(agent_results, model)
    html_path = base_dir / "evaluation_report.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info(f"HTML: {html_path}")
    print(f"   ✅ HTML: {html_path}")
    
    logger.info("=" * 80)
    print("=" * 80)


def _generate_markdown_report(agent_results: List[Dict], model: str) -> str:
    """Generiert einen Markdown-Report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    md = f"""# Evaluation Report: {model}

**Generiert:** {timestamp}  
**Modell:** {model}  
**Agenten:** {len(agent_results)}

---

## Zusammenfassung

"""
    
    # Tabelle mit Übersicht
    md += "| Agent | Tool Exact Match | Tool F1 | RAGAS Faithfulness | RAGAS Context Recall | Dauer |\n"
    md += "|-------|------------------|---------|--------------------|--------------------|-------|\n"
    
    for result in agent_results:
        agent = result.get('agent_type', 'unknown')
        
        # Tool-Metriken
        tool_em = ""
        tool_f1 = ""
        if 'tools' in result and isinstance(result['tools'], dict):
            tool_em = f"{result['tools'].get('exact_match_rate', 0):.1%}"
            tool_f1 = f"{result['tools'].get('mean_f1', 0):.3f}"
        
        # RAGAS-Metriken
        ragas_faith = ""
        ragas_recall = ""
        if 'ragas' in result and isinstance(result['ragas'], dict):
            metrics = result['ragas'].get('metrics', {})
            ragas_faith = f"{metrics.get('faithfulness', {}).get('mean', 0):.3f}"
            ragas_recall = f"{metrics.get('context_recall', {}).get('mean', 0):.3f}"
        
        duration = format_duration(result.get('total_duration_seconds', 0))
        
        md += f"| {agent} | {tool_em} | {tool_f1} | {ragas_faith} | {ragas_recall} | {duration} |\n"
    
    # Detaillierte Ergebnisse pro Agent
    md += "\n---\n\n## Detaillierte Ergebnisse\n\n"
    
    for result in agent_results:
        agent = result.get('agent_type', 'unknown')
        md += f"### {agent.upper()}\n\n"
        
        # Tool-Evaluation
        if 'tools' in result and isinstance(result['tools'], dict):
            tools = result['tools']
            md += "#### Tool-Evaluation\n\n"
            md += f"- **Szenarien:** {tools.get('total_scenarios', 0)}\n"
            md += f"- **Exact Match:** {tools.get('exact_match_count', 0)} ({tools.get('exact_match_rate', 0):.1%})\n"
            md += f"- **F1-Score:** {tools.get('mean_f1', 0):.3f}\n"
            md += f"- **Precision:** {tools.get('mean_precision', 0):.3f}\n"
            md += f"- **Recall:** {tools.get('mean_recall', 0):.3f}\n\n"
        
        # RAGAS-Evaluation
        if 'ragas' in result and isinstance(result['ragas'], dict):
            ragas = result['ragas']
            md += "#### RAGAS-Evaluation\n\n"
            md += f"- **Fragen:** {ragas.get('total_questions', 0)}\n"
            
            metrics = ragas.get('metrics', {})
            for metric_name, values in metrics.items():
                if isinstance(values, dict):
                    mean = values.get('mean', 0)
                    std = values.get('std', 0)
                    md += f"- **{metric_name}:** {mean:.3f} (±{std:.3f})\n"
            md += "\n"
        
        md += "---\n\n"
    
    return md


def _generate_html_report(agent_results: List[Dict], model: str) -> str:
    """Generiert einen HTML-Report mit Bootstrap-Styling."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evaluation Report: {model}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ padding: 20px; background-color: #f8f9fa; }}
        .metric-card {{ margin: 10px 0; }}
        .agent-section {{ margin: 30px 0; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric-value {{ font-size: 1.5em; font-weight: bold; color: #0d6efd; }}
        .table {{ background: white; }}
        h1, h2, h3 {{ color: #333; }}
        .timestamp {{ color: #6c757d; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1 class="mb-4">📊 Evaluation Report: {model}</h1>
        <p class="timestamp">Generiert: {timestamp}</p>
        
        <div class="alert alert-info">
            <strong>Modell:</strong> {model}<br>
            <strong>Evaluierte Agenten:</strong> {len(agent_results)}
        </div>
        
        <h2 class="mt-5 mb-3">Zusammenfassung</h2>
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead class="table-dark">
                    <tr>
                        <th>Agent</th>
                        <th>Tool Exact Match</th>
                        <th>Tool F1</th>
                        <th>RAGAS Faithfulness</th>
                        <th>RAGAS Context Recall</th>
                        <th>Dauer</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Tabellen-Zeilen
    for result in agent_results:
        agent = result.get('agent_type', 'unknown')
        
        # Tool-Metriken
        tool_em = ""
        tool_f1 = ""
        if 'tools' in result and isinstance(result['tools'], dict):
            tool_em = f"{result['tools'].get('exact_match_rate', 0):.1%}"
            tool_f1 = f"{result['tools'].get('mean_f1', 0):.3f}"
        
        # RAGAS-Metriken
        ragas_faith = ""
        ragas_recall = ""
        if 'ragas' in result and isinstance(result['ragas'], dict):
            metrics = result['ragas'].get('metrics', {})
            ragas_faith = f"{metrics.get('faithfulness', {}).get('mean', 0):.3f}"
            ragas_recall = f"{metrics.get('context_recall', {}).get('mean', 0):.3f}"
        
        duration = format_duration(result.get('total_duration_seconds', 0))
        
        html += f"""
                    <tr>
                        <td><strong>{agent}</strong></td>
                        <td>{tool_em}</td>
                        <td>{tool_f1}</td>
                        <td>{ragas_faith}</td>
                        <td>{ragas_recall}</td>
                        <td>{duration}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <h2 class="mt-5 mb-3">Detaillierte Ergebnisse</h2>
"""
    
    # Detaillierte Ergebnisse pro Agent
    for result in agent_results:
        agent = result.get('agent_type', 'unknown')
        html += f"""
        <div class="agent-section">
            <h3>{agent.upper()}</h3>
"""
        
        # Tool-Evaluation
        if 'tools' in result and isinstance(result['tools'], dict):
            tools = result['tools']
            html += """
            <div class="row">
                <div class="col-md-6">
                    <h4>Tool-Evaluation</h4>
                    <div class="metric-card">
"""
            html += f"""
                        <p><strong>Szenarien:</strong> {tools.get('total_scenarios', 0)}</p>
                        <p><strong>Exact Match:</strong> <span class="metric-value">{tools.get('exact_match_rate', 0):.1%}</span> ({tools.get('exact_match_count', 0)} von {tools.get('total_scenarios', 0)})</p>
                        <p><strong>F1-Score:</strong> {tools.get('mean_f1', 0):.3f}</p>
                        <p><strong>Precision:</strong> {tools.get('mean_precision', 0):.3f}</p>
                        <p><strong>Recall:</strong> {tools.get('mean_recall', 0):.3f}</p>
"""
            html += """
                    </div>
                </div>
"""
        
        # RAGAS-Evaluation
        if 'ragas' in result and isinstance(result['ragas'], dict):
            ragas = result['ragas']
            html += """
                <div class="col-md-6">
                    <h4>RAGAS-Evaluation</h4>
                    <div class="metric-card">
"""
            html += f"<p><strong>Fragen:</strong> {ragas.get('total_questions', 0)}</p>\n"
            
            metrics = ragas.get('metrics', {})
            for metric_name, values in metrics.items():
                if isinstance(values, dict):
                    mean = values.get('mean', 0)
                    std = values.get('std', 0)
                    html += f"<p><strong>{metric_name}:</strong> <span class=\"metric-value\">{mean:.3f}</span> (±{std:.3f})</p>\n"
            
            html += """
                    </div>
                </div>
            </div>
"""
        
        html += """
        </div>
"""
    
    html += """
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""
    
    return html


def ensure_model_available(model: str, provider: str = "ollama") -> bool:
    """Prüft ob Modell verfügbar ist.
    
    Args:
        model: Modellname
        provider: 'ollama' oder 'openai'
    """
    if provider == "openai":
        # Bei OpenAI prüfen wir nur ob API-Key vorhanden ist
        return bool(settings.OPENAI_API_KEY)
    
    # Ollama: Prüfe ob Modell lokal verfügbar ist
    import requests
    try:
        response = requests.get(
            f"{settings.OLLAMA_BASE_URL}/api/tags",
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]
            return model in models
        return False
    except Exception:
        return False


def pull_model_if_needed(model: str, provider: str = "ollama") -> bool:
    """Lädt Modell herunter falls nicht vorhanden.
    
    Args:
        model: Modellname
        provider: 'ollama' oder 'openai'
    """
    if provider == "openai":
        # OpenAI: Prüfe API-Key und validiere Modell
        if not settings.OPENAI_API_KEY:
            print(f"❌ OPENAI_API_KEY nicht gesetzt! Bitte in .env konfigurieren.")
            return False
        
        # Validiere Modellname gegen bekannte OpenAI-Modelle
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            # Liste verfügbare Modelle
            models_response = client.models.list()
            available_models = [m.id for m in models_response.data]
            
            if model not in available_models:
                print(f"❌ Modell '{model}' ist nicht verfügbar in Ihrem OpenAI Account!")
                print(f"   Verfügbare Modelle: {', '.join([m for m in available_models if m.startswith('gpt')])[:100]}...")
                return False
            
            return True
        except Exception as e:
            print(f"❌ Fehler beim Validieren des OpenAI-Modells: {e}")
            return False
    
    # Ollama: Prüfe und lade bei Bedarf
    if ensure_model_available(model, provider):
        return True
    
    print(f"⬇️  Lade Modell {model} herunter...")
    import requests
    try:
        response = requests.post(
            f"{settings.OLLAMA_BASE_URL}/api/pull",
            json={"name": model, "stream": True},
            timeout=600,
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line)
                    status = data.get('status', '')
                    if 'completed' in data and 'total' in data:
                        completed = data['completed'] / (1024**3)
                        total = data['total'] / (1024**3)
                        percent = (data['completed'] / data['total'] * 100) if data['total'] > 0 else 0
                        print(f"\r{status}: {completed:.1f}GB / {total:.1f}GB ({percent:.0f}%)", end='', flush=True)
                    elif status:
                        print(f"\r{status}", end='', flush=True)
                except:
                    pass
        
        print()  # Neue Zeile nach Progress
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Fehler beim Laden von {model}: {e}")
        return False


def set_model_in_settings(model: str, provider: str = "ollama"):
    """Setzt das aktive Modell und den Provider in den Settings.
    
    Args:
        model: Modellname
        provider: 'ollama' oder 'openai'
    """
    os.environ["LLM_PROVIDER"] = provider
    settings.LLM_PROVIDER = provider

    if provider == "openai":
        os.environ["OPENAI_MODEL"] = model
        settings.OPENAI_MODEL = model
    elif provider == "anthropic":
        os.environ["ANTHROPIC_MODEL"] = model
        settings.ANTHROPIC_MODEL = model
    else:
        os.environ["OLLAMA_MODEL"] = model
        settings.OLLAMA_MODEL = model


def get_provider_for_model(model: str) -> str:
    """Ermittelt den Provider für ein Modell aus AVAILABLE_MODELS.
    
    Args:
        model: Modellname
        
    Returns:
        Provider-String ('ollama' oder 'openai')
    """
    if model in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[model].get("provider", "ollama")
    
    # Heuristik: GPT-Modelle sind OpenAI
    if model.startswith("gpt-"):
        return "openai"
    
    # Heuristik: Claude-Modelle sind Anthropic
    if model.startswith("claude-"):
        return "anthropic"
    
    # Default: Ollama
    return "ollama"


# ============================================================================
# TOOL-EVALUATION
# ============================================================================

def run_tool_evaluation(
    model: str,
    agent_type: str,
    output_dir: Path,
    limit: Optional[int] = None,
    test_ids: Optional[List[str]] = None,
    enable_trace: bool = False,
    provider: str = "ollama",
    resume: bool = True
) -> Dict[str, Any]:
    """
    Führt die Tool-Evaluation durch.
    
    Args:
        model: Modellname (Ollama oder OpenAI)
        agent_type: Agent-Typ (single, multi, etc.)
        output_dir: Ausgabeverzeichnis
        limit: Optionale Begrenzung der Test-Szenarien
        test_ids: Optionale Liste spezifischer Test-IDs (short_ids)
        enable_trace: Aktiviere Conversation-Trace-Logging (nur für Constrained Agent)
        provider: LLM-Provider ('ollama' oder 'openai')
        resume: Wenn True, versuche von Checkpoint fortzusetzen; wenn False, starte neu
    
    Returns:
        Dictionary mit Evaluationsergebnissen
    """
    import pickle
    
    print("\n" + "=" * 80)
    print("🔧 TOOL-EVALUATION")
    print("=" * 80)
    
    start_time = time.time()
    
    # Checkpoint-Pfad
    checkpoint_path = output_dir / "tool_eval_checkpoint.pkl"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setze Modell und Provider
    set_model_in_settings(model, provider)
    
    # Importiere nach Modell-Setting
    from eval.core.runner import (
        load_scenarios_from_tests,
        run_single_scenario,
        aggregate_results,
        save_report,
    )
    
    # Agent erstellen
    print(f"\n🤖 Initialisiere {agent_type}-Agent mit {model}...")
    
    settings.ENABLE_RAG_TOOL = False  # RAG not part of tool evaluation
    
    if agent_type == "single":
        from src.agent.react_agent import create_react_agent
        agent = create_react_agent(provider=provider)
    elif agent_type == "multi":
        from src.agent.multi.multi_agent_system import MultiAgentSystem
        # Force LLM routing for fair evaluation across all models
        agent = MultiAgentSystem(force_llm_routing=True)
        print("   🎯 LLM-only routing aktiviert für faire Modell-Vergleichbarkeit")
    elif agent_type == "constrained":
        from src.agent.constrained.constrained_agent import create_constrained_agent
        agent = create_constrained_agent()
    elif agent_type == "confirmation":
        from src.agent.confirmation.confirmation_agent import create_confirmation_agent
        agent = create_confirmation_agent()
    else:
        raise ValueError(f"Unbekannter Agent-Typ: {agent_type}")
    
    # Szenarien laden
    print("\n📂 Lade Evaluationsszenarien...")
    all_scenarios = load_scenarios_from_tests()
    
    # Filtere nach spezifischen Test-IDs falls angegeben
    if test_ids:
        scenarios = [s for s in all_scenarios if s.short_id in test_ids]
        print(f"   ✅ {len(scenarios)} von {len(all_scenarios)} Szenarien geladen (gefiltert nach Test-IDs)")
        if len(scenarios) < len(test_ids):
            found_ids = {s.short_id for s in scenarios}
            missing_ids = set(test_ids) - found_ids
            print(f"   ⚠️  Nicht gefundene Test-IDs: {', '.join(sorted(missing_ids))}")
    # Limit anwenden falls gesetzt (nur wenn keine spezifischen IDs)
    elif limit is not None and limit < len(all_scenarios):
        scenarios = all_scenarios[:limit]
        print(f"   ✅ {limit} von {len(all_scenarios)} Szenarien geladen (limitiert)")
    else:
        scenarios = all_scenarios
        print(f"   ✅ {len(scenarios)} Szenarien geladen")
    
    # Szenarien durchführen
    print(f"\n🚀 Starte Evaluation ({len(scenarios)} Szenarien)...")
    if enable_trace and agent_type == "constrained":
        print("   📝 Conversation-Trace-Logging aktiviert")
    print("-" * 80)
    
    # Versuche Checkpoint zu laden
    results = []
    start_idx = 0
    completed_scenario_ids = set()
    
    if checkpoint_path.exists() and resume:
        try:
            with open(checkpoint_path, 'rb') as f:
                checkpoint_data = pickle.load(f)
                
                # Validiere Checkpoint
                checkpoint_model = checkpoint_data.get('model_name')
                checkpoint_agent = checkpoint_data.get('agent_type')
                
                if checkpoint_model == model and checkpoint_agent == agent_type:
                    results = checkpoint_data.get('results', [])
                    completed_scenario_ids = checkpoint_data.get('completed_ids', set())
                    start_idx = len(results)
                    print(f"\n📂 Checkpoint gefunden: {start_idx} Szenarien bereits abgeschlossen")
                    print(f"   Modell: {checkpoint_model}, Agent: {checkpoint_agent}")
                    print(f"   Fortsetzung...\n")
                else:
                    print(f"\n⚠️ Checkpoint ist für anderes Modell/Agent ({checkpoint_model}/{checkpoint_agent})")
                    print(f"   Starte frisch...\n")
        except Exception as e:
            print(f"\n⚠️ Checkpoint konnte nicht geladen werden: {e}")
            print(f"   Starte frisch...\n")
    elif checkpoint_path.exists() and not resume:
        print(f"\n🗑️  Ignoriere vorhandenen Checkpoint (resume=False)")
        print(f"   Starte frisch...\n")
    
    for i, scenario in enumerate(scenarios, 1):
        # Überspringe bereits abgeschlossene Szenarien
        if scenario.short_id in completed_scenario_ids:
            continue
        # Kompakte Ausgabe mit Testname: alles in einer Zeile wie eval_old
        # Extrahiere kurzen Namen aus description (erste Zeile des Docstrings)
        test_name = ""
        if scenario.description:
            first_line = scenario.description.strip().split('\n')[0].strip()
            # Entferne "EASY:", "MEDIUM:", etc. und kürze auf max 40 Zeichen
            test_name = first_line.replace("EASY:", "").replace("MEDIUM:", "").replace("HARD:", "").replace("MULTI_STEP:", "").strip()
            if len(test_name) > 40:
                test_name = test_name[:37] + "..."
        
        display_name = f"{scenario.short_id} ({test_name})" if test_name else scenario.short_id
        print(f"[{i}/{len(scenarios)}] {display_name}...", end=" ", flush=True)
        
        try:
            result = run_single_scenario(agent, scenario, enable_trace=enable_trace)
            results.append(result)
            completed_scenario_ids.add(scenario.short_id)
            
            status = "✓" if result.exact_match else "✗"
            print(f"{status} (F1={result.tool_f1:.2f}, {result.latency_ms:.0f}ms)", end="")

            # Rate limit delay for Anthropic
            if provider == "anthropic":
                time.sleep(5)

            # Checkpoint nach jedem Szenario speichern
            checkpoint_data = {
                'model_name': model,
                'agent_type': agent_type,
                'results': results,
                'completed_ids': completed_scenario_ids,
                'last_scenario': scenario.short_id
            }
            with open(checkpoint_path, 'wb') as f:
                pickle.dump(checkpoint_data, f)
            print(f" 💾")
            
        except Exception as e:
            print(f"ERROR: {str(e)[:50]}")
    
    # Lösche Checkpoint nach erfolgreicher Evaluation
    if checkpoint_path.exists():
        checkpoint_path.unlink()
        print(f"\n🗑️  Checkpoint gelöscht (Evaluation abgeschlossen)")
    
    # Ergebnisse aggregieren
    from eval.core.runner import EvaluationReport
    from datetime import datetime
    
    metrics = aggregate_results(results)
    duration = time.time() - start_time
    
    # Report erstellen
    report = EvaluationReport(
        timestamp=datetime.now().isoformat(),
        model_name=model,
        model_version="1.0",
        total_scenarios=len(results),
        total_duration_seconds=duration,
        evaluation_config={
            "agent_type": agent_type,
            "limit": limit if limit else "all"
        },
        individual_results=results,
        aggregated_metrics=metrics
    )
    
    # Speichern
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Speichere mit save_report
    save_report(report, str(output_dir))
    
    # Speichere Conversation-Trace falls aktiviert (nur für Constrained Agent)
    if enable_trace and agent_type == "constrained" and hasattr(agent, 'save_conversation_trace'):
        trace_file = output_dir / "conversation_trace.json"
        agent.save_conversation_trace(str(trace_file))
        print(f"\n   📝 Conversation-Trace gespeichert: {trace_file}")
    
    # Metriken aus dem Report extrahieren
    exact_match_count = int(metrics.exact_match_rate * metrics.total_scenarios)
    
    # Zusammenfassung
    print("\n" + "-" * 80)
    print("📊 TOOL-EVALUATION ERGEBNISSE")
    print("-" * 80)
    print(f"   Modell:           {model}")
    print(f"   Agent:            {agent_type}")
    print(f"   Szenarien:        {report.total_scenarios}")
    print(f"   Exact Match:      {exact_match_count} ({metrics.exact_match_rate:.1%})")
    print(f"   Mean F1:          {metrics.mean_f1:.3f}")
    print(f"   Mean Precision:   {metrics.mean_precision:.3f}")
    print(f"   Mean Recall:      {metrics.mean_recall:.3f}")
    print(f"   Dauer:            {format_duration(duration)}")
    print(f"   Ergebnisse:       {output_dir}")
    
    return {
        "model": model,
        "agent_type": agent_type,
        "total_scenarios": report.total_scenarios,
        "exact_match_count": exact_match_count,
        "exact_match_rate": metrics.exact_match_rate,
        "mean_f1": metrics.mean_f1,
        "mean_precision": metrics.mean_precision,
        "mean_recall": metrics.mean_recall,
        "duration_seconds": duration,
        "by_difficulty": metrics.metrics_by_difficulty,
        "by_tool": metrics.metrics_by_tool,
        "output_path": str(output_dir),
    }


# ============================================================================
# RAGAS-EVALUATION
# ============================================================================

def run_rag_evaluation(
    model: str,
    agent_type: str,
    output_dir: Path,
    limit: Optional[int] = None,
    provider: str = "ollama",
    judge_provider: Optional[str] = None,
    judge_model: Optional[str] = None,
    judge_workers: int = 8,
    resume: bool = True
) -> Dict[str, Any]:
    """
    Führt die RAGAS-Evaluation durch.
    
    Args:
        model: Modellname (Ollama oder OpenAI)
        agent_type: Agent-Typ (single, multi, etc.)
        output_dir: Ausgabeverzeichnis
        limit: Optionale Begrenzung der Testfragen
        provider: LLM-Provider ('ollama' oder 'openai')
        judge_provider: Judge LLM Provider (None = auto-detect)
        judge_model: Judge-Modell (None = use default from settings)
        judge_workers: Anzahl paralleler Workers für Judge (default: 8)
        resume: Wenn True, versuche von Checkpoint fortzusetzen; wenn False, starte neu
    
    Returns:
        Dictionary mit RAGAS-Ergebnissen
    """
    print("\n" + "=" * 80)
    print("📚 RAGAS-EVALUATION")
    print("=" * 80)
    
    # Display judge configuration prominently
    judge_display = judge_model if judge_model else "qwen2.5:7b (default)"
    provider_display = judge_provider if judge_provider else "auto-detect"
    print(f"   🎯 RAGAS Judge:  {judge_display}")
    print(f"   📡 Judge Provider: {provider_display}")
    print(f"   ⚡ Workers:      {judge_workers}")
    print()
    
    start_time = time.time()
    
    # Setze Modell und Provider
    set_model_in_settings(model, provider)
    
    # RAGAS-Evaluation: Deaktiviere alle Tools außer RAG
    # Diese Tools verfälschen die RAG-Evaluation, da sie externe Quellen nutzen
    settings.ENABLE_DUCKDUCKGO = False
    settings.ENABLE_WEB_SCRAPER = False
    settings.ENABLE_EMAIL = False
    settings.ENABLE_KLIPS = False
    print("   🔒 Alle Tools außer RAG deaktiviert für reine RAG-Evaluation")
    
    # Importiere RAGAS-Komponenten
    from eval.ragas_eval.ragas_evaluation import (
        load_testset,
        generate_chatbot_responses,
        run_ragas_evaluation,
    )
    from langsmith import Client
    from config.settings import LANGSMITH_API_KEY, LANGSMITH_PROJECT
    
    # Prüfe LangSmith-Konfiguration
    if not LANGSMITH_API_KEY:
        print("⚠️  LANGSMITH_API_KEY nicht gesetzt - RAG-Kontext-Tracking deaktiviert")
    
    # Agent erstellen
    print(f"\n🤖 Initialisiere {agent_type}-Agent mit {model}...")
    
    if agent_type == "single":
        from src.agent.react_agent import create_react_agent
        agent = create_react_agent(provider=provider)
    elif agent_type == "multi":
        from src.agent.multi.multi_agent_system import MultiAgentSystem
        # Force LLM routing for fair evaluation across all models
        agent = MultiAgentSystem(force_llm_routing=True)
        print("   🎯 LLM-only routing aktiviert für faire Modell-Vergleichbarkeit")
    elif agent_type == "constrained":
        from src.agent.constrained.constrained_agent import create_constrained_agent
        agent = create_constrained_agent()
    elif agent_type == "confirmation":
        from src.agent.confirmation.confirmation_agent import create_confirmation_agent
        agent = create_confirmation_agent()
    else:
        raise ValueError(f"Unbekannter Agent-Typ: {agent_type}")
    
    # LangSmith Client
    langsmith_client = None
    if LANGSMITH_API_KEY:
        langsmith_client = Client()
        print(f"   ✅ LangSmith verbunden: {LANGSMITH_PROJECT}")

    # Log prompt caching status for Anthropic
    if provider == "anthropic":
        print("   ✅ Anthropic prompt caching aktiviert für System-Prompt")

    # Testset laden
    print("\n📂 Lade Testset...")
    testset_path = PROJECT_ROOT / "eval" / "ragas_eval" / "data" / "Testset.CSV"
    if not testset_path.exists():
        # Fallback-Pfad
        testset_path = PROJECT_ROOT / "data" / "Testset.CSV"
    
    test_df = load_testset(str(testset_path), limit=limit)
    
    # Antworten generieren
    print(f"\n🚀 Generiere Chatbot-Antworten ({len(test_df)} Fragen)...")
    dataset = generate_chatbot_responses(test_df, agent, langsmith_client, model_name=model, resume=resume, provider=provider)
    
    # RAGAS-Evaluation
    print("\n📊 Führe RAGAS-Evaluation durch...")
    results_df = run_ragas_evaluation(
        dataset, 
        model=model,
        judge_provider=judge_provider,
        judge_model=judge_model,
        max_workers=judge_workers
    )
    
    # Ergebnisse speichern - in model+agent/ragas Unterordner
    model_folder = get_model_folder_name(model)
    model_subdir = output_dir / f"{model_folder}_{agent_type}"
    ragas_dir = model_subdir / "ragas"
    ragas_dir.mkdir(parents=True, exist_ok=True)
    
    # CSV
    csv_path = ragas_dir / "ragas_results.csv"
    results_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    
    # JSON-Zusammenfassung
    duration = time.time() - start_time
    
    summary = {
        "model": model,
        "agent_type": agent_type,
        "total_questions": len(test_df),
        "duration_seconds": duration,
        "metrics": {},
        "output_path": str(csv_path),
    }
    
    # Metriken extrahieren
    for metric in ["faithfulness", "context_recall", "context_precision"]:
        if metric in results_df.columns:
            summary["metrics"][metric] = {
                "mean": float(results_df[metric].mean()),
                "std": float(results_df[metric].std()),
                "min": float(results_df[metric].min()),
                "max": float(results_df[metric].max()),
            }
    
    json_path = ragas_dir / "ragas_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Generiere detaillierte Reports (README + HTML)
    _generate_ragas_reports(results_df, test_df, summary, ragas_dir, model, agent_type, judge_provider, judge_model, judge_workers)
    
    # Zusammenfassung anzeigen
    print("\n" + "-" * 80)
    print("📊 RAGAS-EVALUATION ERGEBNISSE")
    print("-" * 80)
    print(f"   Modell:           {model}")
    print(f"   Agent:            {agent_type}")
    print(f"   Fragen:           {len(test_df)}")
    print(f"   Dauer:            {format_duration(duration)}")
    print()
    for metric, values in summary["metrics"].items():
        print(f"   {metric:20s}: {values['mean']:.3f} (±{values['std']:.3f})")
    print(f"\n   Ergebnisse:       {csv_path}")
    print(f"   README:           {ragas_dir / 'README.md'}")
    print(f"   HTML Report:      {ragas_dir / 'ragas_report.html'}")
    
    return summary


# ============================================================================
# VOLLSTÄNDIGE EVALUATION
# ============================================================================

def run_full_evaluation(
    model: str,
    agent_type: str = "single",
    mode: str = "all",
    rag_limit: Optional[int] = None,
    tool_limit: Optional[int] = None,
    output_dir: Optional[Path] = None,
    test_ids: Optional[List[str]] = None,
    enable_trace: bool = False,
    provider: Optional[str] = None,
    ragas_judge_provider: Optional[str] = None,
    ragas_judge_model: Optional[str] = None,
    ragas_workers: int = 8,
    resume: bool = True
) -> Dict[str, Any]:
    """
    Führt die vollständige Evaluation für ein Modell durch.
    
    Args:
        model: Modellname (Ollama oder OpenAI)
        agent_type: Agent-Typ
        mode: "all", "tools", oder "rag"
        rag_limit: Optionale Begrenzung für RAGAS-Testfragen
        tool_limit: Optionale Begrenzung für Tool-Szenarien
        output_dir: Optionales Ausgabeverzeichnis (wenn None, wird neuer Timestamp erstellt)
        test_ids: Optionale Liste spezifischer Test-IDs für Tool-Evaluation
        enable_trace: Aktiviere Conversation-Trace-Logging (nur für Constrained Agent)
        provider: LLM-Provider ('ollama' oder 'openai', wenn None wird automatisch ermittelt)
        ragas_judge_provider: RAGAS Judge Provider ('openai' oder 'ollama')
        ragas_judge_model: RAGAS Judge Modell
        ragas_workers: Anzahl paralleler Workers für RAGAS Judge
        resume: Wenn True, versuche von Checkpoint fortzusetzen; wenn False, starte neu
    
    Returns:
        Zusammenfassung aller Ergebnisse
    """
    # Provider automatisch ermitteln falls nicht angegeben
    if provider is None:
        provider = get_provider_for_model(model)
    
    model_safe = get_model_safe_name(model)  # Für Hauptordner (lesbar: llama3.1-8b)
    model_folder = get_model_folder_name(model)  # Für Unterordner (llama3_1_8b)
    
    # Wenn kein output_dir gegeben, erstelle neuen Timestamp-Ordner
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = OUTPUT_BASE / model_safe / timestamp
    else:
        timestamp = output_dir.name
    
    print("\n" + "=" * 80)
    print("🎯 VOLLSTÄNDIGE EVALUATION")
    print("=" * 80)
    print(f"   Modell:    {model}")
    print(f"   Provider:  {provider}")
    print(f"   Agent:     {agent_type}")
    print(f"   Modus:     {mode}")
    print(f"   Ausgabe:   {output_dir}")
    print("=" * 80)
    
    start_time = time.time()
    results = {
        "model": model,
        "provider": provider,
        "agent_type": agent_type,
        "mode": mode,
        "timestamp": timestamp,
        "output_dir": str(output_dir),
    }
    
    # Modell prüfen/laden
    print(f"\n⏳ Prüfe Modell {model} ({provider})...")
    if not pull_model_if_needed(model, provider):
        print(f"❌ Modell {model} nicht verfügbar!")
        return results
    print(f"   ✅ Modell bereit")
    
    # Tool-Evaluation
    if mode in ("all", "tools"):
        try:
            results["tools"] = run_tool_evaluation(
                model, 
                agent_type, 
                output_dir, 
                limit=tool_limit,
                test_ids=test_ids,
                enable_trace=enable_trace,
                provider=provider,
                resume=resume
            )
        except Exception as e:
            print(f"\n❌ Tool-Evaluation fehlgeschlagen: {e}")
            results["tools"] = {"error": str(e)}
    
    # RAGAS-Evaluation
    if mode in ("all", "rag"):
        try:
            results["ragas"] = run_rag_evaluation(
                model, 
                agent_type, 
                output_dir, 
                limit=rag_limit, 
                provider=provider,
                judge_provider=ragas_judge_provider,
                judge_model=ragas_judge_model,
                judge_workers=ragas_workers,
                resume=resume
            )
        except Exception as e:
            print(f"\n❌ RAGAS-Evaluation fehlgeschlagen: {e}")
            results["ragas"] = {"error": str(e)}
    
    # Gesamtdauer
    total_duration = time.time() - start_time
    results["total_duration_seconds"] = total_duration
    
    # Gesamtzusammenfassung im model_agent Unterordner speichern
    model_agent_dir = output_dir / f"{model_folder}_{agent_type}"
    model_agent_dir.mkdir(parents=True, exist_ok=True)
    
    summary_path = model_agent_dir / "summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    
    # CSV summary
    csv_path = model_agent_dir / "summary.csv"
    _write_summary_csv(csv_path, results)
    
    # Generiere Agent-spezifische Reports (MD + HTML)
    from eval.agent_report_generator import generate_agent_report
    generate_agent_report(model_agent_dir, results, model, agent_type)
    
    # Abschlussbericht
    print("\n" + "=" * 80)
    print("✅ EVALUATION ABGESCHLOSSEN")
    print("=" * 80)
    print(f"   Modell:           {model}")
    print(f"   Agent:            {agent_type}")
    print(f"   Gesamtdauer:      {format_duration(total_duration)}")
    print(f"   Ergebnisse:       {output_dir}")
    
    if "tools" in results and "exact_match_rate" in results.get("tools", {}):
        tools = results["tools"]
        print(f"\n   Tool-Metriken:")
        print(f"      Exact Match:   {tools['exact_match_rate']:.1%}")
        print(f"      Mean F1:       {tools['mean_f1']:.3f}")
        print(f"      Mean Precision:{tools['mean_precision']:.3f}")
        print(f"      Mean Recall:   {tools['mean_recall']:.3f}")
    
    if "ragas" in results and "metrics" in results.get("ragas", {}):
        metrics = results["ragas"]["metrics"]
        print(f"\n   RAGAS-Metriken:")
        for name, values in metrics.items():
            print(f"      {name:20s}: {values['mean']:.3f}")
    
    print("=" * 80)
    
    return results


def _write_summary_csv(path: Path, results: Dict[str, Any]):
    """Schreibt eine Zusammenfassung als CSV."""
    import csv
    
    headers = ["model", "agent_type", "exact_match_rate", "mean_f1", "mean_precision", "mean_recall",
               "faithfulness", "context_recall", "context_precision", "total_duration_s"]
    
    row = {
        "model": results.get("model", ""),
        "agent_type": results.get("agent_type", ""),
        "total_duration_s": results.get("total_duration_seconds", 0),
    }
    
    # Tool-Ergebnisse
    if "tools" in results and isinstance(results["tools"], dict):
        row["exact_match_rate"] = results["tools"].get("exact_match_rate", "")
        row["mean_f1"] = results["tools"].get("mean_f1", "")
        row["mean_precision"] = results["tools"].get("mean_precision", "")
        row["mean_recall"] = results["tools"].get("mean_recall", "")
    
    # RAGAS-Ergebnisse
    if "ragas" in results and isinstance(results["ragas"], dict):
        metrics = results["ragas"].get("metrics", {})
        row["faithfulness"] = metrics.get("faithfulness", {}).get("mean", "")
        row["context_recall"] = metrics.get("context_recall", {}).get("mean", "")
        row["context_precision"] = metrics.get("context_precision", {}).get("mean", "")
    
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerow(row)


# ============================================================================
# MULTI-AGENT EVALUATION
# ============================================================================

def run_all_agents_evaluation(
    model: str,
    mode: str = "all",
    rag_limit: Optional[int] = None,
    tool_limit: Optional[int] = None,
    agents: Optional[List[str]] = None,
    test_ids: Optional[List[str]] = None,
    enable_trace: bool = False,
    provider: Optional[str] = None,
    ragas_judge_provider: Optional[str] = None,
    ragas_judge_model: Optional[str] = None,
    ragas_workers: int = 8,
    resume: bool = True
) -> Dict[str, Any]:
    """
    Führt Evaluation für alle Agent-Typen durch.
    
    Args:
        model: Modellname (Ollama oder OpenAI)
        mode: Evaluationsmodus ('all', 'tools', 'rag')
        rag_limit: Optionale Begrenzung für RAGAS-Testfragen
        tool_limit: Optionale Begrenzung für Tool-Szenarien
        agents: Liste von Agenten (default: alle aus AGENT_TYPES)
        test_ids: Optionale Liste spezifischer Test-IDs für Tool-Evaluation
        enable_trace: Aktiviere Conversation-Trace-Logging (nur für Constrained Agent)
        provider: LLM-Provider ('ollama' oder 'openai', wenn None wird automatisch ermittelt)
        ragas_judge_provider: RAGAS Judge Provider
        ragas_judge_model: RAGAS Judge Modell
        ragas_workers: Anzahl paralleler Workers für RAGAS Judge
        resume: Wenn True, versuche von Checkpoint fortzusetzen; wenn False, starte neu
    """
    # Provider automatisch ermitteln falls nicht angegeben
    if provider is None:
        provider = get_provider_for_model(model)
    
    # Verwende custom Agenten-Liste oder alle
    agent_list = agents if agents else AGENT_TYPES
    
    print("\n" + "=" * 80)
    print("🎯 EVALUATION ALLER AGENT-ARCHITEKTUREN")
    print("=" * 80)
    print(f"   Modell:    {model}")
    print(f"   Provider:  {provider}")
    print(f"   Agents:    {agent_list}")
    print(f"   Modus:     {mode}")
    print("=" * 80)
    
    # Erstelle gemeinsamen Timestamp-Ordner für alle Agenten
    model_safe = get_model_safe_name(model)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shared_output_dir = OUTPUT_BASE / model_safe / timestamp
    shared_output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n📂 Gemeinsamer Ausgabe-Ordner: {shared_output_dir}")
    
    start_time = time.time()
    all_results = {}
    
    for agent_type in agent_list:
        print(f"\n{'#' * 80}")
        print(f"# AGENT: {agent_type}")
        print(f"{'#' * 80}")
        
        try:
            all_results[agent_type] = run_full_evaluation(
                model=model,
                agent_type=agent_type,
                mode=mode,
                rag_limit=rag_limit,
                tool_limit=tool_limit,
                output_dir=shared_output_dir,
                test_ids=test_ids,
                enable_trace=enable_trace,
                provider=provider,
                ragas_judge_provider=ragas_judge_provider,
                ragas_judge_model=ragas_judge_model,
                ragas_workers=ragas_workers,
                resume=resume
            )
        except Exception as e:
            print(f"\n❌ Evaluation für {agent_type} fehlgeschlagen: {e}")
            import traceback
            traceback.print_exc()
            all_results[agent_type] = {"error": str(e)}
    
    total_duration = time.time() - start_time
    
    # Generiere kombinierte Reports (Markdown + HTML)
    print("\n📊 Generiere kombinierte Reports...")
    try:
        generate_combined_report(shared_output_dir, model)
    except Exception as e:
        print(f"\n⚠️  Fehler beim Generieren des kombinierten Reports: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("✅ ALLE AGENT-EVALUATIONEN ABGESCHLOSSEN")
    print("=" * 80)
    print(f"   Gesamtdauer: {format_duration(total_duration)}")
    print(f"   Ergebnisse:  {shared_output_dir}")
    print(f"   📄 Report:   {shared_output_dir / 'evaluation_report.html'}")
    print("=" * 80)
    
    # 📱 Benachrichtigung senden
    try:
        from eval.utils.notify import notify_evaluation_complete
        notify_evaluation_complete(
            model=model,
            agents=agent_list,
            duration=format_duration(total_duration),
            results_path=str(shared_output_dir)
        )
    except Exception as e:
        print(f"\n⚠️  Benachrichtigung fehlgeschlagen: {e}")
    
    return all_results


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Vollständige Evaluation des WiSo-Chatbots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Einzelnes Modell, alle Agenten (Ollama)
  python -m eval.run_full_evaluation --model llama3.1:8b
  
  # OpenAI-Modell verwenden
  python -m eval.run_full_evaluation --model gpt-4o-mini --provider openai
  
  # Nur ein Agent
  python -m eval.run_full_evaluation --model llama3.1:8b --agent single
  
  # Nur Tool-Evaluation
  python -m eval.run_full_evaluation --model llama3.1:8b --mode tools
  
  # Mit Limits
  python -m eval.run_full_evaluation --model llama3.1:8b --tool-limit 20 --rag-limit 20
  
  # OpenAI GPT-4o mit Tool-Evaluation
  python -m eval.run_full_evaluation --model gpt-4o --provider openai --mode tools
        """
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="llama3.1:8b",
        help=f"Modellname (verfügbar: {', '.join(AVAILABLE_MODELS.keys())})"
    )
    
    parser.add_argument(
        "--provider", "-p",
        type=str,
        choices=LLM_PROVIDERS,
        default=None,
        help="LLM-Provider: 'ollama' (lokal), 'openai' oder 'anthropic' (API). Wenn nicht angegeben, wird automatisch ermittelt."
    )
    
    parser.add_argument(
        "--mode",
        type=str,
        choices=["all", "tools", "rag"],
        default="all",
        help="Evaluationsmodus: all (beide), tools, oder rag"
    )
    
    parser.add_argument(
        "--agent", "-a",
        type=str,
        choices=AGENT_TYPES + ["all"],
        default="all",
        help=f"Agent-Typ: {', '.join(AGENT_TYPES)}, oder 'all' für alle (default: all)"
    )
    
    parser.add_argument(
        "--agents",
        type=str,
        nargs="+",
        choices=AGENT_TYPES,
        help=f"Spezifische Agenten (Liste): z.B. --agents single confirmation"
    )
    
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Evaluiere alle konfigurierten Modelle"
    )
    
    parser.add_argument(
        "--rag-limit",
        type=int,
        default=DEFAULT_RAG_LIMIT,
        help=f"Begrenze Anzahl der RAGAS-Testfragen (default: {DEFAULT_RAG_LIMIT}, max: 116)"
    )
    
    parser.add_argument(
        "--tool-limit",
        type=int,
        default=None,
        help="Begrenze Anzahl der Tool-Test-Szenarien (default: alle 100)"
    )
    
    parser.add_argument(
        "--test-ids",
        type=str,
        nargs="+",
        default=None,
        help="Spezifische Test-IDs für Tool-Evaluation (z.B. s8 s21 s24)"
    )
    
    parser.add_argument(
        "--enable-trace",
        action="store_true",
        help="Aktiviere Conversation-Trace-Logging (nur für Constrained Agent)"
    )
    
    parser.add_argument(
        "--ragas-judge-provider",
        type=str,
        choices=["openai", "ollama"],
        default=None,
        help="RAGAS Judge Provider (openai oder ollama, default: auto-detect)"
    )
    
    parser.add_argument(
        "--ragas-judge-model",
        type=str,
        default=None,
        help="RAGAS Judge Modell (default: gpt-4o-mini für OpenAI, qwen2.5:7b für Ollama)"
    )
    
    parser.add_argument(
        "--ragas-workers",
        type=int,
        default=8,
        help="Anzahl paralleler Workers für RAGAS Judge (default: 8, OpenAI empfohlen: 150)"
    )
    
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignoriere vorhandene Checkpoints und starte Evaluation neu"
    )
    
    args = parser.parse_args()
    
    try:
        # Bestimme welche Modelle evaluiert werden sollen
        models_to_eval = list(AVAILABLE_MODELS.keys()) if args.all_models else [args.model]
        
        for model in models_to_eval:
            # Provider ermitteln (aus Argument oder automatisch)
            provider = args.provider if args.provider else get_provider_for_model(model)
            
            if len(models_to_eval) > 1:
                print("\n" + "#" * 80)
                print(f"# MODELL: {model} ({provider})")
                print("#" * 80)
            
            if args.agents:
                # Spezifische Agenten evaluieren
                run_all_agents_evaluation(
                    model=model,
                    mode=args.mode,
                    rag_limit=args.rag_limit,
                    tool_limit=args.tool_limit,
                    agents=args.agents,
                    test_ids=args.test_ids,
                    enable_trace=args.enable_trace,
                    provider=provider,
                    ragas_judge_provider=args.ragas_judge_provider,
                    ragas_judge_model=args.ragas_judge_model,
                    ragas_workers=args.ragas_workers,
                    resume=not args.no_resume
                )
            elif args.agent == "all":
                # Alle Agent-Architekturen evaluieren
                run_all_agents_evaluation(
                    model=model,
                    mode=args.mode,
                    rag_limit=args.rag_limit,
                    tool_limit=args.tool_limit,
                    test_ids=args.test_ids,
                    enable_trace=args.enable_trace,
                    provider=provider,
                    ragas_judge_provider=args.ragas_judge_provider,
                    ragas_judge_model=args.ragas_judge_model,
                    ragas_workers=args.ragas_workers,
                    resume=not args.no_resume
                )
            else:
                # Einzelnen Agent evaluieren
                run_full_evaluation(
                    model=model,
                    agent_type=args.agent,
                    mode=args.mode,
                    rag_limit=args.rag_limit,
                    tool_limit=args.tool_limit,
                    test_ids=args.test_ids,
                    enable_trace=args.enable_trace,
                    provider=provider,
                    ragas_judge_provider=args.ragas_judge_provider,
                    ragas_judge_model=args.ragas_judge_model,
                    ragas_workers=args.ragas_workers,
                    resume=not args.no_resume
                )
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation abgebrochen!")
        sys.exit(1)


if __name__ == "__main__":
    # Logging einrichten
    setup_logging(level="INFO")
    
    main()
