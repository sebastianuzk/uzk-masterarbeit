#!/usr/bin/env python3
"""
Vollständiges Evaluierungsskript für den WiSo-Chatbot

Führt Tool- und/oder RAGAS-Evaluation für verschiedene Modelle durch.

Verwendung:
    # Einzelnes Modell, beide Evaluationen
    python -m eval.run_full_evaluation --model llama3.1:8b
    
    # Nur Tool-Evaluation
    python -m eval.run_full_evaluation --model llama3.1:8b --mode tools
    
    # Nur RAGAS-Evaluation
    python -m eval.run_full_evaluation --model llama3.1:8b --mode rag
    
    # Alle konfigurierten Modelle
    python -m eval.run_full_evaluation --all-models
    
    # Mit bestimmtem Agent-Typ
    python -m eval.run_full_evaluation --model llama3.1:8b --agent single

Ergebnisse: data/eval/final/<modell>/
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Projekt-Root zum Pfad hinzufügen
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import settings

# ============================================================================
# KONFIGURATION
# ============================================================================

# Verfügbare Modelle für Evaluation
AVAILABLE_MODELS = {
    "llama3.1:8b": {
        "name": "LLaMA 3.1 8B",
        "ctx_size": 8192,
        "description": "Meta's LLaMA 3.1 mit 8B Parametern"
    },
    "gpt-oss:20b": {
        "name": "GPT-OSS 20B", 
        "ctx_size": 16384,
        "description": "Open-Source GPT-Variante mit 20B Parametern"
    },
}

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

def format_duration(seconds: float) -> str:
    """Formatiert Sekunden als lesbare Dauer."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"


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
                print(f"   ✅ {agent_type}: Daten geladen")
        else:
            print(f"   ⚠️  {agent_type}: Keine Daten gefunden")
    
    if not agent_results:
        print("   ❌ Keine Evaluationsergebnisse gefunden!")
        return
    
    # Generiere Markdown
    md_content = _generate_markdown_report(agent_results, model)
    md_path = base_dir / "evaluation_report.md"
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(md_content)
    print(f"   ✅ Markdown: {md_path}")
    
    # Generiere HTML
    html_content = _generate_html_report(agent_results, model)
    html_path = base_dir / "evaluation_report.html"
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"   ✅ HTML: {html_path}")
    
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


def ensure_model_available(model: str) -> bool:
    """Prüft ob Modell in Ollama verfügbar ist."""
    import requests
    try:
        # Verwende API statt lokaler Befehle (funktioniert auch für Remote-Server)
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


def pull_model_if_needed(model: str) -> bool:
    """Lädt Modell herunter falls nicht vorhanden."""
    if ensure_model_available(model):
        return True
    
    print(f"⬇️  Lade Modell {model} herunter...")
    import requests
    try:
        # Verwende API für Pull (funktioniert auch für Remote-Server)
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


def set_model_in_settings(model: str):
    """Setzt das aktive Modell in den Settings."""
    os.environ["OLLAMA_MODEL"] = model
    settings.OLLAMA_MODEL = model


# ============================================================================
# TOOL-EVALUATION
# ============================================================================

def run_tool_evaluation(
    model: str,
    agent_type: str,
    output_dir: Path,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Führt die Tool-Evaluation durch.
    
    Args:
        model: Ollama-Modellname
        agent_type: Agent-Typ (single, multi, etc.)
        output_dir: Ausgabeverzeichnis
        limit: Optionale Begrenzung der Test-Szenarien
    
    Returns:
        Dictionary mit Evaluationsergebnissen
    """
    print("\n" + "=" * 80)
    print("🔧 TOOL-EVALUATION")
    print("=" * 80)
    
    start_time = time.time()
    
    # Setze Modell
    set_model_in_settings(model)
    
    # Importiere nach Modell-Setting
    from eval.core.runner import (
        load_scenarios_from_tests,
        run_single_scenario,
        aggregate_results,
        save_report,
    )
    
    # Agent erstellen
    print(f"\n🤖 Initialisiere {agent_type}-Agent mit {model}...")
    
    if agent_type == "single":
        from src.agent.react_agent import create_react_agent
        agent = create_react_agent()
    elif agent_type == "multi":
        from src.agent.multi.multi_agent_system import MultiAgentSystem
        agent = MultiAgentSystem()
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
    
    # Limit anwenden falls gesetzt
    if limit is not None and limit < len(all_scenarios):
        scenarios = all_scenarios[:limit]
        print(f"   ✅ {limit} von {len(all_scenarios)} Szenarien geladen (limitiert)")
    else:
        scenarios = all_scenarios
        print(f"   ✅ {len(scenarios)} Szenarien geladen")
    
    # Szenarien durchführen
    print(f"\n🚀 Starte Evaluation ({len(scenarios)} Szenarien)...")
    print("-" * 80)
    results = []
    
    for i, scenario in enumerate(scenarios, 1):
        # Kompakte Ausgabe: alles in einer Zeile wie eval_old
        print(f"[{i}/{len(scenarios)}] {scenario.short_id}...", end=" ", flush=True)
        
        try:
            result = run_single_scenario(agent, scenario)
            results.append(result)
            
            status = "✓" if result.exact_match else "✗"
            print(f"{status} (F1={result.tool_f1:.2f}, {result.latency_ms:.0f}ms)")
        except Exception as e:
            print(f"ERROR: {str(e)[:50]}")
    
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
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Führt die RAGAS-Evaluation durch.
    
    Args:
        model: Ollama-Modellname
        agent_type: Agent-Typ (single, multi, etc.)
        output_dir: Ausgabeverzeichnis
        limit: Optionale Begrenzung der Testfragen
    
    Returns:
        Dictionary mit RAGAS-Ergebnissen
    """
    print("\n" + "=" * 80)
    print("📚 RAGAS-EVALUATION")
    print("=" * 80)
    
    start_time = time.time()
    
    # Setze Modell
    set_model_in_settings(model)
    
    # Importiere RAGAS-Komponenten
    from eval.ragas.ragas_evaluation import (
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
        agent = create_react_agent()
    elif agent_type == "multi":
        from src.agent.multi.multi_agent_system import MultiAgentSystem
        agent = MultiAgentSystem()
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
    
    # Testset laden
    print("\n📂 Lade Testset...")
    testset_path = PROJECT_ROOT / "eval" / "ragas" / "data" / "Testset.CSV"
    if not testset_path.exists():
        # Fallback-Pfad
        testset_path = PROJECT_ROOT / "data" / "Testset.CSV"
    
    test_df = load_testset(str(testset_path), limit=limit)
    
    # Antworten generieren
    print(f"\n🚀 Generiere Chatbot-Antworten ({len(test_df)} Fragen)...")
    dataset = generate_chatbot_responses(test_df, agent, langsmith_client)
    
    # RAGAS-Evaluation
    print("\n📊 Führe RAGAS-Evaluation durch...")
    results_df = run_ragas_evaluation(dataset, model=model)
    
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
    output_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Führt die vollständige Evaluation für ein Modell durch.
    
    Args:
        model: Ollama-Modellname
        agent_type: Agent-Typ
        mode: "all", "tools", oder "rag"
        rag_limit: Optionale Begrenzung für RAGAS-Testfragen
        tool_limit: Optionale Begrenzung für Tool-Szenarien
        output_dir: Optionales Ausgabeverzeichnis (wenn None, wird neuer Timestamp erstellt)
    
    Returns:
        Zusammenfassung aller Ergebnisse
    """
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
    print(f"   Agent:     {agent_type}")
    print(f"   Modus:     {mode}")
    print(f"   Ausgabe:   {output_dir}")
    print("=" * 80)
    
    start_time = time.time()
    results = {
        "model": model,
        "agent_type": agent_type,
        "mode": mode,
        "timestamp": timestamp,
        "output_dir": str(output_dir),
    }
    
    # Modell prüfen/laden
    print(f"\n⏳ Prüfe Modell {model}...")
    if not pull_model_if_needed(model):
        print(f"❌ Modell {model} nicht verfügbar!")
        return results
    print(f"   ✅ Modell bereit")
    
    # Tool-Evaluation
    if mode in ("all", "tools"):
        try:
            results["tools"] = run_tool_evaluation(model, agent_type, output_dir, limit=tool_limit)
        except Exception as e:
            print(f"\n❌ Tool-Evaluation fehlgeschlagen: {e}")
            results["tools"] = {"error": str(e)}
    
    # RAGAS-Evaluation
    if mode in ("all", "rag"):
        try:
            results["ragas"] = run_rag_evaluation(model, agent_type, output_dir, limit=rag_limit)
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
    agents: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Führt Evaluation für alle Agent-Typen durch.
    
    Args:
        agents: Liste von Agenten (default: alle aus AGENT_TYPES)
    """
    # Verwende custom Agenten-Liste oder alle
    agent_list = agents if agents else AGENT_TYPES
    
    print("\n" + "=" * 80)
    print("🎯 EVALUATION ALLER AGENT-ARCHITEKTUREN")
    print("=" * 80)
    print(f"   Modell:    {model}")
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
                output_dir=shared_output_dir
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
  # Einzelnes Modell, alle Agenten
  python -m eval.run_full_evaluation --model llama3.1:8b
  
  # Nur ein Agent
  python -m eval.run_full_evaluation --model llama3.1:8b --agent single
  
  # Nur Tool-Evaluation
  python -m eval.run_full_evaluation --model llama3.1:8b --mode tools
  
  # Mit Limits
  python -m eval.run_full_evaluation --model llama3.1:8b --tool-limit 20 --rag-limit 20
        """
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="llama3.1:8b",
        help=f"Ollama-Modell (verfügbar: {', '.join(AVAILABLE_MODELS.keys())})"
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
    
    args = parser.parse_args()
    
    try:
        # Bestimme welche Modelle evaluiert werden sollen
        models_to_eval = list(AVAILABLE_MODELS.keys()) if args.all_models else [args.model]
        
        for model in models_to_eval:
            if len(models_to_eval) > 1:
                print("\n" + "#" * 80)
                print(f"# MODELL: {model}")
                print("#" * 80)
            
            if args.agents:
                # Spezifische Agenten evaluieren
                run_all_agents_evaluation(
                    model=model,
                    mode=args.mode,
                    rag_limit=args.rag_limit,
                    tool_limit=args.tool_limit,
                    agents=args.agents
                )
            elif args.agent == "all":
                # Alle Agent-Architekturen evaluieren
                run_all_agents_evaluation(
                    model=model,
                    mode=args.mode,
                    rag_limit=args.rag_limit,
                    tool_limit=args.tool_limit
                )
            else:
                # Einzelnen Agent evaluieren
                run_full_evaluation(
                    model=model,
                    agent_type=args.agent,
                    mode=args.mode,
                    rag_limit=args.rag_limit,
                    tool_limit=args.tool_limit
                )
    except KeyboardInterrupt:
        print("\n\n⚠️  Evaluation abgebrochen!")
        sys.exit(1)


if __name__ == "__main__":
    main()
