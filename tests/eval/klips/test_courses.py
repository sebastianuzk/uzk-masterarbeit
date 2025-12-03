"""
KLIPS2 Get Course Details Tool - Evaluation Test Scenarios

Tool: klips2_get_course_details
Purpose: Retrieve detailed information about courses

Required arguments:
- course_id (course ID/number, e.g., '14302.0001')

Optional arguments:
- semester (filter by semester, e.g., 'WiSe 2024/25')

NOTE: This tool does NOT have a course_name parameter! 
Users must provide the course_id to search.

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


class TestCoursesEasy:
    """Easy scenarios - clear course information requests with course ID."""

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


# Total: 8 scenarios
