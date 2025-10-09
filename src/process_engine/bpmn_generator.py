"""
BPMN Generator für automatische Workflow-Erstellung
Generiert BPMN 2.0 XML-Definitionen basierend auf Universitätsprozessen
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import os

@dataclass
class BPMNTask:
    """Repräsentiert eine BPMN Task"""
    task_id: str
    name: str
    task_type: str  # 'service', 'user', 'manual', 'script'
    job_type: Optional[str] = None  # Für Service Tasks
    inputs: Dict[str, Any] = None
    outputs: Dict[str, Any] = None

@dataclass
class BPMNGateway:
    """Repräsentiert ein BPMN Gateway"""
    gateway_id: str
    name: str
    gateway_type: str  # 'exclusive', 'parallel', 'inclusive'
    conditions: Dict[str, str] = None

@dataclass
class BPMNEvent:
    """Repräsentiert ein BPMN Event"""
    event_id: str
    name: str
    event_type: str  # 'start', 'end', 'intermediate'
    event_definition: Optional[str] = None  # 'message', 'timer', 'signal'

class BPMNGenerator:
    """Generiert BPMN 2.0 XML-Definitionen für Universitätsprozesse"""
    
    def __init__(self):
        self.namespace = {
            'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
            'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
            'dc': 'http://www.omg.org/spec/DD/20100524/DC',
            'di': 'http://www.omg.org/spec/DD/20100524/DI',
            'zeebe': 'http://camunda.org/schema/zeebe/1.0'
        }
        
        # Registriere Namespaces
        for prefix, uri in self.namespace.items():
            ET.register_namespace(prefix, uri)
    
    def generate_student_transcript_workflow(self) -> str:
        """Generiert BPMN für Studenten-Zeugnis-Anfrage"""
        
        # Process Definition
        process_id = "student-transcript-request"
        process_name = "Student Transcript Request Process"
        
        # BPMN Elemente definieren
        start_event = BPMNEvent("start_transcript_request", "Transcript Request Started", "start")
        
        validate_data = BPMNTask(
            "validate_student_data",
            "Validate Student Data",
            "service",
            "validate-student-data"
        )
        
        data_complete_gateway = BPMNGateway(
            "data_complete_check",
            "Data Complete?",
            "exclusive",
            {"${data_complete == true}": "query_student_info", "else": "request_additional_data"}
        )
        
        request_data = BPMNTask(
            "request_additional_data",
            "Request Additional Data",
            "service",
            "send-email"
        )
        
        query_student = BPMNTask(
            "query_student_info",
            "Query Student Information",
            "service",
            "database-query"
        )
        
        generate_transcript = BPMNTask(
            "generate_transcript",
            "Generate Transcript Document",
            "service",
            "generate-document"
        )
        
        send_transcript = BPMNTask(
            "send_transcript_email",
            "Send Transcript via Email",
            "service",
            "send-email"
        )
        
        notify_completion = BPMNTask(
            "notify_completion",
            "Notify Process Completion",
            "service",
            "send-notification"
        )
        
        end_event = BPMNEvent("end_transcript_process", "Transcript Process Completed", "end")
        
        # BPMN XML generieren
        bpmn_xml = self._create_bpmn_xml(
            process_id=process_id,
            process_name=process_name,
            elements=[
                start_event, validate_data, data_complete_gateway, request_data,
                query_student, generate_transcript, send_transcript, notify_completion, end_event
            ],
            sequence_flows=[
                ("start_transcript_request", "validate_student_data"),
                ("validate_student_data", "data_complete_check"),
                ("data_complete_check", "request_additional_data", "${data_complete == false}"),
                ("data_complete_check", "query_student_info", "${data_complete == true}"),
                ("request_additional_data", "end_transcript_process"),
                ("query_student_info", "generate_transcript"),
                ("generate_transcript", "send_transcript_email"),
                ("send_transcript_email", "notify_completion"),
                ("notify_completion", "end_transcript_process")
            ]
        )
        
        return bpmn_xml
    
    def generate_exam_registration_workflow(self) -> str:
        """Generiert BPMN für Prüfungsanmeldung"""
        
        process_id = "exam-registration"
        process_name = "Exam Registration Process"
        
        start_event = BPMNEvent("start_exam_registration", "Exam Registration Started", "start")
        
        validate_data = BPMNTask(
            "validate_registration_data",
            "Validate Registration Data",
            "service",
            "validate-student-data"
        )
        
        check_eligibility = BPMNTask(
            "check_exam_eligibility",
            "Check Exam Eligibility",
            "service",
            "database-query"
        )
        
        eligibility_gateway = BPMNGateway(
            "eligibility_check",
            "Eligible for Exam?",
            "exclusive",
            {"${eligible == true}": "register_for_exam", "else": "send_rejection"}
        )
        
        register_exam = BPMNTask(
            "register_for_exam",
            "Register Student for Exam",
            "service",
            "database-query"
        )
        
        send_confirmation = BPMNTask(
            "send_confirmation_email",
            "Send Registration Confirmation",
            "service",
            "send-email"
        )
        
        send_rejection = BPMNTask(
            "send_rejection_email",
            "Send Rejection Notification",
            "service",
            "send-email"
        )
        
        end_event = BPMNEvent("end_exam_registration", "Exam Registration Completed", "end")
        
        bpmn_xml = self._create_bpmn_xml(
            process_id=process_id,
            process_name=process_name,
            elements=[
                start_event, validate_data, check_eligibility, eligibility_gateway,
                register_exam, send_confirmation, send_rejection, end_event
            ],
            sequence_flows=[
                ("start_exam_registration", "validate_registration_data"),
                ("validate_registration_data", "check_exam_eligibility"),
                ("check_exam_eligibility", "eligibility_check"),
                ("eligibility_check", "register_for_exam", "${eligible == true}"),
                ("eligibility_check", "send_rejection_email", "${eligible == false}"),
                ("register_for_exam", "send_confirmation_email"),
                ("send_confirmation_email", "end_exam_registration"),
                ("send_rejection_email", "end_exam_registration")
            ]
        )
        
        return bpmn_xml
    
    def generate_grade_inquiry_workflow(self) -> str:
        """Generiert BPMN für Notenabfrage"""
        
        process_id = "grade-inquiry"
        process_name = "Grade Inquiry Process"
        
        start_event = BPMNEvent("start_grade_inquiry", "Grade Inquiry Started", "start")
        
        validate_student = BPMNTask(
            "validate_student_identity",
            "Validate Student Identity",
            "service",
            "validate-student-data"
        )
        
        query_grades = BPMNTask(
            "query_student_grades",
            "Query Student Grades",
            "service",
            "database-query"
        )
        
        grades_found_gateway = BPMNGateway(
            "grades_found_check",
            "Grades Found?",
            "exclusive",
            {"${grades_found == true}": "send_grades", "else": "send_no_grades"}
        )
        
        send_grades = BPMNTask(
            "send_grades_email",
            "Send Grades via Email",
            "service",
            "send-email"
        )
        
        send_no_grades = BPMNTask(
            "send_no_grades_notification",
            "Send No Grades Found Notification",
            "service",
            "send-email"
        )
        
        end_event = BPMNEvent("end_grade_inquiry", "Grade Inquiry Completed", "end")
        
        bpmn_xml = self._create_bpmn_xml(
            process_id=process_id,
            process_name=process_name,
            elements=[
                start_event, validate_student, query_grades, grades_found_gateway,
                send_grades, send_no_grades, end_event
            ],
            sequence_flows=[
                ("start_grade_inquiry", "validate_student_identity"),
                ("validate_student_identity", "query_student_grades"),
                ("query_student_grades", "grades_found_check"),
                ("grades_found_check", "send_grades_email", "${grades_found == true}"),
                ("grades_found_check", "send_no_grades_notification", "${grades_found == false}"),
                ("send_grades_email", "end_grade_inquiry"),
                ("send_no_grades_notification", "end_grade_inquiry")
            ]
        )
        
        return bpmn_xml
    
    def _create_bpmn_xml(self, 
                        process_id: str,
                        process_name: str,
                        elements: List[Any],
                        sequence_flows: List[tuple]) -> str:
        """Erstellt BPMN 2.0 XML aus Elementen und Flows"""
        
        # Root Element
        definitions = ET.Element("bpmn:definitions")
        definitions.set("xmlns:bpmn", self.namespace['bpmn'])
        definitions.set("xmlns:bpmndi", self.namespace['bpmndi'])
        definitions.set("xmlns:dc", self.namespace['dc'])
        definitions.set("xmlns:di", self.namespace['di'])
        definitions.set("xmlns:zeebe", self.namespace['zeebe'])
        definitions.set("id", f"Definitions_{process_id}")
        definitions.set("targetNamespace", "http://bpmn.io/schema/bpmn")
        definitions.set("exporter", "Zeebe Modeler")
        definitions.set("exporterVersion", "0.11.0")
        
        # Process Element
        process = ET.SubElement(definitions, "bpmn:process")
        process.set("id", process_id)
        process.set("name", process_name)
        process.set("isExecutable", "true")
        
        # Elemente hinzufügen
        for element in elements:
            if isinstance(element, BPMNEvent):
                self._add_event_to_process(process, element)
            elif isinstance(element, BPMNTask):
                self._add_task_to_process(process, element)
            elif isinstance(element, BPMNGateway):
                self._add_gateway_to_process(process, element)
        
        # Sequence Flows hinzufügen
        for i, flow in enumerate(sequence_flows):
            flow_id = f"Flow_{i+1:03d}"
            self._add_sequence_flow(process, flow_id, flow)
        
        # XML formatieren
        rough_string = ET.tostring(definitions, 'unicode')
        reparsed = minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ")
        
        # Entferne leere Zeilen
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def _add_event_to_process(self, process: ET.Element, event: BPMNEvent):
        """Fügt ein Event zum Prozess hinzu"""
        if event.event_type == "start":
            event_element = ET.SubElement(process, "bpmn:startEvent")
        elif event.event_type == "end":
            event_element = ET.SubElement(process, "bpmn:endEvent")
        else:
            event_element = ET.SubElement(process, "bpmn:intermediateThrowEvent")
        
        event_element.set("id", event.event_id)
        event_element.set("name", event.name)
        
        if event.event_definition:
            if event.event_definition == "message":
                msg_def = ET.SubElement(event_element, "bpmn:messageEventDefinition")
                msg_def.set("id", f"{event.event_id}_MessageEventDefinition")
    
    def _add_task_to_process(self, process: ET.Element, task: BPMNTask):
        """Fügt eine Task zum Prozess hinzu"""
        if task.task_type == "service":
            task_element = ET.SubElement(process, "bpmn:serviceTask")
        elif task.task_type == "user":
            task_element = ET.SubElement(process, "bpmn:userTask")
        elif task.task_type == "manual":
            task_element = ET.SubElement(process, "bpmn:manualTask")
        else:
            task_element = ET.SubElement(process, "bpmn:task")
        
        task_element.set("id", task.task_id)
        task_element.set("name", task.name)
        
        # Zeebe Annotations für Service Tasks
        if task.task_type == "service" and task.job_type:
            extension_elements = ET.SubElement(task_element, "bpmn:extensionElements")
            task_definition = ET.SubElement(extension_elements, "zeebe:taskDefinition")
            task_definition.set("type", task.job_type)
    
    def _add_gateway_to_process(self, process: ET.Element, gateway: BPMNGateway):
        """Fügt ein Gateway zum Prozess hinzu"""
        if gateway.gateway_type == "exclusive":
            gateway_element = ET.SubElement(process, "bpmn:exclusiveGateway")
        elif gateway.gateway_type == "parallel":
            gateway_element = ET.SubElement(process, "bpmn:parallelGateway")
        else:
            gateway_element = ET.SubElement(process, "bpmn:inclusiveGateway")
        
        gateway_element.set("id", gateway.gateway_id)
        gateway_element.set("name", gateway.name)
    
    def _add_sequence_flow(self, process: ET.Element, flow_id: str, flow_data: tuple):
        """Fügt einen Sequence Flow zum Prozess hinzu"""
        flow_element = ET.SubElement(process, "bpmn:sequenceFlow")
        flow_element.set("id", flow_id)
        flow_element.set("sourceRef", flow_data[0])
        flow_element.set("targetRef", flow_data[1])
        
        # Condition Expression für conditional flows
        if len(flow_data) > 2 and flow_data[2]:
            condition_expr = ET.SubElement(flow_element, "bpmn:conditionExpression")
            condition_expr.set("xsi:type", "bpmn:tFormalExpression")
            condition_expr.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
            condition_expr.text = flow_data[2]
    
    def save_workflow_to_file(self, bpmn_xml: str, filename: str, output_dir: str = "workflows"):
        """Speichert BPMN XML in Datei"""
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(bpmn_xml)
        
        return filepath
    
    def generate_all_university_workflows(self, output_dir: str = "workflows") -> Dict[str, str]:
        """Generiert alle Standard-Universitäts-Workflows"""
        workflows = {}
        
        # Student Transcript Request
        transcript_xml = self.generate_student_transcript_workflow()
        transcript_file = self.save_workflow_to_file(
            transcript_xml, 
            "student-transcript-request.bpmn", 
            output_dir
        )
        workflows["student-transcript-request"] = transcript_file
        
        # Exam Registration
        exam_xml = self.generate_exam_registration_workflow()
        exam_file = self.save_workflow_to_file(
            exam_xml, 
            "exam-registration.bpmn", 
            output_dir
        )
        workflows["exam-registration"] = exam_file
        
        # Grade Inquiry
        grade_xml = self.generate_grade_inquiry_workflow()
        grade_file = self.save_workflow_to_file(
            grade_xml, 
            "grade-inquiry.bpmn", 
            output_dir
        )
        workflows["grade-inquiry"] = grade_file
        
        return workflows
    
    def create_custom_workflow(self, 
                              process_id: str,
                              process_name: str,
                              tasks: List[Dict[str, Any]],
                              gateways: List[Dict[str, Any]] = None,
                              flows: List[tuple] = None) -> str:
        """Erstellt einen benutzerdefinierten Workflow"""
        
        elements = []
        
        # Start Event
        elements.append(BPMNEvent(f"start_{process_id}", f"{process_name} Started", "start"))
        
        # Tasks hinzufügen
        for task_data in tasks:
            task = BPMNTask(
                task_id=task_data['id'],
                name=task_data['name'],
                task_type=task_data.get('type', 'service'),
                job_type=task_data.get('job_type')
            )
            elements.append(task)
        
        # Gateways hinzufügen
        if gateways:
            for gateway_data in gateways:
                gateway = BPMNGateway(
                    gateway_id=gateway_data['id'],
                    name=gateway_data['name'],
                    gateway_type=gateway_data.get('type', 'exclusive'),
                    conditions=gateway_data.get('conditions')
                )
                elements.append(gateway)
        
        # End Event
        elements.append(BPMNEvent(f"end_{process_id}", f"{process_name} Completed", "end"))
        
        # Standard Flows erstellen falls nicht angegeben
        if not flows:
            flows = []
            for i in range(len(tasks)):
                if i == 0:
                    flows.append((f"start_{process_id}", tasks[i]['id']))
                else:
                    flows.append((tasks[i-1]['id'], tasks[i]['id']))
            flows.append((tasks[-1]['id'], f"end_{process_id}"))
        
        return self._create_bpmn_xml(process_id, process_name, elements, flows)