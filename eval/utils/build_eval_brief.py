#!/usr/bin/env python3
"""Build a single self-contained Markdown brief per evaluation run for
feeding into ChatGPT.

One file is produced per (model, agent_type, run) — i.e. one per
``results.json``. The brief contains:

  1. Run metadata (model, agent type, timestamp, source path).
  2. Overall metrics (TSR, F1, precision, recall, arg-accuracy, latency, tokens).
  3. Results by main difficulty (Easy/Medium/Hard) — class-name taxonomy.
  4. Results by hard sub-type (Standard/Multi_step/Multi_tool/Negative/EdgeCases).
  5. Results by tool category.
  6. Diagnostic failure indicators (forbidden / missing / extra / runtime).
  7. Failed scenarios — each with prompt, expected vs. actual tools,
     argument diff, error message, latency.

Bucketing follows the thesis taxonomy (test class name in ``scenario_id``),
not the per-scenario ``difficulty`` field in results.json.

Usage
-----

    # Single results.json -> write brief next to it as `eval_brief.md`
    python -m eval.utils.build_eval_brief path/to/results.json

    # Walk a directory and produce a brief for every results.json
    python -m eval.utils.build_eval_brief "Results Final/Run 1" --recursive

    # Write to a single output file (only when a single results.json given)
    python -m eval.utils.build_eval_brief results.json -o brief.md
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

# --- Thesis taxonomy --------------------------------------------------------

TOP_ORDER = ["Easy", "Medium", "Hard"]
HARD_ORDER = ["Standard", "Multi_step", "Multi_tool", "Negative", "EdgeCases"]


def _scenario_class(scenario_id: str) -> str:
    return scenario_id.split("_test_", 1)[0]


def top_bucket(scenario_id: str) -> str | None:
    cls = _scenario_class(scenario_id)
    if cls.endswith("Easy"):
        return "Easy"
    if cls.endswith("Medium"):
        return "Medium"
    if (
        cls.endswith("Hard")
        or "MultiStep" in cls
        or "MultiTool" in cls
        or "Negative" in cls
        or "EdgeCases" in cls
    ):
        return "Hard"
    return None


def hard_subbucket(scenario_id: str) -> str | None:
    cls = _scenario_class(scenario_id)
    if "MultiTool" in cls:
        return "Multi_tool"
    if "MultiStep" in cls:
        return "Multi_step"
    if "EdgeCases" in cls:
        return "EdgeCases"
    if "Negative" in cls:
        return "Negative"
    if cls.endswith("Hard"):
        return "Standard"
    return None


# --- Helpers ----------------------------------------------------------------


def _safe_mean(values: Iterable[float]) -> float | None:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return statistics.mean(vals) if vals else None


def _fmt_pct(x: float | None) -> str:
    return f"{x * 100:.1f}%" if x is not None else "n/a"


def _fmt_num(x: float | None, n: int = 3) -> str:
    return f"{x:.{n}f}" if x is not None else "n/a"


def _fmt_ms(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.0f} ms"
    return f"{ms / 1000:.2f} s"


def _fmt_dur(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(int(seconds), 60)
    if m < 60:
        return f"{m}m {s}s"
    h, m = divmod(m, 60)
    return f"{h}h {m}m {s}s"


def _short_args(d: dict, limit: int = 200) -> str:
    if not d:
        return "{}"
    s = json.dumps(d, ensure_ascii=False, sort_keys=True)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _bucket_metrics(items: list[dict]) -> dict[str, Any]:
    n = len(items)
    return {
        "count": n,
        "mean_f1": statistics.mean(s["tool_f1"] for s in items),
        "tsr": sum(1 for s in items if s.get("exact_match")) / n,
        "mean_precision": statistics.mean(s["tool_precision"] for s in items),
        "mean_recall": statistics.mean(s["tool_recall"] for s in items),
        "mean_arg_acc": _safe_mean(s.get("argument_accuracy") for s in items),
        "mean_latency_ms": statistics.mean(s.get("latency_ms", 0) for s in items),
    }


# --- Brief builder ----------------------------------------------------------


def build_brief(results_json: Path) -> str:
    data = json.loads(results_json.read_text(encoding="utf-8"))
    individual: list[dict] = data["individual_results"]
    agg: dict = data.get("aggregated_metrics", {})

    # Try to infer agent_type and run name from the path.
    # Expected layout: .../<model>/Tools/<agent>/results.json
    parts = results_json.resolve().parts
    agent_type = parts[-2] if len(parts) >= 2 else "unknown"
    suite = parts[-3] if len(parts) >= 3 else "Tools"
    model_dir = parts[-4] if len(parts) >= 4 else data.get("model_name", "unknown")
    run_name = parts[-5] if len(parts) >= 5 else "Run"

    model = data.get("model_name", model_dir)
    timestamp = data.get("timestamp", "unknown")
    duration = data.get("total_duration_seconds", 0)

    # ------------- bucketize -------------
    top = {c: [] for c in TOP_ORDER}
    hard = {c: [] for c in HARD_ORDER}
    by_tool: dict[str, list[dict]] = {}
    for s in individual:
        b = top_bucket(s["scenario_id"])
        if b:
            top[b].append(s)
        h = hard_subbucket(s["scenario_id"])
        if h:
            hard[h].append(s)
        by_tool.setdefault(s["tool"], []).append(s)

    # ------------- header -------------
    lines: list[str] = []
    lines.append(f"# Evaluation Brief — {model} · {agent_type} · {suite} · {run_name}")
    lines.append("")
    lines.append("## 1. Run Metadata")
    lines.append("")
    lines.append(f"- **Model:** `{model}`")
    lines.append(f"- **Agent type:** `{agent_type}`")
    lines.append(f"- **Test suite:** `{suite}`")
    lines.append(f"- **Run:** `{run_name}`")
    lines.append(f"- **Timestamp:** {timestamp}")
    lines.append(f"- **Wall-clock duration:** {_fmt_dur(duration)}")
    lines.append(f"- **Source file:** `{results_json}`")
    lines.append(f"- **Total scenarios:** {len(individual)}")
    lines.append("")

    # ------------- overall metrics -------------
    n = len(individual)
    overall_arg_acc = _safe_mean(s.get("argument_accuracy") for s in individual)
    overall_lat = statistics.mean(s.get("latency_ms", 0) for s in individual) if n else 0
    total_in = sum(s.get("input_tokens", 0) or 0 for s in individual)
    total_out = sum(s.get("output_tokens", 0) or 0 for s in individual)
    total_tok = sum(s.get("total_tokens", 0) or 0 for s in individual)
    avg_tok = total_tok / n if n else 0

    lines.append("## 2. Overall Metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    lines.append(f"| Task Success Rate (exact match) | {_fmt_pct(agg.get('exact_match_rate'))} |")
    lines.append(f"| F1 (mean ± std) | {_fmt_num(agg.get('mean_f1'))} ± {_fmt_num(agg.get('std_f1'))} |")
    lines.append(f"| Precision (mean ± std) | {_fmt_num(agg.get('mean_precision'))} ± {_fmt_num(agg.get('std_precision'))} |")
    lines.append(f"| Recall (mean ± std) | {_fmt_num(agg.get('mean_recall'))} ± {_fmt_num(agg.get('std_recall'))} |")
    lines.append(f"| Argument Accuracy (mean) | {_fmt_pct(overall_arg_acc)} |")
    lines.append(f"| Mean latency / scenario | {_fmt_ms(overall_lat)} |")
    lines.append(f"| Tokens (input / output / total) | {total_in:,} / {total_out:,} / {total_tok:,} |")
    lines.append(f"| Avg tokens / scenario | {avg_tok:.0f} |")
    lines.append("")

    # ------------- by main difficulty -------------
    lines.append("## 3. Results by Main Difficulty (thesis taxonomy)")
    lines.append("")
    lines.append("| Difficulty | N | TSR | F1 | Precision | Recall | Arg Acc | Mean Latency |")
    lines.append("|------------|---|-----|----|-----------|--------|---------|--------------|")
    for cat in TOP_ORDER:
        items = top[cat]
        if not items:
            lines.append(f"| {cat} | 0 | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        m = _bucket_metrics(items)
        lines.append(
            f"| {cat} | {m['count']} | {_fmt_pct(m['tsr'])} | {_fmt_num(m['mean_f1'])} | "
            f"{_fmt_num(m['mean_precision'])} | {_fmt_num(m['mean_recall'])} | "
            f"{_fmt_pct(m['mean_arg_acc'])} | {_fmt_ms(m['mean_latency_ms'])} |"
        )
    lines.append("")

    # ------------- by hard sub-type -------------
    lines.append("## 4. Results by Hard Sub-Type")
    lines.append("")
    lines.append("| Hard Type | N | TSR | F1 | Precision | Recall | Arg Acc | Mean Latency |")
    lines.append("|-----------|---|-----|----|-----------|--------|---------|--------------|")
    for cat in HARD_ORDER:
        items = hard[cat]
        if not items:
            lines.append(f"| {cat} | 0 | n/a | n/a | n/a | n/a | n/a | n/a |")
            continue
        m = _bucket_metrics(items)
        lines.append(
            f"| {cat} | {m['count']} | {_fmt_pct(m['tsr'])} | {_fmt_num(m['mean_f1'])} | "
            f"{_fmt_num(m['mean_precision'])} | {_fmt_num(m['mean_recall'])} | "
            f"{_fmt_pct(m['mean_arg_acc'])} | {_fmt_ms(m['mean_latency_ms'])} |"
        )
    lines.append("")

    # ------------- by tool -------------
    lines.append("## 5. Results by Tool")
    lines.append("")
    lines.append("| Tool | N | TSR | F1 | Arg Acc | Mean Latency |")
    lines.append("|------|---|-----|----|---------|--------------|")
    for tool in sorted(by_tool):
        items = by_tool[tool]
        m = _bucket_metrics(items)
        lines.append(
            f"| `{tool}` | {m['count']} | {_fmt_pct(m['tsr'])} | {_fmt_num(m['mean_f1'])} | "
            f"{_fmt_pct(m['mean_arg_acc'])} | {_fmt_ms(m['mean_latency_ms'])} |"
        )
    lines.append("")

    # ------------- diagnostic failure indicators -------------
    forbidden = sum(1 for s in individual if s.get("forbidden_tools_called"))
    missing = sum(
        len(set(s["expected_tools"]) - set(s["actual_tools"])) for s in individual
    )
    extra = sum(
        len(set(s["actual_tools"]) - set(s["expected_tools"])) for s in individual
    )
    runtime_errors = sum(1 for s in individual if s.get("error"))
    arg_errors = sum(
        1 for s in individual
        if s.get("argument_accuracy") is not None
        and not (isinstance(s["argument_accuracy"], float) and math.isnan(s["argument_accuracy"]))
        and s["argument_accuracy"] < 1.0
    )

    lines.append("## 6. Diagnostic Failure Indicators")
    lines.append("")
    lines.append("| Indicator | Count |")
    lines.append("|-----------|-------|")
    lines.append(f"| Forbidden tool violations | {forbidden} |")
    lines.append(f"| Missing tool calls (sum across scenarios) | {missing} |")
    lines.append(f"| Extra tool calls (sum across scenarios) | {extra} |")
    lines.append(f"| Scenarios with arg-accuracy < 1.0 | {arg_errors} |")
    lines.append(f"| Runtime errors | {runtime_errors} |")
    lines.append("")

    # ------------- failed scenarios -------------
    failed = [s for s in individual if not s.get("exact_match")]
    lines.append(f"## 7. Failed Scenarios ({len(failed)} of {len(individual)})")
    lines.append("")
    if not failed:
        lines.append("_No failures._")
        lines.append("")
    else:
        # Compact table first, then per-scenario detail.
        lines.append("### 7.1 Summary table")
        lines.append("")
        lines.append("| # | short_id | scenario_id | top | hard | F1 | Arg | Issue |")
        lines.append("|---|----------|-------------|-----|------|----|-----|-------|")
        for i, s in enumerate(failed, 1):
            issue = _diagnose_issue(s)
            arg = s.get("argument_accuracy")
            arg_str = "n/a" if arg is None or (isinstance(arg, float) and math.isnan(arg)) else f"{arg:.2f}"
            lines.append(
                f"| {i} | {s.get('short_id', '')} | `{s['scenario_id']}` | "
                f"{top_bucket(s['scenario_id']) or '-'} | "
                f"{hard_subbucket(s['scenario_id']) or '-'} | "
                f"{s['tool_f1']:.2f} | {arg_str} | {issue} |"
            )
        lines.append("")

        lines.append("### 7.2 Per-scenario detail")
        lines.append("")
        for i, s in enumerate(failed, 1):
            lines.extend(_render_scenario_detail(i, s))
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "_Generated by `eval/utils/build_eval_brief.py`. "
        "Buckets follow the thesis taxonomy (test class name)._"
    )
    lines.append("")
    return "\n".join(lines)


def _diagnose_issue(s: dict) -> str:
    bits: list[str] = []
    if s.get("forbidden_tools_called"):
        bits.append(f"forbidden: {s['forbidden_tools_called']}")
    missing_tools = set(s["expected_tools"]) - set(s["actual_tools"])
    if missing_tools:
        bits.append(f"missing tools: {sorted(missing_tools)}")
    extra_tools = set(s["actual_tools"]) - set(s["expected_tools"])
    if extra_tools:
        bits.append(f"extra tools: {sorted(extra_tools)}")
    arg = s.get("argument_accuracy")
    if (
        arg is not None
        and not (isinstance(arg, float) and math.isnan(arg))
        and arg < 1.0
        and not missing_tools
        and not extra_tools
        and not s.get("forbidden_tools_called")
    ):
        bits.append(f"arg accuracy {arg:.0%}")
    if s.get("error"):
        bits.append(f"error: {s['error'][:80]}")
    return "; ".join(bits) if bits else "exact_match=False"


def _render_scenario_detail(idx: int, s: dict) -> list[str]:
    out: list[str] = []
    out.append(f"#### {idx}. `{s['scenario_id']}`")
    out.append("")
    out.append(f"- **short_id:** {s.get('short_id', '')}")
    out.append(f"- **tool (primary):** `{s['tool']}`")
    out.append(f"- **bucket:** {top_bucket(s['scenario_id'])} / {hard_subbucket(s['scenario_id']) or '-'}")
    out.append(f"- **scenario difficulty (raw):** {s.get('difficulty', '-')}")
    out.append(f"- **category:** {s.get('category') or '-'}")
    out.append(f"- **latency:** {_fmt_ms(s.get('latency_ms', 0))}")
    out.append(f"- **F1 / precision / recall:** {s['tool_f1']:.2f} / {s['tool_precision']:.2f} / {s['tool_recall']:.2f}")

    arg = s.get("argument_accuracy")
    if arg is None or (isinstance(arg, float) and math.isnan(arg)):
        out.append("- **argument accuracy:** n/a")
    else:
        out.append(f"- **argument accuracy:** {arg:.2%}")

    out.append("")
    out.append(f"**User prompt:** {s.get('user_prompt', '').strip()}")
    out.append("")
    out.append(f"- **Expected tools:** {s['expected_tools']}")
    out.append(f"- **Actual tools:**   {s['actual_tools']}")
    if s.get("forbidden_tools_called"):
        out.append(f"- **Forbidden tools called:** {s['forbidden_tools_called']}")
    if s.get("missing_arguments"):
        out.append(f"- **Missing arguments:** {_short_args(s['missing_arguments'], 400)}")
    out.append(f"- **Expected arguments:** `{_short_args(s['expected_arguments'], 400)}`")
    out.append(f"- **Actual arguments:**   `{_short_args(s['actual_arguments'], 400)}`")
    if s.get("error"):
        out.append("")
        out.append("**Error:**")
        out.append("```")
        out.append(str(s["error"])[:1000])
        out.append("```")
    return out


# --- CLI --------------------------------------------------------------------


def _iter_results_files(target: Path, recursive: bool) -> Iterable[Path]:
    if target.is_file():
        yield target
        return
    if not target.is_dir():
        raise SystemExit(f"Not found: {target}")
    pattern = "**/results.json" if recursive else "*/results.json"
    yield from sorted(target.glob(pattern))


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path", type=Path,
                    help="Path to a results.json or a directory containing them.")
    ap.add_argument("-o", "--output", type=Path, default=None,
                    help="Write to this single file (only when PATH is a single results.json). "
                         "Otherwise the brief is written next to each results.json as "
                         "`eval_brief.md`.")
    ap.add_argument("-r", "--recursive", action="store_true",
                    help="When PATH is a directory, recurse to find every results.json.")
    args = ap.parse_args(argv)

    files = list(_iter_results_files(args.path, args.recursive))
    if not files:
        raise SystemExit(f"No results.json found at {args.path}")

    if args.output is not None:
        if len(files) != 1:
            raise SystemExit(
                "--output may only be used when PATH points to a single results.json"
            )
        brief = build_brief(files[0])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(brief, encoding="utf-8")
        print(f"   ✓ {args.output}")
        return

    for results_json in files:
        brief = build_brief(results_json)
        out = results_json.with_name("eval_brief.md")
        out.write_text(brief, encoding="utf-8")
        print(f"   ✓ {out}")

    print(f"\nWrote {len(files)} brief(s).")


if __name__ == "__main__":
    main()
