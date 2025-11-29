"""
Core Evaluation Logic Tests

This module tests the fundamental evaluation logic for tool usage assessment.
Tests cover basic success/failure scenarios for the evaluation framework.

Part of Master's Thesis: AI-Powered University Assistant Evaluation Framework
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from tests.eval.evaluation import (
    ToolCall,
    GoldStandard,
    EvaluationResult,
    evaluate_tool_run,
    ArgumentMatchMode,
    is_task_successful,
)


# =============================================================================
# SECTION 1: Basic Success Cases
# =============================================================================

class TestBasicSuccessCases:
    """Tests for basic successful tool usage scenarios."""

    def test_success_single_tool_no_args(self):
        """
        ✅ SUCCESS: Single tool called with no required arguments.
        
        Scenario: Agent calls the correct tool, no arguments are validated.
        Expected: Task should succeed.
        """
        tool_calls = [ToolCall(name="duckduckgo_search", arguments={"query": "test"})]
        gold = GoldStandard(required_tools=["duckduckgo_search"])
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True
        assert len(result.failure_reasons) == 0
        assert "duckduckgo_search" in result.matched_tools

    def test_success_single_tool_with_correct_args(self):
        """
        ✅ SUCCESS: Single tool called with all correct arguments.
        
        Scenario: Agent calls correct tool with exact expected arguments.
        Expected: Task should succeed with all arguments matched.
        """
        tool_calls = [
            ToolCall(
                name="send_email",
                arguments={"subject": "Test Betreff", "body": "Test Nachricht"}
            )
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {"subject": "Test Betreff", "body": "Test Nachricht"}
            }
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True
        assert len(result.failure_reasons) == 0

    def test_success_with_extra_arguments(self):
        """
        ✅ SUCCESS: Tool called with extra arguments beyond required ones.
        
        Scenario: Agent provides more arguments than strictly required.
        Expected: Task should succeed (extra args are allowed by default).
        """
        tool_calls = [
            ToolCall(
                name="send_email",
                arguments={
                    "subject": "Test",
                    "body": "Message",
                    "priority": "high",  # Extra argument
                    "cc": "other@email.com"  # Extra argument
                }
            )
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={"send_email": {"subject": "Test", "body": "Message"}}
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True

    def test_success_with_whitespace_normalization(self):
        """
        ✅ SUCCESS: Arguments match after whitespace normalization.
        
        Scenario: Arguments have minor whitespace differences.
        Expected: Task should succeed with NORMALIZED mode.
        """
        tool_calls = [
            ToolCall(
                name="send_email",
                arguments={"subject": "  Test   Betreff  ", "body": "Nachricht"}
            )
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={"send_email": {"subject": "Test Betreff", "body": "Nachricht"}},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True

    def test_success_case_insensitive_normalized(self):
        """
        ✅ SUCCESS: Arguments match with different casing in NORMALIZED mode.
        
        Scenario: Agent uses different letter casing than expected.
        Expected: Task should succeed with NORMALIZED mode.
        """
        tool_calls = [
            ToolCall(
                name="duckduckgo_search",
                arguments={"query": "UNIVERSITÄT ZU KÖLN"}
            )
        ]
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            required_arguments={"duckduckgo_search": {"query": "universität zu köln"}},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True


# =============================================================================
# SECTION 2: Basic Failure Cases
# =============================================================================

class TestBasicFailureCases:
    """Tests for basic failure scenarios in tool usage."""

    def test_fail_no_tool_called(self):
        """
        ❌ FAILURE: No tool was called at all.
        
        Scenario: Agent fails to invoke any tool.
        Expected: Task should fail with clear error message.
        """
        tool_calls = []
        gold = GoldStandard(required_tools=["send_email"])
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "No tool was called" in result.failure_reasons
        assert "send_email" in result.missing_tools

    def test_fail_wrong_tool_called(self):
        """
        ❌ FAILURE: Different tool called than required.
        
        Scenario: Agent calls web_scraper instead of send_email.
        Expected: Task should fail - required tool is missing.
        """
        tool_calls = [ToolCall(name="web_scraper", arguments={"url": "http://test.com"})]
        gold = GoldStandard(required_tools=["send_email"])
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "send_email" in result.missing_tools
        assert any("send_email" in reason for reason in result.failure_reasons)

    def test_fail_forbidden_tool_called(self):
        """
        ❌ FAILURE: Forbidden tool was called.
        
        Scenario: Agent calls a tool explicitly marked as forbidden.
        Expected: Task should fail with forbidden tool error.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Test", "body": "Test"}),
            ToolCall(name="web_scraper", arguments={"url": "http://malicious.com"})
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            forbidden_tools={"web_scraper"}
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "web_scraper" in result.wrong_tools
        assert any("Forbidden tool" in reason for reason in result.failure_reasons)

    def test_fail_missing_required_argument(self):
        """
        ❌ FAILURE: Required argument is missing.
        
        Scenario: Agent calls correct tool but omits a required argument.
        Expected: Task should fail with missing argument error.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Test"})  # Missing 'body'
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={"send_email": {"subject": "Test", "body": "Required body"}}
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "send_email" in result.missing_arguments
        assert "body" in result.missing_arguments["send_email"]

    def test_fail_wrong_argument_value(self):
        """
        ❌ FAILURE: Argument has incorrect value.
        
        Scenario: Agent calls correct tool with wrong argument value.
        Expected: Task should fail with wrong value error.
        """
        tool_calls = [
            ToolCall(
                name="send_email",
                arguments={"subject": "Wrong Subject", "body": "Test"}
            )
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={"send_email": {"subject": "Correct Subject", "body": "Test"}}
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "send_email" in result.wrong_arguments
        assert "subject" in result.wrong_arguments["send_email"]

    def test_fail_exact_match_with_whitespace_difference(self):
        """
        ❌ FAILURE: Arguments differ by whitespace in EXACT mode.
        
        Scenario: Minor whitespace differences should fail in EXACT mode.
        Expected: Task should fail due to exact match requirement.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Test  Subject"})
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={"send_email": {"subject": "Test Subject"}},
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False


# =============================================================================
# SECTION 3: Multiple Tool Scenarios
# =============================================================================

class TestMultipleToolScenarios:
    """Tests for scenarios involving multiple tool calls."""

    def test_success_multiple_required_tools_unordered(self):
        """
        ✅ SUCCESS: Multiple required tools called in any order.
        
        Scenario: Two tools required, called in reverse order.
        Expected: Task should succeed (order not enforced).
        """
        tool_calls = [
            ToolCall(name="duckduckgo_search", arguments={"query": "test"}),
            ToolCall(name="send_email", arguments={"subject": "Result", "body": "Found it"})
        ]
        gold = GoldStandard(
            required_tools=["send_email", "duckduckgo_search"],
            ordered=False
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True

    def test_success_multiple_tools_correct_order(self):
        """
        ✅ SUCCESS: Multiple required tools called in correct order.
        
        Scenario: Ordered sequence requirement met exactly.
        Expected: Task should succeed.
        """
        tool_calls = [
            ToolCall(name="duckduckgo_search", arguments={"query": "info"}),
            ToolCall(name="send_email", arguments={"subject": "Info", "body": "Here"})
        ]
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "send_email"],
            ordered=True
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True

    def test_fail_multiple_tools_wrong_order(self):
        """
        ❌ FAILURE: Multiple tools called in wrong order.
        
        Scenario: Ordered sequence requirement violated.
        Expected: Task should fail with sequence error.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Early", "body": "Too soon"}),
            ToolCall(name="duckduckgo_search", arguments={"query": "info"})
        ]
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "send_email"],
            ordered=True
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert result.sequence_error is not None

    def test_fail_only_one_of_multiple_tools_called(self):
        """
        ❌ FAILURE: Only some of the required tools were called.
        
        Scenario: Agent calls only 1 of 2 required tools.
        Expected: Task should fail with missing tool error.
        """
        tool_calls = [
            ToolCall(name="duckduckgo_search", arguments={"query": "test"})
        ]
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "send_email"]
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "send_email" in result.missing_tools


# =============================================================================
# SECTION 4: Edge Cases and Special Scenarios
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_tool_called_multiple_times_last_used(self):
        """
        Edge case: Same tool called multiple times.
        
        Scenario: Agent retries a tool call with corrected arguments.
        Expected: The last call should be used for evaluation.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Wrong", "body": "First try"}),
            ToolCall(name="send_email", arguments={"subject": "Correct", "body": "Second try"})
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={"send_email": {"subject": "Correct", "body": "Second try"}}
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True

    def test_optional_tool_not_called_still_success(self):
        """
        ✅ SUCCESS: Optional tool not called should not affect success.
        
        Scenario: An optional tool exists but wasn't called.
        Expected: Task should succeed.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Test", "body": "Body"})
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            optional_tools={"web_scraper", "duckduckgo_search"}
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True

    def test_extra_tools_allowed_by_default(self):
        """
        ✅ SUCCESS: Extra tools allowed when allow_extra_tools=True (default).
        
        Scenario: Agent calls additional unspecified tools.
        Expected: Task should succeed, extra tools recorded.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Test", "body": "Body"}),
            ToolCall(name="unknown_tool", arguments={"arg": "value"})
        ]
        gold = GoldStandard(required_tools=["send_email"])
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is True
        assert "unknown_tool" in result.extra_tools

    def test_extra_tools_forbidden_when_disabled(self):
        """
        ❌ FAILURE: Extra tools cause failure when not allowed.
        
        Scenario: Agent calls unspecified tool with allow_extra_tools=False.
        Expected: Task should fail.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={"subject": "Test", "body": "Body"}),
            ToolCall(name="unknown_tool", arguments={"arg": "value"})
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            allow_extra_tools=False
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "unknown_tool" in result.extra_tools

    def test_empty_arguments_dict(self):
        """
        Edge case: Tool called with empty arguments dict.
        
        Scenario: Tool is called but with no arguments at all.
        Expected: Should fail if arguments are required.
        """
        tool_calls = [
            ToolCall(name="send_email", arguments={})
        ]
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={"send_email": {"subject": "Test"}}
        )
        
        result = evaluate_tool_run(tool_calls, gold)
        
        assert result.success is False
        assert "subject" in result.missing_arguments.get("send_email", [])


# =============================================================================
# SECTION 5: Convenience Function Tests
# =============================================================================

class TestConvenienceFunctions:
    """Tests for helper and convenience functions."""

    def test_is_task_successful_true(self):
        """Test is_task_successful returns True for success."""
        tool_calls = [ToolCall(name="send_email", arguments={})]
        gold = GoldStandard(required_tools=["send_email"])
        
        assert is_task_successful(tool_calls, gold) is True

    def test_is_task_successful_false(self):
        """Test is_task_successful returns False for failure."""
        tool_calls = [ToolCall(name="wrong_tool", arguments={})]
        gold = GoldStandard(required_tools=["send_email"])
        
        assert is_task_successful(tool_calls, gold) is False
