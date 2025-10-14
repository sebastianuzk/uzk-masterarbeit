"""
BPMN Execution Engine
Token-basierte Ausführung von BPMN Prozessen
"""
import logging
import threading
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import asyncio
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import json

from .elements import (
    ProcessDefinition, BPMNElement, StartEvent, EndEvent, IntermediateEvent,
    UserTask, ServiceTask, ExclusiveGateway, ParallelGateway, SequenceFlow,
    ExecutionContext, TaskStatus
)

logger = logging.getLogger(__name__)


class InstanceStatus(Enum):
    """Process Instance Status"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"


@dataclass
class Token:
    """Execution Token - repräsentiert Position im Prozess"""
    
    id: str
    process_instance_id: str
    current_element: BPMNElement
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    active: bool = True
    
    def move_to(self, target_element: BPMNElement) -> 'Token':
        """Erstelle neuen Token für Ziel-Element"""
        return Token(
            id=str(uuid.uuid4()),
            process_instance_id=self.process_instance_id,
            current_element=target_element,
            variables=self.variables.copy(),
            created_at=datetime.now(),
            active=True
        )
    
    def clone(self) -> 'Token':
        """Clone Token für parallele Pfade"""
        return Token(
            id=str(uuid.uuid4()),
            process_instance_id=self.process_instance_id,
            current_element=self.current_element,
            variables=self.variables.copy(),
            created_at=datetime.now(),
            active=True
        )


@dataclass
class ProcessInstance:
    """Process Instance - laufende Prozess-Instanz"""
    
    id: str
    process_definition: ProcessDefinition
    status: InstanceStatus = InstanceStatus.ACTIVE
    variables: Dict[str, Any] = field(default_factory=dict)
    tokens: List[Token] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    business_key: Optional[str] = None
    
    def is_active(self) -> bool:
        """Prüfe ob Instance aktiv ist"""
        return self.status == InstanceStatus.ACTIVE and len(self.get_active_tokens()) > 0
    
    def get_active_tokens(self) -> List[Token]:
        """Hole alle aktiven Tokens"""
        return [token for token in self.tokens if token.active]
    
    def add_token(self, token: Token):
        """Füge Token hinzu"""
        self.tokens.append(token)
    
    def remove_token(self, token: Token):
        """Entferne Token"""
        token.active = False
    
    def complete(self):
        """Schließe Process Instance ab"""
        self.status = InstanceStatus.COMPLETED
        self.end_time = datetime.now()
        for token in self.tokens:
            token.active = False
    
    def fail(self, reason: str):
        """Markiere Process Instance als fehlgeschlagen"""
        self.status = InstanceStatus.FAILED
        self.end_time = datetime.now()
        self.variables['failure_reason'] = reason
        for token in self.tokens:
            token.active = False


@dataclass
class TaskInstance:
    """Task Instance - aktiver User/Service Task"""
    
    id: str
    process_instance_id: str
    task_definition: BPMNElement
    token: Token
    status: TaskStatus = TaskStatus.ACTIVE
    assignee: Optional[str] = None
    variables: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    form_data: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self, completion_variables: Dict[str, Any] = None):
        """Schließe Task ab"""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()
        if completion_variables:
            self.variables.update(completion_variables)
            self.token.variables.update(completion_variables)


class ProcessExecutionEngine:
    """BPMN Process Execution Engine"""
    
    def __init__(self, db_path: str = "bpmn_engine.db"):
        self.db_path = db_path
        self.process_definitions: Dict[str, ProcessDefinition] = {}
        self.active_instances: Dict[str, ProcessInstance] = {}
        self.active_tasks: Dict[str, TaskInstance] = {}
        self.service_handlers: Dict[str, Callable] = {}
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Event Callbacks
        self.instance_started_callbacks: List[Callable] = []
        self.instance_completed_callbacks: List[Callable] = []
        self.task_created_callbacks: List[Callable] = []
        self.task_completed_callbacks: List[Callable] = []
        
        self._setup_database()
        self._load_active_instances()
    
    def _setup_database(self):
        """Setup SQLite Database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Process Instances Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_instances (
                id TEXT PRIMARY KEY,
                process_definition_id TEXT NOT NULL,
                status TEXT NOT NULL,
                variables TEXT,
                business_key TEXT,
                start_time TIMESTAMP,
                end_time TIMESTAMP
            )
        ''')
        
        # Tokens Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id TEXT PRIMARY KEY,
                process_instance_id TEXT NOT NULL,
                current_element_id TEXT NOT NULL,
                variables TEXT,
                created_at TIMESTAMP,
                active BOOLEAN DEFAULT 1,
                FOREIGN KEY (process_instance_id) REFERENCES process_instances (id)
            )
        ''')
        
        # Task Instances Table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_instances (
                id TEXT PRIMARY KEY,
                process_instance_id TEXT NOT NULL,
                task_definition_id TEXT NOT NULL,
                token_id TEXT NOT NULL,
                status TEXT NOT NULL,
                assignee TEXT,
                variables TEXT,
                form_data TEXT,
                created_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (process_instance_id) REFERENCES process_instances (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_active_instances(self):
        """Lade aktive Instances aus Database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Lade aktive Process Instances
        cursor.execute('''
            SELECT id, process_definition_id, status, variables, business_key, start_time, end_time
            FROM process_instances WHERE status = 'ACTIVE'
        ''')
        
        for row in cursor.fetchall():
            instance_id = row[0]
            process_def_id = row[1]
            
            # Prüfe ob Process Definition verfügbar ist
            if process_def_id in self.process_definitions:
                process_def = self.process_definitions[process_def_id]
                
                instance = ProcessInstance(
                    id=instance_id,
                    process_definition=process_def,
                    status=InstanceStatus(row[2]),
                    variables=json.loads(row[3]) if row[3] else {},
                    business_key=row[4],
                    start_time=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                    end_time=datetime.fromisoformat(row[6]) if row[6] else None
                )
                
                # Lade Tokens
                cursor.execute('''
                    SELECT id, current_element_id, variables, created_at, active
                    FROM tokens WHERE process_instance_id = ? AND active = 1
                ''', (instance_id,))
                
                for token_row in cursor.fetchall():
                    element = process_def.get_element(token_row[1])
                    if element:
                        token = Token(
                            id=token_row[0],
                            process_instance_id=instance_id,
                            current_element=element,
                            variables=json.loads(token_row[2]) if token_row[2] else {},
                            created_at=datetime.fromisoformat(token_row[3]) if token_row[3] else datetime.now(),
                            active=bool(token_row[4])
                        )
                        instance.add_token(token)
                
                self.active_instances[instance_id] = instance
        
        # Lade aktive Tasks
        cursor.execute('''
            SELECT id, process_instance_id, task_definition_id, token_id, status, assignee, 
                   variables, form_data, created_at, completed_at
            FROM task_instances WHERE status = 'ACTIVE'
        ''')
        
        for row in cursor.fetchall():
            task_id = row[0]
            instance_id = row[1]
            task_def_id = row[2]
            
            if instance_id in self.active_instances:
                instance = self.active_instances[instance_id]
                task_def = instance.process_definition.get_element(task_def_id)
                
                # Finde Token
                token = None
                for t in instance.tokens:
                    if t.id == row[3]:
                        token = t
                        break
                
                if task_def and token:
                    task_instance = TaskInstance(
                        id=task_id,
                        process_instance_id=instance_id,
                        task_definition=task_def,
                        token=token,
                        status=TaskStatus(row[4]),
                        assignee=row[5],
                        variables=json.loads(row[6]) if row[6] else {},
                        form_data=json.loads(row[7]) if row[7] else {},
                        created_at=datetime.fromisoformat(row[8]) if row[8] else datetime.now(),
                        completed_at=datetime.fromisoformat(row[9]) if row[9] else None
                    )
                    
                    self.active_tasks[task_id] = task_instance
        
        conn.close()
        logger.info(f"Loaded {len(self.active_instances)} active instances and {len(self.active_tasks)} active tasks")
    
    def deploy_process(self, process_definition: ProcessDefinition):
        """Deploy Process Definition"""
        errors = process_definition.validate()
        if errors:
            raise ValueError(f"Process validation failed: {errors}")
        
        self.process_definitions[process_definition.id] = process_definition
        logger.info(f"Deployed process definition '{process_definition.id}'")
    
    def start_process(self, process_definition_id: str, variables: Dict[str, Any] = None, 
                     business_key: str = None) -> str:
        """Starte neue Process Instance"""
        if process_definition_id not in self.process_definitions:
            raise ValueError(f"Process definition '{process_definition_id}' not found")
        
        process_def = self.process_definitions[process_definition_id]
        instance_id = str(uuid.uuid4())
        
        instance = ProcessInstance(
            id=instance_id,
            process_definition=process_def,
            variables=variables or {},
            business_key=business_key
        )
        
        # Erstelle Start-Tokens für alle Start Events
        for start_event in process_def.start_events:
            token = Token(
                id=str(uuid.uuid4()),
                process_instance_id=instance_id,
                current_element=start_event,
                variables=instance.variables.copy()
            )
            instance.add_token(token)
        
        self.active_instances[instance_id] = instance
        self._persist_instance(instance)
        
        # Trigger Instance Started Callbacks
        for callback in self.instance_started_callbacks:
            try:
                callback(instance)
            except Exception as e:
                logger.error(f"Error in instance started callback: {e}")
        
        # Starte Execution
        self._execute_tokens(instance.get_active_tokens())
        
        logger.info(f"Started process instance '{instance_id}' for definition '{process_definition_id}'")
        return instance_id
    
    def _execute_tokens(self, tokens: List[Token]):
        """Führe Tokens aus"""
        for token in tokens:
            self._execute_token(token)
    
    def _execute_token(self, token: Token):
        """Führe einzelnen Token aus"""
        if not token.active:
            return
        
        element = token.current_element
        instance = self.active_instances.get(token.process_instance_id)
        
        if not instance:
            logger.error(f"Process instance {token.process_instance_id} not found")
            return
        
        execution_context = ExecutionContext(
            process_instance_id=instance.id,
            process_definition=instance.process_definition,
            variables=token.variables
        )
        
        logger.debug(f"Executing token {token.id} at element {element.id} ({element.__class__.__name__})")
        
        try:
            if isinstance(element, StartEvent):
                self._execute_start_event(token, element, execution_context)
            elif isinstance(element, EndEvent):
                self._execute_end_event(token, element, execution_context)
            elif isinstance(element, UserTask):
                self._execute_user_task(token, element, execution_context)
            elif isinstance(element, ServiceTask):
                self._execute_service_task(token, element, execution_context)
            elif isinstance(element, ExclusiveGateway):
                self._execute_exclusive_gateway(token, element, execution_context)
            elif isinstance(element, ParallelGateway):
                self._execute_parallel_gateway(token, element, execution_context)
            elif isinstance(element, IntermediateEvent):
                self._execute_intermediate_event(token, element, execution_context)
            else:
                logger.warning(f"Unknown element type: {type(element)}")
                self._continue_execution(token)
        
        except Exception as e:
            logger.error(f"Error executing token {token.id}: {e}")
            instance.fail(str(e))
            self._persist_instance(instance)
    
    def _execute_start_event(self, token: Token, element: StartEvent, context: ExecutionContext):
        """Führe Start Event aus"""
        # Start Events führen direkt zu den nächsten Elementen
        self._continue_execution(token)
    
    def _execute_end_event(self, token: Token, element: EndEvent, context: ExecutionContext):
        """Führe End Event aus"""
        instance = self.active_instances[token.process_instance_id]
        
        # Entferne Token
        instance.remove_token(token)
        
        # Prüfe ob alle Tokens beendet sind
        if not instance.get_active_tokens():
            instance.complete()
            self._persist_instance(instance)
            
            # Trigger Instance Completed Callbacks
            for callback in self.instance_completed_callbacks:
                try:
                    callback(instance)
                except Exception as e:
                    logger.error(f"Error in instance completed callback: {e}")
            
            logger.info(f"Process instance {instance.id} completed")
    
    def _execute_user_task(self, token: Token, element: UserTask, context: ExecutionContext):
        """Führe User Task aus"""
        task_id = str(uuid.uuid4())
        
        task_instance = TaskInstance(
            id=task_id,
            process_instance_id=token.process_instance_id,
            task_definition=element,
            token=token,
            assignee=element.assignee
        )
        
        self.active_tasks[task_id] = task_instance
        self._persist_task(task_instance)
        
        # Trigger Task Created Callbacks
        for callback in self.task_created_callbacks:
            try:
                callback(task_instance)
            except Exception as e:
                logger.error(f"Error in task created callback: {e}")
        
        logger.info(f"Created user task {task_id} ({element.name}) for instance {token.process_instance_id}")
    
    def _execute_service_task(self, token: Token, element: ServiceTask, context: ExecutionContext):
        """Führe Service Task aus"""
        try:
            # Versuche Service Handler zu finden
            handler = None
            if element.class_name and element.class_name in self.service_handlers:
                handler = self.service_handlers[element.class_name]
            elif element.expression:
                # Vereinfachte Expression Evaluation
                handler = self._evaluate_expression(element.expression)
            
            if handler:
                result = handler(context)
                if isinstance(result, dict):
                    token.variables.update(result)
            
            # Service Tasks werden automatisch abgeschlossen
            self._continue_execution(token)
            
        except Exception as e:
            logger.error(f"Service task {element.id} failed: {e}")
            instance = self.active_instances[token.process_instance_id]
            instance.fail(f"Service task failed: {e}")
            self._persist_instance(instance)
    
    def _execute_exclusive_gateway(self, token: Token, element: ExclusiveGateway, context: ExecutionContext):
        """Führe Exclusive Gateway aus"""
        next_elements = element.evaluate(context)
        
        if next_elements:
            # Bewege Token zum gewählten Element
            next_element = next_elements[0]
            token.current_element = next_element
            self._execute_token(token)
        else:
            logger.warning(f"No outgoing flow activated for exclusive gateway {element.id}")
            instance = self.active_instances[token.process_instance_id]
            instance.fail(f"No outgoing flow for gateway {element.id}")
            self._persist_instance(instance)
    
    def _execute_parallel_gateway(self, token: Token, element: ParallelGateway, context: ExecutionContext):
        """Führe Parallel Gateway aus"""
        next_elements = element.evaluate(context)
        instance = self.active_instances[token.process_instance_id]
        
        # Entferne ursprünglichen Token
        instance.remove_token(token)
        
        # Erstelle neue Tokens für alle parallelen Pfade
        for next_element in next_elements:
            new_token = token.clone()
            new_token.current_element = next_element
            instance.add_token(new_token)
            self._execute_token(new_token)
    
    def _execute_intermediate_event(self, token: Token, element: IntermediateEvent, context: ExecutionContext):
        """Führe Intermediate Event aus"""
        if element.event_type == "timer":
            # Timer Event - vereinfacht
            duration_str = element.get_property('duration')
            if duration_str:
                # Für Masterarbeit: vereinfachte Timer-Behandlung
                logger.info(f"Timer event {element.id} with duration {duration_str}")
            
            # Timer Events führen direkt weiter (vereinfacht)
            self._continue_execution(token)
        else:
            # Andere Event-Typen führen direkt weiter
            self._continue_execution(token)
    
    def _continue_execution(self, token: Token):
        """Setze Execution mit nächsten Elementen fort"""
        outgoing_elements = token.current_element.get_outgoing_elements()
        instance = self.active_instances[token.process_instance_id]
        
        if len(outgoing_elements) == 0:
            # Keine ausgehenden Elemente - Token beenden
            instance.remove_token(token)
        elif len(outgoing_elements) == 1:
            # Ein ausgehendes Element - Token bewegen
            token.current_element = outgoing_elements[0]
            self._execute_token(token)
        else:
            # Mehrere ausgehende Elemente - parallele Tokens erstellen
            instance.remove_token(token)
            for element in outgoing_elements:
                new_token = token.clone()
                new_token.current_element = element
                instance.add_token(new_token)
                self._execute_token(new_token)
        
        self._persist_instance(instance)
    
    def complete_task(self, task_id: str, completion_variables: Dict[str, Any] = None) -> bool:
        """Schließe User Task ab"""
        if task_id not in self.active_tasks:
            return False
        
        task_instance = self.active_tasks[task_id]
        task_instance.complete(completion_variables or {})
        
        # Entferne von aktiven Tasks
        del self.active_tasks[task_id]
        self._persist_task(task_instance)
        
        # Trigger Task Completed Callbacks
        for callback in self.task_completed_callbacks:
            try:
                callback(task_instance)
            except Exception as e:
                logger.error(f"Error in task completed callback: {e}")
        
        # Setze Token-Execution fort
        self._continue_execution(task_instance.token)
        
        logger.info(f"Completed task {task_id}")
        return True
    
    def register_service_handler(self, class_name: str, handler: Callable):
        """Registriere Service Task Handler"""
        self.service_handlers[class_name] = handler
        logger.info(f"Registered service handler for '{class_name}'")
    
    def _evaluate_expression(self, expression: str) -> Optional[Callable]:
        """Evaluiere Expression zu Callable (vereinfacht)"""
        # Für Masterarbeit: sehr vereinfacht
        return None
    
    def _persist_instance(self, instance: ProcessInstance):
        """Persistiere Process Instance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Update/Insert Process Instance
        cursor.execute('''
            INSERT OR REPLACE INTO process_instances 
            (id, process_definition_id, status, variables, business_key, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            instance.id,
            instance.process_definition.id,
            instance.status.value,
            json.dumps(instance.variables),
            instance.business_key,
            instance.start_time.isoformat(),
            instance.end_time.isoformat() if instance.end_time else None
        ))
        
        # Persist Tokens
        for token in instance.tokens:
            cursor.execute('''
                INSERT OR REPLACE INTO tokens
                (id, process_instance_id, current_element_id, variables, created_at, active)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                token.id,
                token.process_instance_id,
                token.current_element.id,
                json.dumps(token.variables),
                token.created_at.isoformat(),
                token.active
            ))
        
        conn.commit()
        conn.close()
    
    def _persist_task(self, task_instance: TaskInstance):
        """Persistiere Task Instance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO task_instances
            (id, process_instance_id, task_definition_id, token_id, status, assignee, 
             variables, form_data, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_instance.id,
            task_instance.process_instance_id,
            task_instance.task_definition.id,
            task_instance.token.id,
            task_instance.status.value,
            task_instance.assignee,
            json.dumps(task_instance.variables),
            json.dumps(task_instance.form_data),
            task_instance.created_at.isoformat(),
            task_instance.completed_at.isoformat() if task_instance.completed_at else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_process_instance(self, instance_id: str) -> Optional[ProcessInstance]:
        """Hole Process Instance"""
        return self.active_instances.get(instance_id)
    
    def get_active_instances(self) -> List[ProcessInstance]:
        """Hole alle aktiven Instances"""
        return list(self.active_instances.values())
    
    def get_active_tasks(self) -> List[TaskInstance]:
        """Hole alle aktiven Tasks"""
        return list(self.active_tasks.values())
    
    def get_tasks_for_assignee(self, assignee: str) -> List[TaskInstance]:
        """Hole Tasks für bestimmten Assignee"""
        return [task for task in self.active_tasks.values() if task.assignee == assignee]
    
    def add_instance_started_callback(self, callback: Callable[[ProcessInstance], None]):
        """Füge Instance Started Callback hinzu"""
        self.instance_started_callbacks.append(callback)
    
    def add_instance_completed_callback(self, callback: Callable[[ProcessInstance], None]):
        """Füge Instance Completed Callback hinzu"""
        self.instance_completed_callbacks.append(callback)
    
    def add_task_created_callback(self, callback: Callable[[TaskInstance], None]):
        """Füge Task Created Callback hinzu"""
        self.task_created_callbacks.append(callback)
    
    def add_task_completed_callback(self, callback: Callable[[TaskInstance], None]):
        """Füge Task Completed Callback hinzu"""
        self.task_completed_callbacks.append(callback)
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Hole Engine Status"""
        return {
            'running': self.running,
            'deployed_processes': len(self.process_definitions),
            'active_instances': len(self.active_instances),
            'active_tasks': len(self.active_tasks),
            'process_definitions': list(self.process_definitions.keys())
        }