"""
Unit Tests für das RAG Tool
===========================
Testet die RAG-Funktionalität mit gemockter ChromaDB.
"""
import os
import sys

import pytest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.tools.rag_tool import (
    UniversityRAGTool,
    create_university_rag_tool
)


class TestUniversityRAGTool:
    """Tests für das University RAG Tool"""
    
    def test_tool_name(self):
        """Test: Tool hat korrekten Namen"""
        tool = UniversityRAGTool()
        assert tool.name == "university_knowledge_search"
    
    def test_tool_description(self):
        """Test: Tool hat eine aussagekräftige Beschreibung"""
        tool = UniversityRAGTool()
        assert len(tool.description) > 0
        assert "Universität" in tool.description or "Uni" in tool.description
        assert "Köln" in tool.description or "WiSo" in tool.description
    
    def test_description_mentions_use_cases(self):
        """Test: Beschreibung erwähnt typische Anwendungsfälle"""
        tool = UniversityRAGTool()
        description = tool.description.lower()
        # Sollte mindestens einige typische Anwendungsfälle erwähnen
        keywords = ["bewerbung", "studien", "fristen", "prüfung"]
        matches = sum(1 for kw in keywords if kw in description)
        assert matches >= 2, "Beschreibung sollte typische Anwendungsfälle erwähnen"
    
    def test_tool_initialization(self):
        """Test: Tool wird korrekt initialisiert"""
        tool = UniversityRAGTool()
        # Tool sollte initialisiert werden ohne Fehler
        assert tool.name == "university_knowledge_search"
        assert hasattr(tool, '_use_advanced')
    
    @patch.object(UniversityRAGTool, '_get_chromadb_client')
    def test_run_returns_string(self, mock_get_client):
        """Test: _run gibt einen String zurück"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [['Test Dokument über Bewerbungen']],
            'metadatas': [[{'source': 'test.html'}]],
            'distances': [[0.5]]
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        tool = UniversityRAGTool()
        result = tool._run("Bewerbungsfristen")
        
        assert isinstance(result, str)
    
    @patch.object(UniversityRAGTool, '_get_chromadb_client')
    def test_run_handles_empty_results(self, mock_get_client):
        """Test: Leere Ergebnisse werden behandelt"""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            'documents': [[]],
            'metadatas': [[]],
            'distances': [[]]
        }
        mock_client = MagicMock()
        mock_client.get_collection.return_value = mock_collection
        mock_get_client.return_value = mock_client
        
        tool = UniversityRAGTool()
        result = tool._run("xyznonexistent12345")
        
        assert isinstance(result, str)
        # Sollte eine Nachricht über keine Ergebnisse enthalten
        assert len(result) > 0
    
    @patch.object(UniversityRAGTool, '_get_chromadb_client')
    def test_run_handles_no_collection(self, mock_get_client):
        """Test: Fehler wenn keine Collection vorhanden"""
        mock_client = MagicMock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_get_client.return_value = mock_client
        
        tool = UniversityRAGTool()
        result = tool._run("Test Query")
        
        # Tool sollte nicht crashen
        assert isinstance(result, str)
    
    @patch.object(UniversityRAGTool, '_get_chromadb_client')
    def test_run_handles_exception(self, mock_get_client):
        """Test: Exceptions werden behandelt"""
        mock_get_client.side_effect = FileNotFoundError("Vector DB nicht gefunden")
        
        tool = UniversityRAGTool()
        # Tool sollte nicht crashen
        result = tool._run("Test Query")
        assert isinstance(result, str)


class TestCreateUniversityRAGTool:
    """Tests für die Factory-Funktion"""
    
    def test_create_tool(self):
        """Test: Factory erstellt Tool korrekt"""
        tool = create_university_rag_tool()
        assert isinstance(tool, UniversityRAGTool)
        assert tool.name == "university_knowledge_search"
    
    def test_create_tool_returns_new_instance(self):
        """Test: Factory erstellt neue Instanzen"""
        tool1 = create_university_rag_tool()
        tool2 = create_university_rag_tool()
        assert tool1 is not tool2
