"""
Echte BPMN Process Engine
Wissenschaftliche Implementation für Masterarbeit
"""

from .elements import (
    ProcessDefinition, BPMNElement, StartEvent, EndEvent, IntermediateEvent,
    UserTask, ServiceTask, ExclusiveGateway, ParallelGateway, SequenceFlow,
    ElementType
)

from .engine import ProcessExecutionEngine, ProcessInstance, TaskInstance, Token
from .parser import BPMNParser
from .integration import BPMNEngineManager

__all__ = [
    # Elements
    'ProcessDefinition', 'BPMNElement', 'StartEvent', 'EndEvent', 'IntermediateEvent',
    'UserTask', 'ServiceTask', 'ExclusiveGateway', 'ParallelGateway', 'SequenceFlow',
    'ElementType',
    
    # Engine
    'ProcessExecutionEngine', 'ProcessInstance', 'TaskInstance', 'Token',
    
    # Parser & Manager
    'BPMNParser', 'BPMNEngineManager'
]