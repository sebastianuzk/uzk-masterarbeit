"""
KLIPS2 Apply Study Tool - Evaluation Test Scenarios

Tool: klips2_apply_study
Purpose: Apply for a course of study at the University of Cologne

Required arguments:
- studiengang (study program name)
- semester_type (WS/SS)
- year (year of the semester)

Optional arguments:
- bewerbungstyp (application type: Erstsemester, Hochschulwechsler, etc.)

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


class TestApplyEasy:
    """Easy scenarios - all information provided clearly."""

    def test_apply_01_complete_bachelor(self):
        """
        EASY: Complete bachelor application with all required data.
        """
        user_prompt = """
        Ich möchte mich für den Bachelorstudiengang Informatik zum 
        Wintersemester 2024/25 bewerben.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Informatik",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_02_summer_semester(self):
        """
        EASY: Application for summer semester.
        """
        user_prompt = """
        Bewerbung für BWL Bachelor zum Sommersemester 2025 bitte.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "BWL",
                    "semester_type": "SS",
                    "year": "2025"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_apply_study"]["semester_type"] == "SS"

    def test_apply_03_master_program(self):
        """
        EASY: Master program application with explicit type.
        """
        user_prompt = """
        Ich möchte mich für den Master in Wirtschaftsinformatik 
        zum WS 2024/25 als Erstsemester bewerben.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Wirtschaftsinformatik",
                    "semester_type": "WS",
                    "year": "2024",
                    "bewerbungstyp": "Erstsemester"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "bewerbungstyp" in gold.required_arguments["klips2_apply_study"]

    def test_apply_04_english_request(self):
        """
        EASY: Application request in English.
        """
        user_prompt = """
        I want to apply for the Chemistry Bachelor program 
        for Winter Semester 2024/25.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Chemistry",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_05_hochschulwechsler(self):
        """
        EASY: Application as university changer (Hochschulwechsler).
        """
        user_prompt = """
        Als Hochschulwechsler möchte ich mich für Psychologie 
        Bachelor zum WS 2024/25 bewerben.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Psychologie",
                    "semester_type": "WS",
                    "year": "2024",
                    "bewerbungstyp": "Hochschulwechsler"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_apply_study"]["bewerbungstyp"] == "Hochschulwechsler"


class TestApplyMedium:
    """Medium scenarios - information in conversational format."""

    def test_apply_06_conversational(self):
        """
        MEDIUM: Application request in conversational format.
        """
        user_prompt = """
        Hey, ich hab gehört man kann sich jetzt für das nächste Semester 
        bewerben. Ich interessiere mich für Medizin und würde gerne 
        zum Winter anfangen, also 2024.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Medizin",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_07_abbreviation_ws(self):
        """
        MEDIUM: Semester type as abbreviation.
        """
        user_prompt = """
        Bewerbung: Jura B.A., WS24
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Jura",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_08_long_program_name(self):
        """
        MEDIUM: Long, complex study program name.
        """
        user_prompt = """
        Ich möchte mich für den Studiengang "Medienwissenschaft und 
        Medienpraxis" zum Wintersemester 2024/25 bewerben.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Medienwissenschaft und Medienpraxis",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_09_lehramt(self):
        """
        MEDIUM: Teacher training program (Lehramt).
        """
        user_prompt = """
        Bewerbung für Lehramt Gymnasium mit den Fächern Deutsch und 
        Geschichte zum WS 2024/25.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Lehramt Gymnasium Deutsch Geschichte",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.argument_match_mode == ArgumentMatchMode.SEMANTIC

    def test_apply_10_next_year(self):
        """
        MEDIUM: Application for next year's winter semester.
        """
        user_prompt = """
        Ich plane fürs nächste Wintersemester 2025 eine Bewerbung 
        für Physik abzugeben.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Physik",
                    "semester_type": "WS",
                    "year": "2025"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_apply_study"]["year"] == "2025"


class TestApplyHard:
    """Hard scenarios - missing or ambiguous information."""

    def test_apply_11_missing_semester(self):
        """
        HARD: Application missing semester information.
        LLM should ask for semester, NOT call tool.
        """
        user_prompt = """
        Ich möchte mich für Informatik bewerben.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_12_missing_program(self):
        """
        HARD: Application missing study program.
        """
        user_prompt = """
        Ich möchte mich zum Wintersemester 2024/25 bewerben.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_13_vague_timing(self):
        """
        HARD: Vague timing without specific semester.
        """
        user_prompt = """
        Ich würde gerne irgendwann Psychologie studieren.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_14_ambiguous_year(self):
        """
        HARD: Ambiguous year reference.
        """
        user_prompt = """
        Bewerbung für Biologie zum Wintersemester.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_15_just_question(self):
        """
        HARD: Just a question about application, not a request.
        """
        user_prompt = """
        Kann man sich noch für Informatik bewerben?
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools


class TestApplyMultiStep:
    """Multi-step scenarios simulating conversations."""

    def test_apply_multistep_01_provide_program_later(self):
        """
        MULTI-STEP: User provides program after initial prompt.
        
        Turn 1: "Ich möchte mich bewerben zum WS 2024/25"
        Turn 2: "Informatik"
        """
        user_prompt = """
        Previous conversation:
        User: Ich möchte mich bewerben zum WS 2024/25
        Assistant: Für welchen Studiengang möchten Sie sich bewerben?
        
        Current message: Informatik
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Informatik",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_multistep_02_provide_semester_later(self):
        """
        MULTI-STEP: User provides semester after initial prompt.
        
        Turn 1: "Bewerbung für BWL"
        Turn 2: "Zum Sommersemester 2025"
        """
        user_prompt = """
        Previous conversation:
        User: Bewerbung für BWL
        Assistant: Für welches Semester möchten Sie sich bewerben?
        
        Current message: Zum Sommersemester 2025
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "BWL",
                    "semester_type": "SS",
                    "year": "2025"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_apply_study"]["semester_type"] == "SS"

    def test_apply_multistep_03_correction(self):
        """
        MULTI-STEP: User corrects themselves.
        
        Turn 1: "Bewerbung Medizin WS 2024"
        Turn 2: "Sorry, ich meinte Biologie nicht Medizin"
        """
        user_prompt = """
        Previous conversation:
        User: Bewerbung Medizin WS 2024
        Assistant: Ich werde Ihre Bewerbung für Medizin zum WS 2024 vorbereiten.
        
        Current message: Sorry, ich meinte Biologie nicht Medizin
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Biologie",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_apply_study"]["studiengang"] == "Biologie"

    def test_apply_multistep_04_add_type(self):
        """
        MULTI-STEP: User adds bewerbungstyp in follow-up.
        
        Turn 1: "Informatik WS 2024"
        Turn 2: "Ich wechsle von einer anderen Uni"
        """
        user_prompt = """
        Previous conversation:
        User: Informatik WS 2024 bitte
        Assistant: Bewerben Sie sich als Erstsemester oder wechseln Sie von einer anderen Hochschule?
        
        Current message: Ich wechsle von einer anderen Uni
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Informatik",
                    "semester_type": "WS",
                    "year": "2024",
                    "bewerbungstyp": "Hochschulwechsler"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_apply_study"]["bewerbungstyp"] == "Hochschulwechsler"

    def test_apply_multistep_05_three_turns(self):
        """
        MULTI-STEP: Information gathered over three turns.
        
        Turn 1: "Ich will studieren"
        Turn 2: "Chemie"
        Turn 3: "Nächstes Wintersemester, also 2024"
        """
        user_prompt = """
        Previous conversation:
        User: Ich will studieren
        Assistant: Was möchten Sie studieren?
        User: Chemie
        Assistant: Für welches Semester möchten Sie sich bewerben?
        
        Current message: Nächstes Wintersemester, also 2024
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Chemie",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_multistep_06_still_missing_after_clarification(self):
        """
        MULTI-STEP: Still missing info after clarification - don't call tool.
        
        Turn 1: "Bewerbung bitte"
        Turn 2: "Informatik" (still missing semester)
        """
        user_prompt = """
        Previous conversation:
        User: Bewerbung bitte
        Assistant: Für welchen Studiengang möchten Sie sich bewerben?
        
        Current message: Informatik
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_multistep_07_change_semester(self):
        """
        MULTI-STEP: User changes semester preference.
        
        Turn 1: "BWL WS 2024"
        Turn 2: "Doch lieber SS 2025"
        """
        user_prompt = """
        Previous conversation:
        User: Ich möchte mich für BWL zum WS 2024 bewerben
        Assistant: Soll ich die Bewerbung für BWL zum WS 2024 einreichen?
        
        Current message: Doch lieber SS 2025
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "BWL",
                    "semester_type": "SS",
                    "year": "2025"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_apply_study"]["year"] == "2025"

    def test_apply_multistep_08_abbreviation_clarified(self):
        """
        MULTI-STEP: Abbreviation clarified in follow-up.
        
        Turn 1: "WiWi zum WS24"
        Turn 2: "Wirtschaftswissenschaften"
        """
        user_prompt = """
        Previous conversation:
        User: WiWi zum WS24 bitte
        Assistant: Meinen Sie Wirtschaftswissenschaften oder einen anderen Studiengang?
        
        Current message: Ja, Wirtschaftswissenschaften
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Wirtschaftswissenschaften",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_multistep_09_confirmation(self):
        """
        MULTI-STEP: User confirms after summary.
        
        Turn 1: "Mathe Bachelor WS 2024"
        Turn 2: "Ja, genau so"
        """
        user_prompt = """
        Previous conversation:
        User: Mathe Bachelor WS 2024
        Assistant: Zusammenfassung - Studiengang: Mathematik Bachelor, Semester: WS 2024/25. Soll ich die Bewerbung einreichen?
        
        Current message: Ja, genau so
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "studiengang": "Mathematik",
                    "semester_type": "WS",
                    "year": "2024"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_multistep_10_cancellation(self):
        """
        MULTI-STEP: User cancels application process.
        
        Turn 1: "Informatik WS 2024"
        Turn 2: "Doch nicht, ich überleg mir das nochmal"
        """
        user_prompt = """
        Previous conversation:
        User: Bewerbung für Informatik WS 2024
        Assistant: Soll ich die Bewerbung für Informatik zum WS 2024 einreichen?
        
        Current message: Doch nicht, ich überleg mir das nochmal
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools


# Total: 25 scenarios
