"""
BPMN Element Models
Definiert alle BPMN 2.0 Elemente als Python-Klassen
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid


class ElementType(Enum):
    """BPMN Element Typen"""
    START_EVENT = "startEvent"
    END_EVENT = "endEvent"
    INTERMEDIATE_EVENT = "intermediateEvent"
    USER_TASK = "userTask"
    SERVICE_TASK = "serviceTask"
    EXCLUSIVE_GATEWAY = "exclusiveGateway"
    PARALLEL_GATEWAY = "parallelGateway"
    SEQUENCE_FLOW = "sequenceFlow"
    SUBPROCESS = "subProcess"


class TaskStatus(Enum):
    """Task Status Enumeration"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ProcessVariable:
    """Process Variable mit Typ und Wert"""
    name: str
    value: Any
    type: str = "string"
    scope: str = "process"  # process, task, local


class BPMNElement(ABC):
    """Basis-Klasse für alle BPMN-Elemente"""
    
    def __init__(self, element_id: str, name: str = ""):
        self.id = element_id
        self.name = name or element_id
        self.incoming: List['SequenceFlow'] = []
        self.outgoing: List['SequenceFlow'] = []
        self.properties: Dict[str, Any] = {}
        
    @abstractmethod
    def get_element_type(self) -> ElementType:
        """Gibt den BPMN Element-Typ zurück"""
        pass
    
    def add_incoming(self, flow: 'SequenceFlow'):
        """Füge eingehenden SequenceFlow hinzu"""
        if flow not in self.incoming:
            self.incoming.append(flow)
    
    def add_outgoing(self, flow: 'SequenceFlow'):
        """Füge ausgehenden SequenceFlow hinzu"""
        if flow not in self.outgoing:
            self.outgoing.append(flow)
    
    def get_outgoing_elements(self) -> List['BPMNElement']:
        """Gibt alle direkt erreichbaren Elemente zurück"""
        return [flow.target for flow in self.outgoing]
    
    def set_property(self, key: str, value: Any):
        """Setze Element-Property"""
        self.properties[key] = value
    
    def get_property(self, key: str, default: Any = None) -> Any:
        """Hole Element-Property"""
        return self.properties.get(key, default)
    
    def __repr__(self):
        return f"{self.__class__.__name__}(id='{self.id}', name='{self.name}')"


class Event(BPMNElement):
    """Basis-Klasse für Events"""
    
    def __init__(self, element_id: str, name: str = "", event_type: str = "none"):
        super().__init__(element_id, name)
        self.event_type = event_type  # none, timer, message, error, etc.


class StartEvent(Event):
    """BPMN Start Event"""
    
    def get_element_type(self) -> ElementType:
        return ElementType.START_EVENT


class EndEvent(Event):
    """BPMN End Event"""
    
    def get_element_type(self) -> ElementType:
        return ElementType.END_EVENT


class IntermediateEvent(Event):
    """BPMN Intermediate Event"""
    
    def __init__(self, element_id: str, name: str = "", event_type: str = "none", catching: bool = True):
        super().__init__(element_id, name, event_type)
        self.catching = catching  # True for catching, False for throwing
    
    def get_element_type(self) -> ElementType:
        return ElementType.INTERMEDIATE_EVENT


class Task(BPMNElement):
    """Basis-Klasse für Tasks"""
    
    def __init__(self, element_id: str, name: str = ""):
        super().__init__(element_id, name)
        self.assignee: Optional[str] = None
        self.candidate_groups: List[str] = []
        self.candidate_users: List[str] = []
        self.form_key: Optional[str] = None
        
    @abstractmethod
    def execute(self, execution_context: 'ExecutionContext') -> bool:
        """Führe Task aus - True wenn sofort abgeschlossen, False wenn async"""
        pass


class UserTask(Task):
    """BPMN User Task - erfordert menschliche Interaktion"""
    
    def __init__(self, element_id: str, name: str = ""):
        super().__init__(element_id, name)
        self.form_fields: List[Dict[str, Any]] = []
    
    def get_element_type(self) -> ElementType:
        return ElementType.USER_TASK
    
    def execute(self, execution_context: 'ExecutionContext') -> bool:
        """User Tasks sind nie sofort abgeschlossen"""
        return False
    
    def add_form_field(self, field_id: str, field_type: str, label: str, required: bool = False):
        """Füge Form-Field hinzu"""
        self.form_fields.append({
            'id': field_id,
            'type': field_type,
            'label': label,
            'required': required
        })


class ServiceTask(Task):
    """BPMN Service Task - automatische Ausführung"""
    
    def __init__(self, element_id: str, name: str = "", service_handler: Optional[Callable] = None):
        super().__init__(element_id, name)
        self.service_handler = service_handler
        self.class_name: Optional[str] = None
        self.expression: Optional[str] = None
    
    def get_element_type(self) -> ElementType:
        return ElementType.SERVICE_TASK
    
    def execute(self, execution_context: 'ExecutionContext') -> bool:
        """Service Tasks werden automatisch ausgeführt"""
        if self.service_handler:
            try:
                result = self.service_handler(execution_context)
                return True
            except Exception as e:
                execution_context.add_error(f"Service Task Error: {e}")
                return False
        return True


class Gateway(BPMNElement):
    """Basis-Klasse für Gateways"""
    
    def __init__(self, element_id: str, name: str = ""):
        super().__init__(element_id, name)
        
    @abstractmethod
    def evaluate(self, execution_context: 'ExecutionContext') -> List['BPMNElement']:
        """Evaluiere Gateway und gib nächste Elemente zurück"""
        pass


class ExclusiveGateway(Gateway):
    """BPMN Exclusive Gateway (XOR) - nur ein Pfad wird genommen"""
    
    def get_element_type(self) -> ElementType:
        return ElementType.EXCLUSIVE_GATEWAY
    
    def evaluate(self, execution_context: 'ExecutionContext') -> List['BPMNElement']:
        """Evaluiere Bedingungen und wähle einen Pfad"""
        variables = execution_context.get_variables()
        
        # Evaluiere alle ausgehenden Flows
        for flow in self.outgoing:
            if flow.condition_expression:
                if self._evaluate_condition(flow.condition_expression, variables):
                    return [flow.target]
            elif flow.is_default:
                # Default Flow als Fallback
                continue
        
        # Wenn keine Bedingung erfüllt, nehme Default Flow
        default_flows = [flow for flow in self.outgoing if flow.is_default]
        if default_flows:
            return [default_flows[0].target]
        
        # Fallback: erster Flow
        if self.outgoing:
            return [self.outgoing[0].target]
        
        return []
    
    def _evaluate_condition(self, expression: str, variables: Dict[str, Any]) -> bool:
        """Evaluiere Bedingungsausdruck"""
        try:
            # Sichere Evaluierung von einfachen Ausdrücken
            # Für Masterarbeit: simplified evaluation
            local_vars = dict(variables)
            return eval(expression, {"__builtins__": {}}, local_vars)
        except:
            return False


class ParallelGateway(Gateway):
    """BPMN Parallel Gateway (AND) - alle Pfade werden genommen"""
    
    def get_element_type(self) -> ElementType:
        return ElementType.PARALLEL_GATEWAY
    
    def evaluate(self, execution_context: 'ExecutionContext') -> List['BPMNElement']:
        """Alle ausgehenden Pfade werden parallel ausgeführt"""
        return [flow.target for flow in self.outgoing]


class SequenceFlow(BPMNElement):
    """BPMN Sequence Flow - Verbindung zwischen Elementen"""
    
    def __init__(self, element_id: str, source: BPMNElement, target: BPMNElement, name: str = ""):
        super().__init__(element_id, name)
        self.source = source
        self.target = target
        self.condition_expression: Optional[str] = None
        self.is_default: bool = False
        
        # Verkettung aufbauen
        source.add_outgoing(self)
        target.add_incoming(self)
    
    def get_element_type(self) -> ElementType:
        return ElementType.SEQUENCE_FLOW
    
    def set_condition(self, expression: str):
        """Setze Bedingungsausdruck für diesen Flow"""
        self.condition_expression = expression
    
    def set_default(self, is_default: bool = True):
        """Markiere als Default Flow"""
        self.is_default = is_default


@dataclass
class ProcessDefinition:
    """BPMN Process Definition"""
    
    id: str
    name: str
    elements: Dict[str, BPMNElement] = field(default_factory=dict)
    start_events: List[StartEvent] = field(default_factory=list)
    end_events: List[EndEvent] = field(default_factory=list)
    variables: Dict[str, ProcessVariable] = field(default_factory=dict)
    version: int = 1
    deployable: bool = True
    
    def add_element(self, element: BPMNElement):
        """Füge BPMN Element hinzu"""
        self.elements[element.id] = element
        
        if isinstance(element, StartEvent):
            self.start_events.append(element)
        elif isinstance(element, EndEvent):
            self.end_events.append(element)
    
    def get_element(self, element_id: str) -> Optional[BPMNElement]:
        """Hole Element by ID"""
        return self.elements.get(element_id)
    
    def add_variable(self, name: str, value: Any, var_type: str = "string"):
        """Füge Process Variable hinzu"""
        self.variables[name] = ProcessVariable(name, value, var_type)
    
    def validate(self) -> List[str]:
        """Validiere Process Definition"""
        errors = []
        
        if not self.start_events:
            errors.append("Process muss mindestens ein Start Event haben")
        
        if not self.end_events:
            errors.append("Process sollte mindestens ein End Event haben")
        
        # Prüfe ob alle BPMN-Elemente (außer SequenceFlows) erreichbar sind
        reachable = set()
        to_visit = list(self.start_events)
        
        while to_visit:
            current = to_visit.pop()
            if current.id in reachable:
                continue
            reachable.add(current.id)
            to_visit.extend(current.get_outgoing_elements())
        
        # Nur BPMN-Elemente prüfen, nicht SequenceFlows
        bpmn_elements = {eid: elem for eid, elem in self.elements.items() 
                        if not isinstance(elem, SequenceFlow)}
        unreachable = set(bpmn_elements.keys()) - reachable
        if unreachable:
            errors.append(f"Unreachable elements: {unreachable}")
        
        return errors
    
    def __repr__(self):
        return f"ProcessDefinition(id='{self.id}', elements={len(self.elements)})"


@dataclass  
class ExecutionContext:
    """Execution Context für Process Instance"""
    
    process_instance_id: str
    process_definition: ProcessDefinition
    variables: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_variable(self, name: str, default: Any = None) -> Any:
        """Hole Process Variable"""
        return self.variables.get(name, default)
    
    def set_variable(self, name: str, value: Any):
        """Setze Process Variable"""
        self.variables[name] = value
    
    def get_variables(self) -> Dict[str, Any]:
        """Hole alle Variables"""
        return self.variables.copy()
    
    def add_error(self, error: str):
        """Füge Error hinzu"""
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """Prüfe ob Errors vorhanden"""
        return len(self.errors) > 0