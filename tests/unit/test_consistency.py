"""
Consistency checks between the four source-of-truth artefacts:

  1. TOOL_SPECS          – src/agent/tool_specs.py
  2. Pydantic schemas    – TOOL_SCHEMAS in constrained_agent.py
  3. Eval scenarios      – eval/scenarios/**  and tests/eval/**
  4. Agent system prompts – _get_system_prompt() methods in every agent file

All tests are pure static analysis (no LLM, no network, no file writes).
"""

import re
from pathlib import Path
from typing import Dict, Set

import pytest

from src.agent.tool_specs import TOOL_SPECS
from src.agent.constrained.constrained_agent import TOOL_SCHEMAS

# Project root (two levels up from this file: tests/unit/ → tests/ → root)
ROOT = Path(__file__).parents[2]


# ---------------------------------------------------------------------------
# 1. Pydantic schema ↔ TOOL_SPECS
# ---------------------------------------------------------------------------

class TestSchemaConsistency:
    """TOOL_SCHEMAS (constrained_agent) must align with TOOL_SPECS on every field."""

    def test_all_tool_specs_have_a_pydantic_schema(self):
        missing = set(TOOL_SPECS) - set(TOOL_SCHEMAS)
        assert not missing, (
            f"Tools defined in TOOL_SPECS but missing a Pydantic schema: {missing}\n"
            "Add a schema class and register it in TOOL_SCHEMAS in constrained_agent.py."
        )

    def test_no_extra_schemas_beyond_tool_specs(self):
        extra = set(TOOL_SCHEMAS) - set(TOOL_SPECS)
        assert not extra, (
            f"TOOL_SCHEMAS has entries not present in TOOL_SPECS: {extra}\n"
            "Either add the tool to TOOL_SPECS or remove the orphaned schema."
        )

    def test_spec_required_params_are_required_in_schema(self):
        """Every required_param in TOOL_SPECS must be a required (no-default) field in the schema."""
        errors: list[str] = []
        for tool_name, schema_cls in TOOL_SCHEMAS.items():
            spec_required = set(TOOL_SPECS[tool_name].get("required_params", {}).keys())
            schema_required = {
                name for name, field in schema_cls.model_fields.items()
                if field.is_required()
            }
            missing_in_schema = spec_required - schema_required
            if missing_in_schema:
                errors.append(
                    f"  {tool_name}: TOOL_SPECS marks {missing_in_schema!r} as required, "
                    f"but those fields have a default in the schema."
                )
        assert not errors, (
            "Required-param mismatches between TOOL_SPECS and Pydantic schemas:\n"
            + "\n".join(errors)
        )

    def test_spec_optional_params_present_in_schema(self):
        """Every optional_param in TOOL_SPECS must appear as a field (any kind) in the schema."""
        errors: list[str] = []
        for tool_name, schema_cls in TOOL_SCHEMAS.items():
            spec_optional = set(TOOL_SPECS[tool_name].get("optional_params", {}).keys())
            schema_fields = set(schema_cls.model_fields.keys())
            missing = spec_optional - schema_fields
            if missing:
                errors.append(
                    f"  {tool_name}: TOOL_SPECS optional params {missing!r} "
                    f"have no corresponding field in the schema."
                )
        assert not errors, (
            "Optional-param mismatches between TOOL_SPECS and Pydantic schemas:\n"
            + "\n".join(errors)
        )


# ---------------------------------------------------------------------------
# 2. Eval scenarios ↔ TOOL_SPECS
# ---------------------------------------------------------------------------

class TestScenarioConsistency:
    """Eval scenario files must reference only valid TOOL_SPECS tool names."""

    SCENARIO_DIRS = ["eval/scenarios", "tests/eval"]

    # Matches: required_tools=["tool_a", "tool_b"]   (list may span one line)
    _LIST_RE = re.compile(r'required_tools\s*=\s*\[([^\]]*)\]', re.DOTALL)
    # Matches string literals inside a list bracket
    _STRING_RE = re.compile(r'"([^"\\]+)"|\'([^\'\\]+)\'')
    # Matches first-level keys of required_arguments = { "tool_name": { ...
    _ARGS_KEY_RE = re.compile(r'required_arguments\s*=\s*\{[^{}]*?"([^"]+)"\s*:', re.DOTALL)

    def _collect_required_tools(self) -> Dict[str, Set[str]]:
        """Return {relative_path: {tool_name, ...}} for every scenario file."""
        result: Dict[str, Set[str]] = {}
        for rel_dir in self.SCENARIO_DIRS:
            base = ROOT / rel_dir
            if not base.exists():
                continue
            for path in base.rglob("*.py"):
                text = path.read_text()
                tools: Set[str] = set()
                for m in self._LIST_RE.finditer(text):
                    inner = m.group(1)
                    for sm in self._STRING_RE.finditer(inner):
                        name = sm.group(1) or sm.group(2)
                        if name:
                            tools.add(name)
                if tools:
                    result[str(path.relative_to(ROOT))] = tools
        return result

    def test_scenario_tool_names_exist_in_tool_specs(self):
        known = set(TOOL_SPECS.keys())
        errors: list[str] = []
        for file_path, tools in self._collect_required_tools().items():
            unknown = tools - known
            if unknown:
                errors.append(f"  {file_path}: unknown tool names {unknown!r}")
        assert not errors, (
            "Scenario files reference tool names not present in TOOL_SPECS:\n"
            + "\n".join(errors)
        )

    def test_required_arguments_keys_exist_in_tool_specs(self):
        known = set(TOOL_SPECS.keys())
        errors: list[str] = []
        for rel_dir in self.SCENARIO_DIRS:
            base = ROOT / rel_dir
            if not base.exists():
                continue
            for path in base.rglob("*.py"):
                text = path.read_text()
                for m in self._ARGS_KEY_RE.finditer(text):
                    name = m.group(1)
                    if name and name not in known:
                        errors.append(
                            f"  {path.relative_to(ROOT)}: "
                            f"required_arguments references unknown tool '{name}'"
                        )
        assert not errors, (
            "required_arguments dicts reference tool names not in TOOL_SPECS:\n"
            + "\n".join(errors)
        )


# ---------------------------------------------------------------------------
# 3. Agent system prompts ↔ TOOL_SPECS
# ---------------------------------------------------------------------------

class TestPromptConsistency:
    """Agent source files must not hardcode tool names that are absent from TOOL_SPECS."""

    AGENT_FILES = [
        "src/agent/react_agent.py",
        "src/agent/confirmation/confirmation_agent.py",
        "src/agent/constrained/constrained_agent.py",
        "src/agent/multi/klips_agent.py",
        "src/agent/multi/email_agent.py",
        "src/agent/multi/knowledge_agent.py",
        "src/agent/multi/base_agent.py",
        "src/agent/multi/orchestrator.py",
    ]

    # Only match string literals that look exactly like tool names:
    #   klips2_*  |  duckduckgo_*  |  university_knowledge_*  |  web_scraper  |  send_email
    _TOOL_LITERAL_RE = re.compile(
        r'["\']('
        r'klips2_[a-z_]+'
        r'|duckduckgo_[a-z_]+'
        r'|university_knowledge_[a-z_]+'
        r'|web_scraper'
        r'|send_email'
        r')["\']'
    )

    # Matches hardcoded "- tool_name: param1, param2, ..." summary lines in prompts
    _PARAM_SUMMARY_RE = re.compile(
        r'["\']- ([a-z][a-z0-9_]+): ([^\n"\']+)["\']'
    )

    def _find_tool_literals(self, source: str) -> Set[str]:
        return {m.group(1) for m in self._TOOL_LITERAL_RE.finditer(source)}

    def test_no_unknown_tool_names_in_agent_files(self):
        known = set(TOOL_SPECS.keys())
        errors: list[str] = []
        for rel_path in self.AGENT_FILES:
            path = ROOT / rel_path
            if not path.exists():
                continue
            found = self._find_tool_literals(path.read_text())
            unknown = found - known
            if unknown:
                errors.append(f"  {rel_path}: string literals resembling unknown tools: {unknown!r}")
        assert not errors, (
            "Agent files contain tool-name-like string literals not in TOOL_SPECS:\n"
            + "\n".join(errors)
        )

    def test_constrained_agent_hardcoded_param_lists_match_tool_specs(self):
        """
        Lines like ``"- klips2_register: vorname, nachname, ..."`` in
        constrained_agent._get_system_prompt must list exactly the
        required_params from TOOL_SPECS (no more, no fewer).
        """
        path = ROOT / "src/agent/constrained/constrained_agent.py"
        # Only look inside _get_system_prompt to avoid false positives
        source = path.read_text()
        start = source.find("def _get_system_prompt")
        # Find the next top-level def (same indentation) to delimit the method
        next_def = re.search(r'\n    def ', source[start + 1:])
        method_src = source[start: start + 1 + next_def.start()] if next_def else source[start:]

        errors: list[str] = []
        for m in self._PARAM_SUMMARY_RE.finditer(method_src):
            tool_name = m.group(1)
            if tool_name not in TOOL_SPECS:
                errors.append(
                    f"  Prompt line references unknown tool '{tool_name}'"
                )
                continue
            # Parse raw param tokens, stripping inline comments like "(bei ...)"
            raw_tokens = [chunk.strip() for chunk in m.group(2).split(",")]
            hardcoded = set()
            for token in raw_tokens:
                param = token.split()[0].strip() if token.split() else ""
                if param:
                    hardcoded.add(param)

            spec_required = set(TOOL_SPECS[tool_name].get("required_params", {}).keys())
            diff = spec_required.symmetric_difference(hardcoded)
            if diff:
                errors.append(
                    f"  {tool_name}: hardcoded prompt params {sorted(hardcoded)} "
                    f"differ from TOOL_SPECS required_params {sorted(spec_required)} "
                    f"(symmetric diff: {diff!r})"
                )
        assert not errors, (
            "Hardcoded parameter lists in constrained_agent._get_system_prompt "
            "are out of sync with TOOL_SPECS:\n" + "\n".join(errors)
        )
