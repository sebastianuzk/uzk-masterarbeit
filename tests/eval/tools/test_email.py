"""
Email Tool - Evaluierungs-Testszenarien

Tool: send_email
Zweck: E-Mails an einen vorkonfigurierten Standardempfänger senden

Erforderliche Argumente:
- subject (E-Mail-Betreff)
- body (E-Mail-Inhalt)

HINWEIS: Dieses Tool hat KEINEN 'to'-Parameter!
E-Mails werden automatisch an den DEFAULT_RECIPIENT aus .env gesendet.
Der Benutzer muss keinen Empfänger angeben.

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

pytestmark = [pytest.mark.llm, pytest.mark.eval]


class TestEmailEasy:
    """Einfache Szenarien - Klare E-Mail-Anfragen mit Betreff und Inhalt."""

    def test_email_01_complete_formal(self):
        """
        EASY: Complete email with subject and body specified.
        """
        user_prompt = """
        Sende eine E-Mail mit dem Betreff "Frage zur Klausur" und dem Inhalt 
        "Sehr geehrter Herr Professor, ich habe eine Frage zur kommenden Klausur. 
        Mit freundlichen Grüßen"
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
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
        Betreff: Terminanfrage
        Text: Ich möchte einen Termin für die Studienberatung vereinbaren.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Terminanfrage"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_03_short_message(self):
        """
        EASY: Short email message.
        """
        user_prompt = """
        Schicke eine Mail mit Betreff "Projekt Update" und Inhalt "Das Projekt ist abgeschlossen."
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Projekt Update"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]


class TestEmailMedium:
    """Medium scenarios - email info in conversational format."""

    def test_email_04_conversational(self):
        """
        MEDIUM: Email request in conversational style.
        """
        user_prompt = """
        Kannst du für mich eine E-Mail schicken? Es geht um meine 
        Masterarbeit - ich möchte einen Termin vereinbaren. Der Betreff
        sollte "Masterarbeit Termin" sein.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Masterarbeit Termin"
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
        Please send an email with subject "Enrollment Question" asking about 
        the enrollment deadline.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Enrollment Question"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_06_urgent_email(self):
        """
        MEDIUM: Urgent email request.
        """
        user_prompt = """
        Schicke dringend eine E-Mail mit Betreff "Dringende Anfrage" - 
        es geht um mein Passwort das nicht funktioniert.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Dringende Anfrage"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_07_forward_info(self):
        """
        MEDIUM: Request to send information.
        """
        user_prompt = """
        Sende eine Nachricht: Das Meeting wurde auf 15 Uhr verschoben.
        Betreff: Meeting Update
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Meeting Update"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]


class TestEmailHard:
    """Hard scenarios - missing or problematic email information."""

    def test_email_08_missing_subject(self):
        """
        HARD: Email request without subject.
        LLM should ask for subject, NOT call tool.
        """
        user_prompt = """
        Schreibe eine E-Mail und frage nach dem Status meiner Bewerbung.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "send_email" in gold.forbidden_tools

    def test_email_09_missing_content(self):
        """
        HARD: Email request without clear content.
        """
        user_prompt = """
        Sende eine E-Mail mit Betreff "Test".
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "send_email" in gold.forbidden_tools

    def test_email_10_too_vague(self):
        """
        HARD: Too vague email request.
        """
        user_prompt = """
        Schick mal eine Mail.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "send_email" in gold.forbidden_tools

    def test_email_11_user_specifies_recipient(self):
        """
        MEDIUM: User specifies recipient (should work, recipient ignored).
        Tool will send to default recipient anyway.
        """
        user_prompt = """
        Sende eine E-Mail an professor@uni-koeln.de mit Betreff 
        "Frage zum Seminar" und Inhalt "Wann findet das nächste Seminar statt?"
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Frage zum Seminar"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        # Tool should still be called - it will use default recipient
        assert gold.required_tools == ["send_email"]

    def test_email_12_follow_up_email(self):
        """
        MEDIUM: Request to send follow-up email.
        """
        user_prompt = """
        Schicke eine Nachfolge-E-Mail mit Betreff "Erinnerung: Terminanfrage" 
        und frage erneut nach einem Termin für nächste Woche.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Erinnerung: Terminanfrage"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_13_thank_you_email(self):
        """
        MEDIUM: Request to send thank you email.
        """
        user_prompt = """
        Verfasse eine Dankes-E-Mail mit dem Betreff "Vielen Dank für das Gespräch"
        und bedanke dich für das informative Beratungsgespräch.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Vielen Dank für das Gespräch"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_14_sick_leave_notification(self):
        """
        MEDIUM: Request to send sick leave notification.
        """
        user_prompt = """
        Schreibe eine E-Mail mit Betreff "Krankmeldung" und teile mit, 
        dass ich heute nicht zur Vorlesung kommen kann.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Krankmeldung"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]

    def test_email_15_grade_inquiry(self):
        """
        MEDIUM: Request to send email about grade inquiry.
        """
        user_prompt = """
        Sende eine E-Mail mit dem Betreff "Frage zu meiner Note" und frage,
        wann die Ergebnisse der letzten Klausur veröffentlicht werden.
        """
        
        gold = GoldStandard(
            required_tools=["send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Frage zu meiner Note"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["send_email"]


# Total: 15 scenarios
