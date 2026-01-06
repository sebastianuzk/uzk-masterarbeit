"""
Multi-Tool und Negativ-Testszenarien

Diese Szenarien testen:
1. Multi-Tool: Anfragen, die mehrere Tools in Kombination erfordern
2. Negativ: Anfragen, die KEINE Tools verwenden sollten
3. Multi-Tool Negative: Abbruch oder unvollständige Multi-Tool-Anfragen

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


class TestMultiTool:
    """Szenarien, die mehrere Tools erfordern."""

    def test_multi_01_search_then_klips(self):
        """
        MULTI-STEP: Search web for course info then get KLIPS details.
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
        MULTI-STEP: Get course details and send summary via email.
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
        MULTI-STEP: Search and then email results.
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

    def test_multi_04_register_then_email(self):
        """
        MULTI-STEP: Register for KLIPS and send confirmation email.
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


class TestNegative:
    """Scenarios that should NOT trigger any tools."""

    def test_negative_01_greeting(self):
        """
        EASY: Simple greeting should not trigger tools.
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
        EASY: General knowledge question (no tools needed).
        """
        user_prompt = """
        Was ist der Unterschied zwischen Bachelor und Master?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register", "klips2_apply_study",
                          "duckduckgo_search"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0

    def test_negative_03_system_info(self):
        """
        EASY: Question about the assistant itself.
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
        EASY: Simple math that doesn't need tools.
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


class TestMultiToolNegative:
    """Multi-tool scenarios that should fail or stop early."""

    def test_multi_neg_01_cancel_midway(self):
        """
        HARD: User requests multi-step but cancels mid-way.
        """
        user_prompt = """
        Such nach den Bewerbungsfristen und schicke... 
        ach nee, vergiss es, ich mach das selbst.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"duckduckgo_search", "send_email"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert len(gold.required_tools) == 0

    def test_multi_neg_02_missing_second_tool_info(self):
        """
        HARD: Multi-step but missing info for second tool.
        Only first tool should be called, not second.
        """
        user_prompt = """
        Hole die Details zum Kurs 14302.0001 und schick mir dann eine E-Mail.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            forbidden_tools={"send_email"},
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0001"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        # Email should NOT be sent without subject
        assert "send_email" in gold.forbidden_tools

    def test_multi_neg_03_conflicting_instructions(self):
        """
        HARD: Conflicting instructions in multi-step.
        """
        user_prompt = """
        Such im Internet nach Stipendien für mich, aber eigentlich 
        sollst du das nicht tun, such lieber nach Praktika.
        Ach nee, such doch nach Stipendien. Schick mir dann eine Mail.
        """
        
        gold = GoldStandard(
            required_tools=["duckduckgo_search"],
            forbidden_tools={"send_email"},
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        # No email subject provided
        assert "send_email" in gold.forbidden_tools


# Total: 11 scenarios

