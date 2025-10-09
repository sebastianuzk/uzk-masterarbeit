"""
Workflow Manager für intelligente Prozessorchestrierung
Verwaltet BPMN-Workflows und deren automatische Ausführung
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from .process_client import ProcessEngineClient, ProcessInstance
from .data_extractor import ConversationDataExtractor, ExtractedData

@dataclass
class WorkflowDefinition:
    """Definition eines Workflows"""
    bpmn_process_id: str
    name: str
    description: str
    version: str
    triggers: List[str]  # Was löst diesen Workflow aus
    required_data: List[str]  # Welche Daten werden benötigt
    auto_start: bool = False
    priority: int = 1

@dataclass
class WorkflowExecution:
    """Ausführung eines Workflows"""
    workflow_id: str
    process_instance: ProcessInstance
    status: str
    progress: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completion_percentage: float = 0.0

class WorkflowManager:
    """Verwaltet Workflow-Definitionen und deren Ausführung"""
    
    def __init__(self, process_client: ProcessEngineClient):
        self.process_client = process_client
        self.data_extractor = ConversationDataExtractor()
        self.logger = logging.getLogger(__name__)
        
        # Workflow Registry
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.active_executions: Dict[int, WorkflowExecution] = {}
        
        # Job Handlers
        self.job_handlers: Dict[str, Callable] = {}
        
        self._load_default_workflows()
        self._register_default_handlers()
    
    def _load_default_workflows(self):
        """Lädt Standard-Universitäts-Workflows"""
        default_workflows = {
            'student_transcript_request': WorkflowDefinition(
                bpmn_process_id='student-transcript-request',
                name='Transcript Request Process',
                description='Automatisierte Bearbeitung von Zeugnis-Anfragen',
                version='1.0',
                triggers=['transcript_request', 'zeugnis', 'notenübersicht'],
                required_data=['student_id', 'email'],
                auto_start=True,
                priority=2
            ),
            'exam_registration': WorkflowDefinition(
                bpmn_process_id='exam-registration',
                name='Exam Registration Process',
                description='Automatische Prüfungsanmeldung',
                version='1.0',
                triggers=['exam_registration', 'prüfungsanmeldung', 'klausuranmeldung'],
                required_data=['student_id', 'course'],
                auto_start=True,
                priority=3
            ),
            'grade_inquiry': WorkflowDefinition(
                bpmn_process_id='grade-inquiry',
                name='Grade Inquiry Process',
                description='Notenabfrage und -bereitstellung',
                version='1.0',
                triggers=['grade_inquiry', 'noten', 'bewertung'],
                required_data=['student_id'],
                auto_start=True,
                priority=1
            ),
            'course_enrollment': WorkflowDefinition(
                bpmn_process_id='course-enrollment',
                name='Course Enrollment Process',
                description='Kurs-Einschreibung verwalten',
                version='1.0',
                triggers=['enrollment', 'einschreibung', 'kursanmeldung'],
                required_data=['student_id', 'course'],
                auto_start=False,
                priority=2
            ),
            'schedule_request': WorkflowDefinition(
                bpmn_process_id='schedule-request',
                name='Schedule Request Process',
                description='Stundenplan-Anfragen bearbeiten',
                version='1.0',
                triggers=['schedule_request', 'stundenplan', 'termine'],
                required_data=['student_id'],
                auto_start=True,
                priority=1
            )
        }
        
        for workflow_id, workflow in default_workflows.items():
            self.register_workflow(workflow_id, workflow)
    
    def _register_default_handlers(self):
        """Registriert Standard Job Handlers"""
        
        # Email Handler
        def handle_send_email(job):
            """Handler für E-Mail Versand"""
            variables = job.variables
            
            email_data = {
                'recipient': variables.get('email', ''),
                'subject': variables.get('email_subject', 'University Process Notification'),
                'body': variables.get('email_body', 'Ihr Antrag wird bearbeitet.'),
                'template': variables.get('email_template', 'default')
            }
            
            # Hier würde die E-Mail Logik integriert werden
            self.logger.info(f"📧 E-Mail wird gesendet an {email_data['recipient']}")
            
            return {
                'email_sent': True,
                'email_timestamp': datetime.now().isoformat(),
                'email_recipient': email_data['recipient']
            }
        
        # Data Validation Handler
        def handle_validate_student_data(job):
            """Handler für Studentendaten-Validierung"""
            variables = job.variables
            
            student_id = variables.get('student_id')
            email = variables.get('email')
            
            # Simulierte Validierung
            validation_result = {
                'student_id_valid': bool(student_id and len(str(student_id)) >= 6),
                'email_valid': bool(email and '@' in email),
                'validation_timestamp': datetime.now().isoformat()
            }
            
            validation_result['data_complete'] = all([
                validation_result['student_id_valid'],
                validation_result['email_valid']
            ])
            
            self.logger.info(f"✅ Studentendaten validiert: {validation_result['data_complete']}")
            
            return validation_result
        
        # Document Generation Handler
        def handle_generate_document(job):
            """Handler für Dokumentenerstellung"""
            variables = job.variables
            
            document_type = variables.get('document_type', 'transcript')
            student_id = variables.get('student_id')
            
            # Simulierte Dokumentenerstellung
            document_result = {
                'document_generated': True,
                'document_type': document_type,
                'document_id': f"DOC_{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'generation_timestamp': datetime.now().isoformat(),
                'file_path': f"/documents/{document_type}_{student_id}.pdf"
            }
            
            self.logger.info(f"📄 Dokument erstellt: {document_result['document_id']}")
            
            return document_result
        
        # Database Query Handler
        def handle_database_query(job):
            """Handler für Datenbankabfragen"""
            variables = job.variables
            
            query_type = variables.get('query_type', 'student_info')
            student_id = variables.get('student_id')
            
            # Simulierte Datenbankabfrage
            if query_type == 'student_info':
                result = {
                    'student_found': True,
                    'student_name': 'Max Mustermann',
                    'study_program': 'Informatik',
                    'semester': 5,
                    'status': 'active'
                }
            elif query_type == 'grades':
                result = {
                    'grades_found': True,
                    'current_gpa': 2.1,
                    'completed_credits': 120,
                    'grades': [
                        {'course': 'Mathematik I', 'grade': 2.0},
                        {'course': 'Programmierung', 'grade': 1.7},
                        {'course': 'Datenbanken', 'grade': 2.3}
                    ]
                }
            else:
                result = {'query_successful': False, 'error': 'Unknown query type'}
            
            result['query_timestamp'] = datetime.now().isoformat()
            result['query_type'] = query_type
            
            self.logger.info(f"🔍 Datenbankabfrage ausgeführt: {query_type}")
            
            return result
        
        # Notification Handler
        def handle_send_notification(job):
            """Handler für System-Benachrichtigungen"""
            variables = job.variables
            
            notification_type = variables.get('notification_type', 'info')
            message = variables.get('notification_message', 'Process completed')
            recipient = variables.get('recipient', 'system')
            
            notification_result = {
                'notification_sent': True,
                'notification_type': notification_type,
                'message': message,
                'recipient': recipient,
                'notification_id': f"NOTIF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info(f"🔔 Benachrichtigung gesendet: {notification_type} an {recipient}")
            
            return notification_result
        
        # Handler registrieren
        self.register_job_handler('send-email', handle_send_email)
        self.register_job_handler('validate-student-data', handle_validate_student_data)
        self.register_job_handler('generate-document', handle_generate_document)
        self.register_job_handler('database-query', handle_database_query)
        self.register_job_handler('send-notification', handle_send_notification)
    
    def register_workflow(self, workflow_id: str, workflow: WorkflowDefinition):
        """Registriert einen neuen Workflow"""
        self.workflows[workflow_id] = workflow
        self.logger.info(f"✅ Workflow registriert: {workflow_id}")
    
    def register_job_handler(self, job_type: str, handler: Callable):
        """Registriert einen Job Handler"""
        self.job_handlers[job_type] = handler
        
        # Bei Process Client registrieren
        if self.process_client:
            self.process_client.register_job_handler(job_type, handler)
        
        self.logger.info(f"✅ Job Handler registriert: {job_type}")
    
    def analyze_conversation_for_workflows(self, messages) -> List[str]:
        """Analysiert Unterhaltung und identifiziert relevante Workflows"""
        extracted_data = self.data_extractor.extract_from_conversation(messages)
        
        # Finde Workflows basierend auf Absichten und Triggern
        triggered_workflows = []
        
        for data in extracted_data:
            if data.entity_type == 'intent':
                intent_value = data.data.get('intent', '')
                
                for workflow_id, workflow in self.workflows.items():
                    # Prüfe Trigger-Übereinstimmungen
                    if any(trigger in intent_value for trigger in workflow.triggers):
                        if workflow_id not in triggered_workflows:
                            triggered_workflows.append(workflow_id)
        
        # Prüfe auch auf Keyword-basierte Trigger
        conversation_text = ' '.join([msg.content.lower() for msg in messages if hasattr(msg, 'content')])
        
        for workflow_id, workflow in self.workflows.items():
            if any(trigger.lower() in conversation_text for trigger in workflow.triggers):
                if workflow_id not in triggered_workflows:
                    triggered_workflows.append(workflow_id)
        
        # Sortiere nach Priorität
        triggered_workflows.sort(key=lambda wf_id: self.workflows[wf_id].priority, reverse=True)
        
        return triggered_workflows
    
    def can_start_workflow(self, workflow_id: str, extracted_data: List[ExtractedData]) -> tuple[bool, List[str]]:
        """Prüft ob ein Workflow gestartet werden kann"""
        if workflow_id not in self.workflows:
            return False, [f"Workflow {workflow_id} not found"]
        
        workflow = self.workflows[workflow_id]
        missing_data = []
        
        # Extrahierte Datentypen sammeln
        available_data_types = set(data.entity_type for data in extracted_data if data.confidence >= 0.7)
        
        # Prüfe erforderliche Daten
        for required in workflow.required_data:
            if required not in available_data_types:
                missing_data.append(required)
        
        can_start = len(missing_data) == 0
        return can_start, missing_data
    
    def start_workflow(self, workflow_id: str, messages, additional_variables: Dict[str, Any] = None) -> Optional[WorkflowExecution]:
        """Startet einen Workflow basierend auf Unterhaltungsdaten"""
        if workflow_id not in self.workflows:
            self.logger.error(f"❌ Workflow nicht gefunden: {workflow_id}")
            return None
        
        workflow = self.workflows[workflow_id]
        
        # Daten extrahieren
        extracted_data = self.data_extractor.extract_from_conversation(messages)
        
        # Prüfe Voraussetzungen
        can_start, missing_data = self.can_start_workflow(workflow_id, extracted_data)
        
        if not can_start:
            self.logger.warning(f"⚠️ Workflow kann nicht gestartet werden. Fehlende Daten: {missing_data}")
            return None
        
        # Process Variables vorbereiten
        variables = self.data_extractor.get_process_variables(extracted_data)
        
        if additional_variables:
            variables.update(additional_variables)
        
        # Workflow-spezifische Variablen
        variables.update({
            'workflow_id': workflow_id,
            'workflow_name': workflow.name,
            'workflow_version': workflow.version,
            'auto_started': workflow.auto_start,
            'conversation_summary': self._summarize_conversation(messages),
            'extracted_data_count': len(extracted_data),
            'data_confidence_avg': sum(d.confidence for d in extracted_data) / len(extracted_data) if extracted_data else 0
        })
        
        # Prozessinstanz starten
        process_instance = self.process_client.start_process_instance(
            workflow.bpmn_process_id,
            variables
        )
        
        if not process_instance:
            self.logger.error(f"❌ Prozessinstanz konnte nicht gestartet werden: {workflow_id}")
            return None
        
        # Workflow Execution erstellen
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            process_instance=process_instance,
            status='STARTED',
            progress={'phase': 'initialization', 'step': 1},
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.active_executions[process_instance.process_instance_key] = execution
        
        self.logger.info(f"🚀 Workflow gestartet: {workflow_id} (Instance: {process_instance.process_instance_key})")
        
        return execution
    
    def _summarize_conversation(self, messages) -> str:
        """Erstellt eine Zusammenfassung der Unterhaltung"""
        if not messages:
            return "Empty conversation"
        
        # Nehme die letzten 3 Nachrichten für Kontext
        recent_messages = messages[-3:] if len(messages) > 3 else messages
        
        summary_parts = []
        for msg in recent_messages:
            if hasattr(msg, 'content'):
                # Kürze lange Nachrichten
                content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                summary_parts.append(content)
        
        return " | ".join(summary_parts)
    
    def get_workflow_status(self, process_instance_key: int) -> Optional[WorkflowExecution]:
        """Holt den Status einer Workflow-Ausführung"""
        return self.active_executions.get(process_instance_key)
    
    def list_active_workflows(self) -> List[WorkflowExecution]:
        """Listet alle aktiven Workflow-Ausführungen"""
        return list(self.active_executions.values())
    
    def cancel_workflow(self, process_instance_key: int) -> bool:
        """Bricht eine Workflow-Ausführung ab"""
        if process_instance_key in self.active_executions:
            success = self.process_client.cancel_process_instance(process_instance_key)
            if success:
                execution = self.active_executions[process_instance_key]
                execution.status = 'CANCELLED'
                execution.updated_at = datetime.now()
                del self.active_executions[process_instance_key]
            return success
        return False
    
    def update_workflow_progress(self, process_instance_key: int, progress: Dict[str, Any]):
        """Aktualisiert den Fortschritt einer Workflow-Ausführung"""
        if process_instance_key in self.active_executions:
            execution = self.active_executions[process_instance_key]
            execution.progress.update(progress)
            execution.updated_at = datetime.now()
            
            # Berechne Completion Percentage basierend auf Fortschritt
            if 'step' in progress and 'total_steps' in progress:
                execution.completion_percentage = (progress['step'] / progress['total_steps']) * 100
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Holt Statistiken über Workflow-Ausführungen"""
        active_count = len(self.active_executions)
        
        # Gruppiere nach Workflow-Typ
        workflow_counts = {}
        for execution in self.active_executions.values():
            workflow_id = execution.workflow_id
            workflow_counts[workflow_id] = workflow_counts.get(workflow_id, 0) + 1
        
        return {
            'total_active_workflows': active_count,
            'workflow_counts': workflow_counts,
            'available_workflows': len(self.workflows),
            'registered_handlers': len(self.job_handlers),
            'last_updated': datetime.now().isoformat()
        }