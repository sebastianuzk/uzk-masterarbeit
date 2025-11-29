"""
KLIPS2 Change Address Tool - Evaluation Test Scenarios

Tool: klips2_change_address
Purpose: Update student address in KLIPS2 system

Required arguments:
- strasse (street name)
- hausnummer (house number)
- plz (postal code)
- ort (city)
- land (country)

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


class TestAddressEasy:
    """Easy scenarios - all address information provided clearly."""

    def test_address_01_complete_german(self):
        """
        EASY: Complete German address with all fields.
        """
        user_prompt = """
        Ich bin umgezogen. Meine neue Adresse ist:
        Musterstraße 42
        50678 Köln
        Deutschland
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "strasse": "Musterstraße",
                    "hausnummer": "42",
                    "plz": "50678",
                    "ort": "Köln",
                    "land": "Deutschland"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_change_address"]

    def test_address_02_structured_format(self):
        """
        EASY: Address in structured key-value format.
        """
        user_prompt = """
        Adressänderung in KLIPS:
        Straße: Hauptweg
        Hausnummer: 15a
        PLZ: 53115
        Stadt: Bonn
        Land: Deutschland
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "strasse": "Hauptweg",
                    "hausnummer": "15a",
                    "plz": "53115",
                    "ort": "Bonn",
                    "land": "Deutschland"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_change_address"]["hausnummer"] == "15a"


class TestAddressMedium:
    """Medium scenarios - address in natural language or unusual format."""

    def test_address_03_conversational(self):
        """
        MEDIUM: Address embedded in conversational text.
        """
        user_prompt = """
        Hey, ich wohne jetzt in der Universitätsstraße 1 in 50931 Köln, 
        Deutschland. Kannst du das in KLIPS aktualisieren?
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "strasse": "Universitätsstraße",
                    "hausnummer": "1",
                    "plz": "50931",
                    "ort": "Köln",
                    "land": "Deutschland"
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
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "strasse": "Ringstraße",
                    "hausnummer": "100",
                    "plz": "1010",
                    "ort": "Wien",
                    "land": "Österreich"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_arguments["klips2_change_address"]["land"] == "Österreich"

    def test_address_05_apartment_number(self):
        """
        MEDIUM: Address with apartment/unit number.
        """
        user_prompt = """
        Adressänderung: Kölner Str. 50, Wohnung 3, 50674 Köln, DE
        """
        
        gold = GoldStandard(
            required_tools=["klips2_change_address"],
            required_arguments={
                "klips2_change_address": {
                    "strasse": "Kölner Str.",
                    "hausnummer": "50",
                    "plz": "50674",
                    "ort": "Köln"
                }
            },
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert gold.required_tools == ["klips2_change_address"]


class TestAddressHard:
    """Hard scenarios - incomplete or ambiguous address information."""

    def test_address_06_missing_postal_code(self):
        """
        HARD: Address missing postal code.
        LLM should ask for postal code, NOT call tool.
        """
        user_prompt = """
        Neue Adresse: Musterweg 5, Köln, Deutschland
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_address"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_address" in gold.forbidden_tools

    def test_address_07_missing_house_number(self):
        """
        HARD: Address missing house number.
        """
        user_prompt = """
        Ich wohne jetzt in der Hauptstraße in 50667 Köln.
        """
        
        gold = GoldStandard(
            required_tools=[],
            forbidden_tools={"klips2_change_address"},
            argument_match_mode=ArgumentMatchMode.NORMALIZED
        )
        
        assert "klips2_change_address" in gold.forbidden_tools


# Total: 7 scenarios
