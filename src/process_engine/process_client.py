"""
Process Engine Client für Camunda Platform 8 Integration
Verwaltet Verbindungen zu Zeebe, Operate und Tasklist
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from pyzeebe import ZeebeWorker, ZeebeClient, create_camunda_cloud_channel
    ZEEBE_AVAILABLE = True
except ImportError:
    ZEEBE_AVAILABLE = False
    print("⚠️ pyzeebe nicht installiert. Process Engine Funktionen eingeschränkt.")

import requests
from config.settings import Settings

@dataclass
class ProcessInstance:
    """Repräsentiert eine Prozessinstanz"""
    process_instance_key: int
    process_definition_key: int
    bpmn_process_id: str
    version: int
    variables: Dict[str, Any]
    state: str
    start_time: datetime
    end_time: Optional[datetime] = None

@dataclass
class WorkflowDeployment:
    """Repräsentiert ein deployed Workflow"""
    deployment_key: int
    process_definition_key: int
    bpmn_process_id: str
    version: int
    resource_name: str

class ProcessEngineClient:
    """Client für Camunda Platform 8 Integration"""
    
    def __init__(self):
        self.settings = Settings()
        self.zeebe_client = None
        self.worker = None
        self.logger = logging.getLogger(__name__)
        
        if self.settings.ENABLE_PROCESS_ENGINE and ZEEBE_AVAILABLE:
            self._initialize_clients()
    
    def _initialize_clients(self):
        """Initialisiert Zeebe Client und Worker"""
        try:
            # Zeebe Client erstellen
            self.zeebe_client = ZeebeClient(
                grpc_channel_options=[
                    ("grpc.keepalive_time_ms", 30000),
                    ("grpc.keepalive_timeout_ms", 5000),
                    ("grpc.http2.max_pings_without_data", 0),
                ]
            )
            
            # Worker für Job-Bearbeitung
            self.worker = ZeebeWorker(self.zeebe_client)
            
            # Test-Verbindung
            topology = self.zeebe_client.topology()
            self.logger.info(f"✅ Zeebe verbunden: {len(topology.brokers)} Broker verfügbar")
            
        except Exception as e:
            self.logger.error(f"❌ Zeebe Verbindung fehlgeschlagen: {e}")
            self.zeebe_client = None
            self.worker = None
    
    def deploy_workflow(self, bpmn_file_path: str) -> Optional[WorkflowDeployment]:
        """Deployed ein BPMN Workflow"""
        if not self.zeebe_client:
            self.logger.warning("Zeebe Client nicht verfügbar")
            return None
        
        try:
            with open(bpmn_file_path, 'rb') as bpmn_file:
                response = self.zeebe_client.deploy_resource(
                    resource_file_path=bpmn_file_path
                )
            
            deployment = response.deployments[0]
            workflow_deployment = WorkflowDeployment(
                deployment_key=response.key,
                process_definition_key=deployment.process.process_definition_key,
                bpmn_process_id=deployment.process.bpmn_process_id,
                version=deployment.process.version,
                resource_name=deployment.process.resource_name
            )
            
            self.logger.info(f"✅ Workflow deployed: {workflow_deployment.bpmn_process_id} v{workflow_deployment.version}")
            return workflow_deployment
            
        except Exception as e:
            self.logger.error(f"❌ Workflow Deployment fehlgeschlagen: {e}")
            return None
    
    def start_process_instance(self, 
                             bpmn_process_id: str, 
                             variables: Dict[str, Any] = None) -> Optional[ProcessInstance]:
        """Startet eine neue Prozessinstanz"""
        if not self.zeebe_client:
            self.logger.warning("Zeebe Client nicht verfügbar")
            return None
        
        try:
            variables = variables or {}
            variables['startTime'] = datetime.now().isoformat()
            variables['initiator'] = 'chatbot'
            
            response = self.zeebe_client.create_process_instance(
                bpmn_process_id=bpmn_process_id,
                variables=variables
            )
            
            process_instance = ProcessInstance(
                process_instance_key=response.process_instance_key,
                process_definition_key=response.process_definition_key,
                bpmn_process_id=response.bpmn_process_id,
                version=response.version,
                variables=variables,
                state='ACTIVE',
                start_time=datetime.now()
            )
            
            self.logger.info(f"✅ Prozess gestartet: {process_instance.process_instance_key}")
            return process_instance
            
        except Exception as e:
            self.logger.error(f"❌ Prozessstart fehlgeschlagen: {e}")
            return None
    
    def cancel_process_instance(self, process_instance_key: int) -> bool:
        """Bricht eine Prozessinstanz ab"""
        if not self.zeebe_client:
            return False
        
        try:
            self.zeebe_client.cancel_process_instance(process_instance_key)
            self.logger.info(f"✅ Prozess abgebrochen: {process_instance_key}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Prozessabbruch fehlgeschlagen: {e}")
            return False
    
    def get_process_instances(self, 
                            bpmn_process_id: Optional[str] = None,
                            state: Optional[str] = None) -> List[ProcessInstance]:
        """Holt Prozessinstanzen via Operate API"""
        try:
            url = f"{self.settings.CAMUNDA_OPERATE_URL}/api/process-instances"
            params = {}
            
            if bpmn_process_id:
                params['bpmnProcessId'] = bpmn_process_id
            if state:
                params['state'] = state
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                instances_data = response.json()
                instances = []
                
                for data in instances_data.get('items', []):
                    instance = ProcessInstance(
                        process_instance_key=data['key'],
                        process_definition_key=data['processDefinitionKey'],
                        bpmn_process_id=data['bpmnProcessId'],
                        version=data['version'],
                        variables={},  # Variablen separat laden
                        state=data['state'],
                        start_time=datetime.fromisoformat(data['startDate'])
                    )
                    
                    if data.get('endDate'):
                        instance.end_time = datetime.fromisoformat(data['endDate'])
                    
                    instances.append(instance)
                
                return instances
            else:
                self.logger.warning(f"Operate API nicht erreichbar: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abrufen der Prozessinstanzen: {e}")
            return []
    
    def publish_message(self, 
                       message_name: str, 
                       correlation_key: str,
                       variables: Dict[str, Any] = None) -> bool:
        """Sendet eine Nachricht an wartende Prozesse"""
        if not self.zeebe_client:
            return False
        
        try:
            variables = variables or {}
            
            self.zeebe_client.publish_message(
                name=message_name,
                correlation_key=correlation_key,
                variables=variables
            )
            
            self.logger.info(f"✅ Nachricht gesendet: {message_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Nachrichtenversand fehlgeschlagen: {e}")
            return False
    
    def complete_job(self, job_key: int, variables: Dict[str, Any] = None) -> bool:
        """Schließt einen Job ab"""
        if not self.zeebe_client:
            return False
        
        try:
            variables = variables or {}
            
            self.zeebe_client.complete_job(
                job_key=job_key,
                variables=variables
            )
            
            self.logger.info(f"✅ Job abgeschlossen: {job_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Job-Abschluss fehlgeschlagen: {e}")
            return False
    
    def register_job_handler(self, job_type: str, handler_function):
        """Registriert einen Handler für Jobs eines bestimmten Typs"""
        if not self.worker:
            self.logger.warning("Worker nicht verfügbar")
            return
        
        try:
            @self.worker.task(task_type=job_type)
            def job_handler(job):
                try:
                    result = handler_function(job)
                    return result or {}
                except Exception as e:
                    self.logger.error(f"❌ Job Handler Fehler: {e}")
                    raise
            
            self.logger.info(f"✅ Job Handler registriert: {job_type}")
            
        except Exception as e:
            self.logger.error(f"❌ Job Handler Registrierung fehlgeschlagen: {e}")
    
    def start_worker(self):
        """Startet den Worker für Job-Bearbeitung"""
        if not self.worker:
            self.logger.warning("Worker nicht verfügbar")
            return
        
        try:
            self.logger.info("🚀 Zeebe Worker gestartet...")
            self.worker.work()
        except Exception as e:
            self.logger.error(f"❌ Worker Fehler: {e}")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Prüft Gesundheitsstatus aller Camunda Komponenten"""
        status = {
            'zeebe': False,
            'operate': False,
            'tasklist': False,
            'timestamp': datetime.now().isoformat()
        }
        
        # Zeebe Status
        if self.zeebe_client:
            try:
                topology = self.zeebe_client.topology()
                status['zeebe'] = len(topology.brokers) > 0
            except:
                status['zeebe'] = False
        
        # Operate Status
        try:
            response = requests.get(f"{self.settings.CAMUNDA_OPERATE_URL}/actuator/health", timeout=5)
            status['operate'] = response.status_code == 200
        except:
            status['operate'] = False
        
        # Tasklist Status
        try:
            response = requests.get(f"{self.settings.CAMUNDA_TASKLIST_URL}/actuator/health", timeout=5)
            status['tasklist'] = response.status_code == 200
        except:
            status['tasklist'] = False
        
        return status
    
    def cleanup(self):
        """Bereinigt Ressourcen"""
        if self.worker:
            try:
                self.worker.stop()
            except:
                pass
        
        if self.zeebe_client:
            try:
                self.zeebe_client.close()
            except:
                pass