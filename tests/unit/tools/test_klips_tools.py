"""
Unit Tests für die KLIPS Tools
==============================
Testet die KLIPS-Tool-Funktionalität mit gemocktem Browser.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.tools.klips import (
    create_klips2_register_tool,
    create_klips2_apply_tool,
    create_klips2_change_password_tool,
    create_klips2_get_course_details_tool,
    create_klips2_activate_account_tool,
    create_klips2_change_address_tool
)


class TestKLIPSToolFactories:
    """Tests für die KLIPS Tool Factory-Funktionen"""
    
    def test_create_register_tool(self):
        """Test: Register-Tool wird korrekt erstellt"""
        tool = create_klips2_register_tool()
        assert tool is not None
        assert tool.name == "klips2_register"
        assert len(tool.description) > 0
    
    def test_create_apply_tool(self):
        """Test: Apply-Tool wird korrekt erstellt"""
        tool = create_klips2_apply_tool()
        assert tool is not None
        assert tool.name == "klips2_apply_study"
        assert len(tool.description) > 0
        assert "Bewerbung" in tool.description or "bewerbung" in tool.description.lower()
    
    def test_create_change_password_tool(self):
        """Test: Password-Tool wird korrekt erstellt"""
        tool = create_klips2_change_password_tool()
        assert tool is not None
        assert tool.name == "klips2_change_password"
        assert len(tool.description) > 0
    
    def test_create_course_details_tool(self):
        """Test: Course-Details-Tool wird korrekt erstellt"""
        tool = create_klips2_get_course_details_tool()
        assert tool is not None
        assert tool.name == "klips2_get_course_details"
        assert len(tool.description) > 0
    
    def test_create_activate_account_tool(self):
        """Test: Activate-Tool wird korrekt erstellt"""
        tool = create_klips2_activate_account_tool()
        assert tool is not None
        assert tool.name == "klips2_activate_account"
        assert len(tool.description) > 0
    
    def test_create_change_address_tool(self):
        """Test: Address-Tool wird korrekt erstellt"""
        tool = create_klips2_change_address_tool()
        assert tool is not None
        assert tool.name == "klips2_change_address"
        assert len(tool.description) > 0


class TestKLIPSApplyToolValidation:
    """Tests für die Validierung des KLIPS Apply Tools"""
    
    def test_apply_tool_has_args_schema(self):
        """Test: Apply-Tool hat ein Args-Schema"""
        tool = create_klips2_apply_tool()
        assert tool.args_schema is not None
    
    def test_apply_tool_schema_has_required_fields(self):
        """Test: Schema enthält Pflichtfelder"""
        tool = create_klips2_apply_tool()
        schema = tool.args_schema
        
        # Prüfe ob Schema die wichtigen Felder hat
        schema_fields = schema.model_fields
        
        assert 'semester' in schema_fields
        assert 'degree_type' in schema_fields
        assert 'study_program' in schema_fields
    
    def test_apply_tool_schema_has_optional_fields(self):
        """Test: Schema enthält optionale Felder"""
        tool = create_klips2_apply_tool()
        schema = tool.args_schema
        schema_fields = schema.model_fields
        
        # Optionale persönliche Daten
        assert 'birth_place' in schema_fields
        assert 'gender' in schema_fields
        
        # Optionale Adressdaten
        assert 'street' in schema_fields
        assert 'zip_code' in schema_fields
        assert 'city' in schema_fields
        
        # HZB-Daten
        assert 'hzb_date' in schema_fields
        assert 'hzb_type' in schema_fields
        assert 'hzb_grade' in schema_fields
    
    def test_apply_tool_has_validate_only_mode(self):
        """Test: Apply-Tool hat einen validate_only Modus"""
        tool = create_klips2_apply_tool()
        schema = tool.args_schema
        schema_fields = schema.model_fields
        
        assert 'validate_only' in schema_fields


class TestKLIPSRegisterToolValidation:
    """Tests für die Validierung des KLIPS Register Tools"""
    
    def test_register_tool_has_args_schema(self):
        """Test: Register-Tool hat ein Args-Schema"""
        tool = create_klips2_register_tool()
        assert tool.args_schema is not None
    
    def test_register_tool_schema_has_personal_fields(self):
        """Test: Schema enthält persönliche Felder"""
        tool = create_klips2_register_tool()
        schema = tool.args_schema
        schema_fields = schema.model_fields
        
        # Typische Registrierungsfelder (deutsche Namen)
        expected_fields = ['vorname', 'nachname', 'email', 'geburtsdatum']
        for field in expected_fields:
            assert field in schema_fields, f"Feld '{field}' fehlt im Schema"


class TestKLIPSActivateToolValidation:
    """Tests für die Validierung des KLIPS Activate Tools"""
    
    def test_activate_tool_has_args_schema(self):
        """Test: Activate-Tool hat ein Args-Schema"""
        tool = create_klips2_activate_account_tool()
        assert tool.args_schema is not None
    
    def test_activate_tool_requires_code(self):
        """Test: Activate-Tool benötigt Aktivierungscode"""
        tool = create_klips2_activate_account_tool()
        schema = tool.args_schema
        schema_fields = schema.model_fields
        
        # Sollte einen Aktivierungscode oder ähnliches Feld haben
        code_fields = [f for f in schema_fields if 'code' in f.lower() or 'activation' in f.lower()]
        assert len(code_fields) > 0 or 'activation_code' in schema_fields


class TestKLIPSChangeAddressToolValidation:
    """Tests für die Validierung des KLIPS Address Tools"""
    
    def test_address_tool_has_args_schema(self):
        """Test: Address-Tool hat ein Args-Schema"""
        tool = create_klips2_change_address_tool()
        assert tool.args_schema is not None
    
    def test_address_tool_has_address_fields(self):
        """Test: Schema enthält Adressfelder"""
        tool = create_klips2_change_address_tool()
        schema = tool.args_schema
        schema_fields = schema.model_fields
        
        # Typische Adressfelder
        address_keywords = ['street', 'zip', 'city', 'straße', 'plz', 'ort']
        matches = sum(1 for kw in address_keywords for f in schema_fields if kw in f.lower())
        assert matches >= 2, "Schema sollte Adressfelder enthalten"
