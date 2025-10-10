"""
Camunda Process Engine Core Implementation
Verwaltet BPMN-Workflows und Prozessinstanzen
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

# PyZeebe Integration
try:
    from pyzeebe import ZeebeClient
    from pyzeebe.worker.worker import ZeebeWorker
    from pyzeebe.job.job import Job
    ZEEBE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ PyZeebe nicht verfügbar: {e}")
    ZEEBE_AVAILABLE = False
    
    # Mock-Klassen für Entwicklung ohne Zeebe
    class ZeebeClient:
        def __init__(self, *args, **kwargs): pass
        async def deploy_process(self, *args, **kwargs): return {"key": 123}
        async def run_process(self, *args, **kwargs): return {"process_instance_key": 456}
        async def topology(self): return type('obj', (object,), {'brokers': [1]})()
    
    class ZeebeWorker:
        def __init__(self, *args, **kwargs): pass
    
    class Job:
        def __init__(self): 
            self.variables = {}
            self.key = 123


class ProcessStatus(Enum):
    """Status-Werte für Prozessinstanzen"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"  
    CANCELED = "CANCELED"
    FAILED = "FAILED"


@dataclass
class ProcessInstance:
    """Repräsentiert eine laufende Prozessinstanz"""
    process_instance_key: int
    process_definition_key: int
    bpmn_process_id: str
    status: ProcessStatus
    variables: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CamundaProcessEngine:
    """Camunda Process Engine mit Zeebe Backend"""
    
    def __init__(self, gateway_address: str = "localhost:26500"):
        self.gateway_address = gateway_address
        self.client: Optional[ZeebeClient] = None
        self.worker: Optional[ZeebeWorker] = None
        self.initialized = False
        self.mock_mode = not ZEEBE_AVAILABLE
        
        # Prozessinstanz-Tracking
        self.active_processes: Dict[int, ProcessInstance] = {}
        self.process_counter = 1000  # Für Mock-Modus
        
        # Logging
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialisiert die Camunda Process Engine"""
        try:
            if ZEEBE_AVAILABLE:
                print("🔄 Initialisiere Camunda Process Engine...")
                
                # Zeebe Client erstellen
                self.client = ZeebeClient(grpc_channel=f"grpc://{self.gateway_address}")
                
                # Verbindung testen mit Retry-Logik
                if await self._test_connection():
                    # Worker für Job-Verarbeitung
                    self.worker = ZeebeWorker(self.client)
                    self.initialized = True
                    self.mock_mode = False
                    print("✅ Camunda Process Engine erfolgreich initialisiert")
                    return True
                else:
                    print("⚠️ Camunda nicht erreichbar - Mock-Modus aktiviert")
                    self.mock_mode = True
                    return True
            else:
                print("⚠️ PyZeebe nicht verfügbar - Mock-Modus aktiviert")
                self.mock_mode = True
                return True
                
        except Exception as e:
            print(f"⚠️ Process Engine Initialisierung fehlgeschlagen: {e}")
            self.mock_mode = True
            return True
    
    async def _test_connection(self, max_retries: int = 3) -> bool:
        """Testet Camunda-Verbindung"""
        for attempt in range(max_retries):
            try:
                if self.client:
                    topology = await self.client.topology()
                    if topology and hasattr(topology, 'brokers'):
                        print(f"✅ Camunda Zeebe erreichbar - {len(topology.brokers)} Broker gefunden")
                        return True
            except Exception as e:
                print(f"⚠️ Verbindungsversuch {attempt + 1} fehlgeschlagen: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        
        return False
    
    async def deploy_process(self, bpmn_file_path: str) -> Optional[int]:
        """Deployed einen BPMN-Prozess"""
        if self.mock_mode:
            print(f"🔄 Mock: BPMN-Prozess deployed: {bpmn_file_path}")
            return self.process_counter
        
        try:
            if self.client:
                with open(bpmn_file_path, 'rb') as bpmn_file:
                    result = await self.client.deploy_process(bpmn_file.read())
                    return result.get('key')
        except Exception as e:
            self.logger.error(f"Process deployment failed: {e}")
            return None
    
    async def start_process(self, bpmn_process_id: str, variables: Dict[str, Any] = None) -> Optional[ProcessInstance]:
        """Startet eine neue Prozessinstanz"""
        if variables is None:
            variables = {}
        
        if self.mock_mode:
            # Mock-Prozessinstanz erstellen
            process_instance = ProcessInstance(
                process_instance_key=self.process_counter,
                process_definition_key=self.process_counter - 100,
                bpmn_process_id=bpmn_process_id,
                status=ProcessStatus.ACTIVE,
                variables=variables,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            self.active_processes[process_instance.process_instance_key] = process_instance
            self.process_counter += 1
            
            print(f"🔄 Mock: Prozess gestartet - {bpmn_process_id} (ID: {process_instance.process_instance_key})")
            return process_instance
        
        try:
            if self.client:
                result = await self.client.run_process(bpmn_process_id, variables)
                process_instance_key = result.get('process_instance_key')
                
                if process_instance_key:
                    process_instance = ProcessInstance(
                        process_instance_key=process_instance_key,
                        process_definition_key=0,  # Wird von Zeebe gefüllt
                        bpmn_process_id=bpmn_process_id,
                        status=ProcessStatus.ACTIVE,
                        variables=variables,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    self.active_processes[process_instance_key] = process_instance
                    return process_instance
                    
        except Exception as e:
            self.logger.error(f"Process start failed: {e}")
            return None
    
    async def get_process_status(self, process_instance_key: int) -> Optional[ProcessInstance]:
        """Ruft Prozess-Status ab"""
        if process_instance_key in self.active_processes:
            return self.active_processes[process_instance_key]
        return None
    
    def get_all_active_processes(self) -> List[ProcessInstance]:
        """Gibt alle aktiven Prozesse zurück"""
        return list(self.active_processes.values())
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Gibt Engine-Status zurück"""
        return {
            "initialized": self.initialized,
            "mock_mode": self.mock_mode,
            "gateway_address": self.gateway_address,
            "active_processes": len(self.active_processes),
            "zeebe_available": ZEEBE_AVAILABLE
        }
    
    async def shutdown(self):
        """Fährt die Process Engine herunter"""
        if self.client and not self.mock_mode:
            try:
                # Zeebe Client schließen
                await self.client.close()
                print("✅ Camunda Process Engine heruntergefahren")
            except Exception as e:
                print(f"⚠️ Fehler beim Herunterfahren: {e}")


# Singleton-Instanz für globalen Zugriff
_process_engine_instance: Optional[CamundaProcessEngine] = None


def get_process_engine() -> CamundaProcessEngine:
    """Gibt die globale Process Engine Instanz zurück"""
    global _process_engine_instance
    if _process_engine_instance is None:
        _process_engine_instance = CamundaProcessEngine()
    return _process_engine_instance


async def initialize_process_engine() -> bool:
    """Initialisiert die globale Process Engine"""
    engine = get_process_engine()
    return await engine.initialize()