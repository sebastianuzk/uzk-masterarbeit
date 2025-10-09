"""
Tests für Process Engine Integration
Testet alle Komponenten der automatisierten Workflow-Orchestrierung
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Dict, Any, List

# Process Engine Imports - Direct imports ohne __init__.py
try:
    from src.process_engine.data_extractor import ConversationDataExtractor, ExtractedData
    from src.process_engine.workflow_manager import WorkflowManager, WorkflowDefinition
    from src.process_engine.bpmn_generator import BPMNGenerator
    from src.tools.process_engine_tool import ProcessEngineTool
    PROCESS_ENGINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Process Engine Imports nicht verfügbar: {e}")
    PROCESS_ENGINE_AVAILABLE = False
    
    # Mock Classes für Tests
    class ConversationDataExtractor:
        pass
    class ExtractedData:
        pass
    class WorkflowManager:
        pass
    class WorkflowDefinition:
        pass
    class BPMNGenerator:
        pass
    class ProcessEngineTool:
        pass

# LangChain Imports für Mock Messages
try:
    from langchain_core.messages import HumanMessage, AIMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    print("⚠️ LangChain nicht verfügbar - verwende Mock Classes")
    LANGCHAIN_AVAILABLE = False
    # Fallback Mock Classes
    class HumanMessage:
        def __init__(self, content: str):
            self.content = content
    
    class AIMessage:
        def __init__(self, content: str):
            self.content = content


@pytest.mark.skipif(not PROCESS_ENGINE_AVAILABLE, reason="Process Engine nicht verfügbar")
class TestConversationDataExtractor:
    """Tests für intelligente Datenextraktion aus Gesprächen"""
    
    def setup_method(self):
        self.extractor = ConversationDataExtractor()
    
    def test_extract_student_id(self):
        """Test Extraktion von Studenten-IDs"""
        message = "Meine Matrikelnummer ist 1234567"
        result = self.extractor.extract_from_message(message)
        
        student_data = [d for d in result if d.entity_type == 'student_id']
        assert len(student_data) > 0
        assert student_data[0].data['student_id'] == '1234567'
        assert student_data[0].confidence > 0.7
    
    def test_extract_email(self):
        """Test Extraktion von E-Mail-Adressen"""
        message = "Meine E-Mail ist max.mustermann@smail.uni-koeln.de"
        result = self.extractor.extract_from_message(message)
        
        email_data = [d for d in result if d.entity_type == 'email']
        assert len(email_data) > 0
        assert email_data[0].data['email'] == 'max.mustermann@smail.uni-koeln.de'
        assert email_data[0].confidence > 0.9
    
    def test_extract_name(self):
        """Test Extraktion von Namen"""
        message = "Ich heiße Max Mustermann"
        result = self.extractor.extract_from_message(message)
        
        name_data = [d for d in result if d.entity_type == 'name']
        assert len(name_data) > 0
        extracted_name = name_data[0].data['name'].lower()
        assert 'max mustermann' in extracted_name
    
    def test_extract_course(self):
        """Test Extraktion von Studiengängen"""
        message = "Ich studiere Informatik im Bachelor"
        result = self.extractor.extract_from_message(message)
        
        course_data = [d for d in result if d.entity_type == 'course']
        assert len(course_data) > 0
        extracted_course = course_data[0].data['course'].lower()
        assert 'informatik' in extracted_course
    
    def test_extract_semester(self):
        """Test Extraktion von Semesterinformationen"""
        message = "Ich bin im 5. Semester"
        result = self.extractor.extract_from_message(message)
        
        semester_data = [d for d in result if d.entity_type == 'semester']
        assert len(semester_data) > 0
        assert semester_data[0].data['semester'] == '5'
    
    def test_extract_contextual_intent_transcript(self):
        """Test Erkennung von Zeugnis-Anfragen"""
        message = "Ich brauche ein Transcript für meine Bewerbung"
        result = self.extractor.extract_from_message(message)
        
        intent_data = [d for d in result if d.entity_type == 'intent']
        assert len(intent_data) > 0
        assert intent_data[0].data['intent'] == 'transcript_request'
    
    def test_extract_contextual_intent_exam(self):
        """Test Erkennung von Prüfungsanmeldungen"""
        message = "Ich möchte mich für die Prüfungsanmeldung registrieren"
        result = self.extractor.extract_from_message(message)
        
        intent_data = [d for d in result if d.entity_type == 'intent']
        assert len(intent_data) > 0
        assert intent_data[0].data['intent'] == 'exam_registration'
    
    def test_extract_from_conversation(self):
        """Test Extraktion aus kompletter Unterhaltung"""
        messages = [
            HumanMessage("Hallo, ich heiße Max Mustermann"),
            HumanMessage("Meine Matrikelnummer ist 1234567"),
            HumanMessage("Ich brauche ein Zeugnis für meine Bewerbung")
        ]
        
        result = self.extractor.extract_from_conversation(messages)
        
        # Prüfe verschiedene extrahierte Datentypen
        data_types = set(d.entity_type for d in result)
        assert 'name' in data_types
        assert 'student_id' in data_types
        assert 'intent' in data_types
    
    def test_consolidate_data(self):
        """Test Konsolidierung und Deduplizierung"""
        # Simuliere doppelte Daten
        data1 = ExtractedData('student_id', {'student_id': '1234567'}, 0.8, 'msg1', datetime.now())
        data2 = ExtractedData('student_id', {'student_id': '1234567'}, 0.9, 'msg2', datetime.now())
        
        result = self.extractor._consolidate_data([data1, data2])
        
        # Sollte nur ein Eintrag mit höherem Vertrauen bleiben
        assert len(result) == 1
        assert result[0].confidence == 0.9
    
    def test_get_process_variables(self):
        """Test Konvertierung zu Process Engine Variablen"""
        extracted_data = [
            ExtractedData('student_id', {'student_id': '1234567'}, 0.9, 'msg', datetime.now()),
            ExtractedData('email', {'email': 'test@example.com'}, 0.95, 'msg', datetime.now()),
            ExtractedData('intent', {'intent': 'transcript_request'}, 0.8, 'msg', datetime.now())
        ]
        
        variables = self.extractor.get_process_variables(extracted_data)
        
        assert 'student_id' in variables
        assert variables['student_id'] == '1234567'
        assert 'email' in variables
        assert variables['email'] == 'test@example.com'
        assert 'has_student_data' in variables
        assert variables['has_student_data'] is True
        assert 'data_quality_score' in variables


@pytest.mark.skipif(not PROCESS_ENGINE_AVAILABLE, reason="Process Engine nicht verfügbar")
class TestWorkflowManager:
    """Tests für Workflow-Verwaltung und Orchestrierung"""
    
    def setup_method(self):
        # Mock Process Client
        self.mock_process_client = Mock()
        self.workflow_manager = WorkflowManager(self.mock_process_client)
    
    def test_default_workflows_loaded(self):
        """Test Standard-Workflows werden geladen"""
        workflows = self.workflow_manager.workflows
        
        expected_workflows = [
            'student_transcript_request',
            'exam_registration', 
            'grade_inquiry',
            'course_enrollment',
            'schedule_request'
        ]
        
        for workflow_id in expected_workflows:
            assert workflow_id in workflows
            assert isinstance(workflows[workflow_id], WorkflowDefinition)
    
    def test_analyze_conversation_for_workflows(self):
        """Test Workflow-Erkennung in Unterhaltungen"""
        messages = [
            HumanMessage("Ich brauche ein Zeugnis für meine Bewerbung")
        ]
        
        triggered_workflows = self.workflow_manager.analyze_conversation_for_workflows(messages)
        
        assert 'student_transcript_request' in triggered_workflows
    
    def test_can_start_workflow_success(self):
        """Test erfolgreiche Workflow-Voraussetzungsprüfung"""
        extracted_data = [
            ExtractedData('student_id', {'student_id': '1234567'}, 0.9, 'msg', datetime.now()),
            ExtractedData('email', {'email': 'test@example.com'}, 0.95, 'msg', datetime.now())
        ]
        
        can_start, missing_data = self.workflow_manager.can_start_workflow(
            'student_transcript_request', 
            extracted_data
        )
        
        assert can_start is True
        assert len(missing_data) == 0
    
    def test_can_start_workflow_missing_data(self):
        """Test Workflow-Voraussetzungsprüfung mit fehlenden Daten"""
        extracted_data = [
            ExtractedData('student_id', {'student_id': '1234567'}, 0.9, 'msg', datetime.now())
            # E-Mail fehlt
        ]
        
        can_start, missing_data = self.workflow_manager.can_start_workflow(
            'student_transcript_request',
            extracted_data
        )
        
        assert can_start is False
        assert 'email' in missing_data
    
    @patch('src.process_engine.workflow_manager.ProcessInstance')
    def test_start_workflow_success(self, mock_process_instance):
        """Test erfolgreicher Workflow-Start"""
        # Mock Process Instance
        mock_instance = Mock()
        mock_instance.process_instance_key = 12345
        self.mock_process_client.start_process_instance.return_value = mock_instance
        
        messages = [
            HumanMessage("Ich heiße Max Mustermann"),
            HumanMessage("Meine Matrikelnummer ist 1234567"), 
            HumanMessage("Meine E-Mail ist max@example.com"),
            HumanMessage("Ich brauche ein Zeugnis")
        ]
        
        execution = self.workflow_manager.start_workflow(
            'student_transcript_request',
            messages
        )
        
        assert execution is not None
        assert execution.workflow_id == 'student_transcript_request'
        assert execution.process_instance == mock_instance
    
    def test_register_workflow(self):
        """Test Workflow-Registrierung"""
        custom_workflow = WorkflowDefinition(
            bpmn_process_id='test-workflow',
            name='Test Workflow',
            description='Test Description',
            version='1.0',
            triggers=['test'],
            required_data=['test_data']
        )
        
        self.workflow_manager.register_workflow('test_workflow', custom_workflow)
        
        assert 'test_workflow' in self.workflow_manager.workflows
        assert self.workflow_manager.workflows['test_workflow'] == custom_workflow
    
    def test_job_handlers_registered(self):
        """Test Standard Job Handlers sind registriert"""
        expected_handlers = [
            'send-email',
            'validate-student-data',
            'generate-document',
            'database-query',
            'send-notification'
        ]
        
        for handler_name in expected_handlers:
            assert handler_name in self.workflow_manager.job_handlers
    
    def test_get_workflow_statistics(self):
        """Test Workflow-Statistiken"""
        stats = self.workflow_manager.get_workflow_statistics()
        
        assert 'total_active_workflows' in stats
        assert 'workflow_counts' in stats
        assert 'available_workflows' in stats
        assert 'registered_handlers' in stats
        assert stats['available_workflows'] >= 5  # Mindestens 5 Standard-Workflows


@pytest.mark.skipif(not PROCESS_ENGINE_AVAILABLE, reason="Process Engine nicht verfügbar")
class TestBPMNGenerator:
    """Tests für BPMN XML Generierung"""
    
    def setup_method(self):
        self.generator = BPMNGenerator()
    
    def test_generate_student_transcript_workflow(self):
        """Test Generierung des Zeugnis-Workflows"""
        bpmn_xml = self.generator.generate_student_transcript_workflow()
        
        assert bpmn_xml is not None
        assert 'student-transcript-request' in bpmn_xml
        assert 'bpmn:process' in bpmn_xml
        assert 'validate_student_data' in bpmn_xml
        assert 'generate_transcript' in bpmn_xml
    
    def test_generate_exam_registration_workflow(self):
        """Test Generierung des Prüfungsanmeldungs-Workflows"""
        bpmn_xml = self.generator.generate_exam_registration_workflow()
        
        assert bpmn_xml is not None
        assert 'exam-registration' in bpmn_xml
        assert 'validate_registration_data' in bpmn_xml
        assert 'check_exam_eligibility' in bpmn_xml
    
    def test_generate_grade_inquiry_workflow(self):
        """Test Generierung des Notenabfrage-Workflows"""
        bpmn_xml = self.generator.generate_grade_inquiry_workflow()
        
        assert bpmn_xml is not None
        assert 'grade-inquiry' in bpmn_xml
        assert 'query_student_grades' in bpmn_xml
    
    def test_generate_all_university_workflows(self):
        """Test Generierung aller Standard-Workflows"""
        temp_dir = "/tmp/test_workflows"
        os.makedirs(temp_dir, exist_ok=True)
        
        workflows = self.generator.generate_all_university_workflows(temp_dir)
        
        expected_workflows = [
            'student-transcript-request',
            'exam-registration', 
            'grade-inquiry'
        ]
        
        for workflow_id in expected_workflows:
            assert workflow_id in workflows
            # Prüfe dass Datei existiert
            assert os.path.exists(workflows[workflow_id])
        
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_create_custom_workflow(self):
        """Test Erstellung benutzerdefinierter Workflows"""
        tasks = [
            {'id': 'task1', 'name': 'First Task', 'type': 'service', 'job_type': 'test-job'},
            {'id': 'task2', 'name': 'Second Task', 'type': 'user'}
        ]
        
        bpmn_xml = self.generator.create_custom_workflow(
            process_id='custom-process',
            process_name='Custom Process',
            tasks=tasks
        )
        
        assert bpmn_xml is not None
        assert 'custom-process' in bpmn_xml
        assert 'task1' in bpmn_xml
        assert 'task2' in bpmn_xml
        assert 'First Task' in bpmn_xml


@pytest.mark.skipif(not PROCESS_ENGINE_AVAILABLE, reason="Process Engine nicht verfügbar")
class TestProcessEngineTool:
    """Tests für Process Engine Tool Integration"""
    
    def setup_method(self):
        with patch('src.tools.process_engine_tool.Settings') as mock_settings:
            mock_settings.return_value.ENABLE_PROCESS_ENGINE = True
            self.tool = ProcessEngineTool()
    
    def test_tool_initialization(self):
        """Test Tool-Initialisierung"""
        assert self.tool.name == "process_engine"
        assert "automatisiert" in self.tool.description.lower()
    
    @patch('src.tools.process_engine_tool.ProcessEngineTool._analyze_conversation')
    def test_analyze_action(self, mock_analyze):
        """Test Analyze-Aktion"""
        mock_analyze.return_value = "Test analysis result"
        
        result = self.tool._run(
            action="analyze",
            conversation_context="Ich brauche ein Zeugnis"
        )
        
        mock_analyze.assert_called_once_with("Ich brauche ein Zeugnis")
        assert result == "Test analysis result"
    
    @patch('src.tools.process_engine_tool.ProcessEngineTool._start_workflow')
    def test_start_workflow_action(self, mock_start):
        """Test Start Workflow-Aktion"""
        mock_start.return_value = "Workflow started"
        
        result = self.tool._run(
            action="start_workflow",
            workflow_id="student_transcript_request",
            conversation_context="Test context"
        )
        
        mock_start.assert_called_once()
        assert result == "Workflow started"
    
    @patch('src.tools.process_engine_tool.ProcessEngineTool._list_available_workflows')
    def test_list_workflows_action(self, mock_list):
        """Test List Workflows-Aktion"""
        mock_list.return_value = "Available workflows listed"
        
        result = self.tool._run(action="list_workflows")
        
        mock_list.assert_called_once()
        assert result == "Available workflows listed"
    
    def test_unknown_action(self):
        """Test unbekannte Aktion"""
        result = self.tool._run(action="unknown_action")
        
        assert "Unbekannte Aktion" in result
        assert "unknown_action" in result


@pytest.mark.skipif(not PROCESS_ENGINE_AVAILABLE, reason="Process Engine nicht verfügbar")
class TestProcessEngineIntegration:
    """Integration Tests für komplettes Process Engine System"""
    
    @patch('src.process_engine.process_client.ProcessEngineClient')
    def test_end_to_end_transcript_workflow(self, mock_client):
        """Test kompletter Zeugnis-Workflow von Anfang bis Ende"""
        # Mock Process Client
        mock_process_instance = Mock()
        mock_process_instance.process_instance_key = 12345
        mock_client.return_value.start_process_instance.return_value = mock_process_instance
        
        # Erstelle Workflow Manager
        workflow_manager = WorkflowManager(mock_client.return_value)
        
        # Simuliere Unterhaltung
        messages = [
            HumanMessage("Hallo, ich heiße Max Mustermann"),
            HumanMessage("Meine Matrikelnummer ist 1234567"),
            HumanMessage("Meine E-Mail ist max.mustermann@smail.uni-koeln.de"),
            HumanMessage("Ich brauche ein Zeugnis für meine Bewerbung")
        ]
        
        # Analysiere Workflows
        triggered_workflows = workflow_manager.analyze_conversation_for_workflows(messages)
        assert 'student_transcript_request' in triggered_workflows
        
        # Starte Workflow
        execution = workflow_manager.start_workflow(
            'student_transcript_request',
            messages
        )
        
        # Prüfe Ergebnis
        assert execution is not None
        assert execution.workflow_id == 'student_transcript_request'
        assert execution.status == 'STARTED'
        
        # Prüfe Process Client wurde aufgerufen
        mock_client.return_value.start_process_instance.assert_called_once()
    
    def test_data_extraction_and_validation(self):
        """Test Datenextraktion und Validierung für Workflows"""
        extractor = ConversationDataExtractor()
        
        # Simuliere komplexe Unterhaltung
        messages = [
            HumanMessage("Ich bin Student an der Uni Köln"),
            HumanMessage("Meine Matrikelnummer: 1234567"),
            HumanMessage("Kontakt: max.mustermann@smail.uni-koeln.de"),
            HumanMessage("Studiengang: Master Informatik, 3. Semester"),
            HumanMessage("Ich benötige meine Noten für eine Bewerbung")
        ]
        
        # Extrahiere Daten
        extracted_data = extractor.extract_from_conversation(messages)
        
        # Prüfe extrahierte Datentypen
        data_types = set(d.entity_type for d in extracted_data)
        expected_types = {'student_id', 'email', 'course', 'semester', 'intent'}
        assert expected_types.issubset(data_types)
        
        # Prüfe Datenqualität
        high_confidence_data = [d for d in extracted_data if d.confidence >= 0.7]
        assert len(high_confidence_data) >= 3
        
        # Prüfe Process Variables
        variables = extractor.get_process_variables(extracted_data)
        assert variables['has_student_data'] is True
        assert variables['data_quality_score'] > 0.7


if __name__ == "__main__":
    # Führe Tests aus
    pytest.main([__file__, "-v", "--tb=short"])