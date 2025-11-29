"""
Email Tool - Evaluation Test Scenarios

Tool: send_email
Purpose: Send emails on behalf of the user

Required arguments:
- to (recipient email address)
- subject (email subject line)
- body (email content)

Optional arguments:
- cc (carbon copy recipients)
- bcc (blind carbon copy recipients)

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

pytestmark = [pytest.mark.llm, pytest.mark.eval]


class TestEmailEasy:
    """Easy scenarios - all email information provided clearly."""

    def test_email_01_complete_formal(self):
        """
        EASY: Complete formal email with all fields specified.
        """
        user_prompt = """
        Sende eine E-Mail an professor@uni-koeln.de mit dem Betreff 
        "Frage zur Klausur" und dem Inhalt "Sehr geehrter Herr Professor, 
        ich habe eine Frage zur kommenden Klausur. Mit freundlichen Grüßen"
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "to": "professor@uni-koeln.de",
                    "subject": "Frage zur Klausur"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_02_structured_format(self):
        """
        EASY: Email in structured format.
        """
        user_prompt = """
        E-Mail versenden:
        An: sekretariat@uni-koeln.de
        Betreff: Terminanfrage
        Text: Ich möchte einen Termin für die Studienberatung vereinbaren.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "to": "sekretariat@uni-koeln.de",
                    "subject": "Terminanfrage"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_03_with_cc(self):
        """
        EASY: Email with CC recipient.
        """
        user_prompt = """
        Schicke eine Mail an team@projekt.de (CC an chef@projekt.de) 
        mit Betreff "Projekt Update" und Inhalt "Das Projekt ist abgeschlossen."
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "to": "team@projekt.de",
                    "cc": "chef@projekt.de",
                    "subject": "Projekt Update"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "cc" in gold.required_arguments["send_email"]


class TestEmailMedium:
    """Medium scenarios - email info in conversational format."""

    def test_email_04_conversational(self):
        """
        MEDIUM: Email request in conversational style.
        """
        user_prompt = """
        Kannst du für mich eine E-Mail an meinen Betreuer schicken? 
        Seine Adresse ist betreuer@uni-koeln.de. Es geht um meine 
        Masterarbeit - ich möchte einen Termin vereinbaren.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "to": "betreuer@uni-koeln.de"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_05_english_request(self):
        """
        MEDIUM: Email request in English.
        """
        user_prompt = """
        Please send an email to support@university.edu asking about 
        the enrollment deadline. Subject should be "Enrollment Question".
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "to": "support@university.edu",
                    "subject": "Enrollment Question"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_06_multiple_recipients(self):
        """
        MEDIUM: Email to multiple recipients.
        """
        user_prompt = """
        Sende eine Nachricht an team1@example.com und team2@example.com 
        mit Betreff "Meeting morgen" und Info dass das Meeting um 14 Uhr ist.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Meeting morgen"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]


class TestEmailHard:
    """Hard scenarios - missing or problematic email information."""

    def test_email_07_missing_recipient(self):
        """
        HARD: Email request without recipient.
        LLM should ask for recipient, NOT call tool.
        """
        user_prompt = """
        Schreibe eine E-Mail mit dem Betreff "Wichtige Anfrage" 
        und frage nach dem Status meiner Bewerbung.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "send_email" in gold.forbidden_tools

    def test_email_08_missing_content(self):
        """
        HARD: Email request without clear content.
        """
        user_prompt = """
        Sende eine E-Mail an test@example.com.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "send_email" in gold.forbidden_tools

    def test_email_09_invalid_email(self):
        """
        HARD: Email request with invalid email address.
        """
        user_prompt = """
        Schicke eine Mail an "keine-email-adresse" mit Betreff "Test" 
        und Inhalt "Test Nachricht".
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "send_email" in gold.forbidden_tools

    def test_email_10_urgent_with_priority(self):
        """
        MEDIUM: Email with urgency indication.
        """
        user_prompt = """
        Schicke dringend eine E-Mail an admin@uni-koeln.de mit Betreff 
        "Dringende Anfrage" - es geht um mein Passwort das nicht funktioniert.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "to": "admin@uni-koeln.de",
                    "subject": "Dringende Anfrage"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_11_forward_info(self):
        """
        MEDIUM: Forward information to someone.
        """
        user_prompt = """
        Leite diese Information an kollege@firma.de weiter: 
        Das Meeting wurde auf 15 Uhr verschoben. Betreff: Meeting Update
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "to": "kollege@firma.de",
                    "subject": "Meeting Update"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]


# Total: 11 scenarios
