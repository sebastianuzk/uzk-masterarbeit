"""
Generator für Agent-spezifische Reports (Markdown und HTML).

Erstellt übersichtliche Reports für einzelne Agent-Evaluationen.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from eval.utils.formatting import format_duration


def generate_agent_report(agent_dir: Path, results: Dict[str, Any], model: str, agent_type: str):
    """Generiert Markdown- und HTML-Report für einen einzelnen Agenten."""
    
    # Markdown Report
    md_content = f"""# Agent Evaluation Report: {agent_type}

**Modell:** {model}  
**Agent-Typ:** {agent_type}  
**Generiert:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Dauer:** {format_duration(results.get('total_duration_seconds', 0))}

---

"""
    
    # Tool-Evaluation Ergebnisse
    if "tools" in results and "error" not in results["tools"]:
        tools = results["tools"]
        md_content += f"""## Tool-Evaluation

### Gesamtmetriken
- **Szenarien:** {tools.get('total_scenarios', 0)}
- **Task Success Rate:** {tools.get('exact_match_rate', 0):.1%} ({tools.get('exact_match_count', 0)} von {tools.get('total_scenarios', 0)})
- **F1-Score:** {tools.get('mean_f1', 0):.3f}
- **Precision:** {tools.get('mean_precision', 0):.3f}
- **Recall:** {tools.get('mean_recall', 0):.3f}
- **Dauer:** {format_duration(tools.get('duration_seconds', 0))}

### Nach Schwierigkeit

| Schwierigkeit | Anzahl | F1-Score | Task Success Rate | Argument Accuracy |
|---------------|--------|----------|-------------|-------------------|
"""

        thesis_order = ["Easy", "Medium", "Hard"]
        hard_order = ["Standard", "Multi_step", "Multi_tool", "Negative", "EdgeCases"]

        by_top = tools.get('by_thesis_difficulty') or tools.get('by_difficulty', {})
        order = thesis_order if tools.get('by_thesis_difficulty') else list(by_top.keys())
        for diff in order:
            metrics = by_top.get(diff)
            if not metrics:
                continue
            arg_acc = metrics.get('mean_argument_accuracy', 0) or 0
            md_content += f"| {diff} | {metrics.get('count', 0)} | {metrics.get('mean_f1', 0):.3f} | {metrics.get('exact_match_rate', 0):.1%} | {arg_acc:.1%} |\n"

        by_hard = tools.get('by_hard_subtype') or {}
        if by_hard:
            md_content += "\n### Nach Hard-Typ\n\n"
            md_content += "| Hard-Typ | Anzahl | F1-Score | Task Success Rate | Argument Accuracy |\n"
            md_content += "|---------------|--------|----------|-------------|-------------------|\n"
            for cat in hard_order:
                metrics = by_hard.get(cat)
                if not metrics:
                    continue
                arg_acc = metrics.get('mean_argument_accuracy', 0) or 0
                md_content += f"| {cat} | {metrics.get('count', 0)} | {metrics.get('mean_f1', 0):.3f} | {metrics.get('exact_match_rate', 0):.1%} | {arg_acc:.1%} |\n"

        md_content += "\n"
    
    # RAGAS-Evaluation Ergebnisse
    if "ragas" in results and "error" not in results["ragas"]:
        ragas = results["ragas"]
        md_content += f"""## RAGAS-Evaluation

### Metriken
- **Fragen:** {ragas.get('total_questions', 0)}
- **Dauer:** {format_duration(ragas.get('duration_seconds', 0))}

| Metrik | Mittelwert | Std.-Abw. | Min | Max |
|--------|------------|-----------|-----|-----|
"""
        
        metrics = ragas.get('metrics', {})
        for name, values in metrics.items():
            md_content += f"| {name} | {values.get('mean', 0):.3f} | {values.get('std', 0):.3f} | {values.get('min', 0):.3f} | {values.get('max', 0):.3f} |\n"
        
        md_content += "\n"
    
    # Links zu Details
    md_content += f"""---

## Detaillierte Ergebnisse

- [Tool-Evaluation Details](tools/report.md)
- [RAGAS-Ergebnisse](ragas/ragas_results.csv)
- [JSON-Daten](summary.json)
"""
    
    # Speichere Markdown
    md_path = agent_dir / "agent_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    
    # HTML Report
    html_content = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent Report: {agent_type}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header .meta {{ opacity: 0.9; font-size: 14px; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .section h2 {{
            margin-top: 0;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .metric {{
            display: inline-block;
            margin: 10px 15px 10px 0;
        }}
        .metric-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #667eea;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-info {{ background: #d1ecf1; color: #0c5460; }}
        .links {{ margin-top: 20px; }}
        .links a {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 8px 16px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-size: 14px;
        }}
        .links a:hover {{ background: #5568d3; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Agent Evaluation: {agent_type}</h1>
        <div class="meta">
            <strong>Modell:</strong> {model} | 
            <strong>Generiert:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            <strong>Gesamtdauer:</strong> {format_duration(results.get('total_duration_seconds', 0))}
        </div>
    </div>
"""
    
    # Tool-Evaluation
    if "tools" in results and "error" not in results["tools"]:
        tools = results["tools"]
        html_content += f"""
    <div class="section">
        <h2>Tool-Evaluation</h2>
        <div>
            <div class="metric">
                <div class="metric-label">Task Success Rate</div>
                <div class="metric-value">{tools.get('exact_match_rate', 0):.1%}</div>
            </div>
            <div class="metric">
                <div class="metric-label">F1-Score</div>
                <div class="metric-value">{tools.get('mean_f1', 0):.3f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Precision</div>
                <div class="metric-value">{tools.get('mean_precision', 0):.3f}</div>
            </div>
            <div class="metric">
                <div class="metric-label">Recall</div>
                <div class="metric-value">{tools.get('mean_recall', 0):.3f}</div>
            </div>
        </div>
        
        <h3>Nach Schwierigkeit</h3>
        <table>
            <thead>
                <tr>
                    <th>Schwierigkeit</th>
                    <th>Anzahl</th>
                    <th>F1-Score</th>
                    <th>Exact Match</th>
                    <th>Argument Accuracy</th>
                </tr>
            </thead>
            <tbody>
"""
        
        by_top = tools.get('by_thesis_difficulty') or tools.get('by_difficulty', {})
        order = ["Easy", "Medium", "Hard"] if tools.get('by_thesis_difficulty') else list(by_top.keys())
        for diff in order:
            metrics = by_top.get(diff)
            if not metrics:
                continue
            arg_acc = metrics.get('mean_argument_accuracy', 0) or 0
            html_content += f"""
                <tr>
                    <td><span class="badge badge-info">{diff}</span></td>
                    <td>{metrics.get('count', 0)}</td>
                    <td>{metrics.get('mean_f1', 0):.3f}</td>
                    <td>{metrics.get('exact_match_rate', 0):.1%}</td>
                    <td>{arg_acc:.1%}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
"""

        by_hard = tools.get('by_hard_subtype') or {}
        if by_hard:
            html_content += """
        <h3>Nach Hard-Typ</h3>
        <table>
            <thead>
                <tr>
                    <th>Hard-Typ</th>
                    <th>Anzahl</th>
                    <th>F1-Score</th>
                    <th>Exact Match</th>
                    <th>Argument Accuracy</th>
                </tr>
            </thead>
            <tbody>
"""
            for cat in ["Standard", "Multi_step", "Multi_tool", "Negative", "EdgeCases"]:
                metrics = by_hard.get(cat)
                if not metrics:
                    continue
                arg_acc = metrics.get('mean_argument_accuracy', 0) or 0
                html_content += f"""
                <tr>
                    <td><span class="badge badge-info">{cat}</span></td>
                    <td>{metrics.get('count', 0)}</td>
                    <td>{metrics.get('mean_f1', 0):.3f}</td>
                    <td>{metrics.get('exact_match_rate', 0):.1%}</td>
                    <td>{arg_acc:.1%}</td>
                </tr>
"""
            html_content += """
            </tbody>
        </table>
"""

        html_content += """
    </div>
"""
    
    # RAGAS-Evaluation
    if "ragas" in results and "error" not in results["ragas"]:
        ragas = results["ragas"]
        html_content += f"""
    <div class="section">
        <h2>RAGAS-Evaluation</h2>
        <p><strong>Fragen evaluiert:</strong> {ragas.get('total_questions', 0)}</p>
        
        <table>
            <thead>
                <tr>
                    <th>Metrik</th>
                    <th>Mittelwert</th>
                    <th>Std.-Abw.</th>
                    <th>Min</th>
                    <th>Max</th>
                </tr>
            </thead>
            <tbody>
"""
        
        metrics = ragas.get('metrics', {})
        for name, values in metrics.items():
            html_content += f"""
                <tr>
                    <td><strong>{name}</strong></td>
                    <td>{values.get('mean', 0):.3f}</td>
                    <td>{values.get('std', 0):.3f}</td>
                    <td>{values.get('min', 0):.3f}</td>
                    <td>{values.get('max', 0):.3f}</td>
                </tr>
"""
        
        html_content += """
            </tbody>
        </table>
    </div>
"""
    
    # Links
    html_content += f"""
    <div class="section">
        <h2>Detaillierte Ergebnisse</h2>
        <div class="links">
            <a href="tools/report.md">📊 Tool-Details</a>
            <a href="ragas/ragas_results.csv">📈 RAGAS-Ergebnisse</a>
            <a href="summary.json">📋 JSON-Daten</a>
        </div>
    </div>
    
</body>
</html>
"""
    
    # Speichere HTML
    html_path = agent_dir / "agent_report.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"   📄 Agent-Reports: {md_path.name}, {html_path.name}")
