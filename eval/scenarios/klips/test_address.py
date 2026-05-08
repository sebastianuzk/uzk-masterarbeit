"""
KLIPS2 Change Address Tool - Evaluierungs-Testszenarien

Tool: klips2_change_address
Zweck: Studierenden-Adresse im KLIPS2-System aktualisieren

Erforderliche Argumente (aus KLIPS2AuthenticatedInput + KLIPS2ChangeAddressInput):
- username (KLIPS2 Benutzername für Login)
- password (KLIPS2 Passwort für Login)
- street (Straße und Hausnummer)
- zip_code (Postleitzahl)
- city (Stadt)

Optionale Argumente:
- country (Standard: "Deutschland")

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


class TestAddressEasy:
    """Einfache Szenarien - Alle Adressinformationen klar angegeben."""

    def test_address_01_complete_german(self):
        """
        EASY: Complete German address with login credentials.
        """
        user_prompt = """
        Ich bin umgezogen und möchte meine Adresse in KLIPS ändern.
        Login: max@uni-koeln.de / Geheim123
        Neue Adresse: Musterstraße 42, 50678 Köln, Deutschland
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "username": "max@uni-koeln.de",
                    "password": "Geheim123",
                    "street": "Musterstraße 42",
                    "zip_code": "50678",
                    "city": "Köln",
                    "country": "Deutschland"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_change_address"]

    def test_address_02_structured_format(self):
        """
        EASY: Address in structured key-value format with credentials.
        """
        user_prompt = """
        Adressänderung in KLIPS:
        Benutzername: anna@uni-koeln.de
        Passwort: Secret456
        Straße: Hauptweg 15a
        PLZ: 53115
        Stadt: Bonn
        Land: Deutschland
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "username": "anna@uni-koeln.de",
                    "password": "Secret456",
                    "street": "Hauptweg 15a",
                    "zip_code": "53115",
                    "city": "Bonn"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_change_address"]


class TestAddressMedium:
    """Medium scenarios - address in natural language or unusual format."""

    def test_address_03_conversational(self):
        """
        MEDIUM: Address embedded in conversational text with credentials.
        """
        user_prompt = """
        Hey, ich wohne jetzt in der Universitätsstraße 1 in 50931 Köln.
        Kannst du das in KLIPS aktualisieren? Mein Login ist 
        student@uni-koeln.de mit Passwort MeinPW123.
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "username": "student@uni-koeln.de",
                    "password": "MeinPW123",
                    "street": "Universitätsstraße 1",
                    "zip_code": "50931",
                    "city": "Köln"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_change_address"]

    def test_address_04_international(self):
        """
        MEDIUM: International address (Austria).
        """
        user_prompt = """
        Neue Adresse: Ringstraße 100, 1010 Wien, Österreich
        Login: peter@uni-koeln.de, Passwort: Austria123
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "username": "peter@uni-koeln.de",
                    "password": "Austria123",
                    "street": "Ringstraße 100",
                    "zip_code": "1010",
                    "city": "Wien",
                    "country": "Österreich"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_change_address"]["country"] == "Österreich"


class TestAddressHard:
    """Hard scenarios - incomplete or ambiguous address information."""

    def test_address_05_missing_credentials(self):
        """
        HARD: Address change without login credentials.
        LLM should ask for credentials, NOT call tool.
        """
        user_prompt = """
        Ich bin umgezogen. Meine neue Adresse ist:
        Musterstraße 42, 50678 Köln, Deutschland
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_address"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_address" in gold.forbidden_tools

    def test_address_06_missing_zip_code(self):
        """
        HARD: Address missing postal code.
        LLM should ask for postal code, NOT call tool.
        """
        user_prompt = """
        KLIPS Login: user@uni-koeln.de / pass123
        Neue Adresse: Musterweg 5, Köln, Deutschland
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_address"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_address" in gold.forbidden_tools

    def test_address_07_missing_city(self):
        """
        HARD: Address missing city.
        """
        user_prompt = """
        Login: test@uni-koeln.de / pw
        Neue Adresse: Hauptstraße 10, 50667
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_address"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_address" in gold.forbidden_tools


# Total: 7 scenarios
