"""
KLIPS2 Change Password Tool - Evaluation Test Scenarios

Tool: klips2_change_password
Purpose: Change KLIPS2 account password

Required arguments:
- current_password (current password)
- new_password (new password)
- confirm_password (confirmation of new password)

Part of Master's Thesis: AI-Powered University Assistant Evaluation Framework
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from tests.eval.evaluation import (
    GoldStandard,
    ArgumentMatchMode,
)

pytestmark = [pytest.mark.llm, pytest.mark.klips, pytest.mark.eval]


class TestPasswordEasy:
    """Easy scenarios - all password information provided."""

    def test_password_01_complete_request(self):
        """
        EASY: Complete password change with all fields.
        """
        user_prompt = """
        Ich möchte mein KLIPS-Passwort ändern.
        Aktuelles Passwort: OldPass123!
        Neues Passwort: NewSecure456!
        Bestätigung: NewSecure456!
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password"],
            required_arguments={
                "klips2_change_password": {
                    "current_password": "OldPass123!",
                    "new_password": "NewSecure456!",
                    "confirm_password": "NewSecure456!"
                }
            },
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        assert gold.required_tools == ["klips2_change_password"]


class TestPasswordMedium:
    """Medium scenarios - password in conversational format."""

    def test_password_02_conversational(self):
        """
        MEDIUM: Password change in conversational format.
        """
        user_prompt = """
        Hey, ich will mein Passwort ändern. Aktuell ist es "MeinAltes1" 
        und ich möchte es zu "MeinNeues2" ändern.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password"],
            required_arguments={
                "klips2_change_password": {
                    "current_password": "MeinAltes1",
                    "new_password": "MeinNeues2",
                    "confirm_password": "MeinNeues2"
                }
            },
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        assert gold.required_tools == ["klips2_change_password"]


class TestPasswordHard:
    """Hard scenarios - missing or problematic password information."""

    def test_password_03_missing_current(self):
        """
        HARD: Missing current password.
        LLM should ask for current password, NOT call tool.
        """
        user_prompt = """
        Mein neues KLIPS-Passwort soll Secure123! sein.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_password"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_password" in gold.forbidden_tools

    def test_password_04_missing_new(self):
        """
        HARD: Missing new password.
        """
        user_prompt = """
        Ich möchte mein Passwort ändern. Das aktuelle ist "Test123".
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_password"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_password" in gold.forbidden_tools

    def test_password_05_weak_password(self):
        """
        HARD: Attempting to set obviously weak password.
        """
        user_prompt = """
        Passwort ändern:
        Alt: SecureOld123!
        Neu: 123456
        Bestätigung: 123456
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_password"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_password" in gold.forbidden_tools


# Total: 5 scenarios
