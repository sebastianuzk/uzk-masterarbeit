"""
Unit Tests für das E-Mail Tool
==============================
Testet die E-Mail-Funktionalität ohne echte E-Mails zu senden (mocked).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.tools.email_tool import (
    EmailTool,
    EmailInput,
    create_email_tool
)


class TestEmailInput:
    """Tests für das Input-Schema"""
    
    def test_valid_input(self):
        """Test: Gültiges Input wird akzeptiert"""
        input_data = EmailInput(
            subject="Test Betreff",
            body="Test Nachricht"
        )
        assert input_data.subject == "Test Betreff"
        assert input_data.body == "Test Nachricht"
    
    def test_empty_body(self):
        """Test: Leerer Body wird akzeptiert"""
        input_data = EmailInput(subject="Test", body="")
        assert input_data.body == ""


class TestEmailTool:
    """Tests für das E-Mail Tool"""
    
    def test_tool_name(self):
        """Test: Tool hat korrekten Namen"""
        tool = EmailTool()
        assert tool.name == "send_email"
    
    def test_tool_description(self):
        """Test: Tool hat eine Beschreibung"""
        tool = EmailTool()
        assert len(tool.description) > 0
        assert "E-Mail" in tool.description or "email" in tool.description.lower()
    
    def test_args_schema(self):
        """Test: Tool verwendet korrektes Args-Schema"""
        tool = EmailTool()
        assert tool.args_schema == EmailInput
    
    def test_is_valid_email_valid(self):
        """Test: Gültige E-Mail-Adressen werden erkannt"""
        tool = EmailTool()
        assert tool._is_valid_email("test@example.com") == True
        assert tool._is_valid_email("user.name@domain.de") == True
        assert tool._is_valid_email("user+tag@example.org") == True
    
    def test_is_valid_email_invalid(self):
        """Test: Ungültige E-Mail-Adressen werden erkannt"""
        tool = EmailTool()
        assert tool._is_valid_email("invalid") == False
        assert tool._is_valid_email("@domain.com") == False
        assert tool._is_valid_email("user@") == False
        assert tool._is_valid_email("") == False
    
    @patch.object(EmailTool, '_is_valid_email', return_value=True)
    @patch('src.tools.email_tool.smtplib.SMTP')
    @patch('src.tools.email_tool.settings')
    def test_run_success(self, mock_settings, mock_smtp, mock_valid):
        """Test: E-Mail wird erfolgreich gesendet"""
        # Mock settings
        mock_settings.DEFAULT_RECIPIENT = "recipient@example.com"
        mock_settings.SMTP_SERVER = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USERNAME = "sender@example.com"
        mock_settings.SMTP_PASSWORD = "password"
        
        # Mock SMTP
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__ = Mock(return_value=mock_smtp_instance)
        mock_smtp.return_value.__exit__ = Mock(return_value=False)
        
        tool = EmailTool()
        result = tool._run(subject="Test", body="Test Nachricht")
        
        # Sollte Erfolg melden
        assert "✅" in result or "erfolgreich" in result.lower() or "gesendet" in result.lower()
    
    @patch('src.tools.email_tool.settings')
    def test_run_no_recipient(self, mock_settings):
        """Test: Fehler wenn kein Empfänger konfiguriert"""
        mock_settings.DEFAULT_RECIPIENT = None
        
        tool = EmailTool()
        result = tool._run(subject="Test", body="Test")
        
        assert "❌" in result or "Fehler" in result or "konfiguriert" in result.lower()
    
    @patch('src.tools.email_tool.smtplib.SMTP')
    @patch('src.tools.email_tool.settings')
    def test_run_handles_smtp_error(self, mock_settings, mock_smtp):
        """Test: SMTP-Fehler werden behandelt"""
        mock_settings.DEFAULT_RECIPIENT = "test@example.com"
        mock_settings.SMTP_SERVER = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USERNAME = "sender@example.com"
        mock_settings.SMTP_PASSWORD = "password"
        
        mock_smtp.side_effect = Exception("SMTP Connection failed")
        
        tool = EmailTool()
        result = tool._run(subject="Test", body="Test")
        
        # Tool sollte Fehler abfangen
        assert "Fehler" in result or "❌" in result or "error" in result.lower()


class TestCreateEmailTool:
    """Tests für die Factory-Funktion"""
    
    def test_create_tool(self):
        """Test: Factory erstellt Tool korrekt"""
        tool = create_email_tool()
        assert isinstance(tool, EmailTool)
        assert tool.name == "send_email"
