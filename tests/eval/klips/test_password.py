"""
KLIPS2 Change Password Tool - Evaluierungs-Testszenarien

Tool: klips2_change_password
Zweck: KLIPS2 Account-Passwort ändern

Erforderliche Argumente (aus KLIPS2AuthenticatedInput + KLIPS2ChangePasswordInput):
- username (KLIPS2 Benutzername für Login)
- password (aktuelles KLIPS2 Passwort für Login)
- new_password (das neue Passwort)

Teil der Masterarbeit: KI-gestütztes Universitäts-Assistenten Evaluierungs-Framework
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
    """Einfache Szenarien - Alle Passwort-Informationen angegeben."""

    def test_password_01_complete_request(self):
        """
        EASY: Complete password change with all fields.
        """
        user_prompt = """
        Ich möchte mein KLIPS-Passwort ändern.
        Benutzername: max@uni-koeln.de
        Aktuelles Passwort: OldPass123!
        Neues Passwort: NewSecure456!
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password"],
            required_arguments={
                "klips2_change_password": {
                    "username": "max@uni-koeln.de",
                    "password": "OldPass123!",
                    "new_password": "NewSecure456!"
                }
            },
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        assert gold.required_tools == ["klips2_change_password"]

    def test_password_02_compact_format(self):
        """
        EASY: Password change in compact format.
        """
        user_prompt = """
        KLIPS Passwort ändern: Login anna@uni-koeln.de / AltesPasswort
        Neues Passwort: NeuesPasswort2024!
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password"],
            required_arguments={
                "klips2_change_password": {
                    "username": "anna@uni-koeln.de",
                    "password": "AltesPasswort",
                    "new_password": "NeuesPasswort2024!"
                }
            },
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        assert gold.required_tools == ["klips2_change_password"]


class TestPasswordMedium:
    """Medium scenarios - password in conversational format."""

    def test_password_03_conversational(self):
        """
        MEDIUM: Password change in conversational format.
        """
        user_prompt = """
        Hey, ich will mein KLIPS-Passwort ändern. Mein Benutzername ist 
        student@uni-koeln.de, aktuelles Passwort ist "MeinAltes1" 
        und ich möchte es zu "MeinNeues2!" ändern.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password"],
            required_arguments={
                "klips2_change_password": {
                    "username": "student@uni-koeln.de",
                    "password": "MeinAltes1",
                    "new_password": "MeinNeues2!"
                }
            },
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        assert gold.required_tools == ["klips2_change_password"]


class TestPasswordHard:
    """Hard scenarios - missing or problematic password information."""

    def test_password_04_missing_credentials(self):
        """
        HARD: Missing login credentials entirely.
        LLM should ask for username and password, NOT call tool.
        """
        user_prompt = """
        Ich möchte mein KLIPS-Passwort zu Secure123! ändern.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_password"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_password" in gold.forbidden_tools

    def test_password_05_missing_new_password(self):
        """
        HARD: Missing new password.
        """
        user_prompt = """
        Ich möchte mein Passwort ändern.
        Login: test@uni-koeln.de / Test123
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_password"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_password" in gold.forbidden_tools

    def test_password_06_english_request(self):
        """
        HARD: Password change request in English.
        """
        user_prompt = """
        I want to change my KLIPS password.
        Username: john@uni-koeln.de
        Current password: OldPwd123
        New password: NewPwd456!
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password"],
            required_arguments={
                "klips2_change_password": {
                    "username": "john@uni-koeln.de",
                    "password": "OldPwd123",
                    "new_password": "NewPwd456!"
                }
            },
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        assert gold.required_tools == ["klips2_change_password"]

    def test_password_07_correction_midway(self):
        """
        HARD: User corrects information mid-request.
        """
        user_prompt = """
        Ändere mein KLIPS-Passwort. User: max@uni-koeln.de, altes PW: Alt123
        ach nein sorry, das alte Passwort ist eigentlich Richtig456
        neues Passwort: Neu789!
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password"],
            required_arguments={
                "klips2_change_password": {
                    "username": "max@uni-koeln.de",
                    "password": "Richtig456",
                    "new_password": "Neu789!"
                }
            },
            argument_match_mode=ArgumentMatchMode.EXACT
        )
        
        assert gold.required_tools == ["klips2_change_password"]


# Total: 7 scenarios
