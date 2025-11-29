"""
KLIPS2 Get Course Details Tool - Evaluation Test Scenarios

Tool: klips2_get_course_details
Purpose: Retrieve detailed information about courses

Required arguments:
- course_name OR course_id (search query)

Optional arguments:
- semester (filter by semester)

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
    """Easy scenarios - clear course information requests."""

    def test_courses_01_by_name(self):
        """
        EASY: Course lookup by name.
        """
        user_prompt = """
        Zeige mir Details zur Vorlesung "Einführung in die Informatik".
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_name": "Einführung in die Informatik"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]

    def test_courses_02_by_id(self):
        """
        EASY: Course lookup by course ID.
        """
        user_prompt = """
        Infos zum Kurs mit der ID 12345 bitte.
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
        Kursdetails für "Algorithmen und Datenstrukturen" im WS 2024/25.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_name": "Algorithmen und Datenstrukturen",
                    "semester": "WS 2024/25"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert "semester" in gold.required_arguments["klips2_get_course_details"]


class TestCoursesMedium:
    """Medium scenarios - course requests in natural language."""

    def test_courses_04_conversational(self):
        """
        MEDIUM: Course inquiry in conversational style.
        """
        user_prompt = """
        Ich würde gerne mehr über die Programmierung 1 Vorlesung erfahren, 
        wann findet die statt und wer hält sie?
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_name": "Programmierung 1"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]

    def test_courses_05_abbreviated_name(self):
        """
        MEDIUM: Course with abbreviated name.
        """
        user_prompt = """
        Details zur VL "Info I" bitte.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_name": "Info I"
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
        Can you show me details for the "Machine Learning" course?
        """
        
        gold = GoldStandard(
            required_tools=["klips2_get_course_details"],
            required_arguments={
                "klips2_get_course_details": {
                    "course_name": "Machine Learning"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_get_course_details"]


class TestCoursesHard:
    """Hard scenarios - vague or problematic course requests."""

    def test_courses_07_too_vague(self):
        """
        HARD: Too vague course request.
        LLM should ask for clarification, NOT call tool.
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


# Total: 7 scenarios
