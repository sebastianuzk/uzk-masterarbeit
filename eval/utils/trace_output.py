"""Coloured terminal output helpers for evaluation runs."""

from __future__ import annotations

import json
from typing import Any

# ANSI colour codes
_GRN = "\033[92m"
_RED = "\033[91m"
_YEL = "\033[93m"
_CYA = "\033[96m"
_DIM = "\033[33m"
_RST = "\033[0m"


def print_scenario_outcome(result: Any) -> None:
    """Print a one- or few-line summary explaining why a scenario passed or failed.

    Args:
        result: A ``ScenarioResult`` instance from ``eval.core.runner``.
    """
    if result.exact_match:
        tools_str = ", ".join(result.actual_tools) if result.actual_tools else "(none)"
        print(f"  {_GRN}✓ Tools: {tools_str}{_RST}")
        if result.actual_arguments:
            for tool, args in result.actual_arguments.items():
                if args:
                    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                    print(f"  {_GRN}  {tool}({args_str}){_RST}")
    else:
        missing_tools = [t for t in result.expected_tools if t not in result.actual_tools]
        wrong_tools   = list(result.forbidden_tools_called)
        extra_tools   = [
            t for t in result.actual_tools
            if t not in result.expected_tools and t not in result.forbidden_tools_called
        ]
        if wrong_tools:
            print(f"  {_RED}✗ Forbidden tool called: {wrong_tools}{_RST}")
        if missing_tools:
            print(f"  {_RED}✗ Missing tools: {missing_tools}{_RST}")
        if extra_tools:
            print(f"  {_RED}✗ Unexpected extra tools: {extra_tools}{_RST}")
        # missing_arguments is already computed with the correct semantic match mode —
        # use it directly to avoid re-implementing the comparison logic here.
        for tool, bad_args in result.missing_arguments.items():
            actual_args = result.actual_arguments.get(tool, {})
            for arg, exp_val in bad_args.items():
                act_val = actual_args.get(arg)
                if act_val is None:
                    print(f"  {_RED}✗ {tool}.{arg}: missing (expected {repr(exp_val)}){_RST}")
                else:
                    print(f"  {_RED}✗ {tool}.{arg}: expected {repr(exp_val)}, got {repr(act_val)}{_RST}")


def print_agent_trace(agent: Any, *, max_raw_lines: int = 30) -> None:
    """Print the agent's conversation trace in coloured format and then clear it.

    Only does anything if ``agent`` has a non-empty ``conversation_trace`` list.

    Args:
        agent: Any agent object that may carry a ``conversation_trace`` attribute.
        max_raw_lines: Maximum number of raw-output lines to print per step.
    """
    if not (hasattr(agent, "conversation_trace") and agent.conversation_trace):
        return

    trace = agent.conversation_trace
    print(f"  {_YEL}--- Model trace ({len(trace)} step(s)) ---{_RST}")
    for step in trace:
        step_name = step.get("step", "?")
        tool_name = step.get("tool_name", "")
        header_parts = [f"step={step_name}"]
        if tool_name:
            header_parts.append(f"tool={tool_name}")
        print(f"  {_CYA}{' | '.join(header_parts)}{_RST}")

        raw_out = step.get("raw_output", "")
        if isinstance(raw_out, list):
            raw_out = " ".join(str(b) for b in raw_out)
        if raw_out:
            lines = raw_out.strip().split("\n")
            for line in lines[:max_raw_lines]:
                print(f"    {_DIM}{line}{_RST}")
            if len(lines) > max_raw_lines:
                print(f"    {_DIM}... ({len(lines) - max_raw_lines} more lines){_RST}")

        proposed = step.get("tool_calls_proposed")
        routed_to = step.get("routed_to")
        if routed_to:
            print(f"    {_DIM}Routed to: {routed_to}{_RST}")
        if proposed:
            print(f"    {_DIM}Proposed: {json.dumps(proposed, ensure_ascii=False)}{_RST}")

        val_ok  = step.get("validation_success")
        val_err = step.get("validation_error")
        parsed  = step.get("parsed_result")
        if val_ok is True:
            print(f"    {_GRN}✓ validated{_RST}")
        elif val_ok is False:
            print(f"    {_RED}✗ validation failed{_RST}")
        if val_err:
            print(f"    {_RED}Reason: {val_err}{_RST}")
        if parsed:
            print(f"    {_DIM}Parsed: {json.dumps(parsed, ensure_ascii=False)}{_RST}")

    print(f"  {_YEL}--- end trace ---{_RST}")
    agent.conversation_trace.clear()
