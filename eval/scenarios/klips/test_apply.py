"""
KLIPS2 Apply Study Tool - Evaluierungs-Testszenarien

Tool: klips2_apply_study
Zweck: Bewerbung für einen Studiengang an der Universität zu Köln

Erforderliche Argumente (Basis):
- username (KLIPS2 Benutzername)
- password (KLIPS2 Passwort)
- semester (z.B. "Wintersemester 2025/26")
- degree_type (Bachelor/Master/Promotionsstudium)
- study_program (Name des Studiengangs)

Erforderliche Argumente (Basis, ergänzend):
- study_form (Erststudium/Zweitstudium - PFLICHT für korrekte Bearbeitung)

Optionale Argumente (Basis, mit Standardwerten):
- entry_semester (Standard: "1")

Erforderliche Argumente (Persönliche Daten):
- gender (männlich/weiblich/divers)
- birth_place (Geburtsort)
- nationality (z.B. "deutsch")

Optionale Persönliche Daten (mit Standardwerten):
- birth_country (Standard: "Deutschland")

Erforderliche Argumente (HZB - Hochschulzugangsberechtigung):
- hzb_date (Datum der HZB, Format: TT.MM.JJJJ)
- hzb_type (Art der HZB, z.B. "Allgemeine Hochschulreife")
- hzb_grade (Note, z.B. "2,3")
- hzb_place (Ort/Kreis der HZB)

Optionale HZB-Argumente (mit Standardwerten):
- hzb_name (Name des Zeugnisses, Standard: "Abitur")
- hzb_school (Name der Schule, Standard: "Gymnasium")
- hzb_country (Land der HZB, Standard: "Deutschland")

Zusätzlich erforderlich für Zweitstudium:
- prev_uni (vorherige Universität)
- prev_program (vorheriger Studiengang)
- prev_semesters (Anzahl der Semester)

Optionale Zweitstudium-Felder:
- prev_degree (vorheriger Abschluss)

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

pytestmark = [pytest.mark.llm, pytest.mark.klips, pytest.mark.eval]


class TestApplyEasy:
    """
    Einfache Szenarien - Benutzer liefert ALLE erforderlichen Informationen in einer Nachricht.
    Dies sind umfassende Anfragen mit allen Pflichtdaten.
    """

    def test_apply_01_complete_erststudium(self):
        """
        EASY: Complete first-time student application with ALL required data.
        """
        user_prompt = """
        Ich möchte mich für Informatik Bachelor zum Wintersemester 2024/25 bewerben.
        Mein KLIPS-Benutzername ist max.mustermann@uni-koeln.de, Passwort: Geheim123.
        Es ist mein Erststudium, 1. Fachsemester.
        Ich bin männlich, geboren am 15.03.1999 in Köln, Deutschland, deutsch.
        Abitur vom 15.06.2018 am Gymnasium Köln-Deutz, Note 2,3, in Köln, Deutschland.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "username": "max.mustermann@uni-koeln.de",
                    "password": "Geheim123",
                    "study_program": "Informatik",
                    "degree_type": "Bachelor",
                    "semester": "Wintersemester 2024/25",
                    "entry_semester": "1",
                    "study_form": "Erststudium",
                    "gender": "männlich",
                    "birth_place": "Köln",
                    "birth_country": "Deutschland",
                    "nationality": "deutsch",
                    "hzb_date": "15.06.2018",
                    "hzb_type": "Allgemeine Hochschulreife",
                    "hzb_name": "Abitur",
                    "hzb_grade": "2,3",
                    "hzb_school": "Gymnasium Köln-Deutz",
                    "hzb_country": "Deutschland",
                    "hzb_place": "Köln"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_02_complete_master_erststudium(self):
        """
        EASY: Complete Master application as first-time student.
        """
        user_prompt = """
        Master Wirtschaftsinformatik zum SS 2025, Erststudium, 1. Semester.
        Login: anna.schmidt@smail.uni-koeln.de / MeinPasswort456
        Weiblich, geboren 22.07.1998 in Berlin, Deutschland, deutsche Staatsangehörigkeit.
        Abitur mit 1,8 am 01.07.2016, Friedrich-Ebert-Gymnasium, Berlin, Deutschland.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "username": "anna.schmidt@smail.uni-koeln.de",
                    "password": "MeinPasswort456",
                    "study_program": "Wirtschaftsinformatik",
                    "degree_type": "Master",
                    "semester": "Sommersemester 2025",
                    "entry_semester": "1",
                    "study_form": "Erststudium",
                    "gender": "weiblich",
                    "birth_place": "Berlin",
                    "birth_country": "Deutschland",
                    "nationality": "deutsch",
                    "hzb_date": "01.07.2016",
                    "hzb_grade": "1,8",
                    "hzb_school": "Friedrich-Ebert-Gymnasium",
                    "hzb_place": "Berlin"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert "study_form" in gold.required_arguments["klips2_apply_study"]

    def test_apply_03_complete_zweitstudium(self):
        """
        EASY: Complete application as Zweitstudium (requires previous university info).
        """
        user_prompt = """
        Bewerbung für BWL Bachelor WS 2024/25 als Zweitstudium (3. Fachsemester).
        Benutzername: peter.wagner@uni-koeln.de, Passwort: Sicher789
        Männlich, 10.01.1995, München, Deutschland, deutsch.
        Abitur 2,0 am 20.06.2013, Max-Planck-Gymnasium München.
        Vorherige Uni: TU München, Maschinenbau Bachelor, 6 Semester, nicht abgeschlossen.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "username": "peter.wagner@uni-koeln.de",
                    "password": "Sicher789",
                    "study_program": "BWL",
                    "degree_type": "Bachelor",
                    "semester": "Wintersemester 2024/25",
                    "entry_semester": "3",
                    "study_form": "Zweitstudium",
                    "gender": "männlich",
                    "birth_place": "München",
                    "nationality": "deutsch",
                    "hzb_grade": "2,0",
                    "hzb_school": "Max-Planck-Gymnasium München",
                    "prev_uni": "TU München",
                    "prev_program": "Maschinenbau",
                    "prev_semesters": "6"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert "prev_uni" in gold.required_arguments["klips2_apply_study"]

    def test_apply_04_english_complete(self):
        """
        EASY: Complete application in English.
        """
        user_prompt = """
        Apply for Computer Science Bachelor, Winter Semester 2024/25, first semester.
        Username: john.doe@uni-koeln.de, Password: Secret123
        First-time student. Male, born 05.05.2000 in London, UK, British.
        A-Levels from 01.06.2018, Westminster School London, Grade 1.5.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "username": "john.doe@uni-koeln.de",
                    "password": "Secret123",
                    "study_program": "Computer Science",
                    "degree_type": "Bachelor",
                    "semester": "Wintersemester 2024/25",
                    "entry_semester": "1",
                    "study_form": "Erststudium",
                    "gender": "male",
                    "birth_place": "London",
                    "birth_country": "UK",
                    "nationality": "British",
                    "hzb_school": "Westminster School London",
                    "hzb_grade": "1.5"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]


class TestApplyHard:
    """
    Hard scenarios - missing required information.
    LLM should NOT call the tool but ask for missing data.
    """

    def test_apply_05_missing_credentials(self):
        """
        HARD: Missing username and password.
        LLM should ask for login credentials.
        """
        user_prompt = """
        Ich möchte mich für Informatik Bachelor zum WS 2024/25 bewerben.
        Erststudium, 1. Semester, männlich, geboren 15.03.1999 in Köln.
        Abitur 2,3 vom 15.06.2018, Gymnasium Köln.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_06_missing_personal_data(self):
        """
        HARD: Missing personal data (gender, birth info).
        """
        user_prompt = """
        Bewerbung Informatik Bachelor WS 2024/25.
        Login: max@uni-koeln.de / pass123
        Erststudium, 1. Semester.
        Abitur 2,0 vom 01.06.2018, Gymnasium Bonn.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_07_missing_hzb_data(self):
        """
        HARD: Missing HZB (Hochschulzugangsberechtigung) data.
        """
        user_prompt = """
        Bewerbung für BWL Bachelor zum WS 2024/25.
        User: anna@uni-koeln.de, PW: geheim
        Erststudium, 1. Semester.
        Weiblich, geboren 10.05.1999 in Hamburg, Deutschland, deutsch.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_08_missing_study_form(self):
        """
        HARD: Missing study_form (Erststudium/Zweitstudium).
        """
        user_prompt = """
        Informatik Bachelor WS 2024/25, 1. Semester.
        Login: test@uni-koeln.de / test123
        Männlich, 01.01.2000, Köln, Deutschland, deutsch.
        Abitur 2,5 am 01.06.2018, Gymnasium Köln.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_09_zweitstudium_missing_prev_uni(self):
        """
        HARD: Zweitstudium without previous university information.
        """
        user_prompt = """
        BWL Bachelor WS 2024/25 als Zweitstudium, 3. Semester.
        Login: peter@uni-koeln.de / pw123
        Männlich, 15.03.1995, München, Deutschland, deutsch.
        Abitur 2,0 am 01.06.2013, Gymnasium München.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_10_missing_semester(self):
        """
        HARD: Application missing semester information.
        """
        user_prompt = """
        Ich möchte mich für Informatik bewerben.
        Login: max@uni-koeln.de / pass
        Erststudium, männlich, 15.03.1999, Köln, deutsch.
        Abitur 2,3, Gymnasium Köln.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_11_missing_program(self):
        """
        HARD: Application missing study program.
        """
        user_prompt = """
        Bewerbung zum Wintersemester 2024/25.
        Login: anna@uni-koeln.de / geheim
        Erststudium, 1. Semester, weiblich, 10.05.1999, Hamburg, deutsch.
        Abitur 1,8 am 01.06.2017, Gymnasium Hamburg.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_12_vague_request(self):
        """
        HARD: Vague request without specific details.
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

    def test_apply_13_just_question(self):
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

    def test_apply_14_partial_hzb(self):
        """
        HARD: Partial HZB data (missing grade, school, etc.).
        """
        user_prompt = """
        Informatik Bachelor WS 2024/25, Erststudium, 1. Semester.
        Login: user@uni-koeln.de / pass123
        Männlich, 15.03.1999, Köln, Deutschland, deutsch.
        Ich habe Abitur gemacht.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools


class TestApplyMultiStep:
    """
    Multi-step scenarios simulating conversations where data is collected incrementally.
    """

    def test_apply_multistep_01_provide_credentials_later(self):
        """
        MULTI-STEP: User provides credentials after initial request.
        All other data was already given, now credentials complete the request.
        """
        user_prompt = """
        Previous conversation:
        User: Bewerbung Informatik Bachelor WS 2024/25, Erststudium, 1. Semester.
              Männlich, 15.03.1999, Köln, Deutschland, deutsch.
              Abitur 2,3 am 15.06.2018, Gymnasium Köln-Deutz.
        Assistant: Für die Bewerbung benötige ich noch Ihre KLIPS2-Zugangsdaten.
        
        Current message: Benutzername max@uni-koeln.de, Passwort Geheim123
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "username": "max@uni-koeln.de",
                    "password": "Geheim123",
                    "study_program": "Informatik",
                    "semester": "Wintersemester 2024/25"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_multistep_02_provide_hzb_later(self):
        """
        MULTI-STEP: User provides HZB data after initial request.
        """
        user_prompt = """
        Previous conversation:
        User: Informatik Bachelor WS 2024/25, Erststudium, 1. Semester.
              Login: max@uni-koeln.de / pass123
              Männlich, 15.03.1999, Köln, deutsch.
        Assistant: Ich benötige noch Ihre HZB-Daten (Abitur/Fachhochschulreife).
        
        Current message: Abitur mit Note 2,3 am 15.06.2018 am Gymnasium Köln
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "study_program": "Informatik",
                    "semester": "Wintersemester 2024/25",
                    "hzb_grade": "2,3",
                    "hzb_date": "15.06.2018",
                    "hzb_school": "Gymnasium Köln"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_multistep_03_provide_prev_uni_for_zweitstudium(self):
        """
        MULTI-STEP: Zweitstudium - user provides previous university info.
        """
        user_prompt = """
        Previous conversation:
        User: BWL Bachelor WS 2024/25 als Zweitstudium, 3. Semester.
              Login: peter@uni-koeln.de / pw123
              Männlich, 15.03.1995, München, deutsch.
              Abitur 2,0 am 01.06.2013, Gymnasium München.
        Assistant: Da Sie ein Zweitstudium anstreben, benötige ich Informationen 
                   zu Ihrer vorherigen Hochschule.
        
        Current message: TU München, Maschinenbau Bachelor, 6 Semester, nicht abgeschlossen
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "study_program": "BWL",
                    "study_form": "Zweitstudium",
                    "prev_uni": "TU München",
                    "prev_program": "Maschinenbau",
                    "prev_semesters": "6"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert "prev_uni" in gold.required_arguments["klips2_apply_study"]

    def test_apply_multistep_04_still_missing_after_clarification(self):
        """
        MULTI-STEP: Still missing critical info after clarification - don't call tool.
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

    def test_apply_multistep_05_cancellation(self):
        """
        MULTI-STEP: User cancels application process.
        """
        user_prompt = """
        Previous conversation:
        User: Bewerbung für Informatik WS 2024/25 mit allen Daten...
        Assistant: Soll ich die Bewerbung einreichen?
        
        Current message: Doch nicht, ich überleg mir das nochmal
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_apply_study"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_apply_study" in gold.forbidden_tools

    def test_apply_multistep_06_correction_program(self):
        """
        MULTI-STEP: User corrects study program.
        """
        user_prompt = """
        Previous conversation:
        User: [Vollständige Bewerbungsdaten für Medizin]
        Assistant: Ich bereite die Bewerbung für Medizin vor.
        
        Current message: Sorry, ich meinte Biologie nicht Medizin
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "study_program": "Biologie"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_arguments["klips2_apply_study"]["study_program"] == "Biologie"

    def test_apply_multistep_07_provide_personal_data(self):
        """
        MULTI-STEP: User provides personal data after initial request.
        """
        user_prompt = """
        Previous conversation:
        User: Informatik Bachelor WS 2024/25, Erststudium.
              Login: test@uni-koeln.de / pass
              Abitur 2,3, Gymnasium Köln, 2018.
        Assistant: Ich benötige noch Ihre persönlichen Daten (Geschlecht, Geburtsdatum, Geburtsort).
        
        Current message: Männlich, geboren am 15.03.1999 in Köln, Deutschland, deutsch
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "study_program": "Informatik",
                    "gender": "männlich",
                    "birth_place": "Köln",
                    "nationality": "deutsch"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]


class TestApplyEdgeCases:
    """
    Edge cases and special scenarios.
    """

    def test_apply_edge_01_international_student(self):
        """
        EDGE: International student with non-German HZB.
        """
        user_prompt = """
        Apply for Computer Science Bachelor WS 2024/25, first semester, Erststudium.
        Login: ali.hassan@uni-koeln.de / SecurePass123
        Male, born 20.08.1999 in Cairo, Egypt, Egyptian nationality.
        High School Diploma from 15.06.2017, Cairo International School, Grade 1.2, Egypt.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "username": "ali.hassan@uni-koeln.de",
                    "study_program": "Computer Science",
                    "birth_place": "Cairo",
                    "birth_country": "Egypt",
                    "nationality": "Egyptian",
                    "hzb_country": "Egypt"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_edge_02_diverse_gender(self):
        """
        EDGE: Application with diverse gender.
        """
        user_prompt = """
        Informatik Bachelor WS 2024/25, Erststudium, 1. Semester.
        Login: kim@uni-koeln.de / pass123
        Divers, 01.01.2000, Berlin, Deutschland, deutsch.
        Abitur 1,5 am 01.06.2018, Gymnasium Berlin.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "study_program": "Informatik",
                    "gender": "divers"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_edge_03_fachhochschulreife(self):
        """
        EDGE: Application with Fachhochschulreife instead of Abitur.
        """
        user_prompt = """
        BWL Bachelor WS 2024/25, Erststudium, 1. Semester.
        Login: lisa@uni-koeln.de / pw123
        Weiblich, 05.05.1999, Düsseldorf, Deutschland, deutsch.
        Fachhochschulreife mit Note 2,1 am 01.06.2017, Berufskolleg Düsseldorf.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "study_program": "BWL",
                    "hzb_type": "Fachhochschulreife",
                    "hzb_grade": "2,1",
                    "hzb_school": "Berufskolleg Düsseldorf"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]

    def test_apply_edge_04_higher_semester(self):
        """
        EDGE: Application for higher semester (not 1st).
        """
        user_prompt = """
        Informatik Bachelor WS 2024/25, Erststudium, 5. Fachsemester.
        Login: max@uni-koeln.de / pass
        Männlich, 15.03.1997, Köln, deutsch.
        Abitur 2,0 am 01.06.2015, Gymnasium Köln.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_apply_study"],
            required_arguments={
                "klips2_apply_study": {
                    "study_program": "Informatik",
                    "entry_semester": "5"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.required_tools == ["klips2_apply_study"]


# Total: 25 scenarios (4 Easy + 10 Hard + 7 MultiStep + 4 Edge)
