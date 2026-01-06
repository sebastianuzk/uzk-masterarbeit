"""
KLIPS2 Get Course Details Tool - Evaluierungs-Testszenarien

Tool: klips2_get_course_details
Zweck: Detaillierte Informationen zu Kursen abrufen

Erforderliche Argumente:
- course_id (Kurs-ID/Nummer, z.B. '14302.0001')

Optionale Argumente:
- semester (Filter nach Semester, z.B. 'WiSe 2024/25')

HINWEIS: Dieses Tool hat KEINEN course_name Parameter!
Benutzer müssen die course_id angeben.

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


class TestCoursesEasy:
    """Einfache Szenarien - Klare Kursabfragen mit Kurs-ID."""

    def test_courses_01_by_id(self):
        """
        EASY: Course lookup by course ID.
        """
        user_prompt = """
        Zeige mir Details zum Kurs mit der ID 14302.0001.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0001"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]

    def test_courses_02_by_id_numeric(self):
        """
        EASY: Course lookup by numeric course ID.
        """
        user_prompt = """
        Infos zum Kurs 12345 bitte.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "12345"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]

    def test_courses_03_with_semester(self):
        """
        EASY: Course lookup with semester filter.
        """
        user_prompt = """
        Kursdetails für Kurs 14500.0002 im WS 2024/25.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14500.0002",
                    "semester": "WS 2024/25"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert "semester" in gold.required_arguments["klips2_get_course_details"]


class TestCoursesMedium:
    """Medium scenarios - course requests that may need ID extraction."""

    def test_courses_04_conversational_with_id(self):
        """
        MEDIUM: Course inquiry in conversational style with ID mentioned.
        """
        user_prompt = """
        Ich würde gerne mehr über den Kurs 14302.0010 erfahren, 
        wann findet der statt und wer hält ihn?
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0010"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]

    def test_courses_05_long_id(self):
        """
        MEDIUM: Course with longer ID format.
        """
        user_prompt = """
        Details zur Lehrveranstaltung 14302.0001.1 bitte.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0001.1"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]

    def test_courses_06_english_request(self):
        """
        MEDIUM: Course details request in English.
        """
        user_prompt = """
        Can you show me details for course ID 14500.0001?
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14500.0001"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]


class TestCoursesHard:
    """Hard scenarios - no course ID provided or vague requests."""

    def test_courses_07_no_id_just_name(self):
        """
        HARD: Only course name provided, no ID.
        LLM should ask for course ID, NOT call tool (or explain limitation).
        """
        user_prompt = """
        Zeig mir Details zur Vorlesung "Einführung in die Informatik".
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_get_course_details"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_get_course_details" in gold.forbidden_tools

    def test_courses_08_too_vague(self):
        """
        HARD: Too vague course request without any ID.
        """
        user_prompt = """
        Zeig mir irgendwelche Informatik-Kurse.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_get_course_details"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_get_course_details" in gold.forbidden_tools

    def test_courses_09_id_with_typo(self):
        """
        HARD: Course ID mentioned with typo in surrounding text.
        """
        user_prompt = """
        zeig mir bitte die detials zum kurs 14302.0005, 
        ich brauch das für meine anmledung
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0005"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]

    def test_courses_10_multiple_ids_mentioned(self):
        """
        HARD: Multiple course IDs mentioned, should query the main one.
        """
        user_prompt = """
        Ich habe gehört der Kurs 14302.0001 ist gut, aber eigentlich 
        möchte ich Infos zum Kurs 14302.0002.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_id": "14302.0002"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]


# Total: 10 scenarios
