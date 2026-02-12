#!/usr/bin/env python3
"""
Detaillierter Report-Generator für Evaluation-Ergebnisse

Erstellt eine interaktive HTML-Website und detaillierte Markdown-Datei
mit umfassender Analyse der Evaluationsergebnisse, inkl. negativer Tests.

Verwendung:
    python eval/utils/generate_detailed_report.py <results.json>
    python eval/utils/generate_detailed_report.py data/eval/final/gpt-oss-20b/.../tools/results.json
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from eval.utils.formatting import format_duration


def analyze_negative_tests(results: List[Dict]) -> Dict[str, Any]:
    """
    Analysiert negative Tests (wo keine Tools aufgerufen werden sollten).
    
    Negative Tests sind:
    1. expected_tools ist leer (kein Tool sollte aufgerufen werden)
    2. forbidden_tools_called ist nicht leer (Tool wurde fälschlicherweise aufgerufen)
    """
    negative_tests = []
    correct_rejections = 0
    false_positives = 0
    
    for result in results:
        is_negative = len(result['expected_tools']) == 0
        
        if is_negative:
            test_data = {
                'short_id': result['short_id'],
                'scenario_id': result['scenario_id'],
                'user_prompt': result['user_prompt'],
                'actual_tools': result['actual_tools'],
                'forbidden_tools_called': result['forbidden_tools_called'],
                'correct': len(result['actual_tools']) == 0,
                'difficulty': result['difficulty'],
                'tool': result['tool']
            }
            negative_tests.append(test_data)
            
            if len(result['actual_tools']) == 0:
                correct_rejections += 1
            else:
                false_positives += 1
    
    total_negative = len(negative_tests)
    accuracy = correct_rejections / total_negative if total_negative > 0 else 0
    
    return {
        'total': total_negative,
        'correct_rejections': correct_rejections,
        'false_positives': false_positives,
        'accuracy': accuracy,
        'tests': negative_tests
    }


def analyze_tool_usage(results: List[Dict]) -> Dict[str, Any]:
    """Analysiert Tool-Nutzungsmuster detailliert."""
    tool_stats = {}
    
    for result in results:
        for tool in result['expected_tools']:
            if tool not in tool_stats:
                tool_stats[tool] = {
                    'expected': 0,
                    'correct': 0,
                    'missed': 0,
                    'total_latency': 0,
                    'count': 0
                }
            
            tool_stats[tool]['expected'] += 1
            if tool in result['correct_tools']:
                tool_stats[tool]['correct'] += 1
            else:
                tool_stats[tool]['missed'] += 1
            
            if tool in result['actual_tools']:
                tool_stats[tool]['total_latency'] += result['latency_ms']
                tool_stats[tool]['count'] += 1
    
    # Berechne Durchschnitte
    for tool, stats in tool_stats.items():
        stats['recall'] = stats['correct'] / stats['expected'] if stats['expected'] > 0 else 0
        stats['avg_latency'] = stats['total_latency'] / stats['count'] if stats['count'] > 0 else 0
    
    return tool_stats


def analyze_error_patterns(results: List[Dict]) -> Dict[str, List[Dict]]:
    """Gruppiert Fehler nach Muster."""
    patterns = {
        'missing_tools': [],
        'extra_tools': [],
        'wrong_tools': [],
        'timeout': [],
        'errors': []
    }
    
    for result in results:
        if not result['exact_match']:
            # Fehlende Tools
            missing = set(result['expected_tools']) - set(result['actual_tools'])
            if missing:
                patterns['missing_tools'].append({
                    'short_id': result['short_id'],
                    'missing': list(missing),
                    'prompt': result['user_prompt'],
                    'difficulty': result['difficulty']
                })
            
            # Extra Tools
            extra = set(result['actual_tools']) - set(result['expected_tools'])
            if extra and len(result['expected_tools']) > 0:  # Nur wenn Tools erwartet wurden
                patterns['extra_tools'].append({
                    'short_id': result['short_id'],
                    'extra': list(extra),
                    'prompt': result['user_prompt'],
                    'difficulty': result['difficulty']
                })
            
            # Timeouts (sehr lange Latenz)
            if result['latency_ms'] > 60000:  # > 60 Sekunden
                patterns['timeout'].append({
                    'short_id': result['short_id'],
                    'latency': result['latency_ms'],
                    'prompt': result['user_prompt']
                })
            
            # Runtime Errors
            if result.get('error'):
                patterns['errors'].append({
                    'short_id': result['short_id'],
                    'error': result['error'],
                    'prompt': result['user_prompt']
                })
    
    return patterns


def generate_html_report(data: Dict, output_path: Path):
    """Generiert eine interaktive HTML-Website mit den Ergebnissen."""
    
    agg = data['aggregated_metrics']
    results = data['individual_results']
    negative = analyze_negative_tests(results)
    tool_usage = analyze_tool_usage(results)
    error_patterns = analyze_error_patterns(results)
    
    # Zähle positive Tests
    positive_tests = [r for r in results if len(r['expected_tools']) > 0]
    negative_tests_list = [r for r in results if len(r['expected_tools']) == 0]
    
    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Detaillierter Evaluation Report - {data['model_name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f7fa;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 0;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        header .meta {{
            opacity: 0.9;
            font-size: 1.1em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        
        .stat-card h3 {{
            color: #667eea;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .stat-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2d3748;
        }}
        
        .stat-card .label {{
            color: #718096;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .section {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .section h2 {{
            color: #2d3748;
            font-size: 1.8em;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        
        th {{
            background: #f7fafc;
            font-weight: 600;
            color: #4a5568;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}
        
        tr:hover {{
            background: #f7fafc;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        
        .badge.success {{
            background: #c6f6d5;
            color: #22543d;
        }}
        
        .badge.error {{
            background: #fed7d7;
            color: #742a2a;
        }}
        
        .badge.warning {{
            background: #feebc8;
            color: #7c2d12;
        }}
        
        .badge.info {{
            background: #bee3f8;
            color: #2c5282;
        }}
        
        .progress-bar {{
            width: 100%;
            height: 8px;
            background: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
        }}
        
        .test-card {{
            background: #f7fafc;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            border-left: 4px solid #cbd5e0;
        }}
        
        .test-card.negative {{
            border-left-color: #f56565;
        }}
        
        .test-card.positive {{
            border-left-color: #48bb78;
        }}
        
        .test-card h4 {{
            color: #2d3748;
            margin-bottom: 8px;
        }}
        
        .test-card .prompt {{
            color: #4a5568;
            font-style: italic;
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 4px;
        }}
        
        .test-card .details {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }}
        
        .test-card .detail-item {{
            font-size: 0.9em;
        }}
        
        .test-card .detail-item strong {{
            color: #4a5568;
        }}
        
        code {{
            background: #edf2f7;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        .tabs {{
            display: flex;
            border-bottom: 2px solid #e2e8f0;
            margin-bottom: 20px;
        }}
        
        .tab {{
            padding: 12px 24px;
            cursor: pointer;
            border: none;
            background: none;
            font-size: 1em;
            color: #718096;
            transition: all 0.3s;
        }}
        
        .tab:hover {{
            color: #667eea;
        }}
        
        .tab.active {{
            color: #667eea;
            border-bottom: 3px solid #667eea;
            font-weight: 600;
        }}
        
        .tab-content {{
            display: none;
        }}
        
        .tab-content.active {{
            display: block;
        }}
        
        .metric-box {{
            display: inline-block;
            padding: 8px 16px;
            background: #edf2f7;
            border-radius: 6px;
            margin-right: 10px;
            margin-bottom: 10px;
        }}
        
        .metric-box strong {{
            color: #667eea;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            header h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Detaillierter Evaluation Report</h1>
            <div class="meta">
                <strong>Modell:</strong> {data['model_name']} ({data['model_version']}) | 
                <strong>Generiert:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
                <strong>Dauer:</strong> {format_duration(data['total_duration_seconds'])}
            </div>
        </header>
        
        <!-- Übersicht -->
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Gesamt-Szenarien</h3>
                <div class="value">{data['total_scenarios']}</div>
                <div class="label">Test-Fälle</div>
            </div>
            
            <div class="stat-card">
                <h3>Exact Match</h3>
                <div class="value">{agg['exact_match_rate']:.1%}</div>
                <div class="label">{int(data['total_scenarios'] * agg['exact_match_rate'])} / {data['total_scenarios']}</div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {agg['exact_match_rate']*100}%"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>F1-Score</h3>
                <div class="value">{agg['mean_f1']:.3f}</div>
                <div class="label">Precision: {agg['mean_precision']:.3f} | Recall: {agg['mean_recall']:.3f}</div>
            </div>
            
            <div class="stat-card">
                <h3>Negative Tests</h3>
                <div class="value">{negative['accuracy']:.1%}</div>
                <div class="label">{negative['correct_rejections']} / {negative['total']} korrekt abgelehnt</div>
            </div>
        </div>
        
        <!-- Test-Typen Übersicht -->
        <div class="section">
            <h2>🔍 Test-Typen Übersicht</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <h3>Positive Tests</h3>
                    <div class="value">{len(positive_tests)}</div>
                    <div class="label">Tool-Aufruf erwartet</div>
                </div>
                <div class="stat-card">
                    <h3>Negative Tests</h3>
                    <div class="value">{len(negative_tests_list)}</div>
                    <div class="label">Kein Tool-Aufruf erwartet</div>
                </div>
            </div>
            <p style="margin-top: 20px; color: #4a5568;">
                <strong>Positive Tests:</strong> Szenarien, bei denen mindestens ein Tool aufgerufen werden sollte.<br>
                <strong>Negative Tests:</strong> Szenarien, bei denen KEIN Tool aufgerufen werden sollte (z.B. zu vage Anfragen, fehlende Daten).
            </p>
        </div>
        
        <!-- Negative Tests Detailanalyse -->
        <div class="section">
            <h2>❌ Negative Tests - Detailanalyse</h2>
            <p style="margin-bottom: 20px; color: #4a5568;">
                Negative Tests prüfen, ob der Agent korrekt erkennt, wann KEIN Tool aufgerufen werden sollte.
                Dies ist wichtig, um falsche Tool-Aufrufe bei unvollständigen oder vagen Anfragen zu vermeiden.
            </p>
            
            <div class="metric-box">
                <strong>Gesamt:</strong> {negative['total']} Tests
            </div>
            <div class="metric-box">
                <strong>Korrekt abgelehnt:</strong> {negative['correct_rejections']} ({negative['accuracy']:.1%})
            </div>
            <div class="metric-box">
                <strong>Falsch-Positive:</strong> {negative['false_positives']}
            </div>
"""
    
    # Falsch-Positive Tests anzeigen
    if negative['false_positives'] > 0:
        html += """
            <h3 style="margin-top: 30px; color: #c53030;">⚠️ Falsch-Positive (Tool fälschlicherweise aufgerufen)</h3>
"""
        for test in negative['tests']:
            if not test['correct']:
                html += f"""
            <div class="test-card negative">
                <h4>{test['short_id']} - {test['scenario_id']}</h4>
                <div class="prompt">"{test['user_prompt'][:200]}{'...' if len(test['user_prompt']) > 200 else ''}"</div>
                <div class="details">
                    <div class="detail-item"><strong>Schwierigkeit:</strong> {test['difficulty']}</div>
                    <div class="detail-item"><strong>Tool-Kategorie:</strong> {test['tool']}</div>
                    <div class="detail-item"><strong>Aufgerufene Tools:</strong> <code>{', '.join(test['actual_tools'])}</code></div>
                </div>
            </div>
"""
    
    # Korrekte Ablehnungen
    html += f"""
            <h3 style="margin-top: 30px; color: #38a169;">✅ Korrekte Ablehnungen ({negative['correct_rejections']})</h3>
            <p style="color: #4a5568; margin-bottom: 15px;">Szenarien, bei denen der Agent korrekt erkannt hat, dass kein Tool aufgerufen werden sollte.</p>
"""
    
    correct_count = 0
    for test in negative['tests']:
        if test['correct']:
            correct_count += 1
            if correct_count <= 10:  # Nur erste 10 anzeigen
                html += f"""
            <div class="test-card positive">
                <h4>{test['short_id']} - {test['scenario_id']}</h4>
                <div class="prompt">"{test['user_prompt'][:200]}{'...' if len(test['user_prompt']) > 200 else ''}"</div>
                <div class="details">
                    <div class="detail-item"><strong>Schwierigkeit:</strong> {test['difficulty']}</div>
                    <div class="detail-item"><strong>Tool-Kategorie:</strong> {test['tool']}</div>
                    <div class="detail-item"><span class="badge success">Korrekt abgelehnt</span></div>
                </div>
            </div>
"""
    
    if correct_count > 10:
        html += f"""
            <p style="color: #718096; font-style: italic; margin-top: 10px;">
                ... und {correct_count - 10} weitere korrekte Ablehnungen
            </p>
"""
    
    html += """
        </div>
        
        <!-- Tool-Nutzung -->
        <div class="section">
            <h2>🔧 Tool-Nutzungsstatistik</h2>
            <table>
                <thead>
                    <tr>
                        <th>Tool</th>
                        <th>Erwartet</th>
                        <th>Korrekt</th>
                        <th>Verpasst</th>
                        <th>Recall</th>
                        <th>Ø Latenz</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for tool, stats in sorted(tool_usage.items(), key=lambda x: x[1]['recall'], reverse=True):
        recall_pct = stats['recall'] * 100
        badge_class = 'success' if stats['recall'] >= 0.9 else 'warning' if stats['recall'] >= 0.7 else 'error'
        html += f"""
                    <tr>
                        <td><code>{tool}</code></td>
                        <td>{stats['expected']}</td>
                        <td>{stats['correct']}</td>
                        <td>{stats['missed']}</td>
                        <td><span class="badge {badge_class}">{recall_pct:.1f}%</span></td>
                        <td>{format_duration(stats['avg_latency'] / 1000)}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <!-- Fehler-Muster -->
        <div class="section">
            <h2>🐛 Fehler-Muster</h2>
            
            <div class="tabs">
                <button class="tab active" onclick="showTab('missing')">Fehlende Tools ({len(error_patterns['missing_tools'])})</button>
                <button class="tab" onclick="showTab('extra')">Extra Tools ({len(error_patterns['extra_tools'])})</button>
                <button class="tab" onclick="showTab('timeout')">Timeouts ({len(error_patterns['timeout'])})</button>
                <button class="tab" onclick="showTab('errors')">Runtime Errors ({len(error_patterns['errors'])})</button>
            </div>
"""
    
    # Tab: Fehlende Tools
    html += f"""
            <div id="missing" class="tab-content active">
                <h3>Fehlende Tools</h3>
                <p style="color: #4a5568; margin-bottom: 20px;">
                    Szenarien, bei denen erwartete Tools nicht aufgerufen wurden.
                </p>
"""
    for error in error_patterns['missing_tools'][:20]:
        html += f"""
                <div class="test-card">
                    <h4>{error['short_id']} - <span class="badge error">Fehlende Tools: {', '.join(error['missing'])}</span></h4>
                    <div class="prompt">"{error['prompt'][:200]}{'...' if len(error['prompt']) > 200 else ''}"</div>
                    <div class="details">
                        <div class="detail-item"><strong>Schwierigkeit:</strong> {error['difficulty']}</div>
                    </div>
                </div>
"""
    
    # Tab: Extra Tools
    html += f"""
            </div>
            
            <div id="extra" class="tab-content">
                <h3>Extra Tools</h3>
                <p style="color: #4a5568; margin-bottom: 20px;">
                    Szenarien, bei denen zusätzliche, nicht erwartete Tools aufgerufen wurden.
                </p>
"""
    for error in error_patterns['extra_tools'][:20]:
        html += f"""
                <div class="test-card">
                    <h4>{error['short_id']} - <span class="badge warning">Extra Tools: {', '.join(error['extra'])}</span></h4>
                    <div class="prompt">"{error['prompt'][:200]}{'...' if len(error['prompt']) > 200 else ''}"</div>
                    <div class="details">
                        <div class="detail-item"><strong>Schwierigkeit:</strong> {error['difficulty']}</div>
                    </div>
                </div>
"""
    
    # Tab: Timeouts
    html += f"""
            </div>
            
            <div id="timeout" class="tab-content">
                <h3>Timeouts</h3>
                <p style="color: #4a5568; margin-bottom: 20px;">
                    Szenarien mit sehr langen Antwortzeiten (> 60 Sekunden).
                </p>
"""
    for error in error_patterns['timeout']:
        html += f"""
                <div class="test-card">
                    <h4>{error['short_id']} - <span class="badge error">Latenz: {format_duration(error['latency'] / 1000)}</span></h4>
                    <div class="prompt">"{error['prompt'][:200]}{'...' if len(error['prompt']) > 200 else ''}"</div>
                </div>
"""
    
    # Tab: Runtime Errors
    html += f"""
            </div>
            
            <div id="errors" class="tab-content">
                <h3>Runtime Errors</h3>
                <p style="color: #4a5568; margin-bottom: 20px;">
                    Szenarien mit Laufzeitfehlern während der Ausführung.
                </p>
"""
    for error in error_patterns['errors']:
        html += f"""
                <div class="test-card">
                    <h4>{error['short_id']} - <span class="badge error">Error</span></h4>
                    <div class="prompt">"{error['prompt'][:200]}{'...' if len(error['prompt']) > 200 else ''}"</div>
                    <div style="margin-top: 10px; padding: 10px; background: #fed7d7; border-radius: 4px;">
                        <code style="background: none; color: #742a2a;">{error['error']}</code>
                    </div>
                </div>
"""
    
    html += """
            </div>
        </div>
        
        <!-- Schwierigkeit -->
        <div class="section">
            <h2>📊 Ergebnisse nach Schwierigkeit</h2>
            <table>
                <thead>
                    <tr>
                        <th>Schwierigkeit</th>
                        <th>Anzahl</th>
                        <th>F1-Score</th>
                        <th>Exact Match</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for diff, metrics in sorted(agg['metrics_by_difficulty'].items(), key=lambda x: x[1]['mean_f1'], reverse=True):
        f1_pct = metrics['mean_f1'] * 100
        em_pct = metrics['exact_match_rate'] * 100
        html += f"""
                    <tr>
                        <td><strong>{diff}</strong></td>
                        <td>{metrics['count']}</td>
                        <td>
                            {metrics['mean_f1']:.3f}
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {f1_pct}%"></div>
                            </div>
                        </td>
                        <td>
                            {metrics['exact_match_rate']:.1%}
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {em_pct}%"></div>
                            </div>
                        </td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function showTab(tabName) {
            // Hide all tab contents
            const contents = document.querySelectorAll('.tab-content');
            contents.forEach(content => content.classList.remove('active'));
            
            // Remove active from all tabs
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => tab.classList.remove('active'));
            
            // Show selected tab
            document.getElementById(tabName).classList.add('active');
            
            // Mark tab as active
            event.target.classList.add('active');
        }
    </script>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)


def generate_markdown_report(data: Dict, output_path: Path):
    """Generiert einen detaillierten Markdown-Report."""
    
    agg = data['aggregated_metrics']
    results = data['individual_results']
    negative = analyze_negative_tests(results)
    tool_usage = analyze_tool_usage(results)
    error_patterns = analyze_error_patterns(results)
    
    positive_tests = [r for r in results if len(r['expected_tools']) > 0]
    negative_tests = [r for r in results if len(r['expected_tools']) == 0]
    
    md = f"""# Detaillierter Evaluation Report

**Modell:** {data['model_name']} ({data['model_version']})  
**Generiert:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Dauer:** {format_duration(data['total_duration_seconds'])}

---

## 📊 Übersicht

| Metrik | Wert |
|--------|------|
| **Gesamt-Szenarien** | {data['total_scenarios']} |
| **Exact Match Rate** | {agg['exact_match_rate']:.1%} ({int(data['total_scenarios'] * agg['exact_match_rate'])}/{data['total_scenarios']}) |
| **F1-Score** | {agg['mean_f1']:.3f} |
| **Precision** | {agg['mean_precision']:.3f} |
| **Recall** | {agg['mean_recall']:.3f} |
| **Positive Tests** | {len(positive_tests)} (Tool-Aufruf erwartet) |
| **Negative Tests** | {len(negative_tests)} (kein Tool-Aufruf erwartet) |
| **Negative Test Accuracy** | {negative['accuracy']:.1%} ({negative['correct_rejections']}/{negative['total']}) |

---

## ❌ Negative Tests - Detailanalyse

**Negative Tests** prüfen, ob der Agent korrekt erkennt, wann KEIN Tool aufgerufen werden sollte.
Dies ist wichtig, um falsche Tool-Aufrufe bei unvollständigen oder vagen Anfragen zu vermeiden.

### Zusammenfassung

- **Gesamt:** {negative['total']} negative Tests
- **Korrekt abgelehnt:** {negative['correct_rejections']} ({negative['accuracy']:.1%})
- **Falsch-Positive:** {negative['false_positives']} (Tool wurde fälschlicherweise aufgerufen)

"""
    
    # Falsch-Positive Tests
    if negative['false_positives'] > 0:
        md += f"""### ⚠️ Falsch-Positive Tests ({negative['false_positives']})

Tool wurde aufgerufen, obwohl keiner erwartet war:

"""
        for test in negative['tests']:
            if not test['correct']:
                md += f"""#### {test['short_id']} - {test['scenario_id']}

- **Prompt:** "{test['user_prompt'][:200]}{'...' if len(test['user_prompt']) > 200 else ''}"
- **Schwierigkeit:** {test['difficulty']}
- **Aufgerufene Tools:** `{', '.join(test['actual_tools'])}`

"""
    
    # Korrekte Ablehnungen (Sample)
    md += f"""### ✅ Korrekte Ablehnungen (Sample)

Beispiele von Szenarien, bei denen der Agent korrekt erkannt hat, dass kein Tool aufgerufen werden sollte:

"""
    
    count = 0
    for test in negative['tests']:
        if test['correct'] and count < 5:
            md += f"""#### {test['short_id']} - {test['scenario_id']}

- **Prompt:** "{test['user_prompt'][:200]}{'...' if len(test['user_prompt']) > 200 else ''}"
- **Schwierigkeit:** {test['difficulty']}
- **Status:** ✅ Korrekt abgelehnt

"""
            count += 1
    
    # Tool-Nutzung
    md += f"""---

## 🔧 Tool-Nutzungsstatistik

| Tool | Erwartet | Korrekt | Verpasst | Recall | Ø Latenz |
|------|----------|---------|----------|--------|----------|
"""
    
    for tool, stats in sorted(tool_usage.items(), key=lambda x: x[1]['recall'], reverse=True):
        md += f"| `{tool}` | {stats['expected']} | {stats['correct']} | {stats['missed']} | {stats['recall']:.1%} | {format_duration(stats['avg_latency'] / 1000)} |\n"
    
    # Fehler-Muster
    md += f"""
---

## 🐛 Fehler-Muster

### Fehlende Tools ({len(error_patterns['missing_tools'])})

Szenarien, bei denen erwartete Tools nicht aufgerufen wurden:

"""
    
    for error in error_patterns['missing_tools'][:10]:
        md += f"""#### {error['short_id']} - Fehlende: {', '.join(error['missing'])}

- **Prompt:** "{error['prompt'][:150]}{'...' if len(error['prompt']) > 150 else ''}"
- **Schwierigkeit:** {error['difficulty']}

"""
    
    if len(error_patterns['missing_tools']) > 10:
        md += f"\n*... und {len(error_patterns['missing_tools']) - 10} weitere*\n"
    
    md += f"""
### Extra Tools ({len(error_patterns['extra_tools'])})

Szenarien, bei denen zusätzliche, nicht erwartete Tools aufgerufen wurden:

"""
    
    for error in error_patterns['extra_tools'][:10]:
        md += f"""#### {error['short_id']} - Extra: {', '.join(error['extra'])}

- **Prompt:** "{error['prompt'][:150]}{'...' if len(error['prompt']) > 150 else ''}"
- **Schwierigkeit:** {error['difficulty']}

"""
    
    if len(error_patterns['extra_tools']) > 10:
        md += f"\n*... und {len(error_patterns['extra_tools']) - 10} weitere*\n"
    
    # Timeouts
    if error_patterns['timeout']:
        md += f"""
### Timeouts ({len(error_patterns['timeout'])})

Szenarien mit sehr langen Antwortzeiten (> 60 Sekunden):

"""
        for error in error_patterns['timeout']:
            md += f"""- **{error['short_id']}:** {format_duration(error['latency'] / 1000)} - "{error['prompt'][:100]}..."\n"""
    
    # Runtime Errors
    if error_patterns['errors']:
        md += f"""
### Runtime Errors ({len(error_patterns['errors'])})

"""
        for error in error_patterns['errors']:
            md += f"""#### {error['short_id']}

- **Prompt:** "{error['prompt'][:150]}..."
- **Error:** `{error['error']}`

"""
    
    # Schwierigkeit
    md += f"""
---

## 📊 Ergebnisse nach Schwierigkeit

| Schwierigkeit | Anzahl | F1-Score | Exact Match |
|---------------|--------|----------|-------------|
"""
    
    for diff, metrics in sorted(agg['metrics_by_difficulty'].items(), key=lambda x: x[1]['mean_f1'], reverse=True):
        md += f"| **{diff}** | {metrics['count']} | {metrics['mean_f1']:.3f} | {metrics['exact_match_rate']:.1%} |\n"
    
    md += """
---

## 📋 Alle Einzelergebnisse

<details>
<summary>Klicken um alle {len(results)} Einzelergebnisse zu sehen</summary>

| ID | Scenario | Tool | Difficulty | Expected | Actual | Match | Latenz |
|----|----------|------|------------|----------|--------|-------|--------|
"""
    
    for r in results:
        match_icon = "✅" if r['exact_match'] else "❌"
        expected = ", ".join(r['expected_tools']) if r['expected_tools'] else "NONE"
        actual = ", ".join(r['actual_tools']) if r['actual_tools'] else "NONE"
        md += f"| {r['short_id']} | {r['scenario_id'][:40]}... | {r['tool']} | {r['difficulty']} | {expected} | {actual} | {match_icon} | {format_duration(r['latency_ms'] / 1000)} |\n"
    
    md += """
</details>

---

*Report generiert mit eval/utils/generate_detailed_report.py*
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(
        description='Generiert detaillierten HTML- und Markdown-Report aus results.json',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python eval/utils/generate_detailed_report.py data/eval/final/gpt-oss-20b/.../tools/results.json
  python eval/utils/generate_detailed_report.py results.json --output custom_report
        """
    )
    
    parser.add_argument(
        'results_file',
        type=str,
        help='Pfad zur results.json Datei'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Basis-Name für Output-Dateien (default: detailed_report)'
    )
    
    args = parser.parse_args()
    
    # Lade results.json
    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"❌ Fehler: Datei nicht gefunden: {results_path}")
        sys.exit(1)
    
    print(f"📂 Lade Ergebnisse aus: {results_path}")
    with open(results_path) as f:
        data = json.load(f)
    
    # Bestimme Output-Verzeichnis
    output_dir = results_path.parent
    base_name = args.output or 'detailed_report'
    
    # Generiere Reports
    html_path = output_dir / f'{base_name}.html'
    md_path = output_dir / f'{base_name}.md'
    
    print(f"🔨 Generiere HTML-Report...")
    generate_html_report(data, html_path)
    print(f"   ✅ {html_path}")
    
    print(f"🔨 Generiere Markdown-Report...")
    generate_markdown_report(data, md_path)
    print(f"   ✅ {md_path}")
    
    print(f"\n✨ Fertig! Öffne {html_path.name} im Browser für die interaktive Ansicht.")


if __name__ == '__main__':
    main()
