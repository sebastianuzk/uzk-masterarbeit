"""
Multi-Tool und Negativ-Testszenarien

Diese Szenarien testen:
1. Multi-Tool: Anfragen, die mehrere Tools in Kombination erfordern
2. Negativ: Anfragen, die KEINE Tools verwenden sollten

Teil der Masterarbeit: KI-gestütztes Universitäts-Assistenten Evaluierungs-Framework
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from eval.core.evaluation import (
    GoldStandard,
    ArgumentMatchMode,
)

pytestmark = [pytest.mark.llm, pytest.mark.eval]


class TestMultiTool:
    """Szenarien, die mehrere Tools erfordern."""

    def test_multi_01_search_then_klips(self):
        """
        MULTI-TOOL: Search web for course info then get KLIPS details.
        """
        user_prompt = """
        Suche im Internet nach dem Kurs 14302.0001 und hole dann 
        die Details aus KLIPS.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0001"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "duckduckgo_search" in gold.required_tools
        assert "klips2_get_course_details" in gold.required_tools

    def test_multi_02_klips_then_email(self):
        """
        MULTI-TOOL: Get course details and send summary via email.
        """
        user_prompt = """
        Schau nach den Details zum Kurs 14302.0001 und schicke 
        mir dann eine E-Mail mit der Zusammenfassung (Betreff: Kursinfo).
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details", "send_email"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0001"
                },
                "send_email": {
                    "subject": "Kursinfo"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 2

    def test_multi_03_search_then_email(self):
        """
        MULTI-TOOL: Search and then email results.
        """
        user_prompt = """
        Recherchiere die aktuellen Bewerbungsfristen für die Uni Köln 
        und schicke das Ergebnis als E-Mail mit Betreff "Fristen".
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "send_email"],
            required_arguments={
                "send_email": {
                    "subject": "Fristen"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "duckduckgo_search" in gold.required_tools
        assert "send_email" in gold.required_tools


class TestNegative:
    """Scenarios that should NOT trigger any tools."""

    def test_negative_01_greeting(self):
        """
        NEGATIVE: Simple greeting should not trigger tools.
        """
        user_prompt = """
        Hallo! Wie geht es dir?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register", "klips2_apply_study", 
                          "send_email", "duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0

    def test_negative_02_general_question(self):
        """
        NEGATIVE: General university knowledge question.
        """
        user_prompt = """
        Was ist der Unterschied zwischen Bachelor und Master Information System an der Universitat zu Köln?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register", "klips2_apply_study",
                          "duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "university_knowledge_search" in gold.required_tools

    def test_negative_03_system_info(self):
        """
        NEGATIVE: Question about the assistant itself.
        """
        user_prompt = """
        Welche Funktionen hast du? Was kannst du alles machen?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register", "klips2_apply_study",
                          "send_email", "duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0

    def test_negative_04_simple_calculation(self):
        """
        NEGATIVE: Simple math that doesn't need tools.
        """
        user_prompt = """
        Was ist 2 + 2?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"duckduckgo_search", "send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0

    def test_negative_05_language_translation(self):
        """
        NEGATIVE: Translation request (no tools needed).
        """
        user_prompt = """
        Übersetze "Guten Morgen" ins Englische.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0


class TestMultiToolExtended:
    """Extended multi-tool scenarios."""

    def test_multi_04_register_then_email(self):
        """
        MULTI-TOOL: Register for KLIPS and send confirmation email.
        """
        user_prompt = """
        Registriere mich bei KLIPS2 mit folgenden Daten:
        Vorname: Max, Nachname: Mustermann, Geschlecht: männlich,
        Geburtsdatum: 15.03.1999, E-Mail: max@test.de, Nationalität: deutsch.
        Danach schicke eine Bestätigungs-E-Mail (Betreff: KLIPS Registrierung).
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register", "send_email"],
            required_arguments={
                "send_email": {
                    "subject": "KLIPS Registrierung"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 2

    def test_multi_05_password_then_email(self):
        """
        MULTI-TOOL: Change password and send confirmation email.
        """
        user_prompt = """
        Ändere mein KLIPS-Passwort. Login: max@uni-koeln.de / AltesPasswort,
        neues Passwort: NeuesPasswort123.
        Danach schicke mir eine Bestätigung per E-Mail (Betreff: Passwort geändert).
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_password", "send_email"],
            required_arguments={
                "klips2_change_password": {
                    "username": "max@uni-koeln.de"
                },
                "send_email": {
                    "subject": "Passwort geändert"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_password" in gold.required_tools
        assert "send_email" in gold.required_tools

    def test_multi_06_search_course_email(self):
        """
        MULTI-TOOL: Complex scenario with three tools.
        """
        user_prompt = """
        Recherchiere online nach dem Kurs 14302.0001, hole die Details 
        aus KLIPS und schicke mir alles per E-Mail 
        (Betreff: Kursrecherche).
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search", "klips2_get_course_details", "send_email"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0001"
                },
                "send_email": {
                    "subject": "Kursrecherche"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert len(gold.required_tools) == 3


# Total: 11 scenarios
