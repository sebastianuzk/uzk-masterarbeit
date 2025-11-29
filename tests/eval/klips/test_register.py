"""
KLIPS2 Register Tool - Evaluation Test Scenarios

Tool: klips2_register
Purpose: Account registration for new KLIPS2 users

Required arguments:
- vorname (first name)
- nachname (last name)
- geschlecht (gender)
- geburtsdatum (birth date)
- email
- staatsangehoerigkeit (nationality)

Optional arguments:
- geburtsname (birth name)
- sprache (language preference)

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


class TestRegisterEasy:
    """Easy scenarios - all information provided clearly."""

    def test_register_01_complete_german_male(self):
        """
        EASY: Complete registration request with all data for German male student.
        """
        user_prompt = """
        Ich möchte mich bei KLIPS2 registrieren. Hier sind meine Daten:
        - Vorname: Max
        - Nachname: Mustermann
        - Geschlecht: männlich
        - Geburtsdatum: 15.03.1999
        - E-Mail: max.mustermann@gmail.com
        - Staatsangehörigkeit: Deutschland
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "Max",
                    "nachname": "Mustermann",
                    "geschlecht": "männlich",
                    "geburtsdatum": "15.03.1999",
                    "email": "max.mustermann@gmail.com",
                    "staatsangehoerigkeit": "Deutschland"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_register"]

    def test_register_02_complete_german_female(self):
        """
        EASY: Complete registration request for German female student.
        """
        user_prompt = """
        Bitte registriere mich für KLIPS2:
        Vorname: Anna
        Nachname: Schmidt
        Geschlecht: weiblich
        Geburtsdatum: 22.07.2001
        E-Mail: anna.schmidt@web.de
        Staatsangehörigkeit: deutsch
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "Anna",
                    "nachname": "Schmidt",
                    "geschlecht": "weiblich",
                    "geburtsdatum": "22.07.2001",
                    "email": "anna.schmidt@web.de",
                    "staatsangehoerigkeit": "deutsch"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_register"]

    def test_register_03_international_student(self):
        """
        EASY: Registration for international student with English preference.
        """
        user_prompt = """
        I want to register for KLIPS2. My details:
        First name: John
        Last name: Smith
        Gender: male
        Date of birth: 10.05.1998
        Email: john.smith@outlook.com
        Nationality: United States
        Language preference: English
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "John",
                    "nachname": "Smith",
                    "geschlecht": "male",
                    "geburtsdatum": "10.05.1998",
                    "email": "john.smith@outlook.com",
                    "staatsangehoerigkeit": "United States",
                    "sprache": "English"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "sprache" in gold.required_arguments["klips2_register"]


class TestRegisterMedium:
    """Medium scenarios - information needs extraction from natural language."""

    def test_register_04_conversational_format(self):
        """
        MEDIUM: Registration data embedded in conversational text.
        """
        user_prompt = """
        Hi! Ich bin Lisa Müller und möchte gerne einen KLIPS2-Account erstellen.
        Ich bin am 3. Januar 2000 geboren und bin weiblich. Meine E-Mail ist
        lisa.mueller@gmx.de und ich habe die deutsche Staatsangehörigkeit.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "Lisa",
                    "nachname": "Müller",
                    "geschlecht": "weiblich",
                    "geburtsdatum": "03.01.2000",
                    "email": "lisa.mueller@gmx.de",
                    "staatsangehoerigkeit": "deutsch"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_register"]

    def test_register_05_with_birth_name(self):
        """
        MEDIUM: Registration including optional birth name (Geburtsname).
        """
        user_prompt = """
        KLIPS2-Registrierung bitte:
        - Name: Maria Weber (geborene Schneider)
        - Geschlecht: weiblich
        - Geboren am 18.11.1995
        - E-Mail: maria.weber@uni-koeln.de
        - Nationalität: Österreich
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "Maria",
                    "nachname": "Weber",
                    "geburtsname": "Schneider",
                    "geschlecht": "weiblich",
                    "geburtsdatum": "18.11.1995",
                    "email": "maria.weber@uni-koeln.de",
                    "staatsangehoerigkeit": "Österreich"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "geburtsname" in gold.required_arguments["klips2_register"]

    def test_register_06_diverse_gender(self):
        """
        MEDIUM: Registration with diverse/non-binary gender.
        """
        user_prompt = """
        Ich brauche einen KLIPS-Account.
        Mein Name ist Kim Nowak, ich bin divers und wurde am 5.9.1997 geboren.
        E-Mail: kim.nowak@posteo.de
        Ich bin deutscher Staatsbürger.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "Kim",
                    "nachname": "Nowak",
                    "geschlecht": "divers",
                    "geburtsdatum": "05.09.1997",
                    "email": "kim.nowak@posteo.de",
                    "staatsangehoerigkeit": "deutsch"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_register"]["geschlecht"] == "divers"

    def test_register_07_special_characters_name(self):
        """
        MEDIUM: Name with special characters (umlauts, accents).
        """
        user_prompt = """
        KLIPS2 Registrierung:
        - Vorname: François-José
        - Nachname: O'Brien-Müller
        - Geschlecht: männlich
        - Geburtsdatum: 05.08.1997
        - E-Mail: francois@mail.de
        - Staatsangehörigkeit: Frankreich
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "François-José",
                    "nachname": "O'Brien-Müller",
                    "geschlecht": "männlich",
                    "email": "francois@mail.de"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_register"]

    def test_register_08_date_format_variation(self):
        """
        MEDIUM: Birth date in different format (YYYY-MM-DD).
        """
        user_prompt = """
        Registrierung für KLIPS:
        Name: Peter Wagner
        Geschlecht: m
        Geburtsdatum: 1999-03-15
        Email: peter.wagner@gmx.de
        Nationalität: DE
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "Peter",
                    "nachname": "Wagner",
                    "geburtsdatum": "15.03.1999",
                    "email": "peter.wagner@gmx.de"
                }
            },
            argument_match_mode=ArgumentMatchMode.SEMANTIC
        )
        
        assert gold.argument_match_mode == ArgumentMatchMode.SEMANTIC

    def test_register_09_english_request(self):
        """
        MEDIUM: Registration request fully in English.
        """
        user_prompt = """
        I need to create a KLIPS2 account:
        - First name: Sarah
        - Last name: Johnson
        - Gender: female
        - Date of birth: March 22, 1998
        - Email: sarah.j@university.edu
        - Nationality: USA
        - Preferred language: English
        """
        
        gold = GoldStandard(
            required_tools=["klips2_register"],
            required_arguments={
                "klips2_register": {
                    "vorname": "Sarah",
                    "nachname": "Johnson",
                    "geschlecht": "female",
                    "email": "sarah.j@university.edu",
                    "sprache": "English"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_register"]["sprache"] == "English"


class TestRegisterHard:
    """Hard scenarios - incomplete information, should ask or fail."""

    def test_register_10_missing_email(self):
        """
        HARD: Registration request missing email address.
        LLM should ask for missing email, NOT call tool.
        """
        user_prompt = """
        Registriere mich bitte bei KLIPS2:
        Name: Thomas Klein
        Geschlecht: männlich
        Geburtsdatum: 12.04.1996
        Staatsangehörigkeit: Deutschland
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_register" in gold.forbidden_tools

    def test_register_11_missing_birthdate(self):
        """
        HARD: Registration request missing birth date.
        """
        user_prompt = """
        Ich möchte mich für KLIPS anmelden.
        Ich heiße Peter Bauer, bin männlich, meine E-Mail ist peter@test.de
        und ich bin Deutscher.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_register" in gold.forbidden_tools

    def test_register_12_ambiguous_name(self):
        """
        HARD: Name format is ambiguous (only one name provided).
        """
        user_prompt = """
        KLIPS2 Account erstellen:
        Name: Schulze
        Geschlecht: männlich  
        Geburtsdatum: 01.01.2000
        E-Mail: schulze@email.de
        Nationalität: DE
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_register" in gold.forbidden_tools

    def test_register_13_missing_gender(self):
        """
        HARD: Registration missing gender field.
        """
        user_prompt = """
        Erstelle KLIPS-Account:
        Vorname: Alex
        Nachname: Kim
        Geboren: 10.10.2000
        E-Mail: alex.kim@mail.de
        Staatsangehörigkeit: Südkorea
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_register" in gold.forbidden_tools

    def test_register_14_invalid_email_format(self):
        """
        HARD: Registration with obviously invalid email.
        """
        user_prompt = """
        KLIPS Registrierung:
        Vorname: Test
        Nachname: User
        Geschlecht: männlich
        Geburtsdatum: 01.01.2000
        E-Mail: keine-echte-email
        Staatsangehörigkeit: Deutschland
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_register"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_register" in gold.forbidden_tools


# Total: 14 scenarios
