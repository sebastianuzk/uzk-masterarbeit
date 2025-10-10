"""
CAMUNDA Zeebe Engine Manager
Lokale Process Engine für die Streamlit-App
"""
import logging
import threading
import time
import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Check if zeebe dependencies are available
try:
    from pyzeebe import ZeebeWorker, ZeebeClient, create_insecure_channel
    from pyzeebe.job.job import Job
    ZEEBE_AVAILABLE = True
except ImportError:
    ZEEBE_AVAILABLE = False

logger = logging.getLogger(__name__)


class MockZeebeEngine:
    """Mock Zeebe Engine für lokale Entwicklung ohne Zeebe-Server"""
    
    def __init__(self, db_path: str = "process_instances.db"):
        self.db_path = db_path
        self.processes = {}
        self.process_instances = {}
        self.instance_counter = 0
        self._setup_database()
        self._load_existing_instances()
        
    def _setup_database(self):
        """Setup SQLite-Datenbank für Process Instances"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS process_instances (
                id INTEGER PRIMARY KEY,
                process_key TEXT NOT NULL,
                status TEXT NOT NULL,
                variables TEXT,
                current_task TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_instances (
                id INTEGER PRIMARY KEY,
                process_instance_id INTEGER,
                task_name TEXT NOT NULL,
                status TEXT NOT NULL,
                variables TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (process_instance_id) REFERENCES process_instances (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_existing_instances(self):
        """Lade bestehende Instances aus der Datenbank"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT MAX(id) FROM process_instances')
        result = cursor.fetchone()
        if result[0] is not None:
            self.instance_counter = result[0]
        
        cursor.execute('''
            SELECT id, process_key, status, variables, current_task, created_at
            FROM process_instances WHERE status = 'ACTIVE'
        ''')
        
        for row in cursor.fetchall():
            instance_id = row[0]
            self.process_instances[instance_id] = {
                'process_key': row[1],
                'status': row[2],
                'variables': json.loads(row[3]) if row[3] else {},
                'current_task': row[4],
                'created_at': datetime.fromisoformat(row[5]) if row[5] else datetime.now()
            }
        
        conn.close()
        logger.info(f"Loaded {len(self.process_instances)} active instances from database")
    
    def deploy_process(self, process_id: str, bpmn_content: str):
        """Deploy einen BPMN-Prozess"""
        self.processes[process_id] = {
            'bpmn': bpmn_content,
            'deployed_at': datetime.now(),
            'instances': []
        }
        logger.info(f"Prozess '{process_id}' deployed")
    
    def start_process_instance(self, process_key: str, variables: Dict[str, Any]) -> int:
        """Starte eine neue Process Instance"""
        self.instance_counter += 1
        instance_id = self.instance_counter
        
        # Speichere in Datenbank
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO process_instances (id, process_key, status, variables, current_task)
            VALUES (?, ?, ?, ?, ?)
        ''', (instance_id, process_key, 'ACTIVE', json.dumps(variables), 'angaben_pruefen'))
        
        conn.commit()
        conn.close()
        
        # Speichere in Memory
        self.process_instances[instance_id] = {
            'process_key': process_key,
            'status': 'ACTIVE',
            'variables': variables,
            'current_task': 'angaben_pruefen',
            'created_at': datetime.now()
        }
        
        if process_key in self.processes:
            self.processes[process_key]['instances'].append(instance_id)
        
        logger.info(f"Process Instance {instance_id} für '{process_key}' gestartet")
        return instance_id
    
    def complete_task(self, instance_id: int, task_name: str, variables: Dict[str, Any]):
        """Schließe einen Task ab"""
        if instance_id not in self.process_instances:
            raise ValueError(f"Process Instance {instance_id} nicht gefunden")
        
        instance = self.process_instances[instance_id]
        
        # Update variables
        instance['variables'].update(variables)
        
        # Bestimme nächsten Task oder beende Prozess
        if task_name == 'angaben_pruefen':
            instance['status'] = 'COMPLETED'
            instance['current_task'] = None
        
        # Update in Datenbank
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE process_instances 
            SET status = ?, variables = ?, current_task = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (instance['status'], json.dumps(instance['variables']), 
              instance['current_task'], instance_id))
        
        # Füge Task-Completion hinzu
        cursor.execute('''
            INSERT INTO task_instances (process_instance_id, task_name, status, variables, completed_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (instance_id, task_name, 'COMPLETED', json.dumps(variables)))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Task '{task_name}' für Instance {instance_id} abgeschlossen")
    
    def get_process_instance(self, instance_id: int) -> Optional[Dict[str, Any]]:
        """Hole Process Instance Details"""
        return self.process_instances.get(instance_id)
    
    def get_active_instances(self) -> List[Dict[str, Any]]:
        """Hole alle aktiven Process Instances"""
        return [
            {**instance, 'id': iid} 
            for iid, instance in self.process_instances.items() 
            if instance['status'] == 'ACTIVE'
        ]
    
    def get_all_instances(self) -> List[Dict[str, Any]]:
        """Hole alle Process Instances"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, process_key, status, variables, current_task, created_at, updated_at
            FROM process_instances ORDER BY created_at DESC
        ''')
        
        instances = []
        for row in cursor.fetchall():
            instances.append({
                'id': row[0],
                'process_key': row[1],
                'status': row[2],
                'variables': json.loads(row[3]) if row[3] else {},
                'current_task': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            })
        
        conn.close()
        return instances


class CamundaEngine:
    """CAMUNDA Process Engine Manager"""
    
    def __init__(self, use_mock: bool = True):
        self.use_mock = use_mock or not ZEEBE_AVAILABLE
        self.running = False
        self.engine = None
        
        if self.use_mock:
            self.engine = MockZeebeEngine()
            logger.info("Using Mock Zeebe Engine")
        else:
            logger.info("Using Real Zeebe Engine")
    
    def start(self):
        """Starte die Process Engine"""
        if self.running:
            return
        
        try:
            if self.use_mock:
                self._start_mock_engine()
            else:
                self._start_zeebe_engine()
            
            self.running = True
            logger.info("CAMUNDA Process Engine gestartet")
            
        except Exception as e:
            logger.error(f"Fehler beim Starten der Process Engine: {e}")
            raise
    
    def stop(self):
        """Stoppe die Process Engine"""
        if not self.running:
            return
        
        self.running = False
        logger.info("CAMUNDA Process Engine gestoppt")
    
    def _start_mock_engine(self):
        """Starte Mock Engine"""
        # Deploy standard "Bewerbung" Prozess
        bewerbung_bpmn = self._create_bewerbung_bpmn()
        self.engine.deploy_process("bewerbung", bewerbung_bpmn)
    
    def _start_zeebe_engine(self):
        """Starte echte Zeebe Engine"""
        # TODO: Implementierung für echte Zeebe-Engine
        pass
    
    def _create_bewerbung_bpmn(self) -> str:
        """Erstelle BPMN für Bewerbungsprozess"""
        return '''<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
                  xmlns:zeebe="http://camunda.org/schema/zeebe/1.0"
                  targetNamespace="http://camunda.org/schema/1.0/bpmn"
                  id="bewerbung-process">
  
  <bpmn:process id="bewerbung" name="Bewerbungsprozess" isExecutable="true">
    
    <bpmn:startEvent id="start" name="Bewerbung eingegangen">
      <bpmn:outgoing>flow1</bpmn:outgoing>
    </bpmn:startEvent>
    
    <bpmn:sequenceFlow id="flow1" sourceRef="start" targetRef="angaben_pruefen"/>
    
    <bpmn:userTask id="angaben_pruefen" name="Angaben prüfen">
      <bpmn:incoming>flow1</bpmn:incoming>
      <bpmn:outgoing>flow2</bpmn:outgoing>
    </bpmn:userTask>
    
    <bpmn:sequenceFlow id="flow2" sourceRef="angaben_pruefen" targetRef="end"/>
    
    <bpmn:endEvent id="end" name="Bewerbung bearbeitet">
      <bpmn:incoming>flow2</bpmn:incoming>
    </bpmn:endEvent>
    
  </bpmn:process>
  
</bpmn:definitions>'''
    
    def start_bewerbung_process(self, student_name: str, studiengang: str) -> int:
        """Starte neuen Bewerbungsprozess"""
        if not self.running:
            raise RuntimeError("Process Engine ist nicht gestartet")
        
        variables = {
            'student_name': student_name,
            'studiengang': studiengang,
            'timestamp': datetime.now().isoformat()
        }
        
        instance_id = self.engine.start_process_instance("bewerbung", variables)
        logger.info(f"Bewerbungsprozess gestartet für {student_name} - Instance ID: {instance_id}")
        return instance_id
    
    def complete_angaben_pruefen(self, instance_id: int, student_email: str):
        """Schließe 'Angaben prüfen' Task ab"""
        if not self.running:
            raise RuntimeError("Process Engine ist nicht gestartet")
        
        variables = {
            'student_email': student_email,
            'checked_at': datetime.now().isoformat(),
            'checked_by': 'system'
        }
        
        self.engine.complete_task(instance_id, 'angaben_pruefen', variables)
        logger.info(f"Angaben-Prüfung abgeschlossen für Instance {instance_id}")
    
    def get_process_instance(self, instance_id: int) -> Optional[Dict[str, Any]]:
        """Hole Process Instance Details"""
        if not self.running:
            return None
        return self.engine.get_process_instance(instance_id)
    
    def get_active_instances(self) -> List[Dict[str, Any]]:
        """Hole alle aktiven Process Instances"""
        if not self.running:
            return []
        return self.engine.get_active_instances()
    
    def get_all_instances(self) -> List[Dict[str, Any]]:
        """Hole alle Process Instances"""
        if not self.running:
            return []
        return self.engine.get_all_instances()
    
    def get_status(self) -> Dict[str, Any]:
        """Hole Engine-Status"""
        return {
            'running': self.running,
            'engine_type': 'Mock' if self.use_mock else 'Zeebe',
            'zeebe_available': ZEEBE_AVAILABLE,
            'active_instances': len(self.get_active_instances()),
            'total_instances': len(self.get_all_instances())
        }


# Globale Engine-Instanz
_engine_instance = None

def get_engine() -> CamundaEngine:
    """Hole globale Engine-Instanz"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = CamundaEngine()
    return _engine_instance

def start_engine():
    """Starte globale Engine"""
    engine = get_engine()
    if not engine.running:
        engine.start()
    return engine

def stop_engine():
    """Stoppe globale Engine"""
    global _engine_instance
    if _engine_instance:
        _engine_instance.stop()
        _engine_instance = None