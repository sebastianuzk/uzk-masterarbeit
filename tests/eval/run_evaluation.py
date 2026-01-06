"""
Evaluierungs-Suite für den React Agent ausführen

Dieses Skript:
1. Lädt alle Evaluierungsszenarien aus den Test-Dateien
2. Führt jedes Szenario durch den React Agent
3. Extrahiert Tool-Aufrufe aus der Agent-Antwort
4. Evaluiert gegen Gold-Standards
5. Generiert Berichte (JSON, CSV, Markdown, LaTeX)

Verwendung:
    python -m tests.eval.run_evaluation [--model MODEL_NAME] [--output-dir DIR]

Teil der Masterarbeit: KI-gestützter Universitätsassistent - Evaluierungsframework
"""

import argparse
import time
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Projektroot zum Pfad hinzufügen
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tests.eval.runner import (
    EvaluationScenario,
    Difficulty,
    ScenarioResult,
    EvaluationReport,
    evaluate_scenario,
    aggregate_results,
    save_report,
)
from tests.eval.evaluation import ToolCall, GoldStandard, ArgumentMatchMode


# Token estimation constants for multi-agent systems
# These are rough approximations since we don't have direct access to the LLM tokenizer
# Average English word ~1.3 tokens, we use 2 as conservative upper bound
AVG_TOKENS_PER_WORD = 2
# Average tool call generates ~10 tokens in the response (name + args structure)
AVG_TOKENS_PER_TOOL_CALL = 10


def load_scenarios_from_tests() -> list[EvaluationScenario]:
    """
    Load evaluation scenarios from the test files.
    
    Parses the test files to extract scenarios with their gold standards.
    """
    scenarios = []
    
    # Import test modules to extract scenarios
    from tests.eval.klips import (
        test_register,
        test_apply,
        test_address,
        test_password,
        test_courses,
    )
    from tests.eval.tools import (
        test_email,
        test_duckduckgo,
        test_web_scraper,
        test_multi_negative,
    )
    
    # Map test classes to tool names and categories
    test_modules = [
        (test_register, "klips2_register", "registration"),
        (test_apply, "klips2_apply_study", "application"),
        (test_address, "klips2_change_address", "address"),
        (test_password, "klips2_change_password", "password"),
        (test_courses, "klips2_get_course_details", "courses"),
        (test_email, "send_email", "email"),
        (test_duckduckgo, "duckduckgo_search", "search"),
        (test_web_scraper, "web_scraper", "scraper"),
        (test_multi_negative, "multi", "multi"),
    ]
    
    for module, tool_name, category in test_modules:
        # Find all test classes in the module
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and name.startswith("Test"):
                # Determine difficulty from class name
                if "Easy" in name:
                    difficulty = Difficulty.EASY
                elif "Medium" in name:
                    difficulty = Difficulty.MEDIUM
                elif "Hard" in name:
                    difficulty = Difficulty.HARD
                elif "MultiStep" in name or "Multi" in name:
                    difficulty = Difficulty.MULTI_STEP
                else:
                    difficulty = Difficulty.MEDIUM
                
                # Get test methods
                for method_name in dir(obj):
                    if method_name.startswith("test_"):
                        method = getattr(obj, method_name)
                        if callable(method):
                            # Extract scenario from test method
                            scenario = extract_scenario_from_test(
                                method, 
                                tool_name, 
                                difficulty,
                                category,
                                f"{name}.{method_name}"
                            )
                            if scenario:
                                scenarios.append(scenario)
    
    # Assign short_ids after all scenarios are collected
    for i, scenario in enumerate(scenarios, 1):
        scenario.short_id = f"s{i}"
    
    return scenarios


def extract_scenario_from_test(
    method, 
    tool_name: str, 
    difficulty: Difficulty,
    category: str,
    test_id: str
) -> Optional[EvaluationScenario]:
    """
    Extract an evaluation scenario from a test method.
    
    This parses the test method's source code to extract the user_prompt
    and gold_standard.
    """
    import inspect
    
    try:
        source = inspect.getsource(method)
        
        # Extract user_prompt using regex
        import re
        
        # Find user_prompt = """ ... """
        prompt_match = re.search(
            r'user_prompt\s*=\s*["\'][\'"]{2}(.*?)["\'][\'"]{2}',
            source,
            re.DOTALL
        )
        
        if not prompt_match:
            # Try single quotes
            prompt_match = re.search(
                r'user_prompt\s*=\s*["\']([^"\']+)["\']',
                source,
                re.DOTALL
            )
        
        if not prompt_match:
            return None
        
        user_prompt = prompt_match.group(1).strip()
        
        # Extract gold standard components
        required_tools = []
        tools_match = re.search(
            r'required_tools\s*=\s*\[(.*?)\]',
            source,
            re.DOTALL
        )
        if tools_match:
            tools_str = tools_match.group(1)
            required_tools = re.findall(r'["\']([^"\']+)["\']', tools_str)
        
        # Extract forbidden_tools
        forbidden_tools = set()
        forbidden_match = re.search(
            r'forbidden_tools\s*=\s*\{(.*?)\}',
            source,
            re.DOTALL
        )
        if forbidden_match:
            forbidden_str = forbidden_match.group(1)
            forbidden_tools = set(re.findall(r'["\']([^"\']+)["\']', forbidden_str))
        
        # Extract required_arguments (simplified - just check if present)
        required_arguments = {}
        args_match = re.search(
            r'required_arguments\s*=\s*\{',
            source
        )
        if args_match:
            # For now, we'll do a simplified extraction
            # A more robust parser would be needed for complex nested dicts
            pass
        
        # Determine argument match mode
        if "ArgumentMatchMode.EXACT" in source:
            match_mode = ArgumentMatchMode.EXACT
        elif "ArgumentMatchMode.SEMANTIC" in source:
            match_mode = ArgumentMatchMode.SEMANTIC
        else:
            match_mode = ArgumentMatchMode.NORMALIZED
        
        # Create gold standard
        gold = GoldStandard(
            required_tools=required_tools,
            required_arguments=required_arguments,
            forbidden_tools=forbidden_tools,
            argument_match_mode=match_mode
        )
        
        # Get description from docstring
        description = method.__doc__ or ""
        
        return EvaluationScenario(
            id=test_id,
            tool=tool_name,
            difficulty=difficulty,
            user_prompt=user_prompt,
            gold_standard=gold,
            description=description.strip(),
            category=category
        )
        
    except Exception as e:
        print(f"Warning: Could not extract scenario from {test_id}: {e}")
        return None


def extract_tool_calls_from_response(response: dict) -> list[ToolCall]:
    """
    Extract tool calls from LangGraph agent response.
    
    The response contains messages, some of which may be tool calls.
    """
    tool_calls = []
    
    messages = response.get("messages", [])
    
    for msg in messages:
        # Check for tool calls in AIMessage
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    name=tc.get("name", ""),
                    arguments=tc.get("args", {})
                ))
        
        # Check for ToolMessage (indicates a tool was called)
        if hasattr(msg, 'name') and hasattr(msg, 'content'):
            # This is a tool response, the tool was already called
            pass
    
    return tool_calls


def extract_token_usage_from_response(response: dict) -> tuple[int, int, int]:
    """
    Extract actual token usage from Ollama response metadata.
    
    Ollama provides token counts in:
    - response_metadata: {'prompt_eval_count': X, 'eval_count': Y}
    - usage_metadata: {'input_tokens': X, 'output_tokens': Y, 'total_tokens': Z}
    
    Returns: (input_tokens, output_tokens, total_tokens)
    """
    total_input = 0
    total_output = 0
    
    messages = response.get("messages", [])
    
    for msg in messages:
        # Check for usage_metadata (preferred, cleaner API)
        if hasattr(msg, 'usage_metadata') and msg.usage_metadata:
            usage = msg.usage_metadata
            if isinstance(usage, dict):
                total_input += usage.get('input_tokens', 0)
                total_output += usage.get('output_tokens', 0)
        
        # Fallback to response_metadata
        elif hasattr(msg, 'response_metadata') and msg.response_metadata:
            meta = msg.response_metadata
            if isinstance(meta, dict):
                total_input += meta.get('prompt_eval_count', 0)
                total_output += meta.get('eval_count', 0)
    
    return total_input, total_output, total_input + total_output


def run_single_scenario(agent, scenario: EvaluationScenario) -> ScenarioResult:
    """
    Run a single evaluation scenario through the agent.
    
    NOTE: For single-agent (ReactAgent), this only evaluates tool SELECTION by
    calling the LLM directly. For multi-agent, we run the full agent and extract
    tool calls from the response.
    """
    # Clear agent memory for fresh start
    agent.clear_memory()
    
    # Measure latency
    start_time = time.time()
    
    # Import langchain messages at the top of the function
    from langchain_core.messages import HumanMessage, SystemMessage
    
    try:
        # Check if this is a multi-agent system (doesn't have direct .llm access)
        is_multi_agent = not hasattr(agent, 'llm')
        
        if is_multi_agent:
            # For multi-agent: Use get_tool_selection to test routing + tool selection
            # without actually executing the tools (same as single-agent approach)
            
            # Get tool selection without execution
            tool_selection = agent.get_tool_selection(scenario.user_prompt)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Convert to ToolCall objects
            tool_calls = []
            for tc in tool_selection:
                tool_calls.append(ToolCall(
                    name=tc.get("name", ""),
                    arguments=tc.get("args", {})
                ))
            
            # Token estimation for multi-agent
            # Using conservative constants defined at module level
            input_tokens = len(scenario.user_prompt.split()) * AVG_TOKENS_PER_WORD
            output_tokens = len(tool_calls) * AVG_TOKENS_PER_TOOL_CALL
            total_tokens = input_tokens + output_tokens
            
        else:
            # For single-agent (ReactAgent): Call LLM directly with tools bound
            
            # Get the LLM with tools bound
            llm_with_tools = agent.llm.bind_tools(agent.tools)
            
            # Create message list
            messages = [
                agent.system_message,
                HumanMessage(content=scenario.user_prompt)
            ]
            
            # Invoke LLM to get tool selection (without executing tools)
            response = llm_with_tools.invoke(messages)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Extract tool calls from the AIMessage response
            tool_calls = []
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tc in response.tool_calls:
                    tool_calls.append(ToolCall(
                        name=tc.get("name", ""),
                        arguments=tc.get("args", {})
                    ))
            
            # Extract token usage from the response
            input_tokens, output_tokens, total_tokens = 0, 0, 0
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
        
        # Evaluate
        result = evaluate_scenario(scenario, tool_calls, latency_ms)
        
        # Add token counts
        result.input_tokens = input_tokens
        result.output_tokens = output_tokens
        result.total_tokens = total_tokens
        
        return result
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        
        # Return error result
        return ScenarioResult(
            scenario_id=scenario.id,
            short_id=scenario.short_id,
            tool=scenario.tool,
            difficulty=scenario.difficulty.value,
            category=scenario.category,
            user_prompt=scenario.user_prompt,
            expected_tools=scenario.gold_standard.required_tools,
            actual_tools=[],
            correct_tools=[],
            forbidden_tools_called=[],
            expected_arguments=scenario.gold_standard.required_arguments,
            actual_arguments={},
            correct_arguments={},
            missing_arguments={},
            tool_precision=0.0,
            tool_recall=0.0,
            tool_f1=0.0,
            argument_accuracy=0.0,
            exact_match=False,
            latency_ms=latency_ms,
            error=str(e),
            input_tokens=0,
            output_tokens=0,
            total_tokens=0
        )


def run_evaluation(
    model_name: Optional[str] = None,
    output_dir: str = "data/eval_results",
    max_scenarios: Optional[int] = None,
    verbose: bool = True,
    agent_mode: str = "single"
) -> EvaluationReport:
    """
    Run the full evaluation suite.
    
    Args:
        model_name: Optional model name override
        output_dir: Directory for output files (will be organized by agent mode)
        max_scenarios: Limit number of scenarios (for testing)
        verbose: Print progress
        agent_mode: 'single' for ReactAgent, 'multi' for MultiAgentSystem
    
    Returns:
        EvaluationReport with all results
    """
    from config.settings import settings
    from src.agent import create_agent
    
    # Get model info
    actual_model = model_name or settings.OLLAMA_MODEL
    
    # Mode label and subdirectory for output organization
    mode_labels = {
        "single": "Single-Agent",
        "multi": "Multi-Agent",
        "confirmation": "Confirmation-Agent",
        "constrained": "Constrained-Agent"
    }
    mode_subdirs = {
        "single": "single_agent",
        "multi": "multi_agent",
        "confirmation": "confirmation_agent",
        "constrained": "constrained_agent"
    }
    mode_label = mode_labels.get(agent_mode, "Single-Agent")
    mode_subdir = mode_subdirs.get(agent_mode, "single_agent")
    actual_output_dir = f"{output_dir}/{mode_subdir}"
    
    if verbose:
        print("=" * 60)
        print("Tool Evaluation Suite")
        print("=" * 60)
        print(f"Model: {actual_model}")
        print(f"Agent Mode: {mode_label}")
        print(f"Output: {actual_output_dir}")
        print()
    
    # Load scenarios
    if verbose:
        print("Loading scenarios...")
    
    scenarios = load_scenarios_from_tests()
    
    if max_scenarios:
        scenarios = scenarios[:max_scenarios]
    
    if verbose:
        print(f"Loaded {len(scenarios)} scenarios")
        print()
    
    # Initialize agent
    if verbose:
        print(f"Initializing {mode_label}...")
    
    # Override model in settings if specified
    if model_name:
        settings.OLLAMA_MODEL = model_name
    
    agent = create_agent(mode=agent_mode)
    
    if verbose:
        tools_count = len(agent.get_available_tools())
        print(f"Agent ready with {tools_count} tools")
        print()
    
    # Run evaluation
    if verbose:
        print("Running evaluation...")
        print("-" * 60)
    
    results = []
    start_time = time.time()
    
    for i, scenario in enumerate(scenarios):
        if verbose:
            print(f"[{i+1}/{len(scenarios)}] {scenario.id}...", end=" ", flush=True)
        
        result = run_single_scenario(agent, scenario)
        results.append(result)
        
        if verbose:
            status = "✓" if result.exact_match else "✗"
            print(f"{status} (F1={result.tool_f1:.2f}, {result.latency_ms:.0f}ms)")
    
    total_duration = time.time() - start_time
    
    if verbose:
        print("-" * 60)
        print()
    
    # Aggregate results
    metrics = aggregate_results(results)
    
    # Create report
    report = EvaluationReport(
        timestamp=datetime.now().isoformat(),
        model_name=actual_model,
        model_version="1.0",  # Could be extracted from settings
        total_scenarios=len(scenarios),
        total_duration_seconds=total_duration,
        individual_results=results,
        aggregated_metrics=metrics,
        evaluation_config={
            "max_scenarios": max_scenarios,
            "output_dir": actual_output_dir,
            "agent_mode": agent_mode,
        }
    )
    
    # Print summary
    if verbose:
        print("=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        print(f"Agent Mode: {mode_label}")
        print(f"Total scenarios: {metrics.total_scenarios}")
        print(f"Exact match rate: {metrics.exact_match_rate:.1%}")
        print(f"Mean F1: {metrics.mean_f1:.3f} (±{metrics.std_f1:.3f})")
        print(f"Mean Precision: {metrics.mean_precision:.3f}")
        print(f"Mean Recall: {metrics.mean_recall:.3f}")
        print(f"Mean Argument Accuracy: {metrics.mean_argument_accuracy:.3f}")
        print()
        print(f"Forbidden tool violations: {metrics.forbidden_tool_violations}")
        print(f"Missing tools: {metrics.missing_tool_count}")
        print(f"Extra tools: {metrics.extra_tool_count}")
        print(f"Errors: {metrics.total_errors}")
        print()
        print("⏱️  TIME & TOKEN STATISTICS")
        print("-" * 40)
        print(f"Total duration: {total_duration:.1f}s ({total_duration/60:.1f} min)")
        print(f"Avg latency per scenario: {metrics.avg_latency_ms:.0f}ms")
        print(f"Total tokens (estimated): {metrics.total_tokens:,}")
        print(f"  - Input tokens: {metrics.total_input_tokens:,}")
        print(f"  - Output tokens: {metrics.total_output_tokens:,}")
        print(f"Avg tokens per scenario: {metrics.avg_tokens_per_scenario:.0f}")
        print()
    
    # Save report
    save_report(report, actual_output_dir)
    
    return report


def export_scenarios(output_dir: str = "data/eval_scenarios", format: str = "all"):
    """
    Export all evaluation scenarios without running the evaluation.
    
    Args:
        output_dir: Directory to save exported scenarios
        format: Export format - 'csv', 'json', 'txt', or 'all'
    """
    import csv
    import json
    
    print("Loading scenarios...")
    scenarios = load_scenarios_from_tests()
    print(f"Loaded {len(scenarios)} scenarios")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Prepare scenario data
    scenario_data = []
    for i, s in enumerate(scenarios, 1):
        scenario_data.append({
            "short_id": f"s{i}",  # Short ID: s1, s2, s3, ...
            "id": s.id,
            "tool": s.tool,
            "difficulty": s.difficulty.value,
            "category": s.category,
            "description": s.description,
            "user_prompt": s.user_prompt.strip(),
            "required_tools": s.gold_standard.required_tools,
            "forbidden_tools": list(s.gold_standard.forbidden_tools) if s.gold_standard.forbidden_tools else [],
            "argument_match_mode": s.gold_standard.argument_match_mode.value,
        })
    
    # Export as JSON
    if format in ("json", "all"):
        json_path = output_path / "scenarios.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(scenario_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved: {json_path}")
    
    # Export as CSV
    if format in ("csv", "all"):
        csv_path = output_path / "scenarios.csv"
        fieldnames = ["short_id", "id", "tool", "difficulty", "category", "description", 
                      "user_prompt", "required_tools", "forbidden_tools"]
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for s in scenario_data:
                row = {k: v for k, v in s.items() if k in fieldnames}
                row["required_tools"] = ";".join(row["required_tools"])
                row["forbidden_tools"] = ";".join(row["forbidden_tools"])
                # Clean prompt for CSV
                row["user_prompt"] = " ".join(row["user_prompt"].split())
                writer.writerow(row)
        print(f"✅ Saved: {csv_path}")
    
    # Export as plain text (one prompt per line, easy to read)
    if format in ("txt", "all"):
        txt_path = output_path / "scenarios.txt"
        with open(txt_path, "w", encoding="utf-8") as f:
            for i, s in enumerate(scenario_data, 1):
                f.write(f"{'='*60}\n")
                f.write(f"SCENARIO {s['short_id']} ({s['id']})\n")
                f.write(f"{'='*60}\n")
                f.write(f"Tool: {s['tool']}\n")
                f.write(f"Difficulty: {s['difficulty']}\n")
                f.write(f"Category: {s['category']}\n")
                f.write(f"Description: {s['description']}\n")
                f.write(f"\n--- USER PROMPT ---\n")
                f.write(f"{s['user_prompt']}\n")
                f.write(f"\n--- EXPECTED ---\n")
                if s['required_tools']:
                    f.write(f"Required tools: {', '.join(s['required_tools'])}\n")
                else:
                    f.write(f"Required tools: NONE (should not call any tool)\n")
                if s['forbidden_tools']:
                    f.write(f"Forbidden tools: {', '.join(s['forbidden_tools'])}\n")
                f.write(f"\n\n")
        print(f"✅ Saved: {txt_path}")
    
    # Export as Markdown (nice for documentation)
    if format in ("md", "all"):
        md_path = output_path / "scenarios.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Evaluation Scenarios\n\n")
            f.write(f"Total: {len(scenario_data)} scenarios\n\n")
            
            # Group by tool
            by_tool = {}
            for s in scenario_data:
                tool = s['tool']
                if tool not in by_tool:
                    by_tool[tool] = []
                by_tool[tool].append(s)
            
            f.write("## Summary by Tool\n\n")
            f.write("| Tool | Count |\n")
            f.write("|------|-------|\n")
            for tool, items in sorted(by_tool.items()):
                f.write(f"| `{tool}` | {len(items)} |\n")
            f.write("\n")
            
            # Summary by difficulty
            by_diff = {}
            for s in scenario_data:
                diff = s['difficulty']
                if diff not in by_diff:
                    by_diff[diff] = 0
                by_diff[diff] += 1
            
            f.write("## Summary by Difficulty\n\n")
            f.write("| Difficulty | Count |\n")
            f.write("|------------|-------|\n")
            for diff, count in sorted(by_diff.items()):
                f.write(f"| {diff} | {count} |\n")
            f.write("\n")
            
            # All scenarios
            f.write("## All Scenarios\n\n")
            for tool, items in sorted(by_tool.items()):
                f.write(f"### {tool}\n\n")
                for s in items:
                    f.write(f"#### {s['id']}\n\n")
                    f.write(f"**Difficulty:** {s['difficulty']}  \n")
                    f.write(f"**Category:** {s['category']}  \n")
                    if s['description']:
                        f.write(f"**Description:** {s['description']}  \n")
                    f.write(f"\n**User Prompt:**\n```\n{s['user_prompt']}\n```\n\n")
                    if s['required_tools']:
                        f.write(f"**Expected:** Call `{', '.join(s['required_tools'])}`\n\n")
                    else:
                        f.write(f"**Expected:** Do NOT call any tool")
                        if s['forbidden_tools']:
                            f.write(f" (forbidden: `{', '.join(s['forbidden_tools'])}`)")
                        f.write("\n\n")
        print(f"✅ Saved: {md_path}")
    
    print(f"\n📊 Exported {len(scenarios)} scenarios to {output_path}/")
    
    return scenarios


def main():
    parser = argparse.ArgumentParser(description="Run tool evaluation suite")
    parser.add_argument("--model", type=str, help="Model name to use")
    parser.add_argument("--output-dir", type=str, default="data/eval_results",
                        help="Output directory for results")
    parser.add_argument("--max-scenarios", type=int, help="Limit scenarios (for testing)")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress output")
    parser.add_argument("--export-only", action="store_true", 
                        help="Only export scenarios without running evaluation")
    parser.add_argument("--export-format", type=str, default="all",
                        choices=["csv", "json", "txt", "md", "all"],
                        help="Export format (default: all)")
    parser.add_argument("--export-dir", type=str, default="data/eval_scenarios",
                        help="Directory for exported scenarios")
    parser.add_argument("--agent-mode", type=str, default="single",
                        choices=["single", "multi", "confirmation", "constrained", "confirmation"],
                        help="Agent mode: 'single' for ReactAgent, 'multi' for MultiAgentSystem, 'confirmation' for ConfirmationAgent, 'constrained' for ConstrainedAgent, 'confirmation' for ConfirmationAgent (default: single)")
    
    args = parser.parse_args()
    
    if args.export_only:
        export_scenarios(
            output_dir=args.export_dir,
            format=args.export_format
        )
    else:
        run_evaluation(
            model_name=args.model,
            output_dir=args.output_dir,
            max_scenarios=args.max_scenarios,
            verbose=not args.quiet,
            agent_mode=args.agent_mode
        )


if __name__ == "__main__":
    main()
