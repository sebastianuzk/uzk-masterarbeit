"""
BPMN XML Parser
Parst BPMN 2.0 XML Dateien und erstellt ProcessDefinition Objekte
"""
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

from .elements import (
    ProcessDefinition, BPMNElement, StartEvent, EndEvent, IntermediateEvent,
    UserTask, ServiceTask, ExclusiveGateway, ParallelGateway, SequenceFlow,
    ElementType
)

logger = logging.getLogger(__name__)


class BPMNParser:
    """BPMN 2.0 XML Parser"""
    
    # BPMN 2.0 Namespaces
    BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    BPMNDI_NS = "http://www.omg.org/spec/BPMN/20100524/DI"
    DC_NS = "http://www.omg.org/spec/DD/20100524/DC"
    DI_NS = "http://www.omg.org/spec/DD/20100524/DI"
    
    def __init__(self):
        self.namespaces = {
            'bpmn': self.BPMN_NS,
            'bpmndi': self.BPMNDI_NS,
            'dc': self.DC_NS,
            'di': self.DI_NS
        }
        self.elements: Dict[str, BPMNElement] = {}
        self.flows: List[Dict[str, str]] = []
    
    def parse_file(self, bpmn_file_path: str) -> ProcessDefinition:
        """Parse BPMN XML Datei"""
        try:
            tree = ET.parse(bpmn_file_path)
            return self._parse_tree(tree)
        except ET.ParseError as e:
            raise ValueError(f"Invalid BPMN XML: {e}")
        except FileNotFoundError:
            raise ValueError(f"BPMN file not found: {bpmn_file_path}")
    
    def parse_string(self, bpmn_xml: str) -> ProcessDefinition:
        """Parse BPMN XML String"""
        try:
            root = ET.fromstring(bpmn_xml)
            tree = ET.ElementTree(root)
            return self._parse_tree(tree)
        except ET.ParseError as e:
            raise ValueError(f"Invalid BPMN XML: {e}")
    
    def _parse_tree(self, tree: ET.ElementTree) -> ProcessDefinition:
        """Parse ElementTree zu ProcessDefinition"""
        root = tree.getroot()
        
        # Reset parser state
        self.elements = {}
        self.flows = []
        
        # Finde Process Element
        processes = root.findall('.//bpmn:process', self.namespaces)
        if not processes:
            raise ValueError("No process element found in BPMN")
        
        # Nehme ersten Process (für Masterarbeit vereinfacht)
        process_element = processes[0]
        process_id = process_element.get('id', 'default_process')
        process_name = process_element.get('name', process_id)
        
        process_def = ProcessDefinition(id=process_id, name=process_name)
        
        # Parse alle Elemente
        self._parse_start_events(process_element, process_def)
        self._parse_end_events(process_element, process_def)
        self._parse_intermediate_events(process_element, process_def)
        self._parse_user_tasks(process_element, process_def)
        self._parse_service_tasks(process_element, process_def)
        self._parse_exclusive_gateways(process_element, process_def)
        self._parse_parallel_gateways(process_element, process_def)
        self._parse_sequence_flows(process_element, process_def)
        
        # Erstelle SequenceFlow Verbindungen
        self._create_flow_connections(process_def)
        
        # Validiere Process
        errors = process_def.validate()
        if errors:
            logger.warning(f"Process validation warnings: {errors}")
        
        logger.info(f"Parsed BPMN process '{process_name}' with {len(process_def.elements)} elements")
        return process_def
    
    def _parse_start_events(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse Start Events"""
        start_events = process_element.findall('.//bpmn:startEvent', self.namespaces)
        for event_elem in start_events:
            event_id = event_elem.get('id')
            event_name = event_elem.get('name', '')
            
            start_event = StartEvent(event_id, event_name)
            self.elements[event_id] = start_event
            process_def.add_element(start_event)
    
    def _parse_end_events(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse End Events"""
        end_events = process_element.findall('.//bpmn:endEvent', self.namespaces)
        for event_elem in end_events:
            event_id = event_elem.get('id')
            event_name = event_elem.get('name', '')
            
            end_event = EndEvent(event_id, event_name)
            self.elements[event_id] = end_event
            process_def.add_element(end_event)
    
    def _parse_intermediate_events(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse Intermediate Events"""
        # Catching Events
        catching_events = process_element.findall('.//bpmn:intermediateCatchEvent', self.namespaces)
        for event_elem in catching_events:
            event_id = event_elem.get('id')
            event_name = event_elem.get('name', '')
            
            intermediate_event = IntermediateEvent(event_id, event_name, catching=True)
            
            # Check for timer events
            timer_defs = event_elem.findall('.//bpmn:timerEventDefinition', self.namespaces)
            if timer_defs:
                intermediate_event.event_type = "timer"
                # Parse timer expression if present
                time_duration = event_elem.find('.//bpmn:timeDuration', self.namespaces)
                if time_duration is not None:
                    intermediate_event.set_property('duration', time_duration.text)
            
            self.elements[event_id] = intermediate_event
            process_def.add_element(intermediate_event)
        
        # Throwing Events
        throwing_events = process_element.findall('.//bpmn:intermediateThrowEvent', self.namespaces)
        for event_elem in throwing_events:
            event_id = event_elem.get('id')
            event_name = event_elem.get('name', '')
            
            intermediate_event = IntermediateEvent(event_id, event_name, catching=False)
            self.elements[event_id] = intermediate_event
            process_def.add_element(intermediate_event)
    
    def _parse_user_tasks(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse User Tasks"""
        user_tasks = process_element.findall('.//bpmn:userTask', self.namespaces)
        for task_elem in user_tasks:
            task_id = task_elem.get('id')
            task_name = task_elem.get('name', '')
            
            user_task = UserTask(task_id, task_name)
            
            # Parse Assignee
            assignee = task_elem.get('assignee')
            if assignee:
                user_task.assignee = assignee
            
            # Parse Candidate Groups
            candidate_groups = task_elem.get('candidateGroups')
            if candidate_groups:
                user_task.candidate_groups = [g.strip() for g in candidate_groups.split(',')]
            
            # Parse Form Key
            form_key = task_elem.get('formKey')
            if form_key:
                user_task.form_key = form_key
            
            # Parse Form Fields (vereinfacht)
            documentation = task_elem.find('.//bpmn:documentation', self.namespaces)
            if documentation is not None and documentation.text:
                # Einfache Form Field Parsing aus Documentation
                self._parse_form_fields_from_documentation(user_task, documentation.text)
            
            self.elements[task_id] = user_task
            process_def.add_element(user_task)
    
    def _parse_service_tasks(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse Service Tasks"""
        service_tasks = process_element.findall('.//bpmn:serviceTask', self.namespaces)
        for task_elem in service_tasks:
            task_id = task_elem.get('id')
            task_name = task_elem.get('name', '')
            
            service_task = ServiceTask(task_id, task_name)
            
            # Parse Class Name (Java Delegate)
            class_name = task_elem.get('class')
            if class_name:
                service_task.class_name = class_name
            
            # Parse Expression
            expression = task_elem.get('expression')
            if expression:
                service_task.expression = expression
            
            self.elements[task_id] = service_task
            process_def.add_element(service_task)
    
    def _parse_exclusive_gateways(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse Exclusive Gateways"""
        exclusive_gateways = process_element.findall('.//bpmn:exclusiveGateway', self.namespaces)
        for gateway_elem in exclusive_gateways:
            gateway_id = gateway_elem.get('id')
            gateway_name = gateway_elem.get('name', '')
            
            exclusive_gateway = ExclusiveGateway(gateway_id, gateway_name)
            self.elements[gateway_id] = exclusive_gateway
            process_def.add_element(exclusive_gateway)
    
    def _parse_parallel_gateways(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse Parallel Gateways"""
        parallel_gateways = process_element.findall('.//bpmn:parallelGateway', self.namespaces)
        for gateway_elem in parallel_gateways:
            gateway_id = gateway_elem.get('id')
            gateway_name = gateway_elem.get('name', '')
            
            parallel_gateway = ParallelGateway(gateway_id, gateway_name)
            self.elements[gateway_id] = parallel_gateway
            process_def.add_element(parallel_gateway)
    
    def _parse_sequence_flows(self, process_element: ET.Element, process_def: ProcessDefinition):
        """Parse Sequence Flows"""
        sequence_flows = process_element.findall('.//bpmn:sequenceFlow', self.namespaces)
        for flow_elem in sequence_flows:
            flow_id = flow_elem.get('id')
            flow_name = flow_elem.get('name', '')
            source_ref = flow_elem.get('sourceRef')
            target_ref = flow_elem.get('targetRef')
            
            # Speichere Flow-Info für spätere Verbindung
            flow_info = {
                'id': flow_id,
                'name': flow_name,
                'source_ref': source_ref,
                'target_ref': target_ref,
                'condition': None,
                'is_default': False
            }
            
            # Parse Condition Expression
            condition_expr = flow_elem.find('.//bpmn:conditionExpression', self.namespaces)
            if condition_expr is not None and condition_expr.text:
                flow_info['condition'] = condition_expr.text.strip()
            
            self.flows.append(flow_info)
    
    def _create_flow_connections(self, process_def: ProcessDefinition):
        """Erstelle SequenceFlow Verbindungen zwischen Elementen"""
        for flow_info in self.flows:
            source_element = self.elements.get(flow_info['source_ref'])
            target_element = self.elements.get(flow_info['target_ref'])
            
            if source_element and target_element:
                sequence_flow = SequenceFlow(
                    flow_info['id'],
                    source_element,
                    target_element,
                    flow_info['name']
                )
                
                if flow_info['condition']:
                    sequence_flow.set_condition(flow_info['condition'])
                
                process_def.add_element(sequence_flow)
            else:
                logger.warning(f"Could not connect flow {flow_info['id']}: "
                             f"source={flow_info['source_ref']}, target={flow_info['target_ref']}")
    
    def _parse_form_fields_from_documentation(self, user_task: UserTask, documentation: str):
        """Parse Form Fields aus Documentation (vereinfacht für Masterarbeit)"""
        lines = documentation.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('FORM:'):
                # Format: FORM:field_id:type:label:required
                parts = line.split(':')
                if len(parts) >= 4:
                    field_id = parts[1]
                    field_type = parts[2]
                    label = parts[3]
                    required = len(parts) > 4 and parts[4].lower() == 'true'
                    
                    user_task.add_form_field(field_id, field_type, label, required)


def create_sample_bpmn() -> str:
    """Erstelle Beispiel BPMN für Tests"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI"
                  xmlns:dc="http://www.omg.org/spec/DD/20100524/DC"
                  xmlns:di="http://www.omg.org/spec/DD/20100524/DI"
                  id="sample_process_definitions">
  
  <bpmn:process id="bewerbung_process" name="Universitäts-Bewerbungsprozess" isExecutable="true">
    
    <!-- Start Event -->
    <bpmn:startEvent id="start_bewerbung" name="Bewerbung eingegangen">
      <bpmn:outgoing>flow_start_to_pruefen</bpmn:outgoing>
    </bpmn:startEvent>
    
    <!-- User Task: Angaben prüfen -->
    <bpmn:userTask id="angaben_pruefen" name="Angaben prüfen" assignee="sachbearbeiter">
      <bpmn:documentation>
        FORM:student_email:email:E-Mail Adresse:true
        FORM:bemerkung:text:Bemerkungen:false
      </bpmn:documentation>
      <bpmn:incoming>flow_start_to_pruefen</bpmn:incoming>
      <bpmn:outgoing>flow_pruefen_to_gateway</bpmn:outgoing>
    </bpmn:userTask>
    
    <!-- Exclusive Gateway: Entscheidung -->
    <bpmn:exclusiveGateway id="entscheidung_gateway" name="Bewerbung gültig?">
      <bpmn:incoming>flow_pruefen_to_gateway</bpmn:incoming>
      <bpmn:outgoing>flow_gateway_to_akzeptiert</bpmn:outgoing>
      <bpmn:outgoing>flow_gateway_to_abgelehnt</bpmn:outgoing>
    </bpmn:exclusiveGateway>
    
    <!-- Service Task: Akzeptierung verarbeiten -->
    <bpmn:serviceTask id="bewerbung_akzeptiert" name="Bewerbung akzeptieren" class="AcceptApplicationService">
      <bpmn:incoming>flow_gateway_to_akzeptiert</bpmn:incoming>
      <bpmn:outgoing>flow_akzeptiert_to_end</bpmn:outgoing>
    </bpmn:serviceTask>
    
    <!-- User Task: Ablehnung begründen -->
    <bpmn:userTask id="bewerbung_ablehnen" name="Ablehnung begründen" assignee="sachbearbeiter">
      <bpmn:documentation>
        FORM:ablehnungsgrund:textarea:Grund der Ablehnung:true
      </bpmn:documentation>
      <bpmn:incoming>flow_gateway_to_abgelehnt</bpmn:incoming>
      <bpmn:outgoing>flow_abgelehnt_to_end</bpmn:outgoing>
    </bpmn:userTask>
    
    <!-- End Events -->
    <bpmn:endEvent id="end_akzeptiert" name="Bewerbung akzeptiert">
      <bpmn:incoming>flow_akzeptiert_to_end</bpmn:incoming>
    </bpmn:endEvent>
    
    <bpmn:endEvent id="end_abgelehnt" name="Bewerbung abgelehnt">
      <bpmn:incoming>flow_abgelehnt_to_end</bpmn:incoming>
    </bpmn:endEvent>
    
    <!-- Sequence Flows -->
    <bpmn:sequenceFlow id="flow_start_to_pruefen" sourceRef="start_bewerbung" targetRef="angaben_pruefen"/>
    <bpmn:sequenceFlow id="flow_pruefen_to_gateway" sourceRef="angaben_pruefen" targetRef="entscheidung_gateway"/>
    
    <bpmn:sequenceFlow id="flow_gateway_to_akzeptiert" sourceRef="entscheidung_gateway" targetRef="bewerbung_akzeptiert">
      <bpmn:conditionExpression>bewerbung_gueltig == True</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    
    <bpmn:sequenceFlow id="flow_gateway_to_abgelehnt" sourceRef="entscheidung_gateway" targetRef="bewerbung_ablehnen">
      <bpmn:conditionExpression>bewerbung_gueltig == False</bpmn:conditionExpression>
    </bpmn:sequenceFlow>
    
    <bpmn:sequenceFlow id="flow_akzeptiert_to_end" sourceRef="bewerbung_akzeptiert" targetRef="end_akzeptiert"/>
    <bpmn:sequenceFlow id="flow_abgelehnt_to_end" sourceRef="bewerbung_ablehnen" targetRef="end_abgelehnt"/>
    
  </bpmn:process>
  
</bpmn:definitions>'''