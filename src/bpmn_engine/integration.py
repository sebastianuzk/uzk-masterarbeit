"""
BPMN Engine Integration
Integriert die echte BPMN Engine in die bestehende Anwendung
"""
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .parser import BPMNParser, create_sample_bpmn
from .engine import ProcessExecutionEngine, ProcessInstance, TaskInstance
from .elements import ProcessDefinition

logger = logging.getLogger(__name__)


class BPMNEngineManager:
    """Manager für die BPMN Engine Integration"""
    
    def __init__(self, db_path: str = "bpmn_engine.db", processes_directory: str = "bpmn_processes"):
        self.parser = BPMNParser()
        self.execution_engine = ProcessExecutionEngine(db_path)
        self.processes_directory = processes_directory
        self.running = False
        self._last_modified_times: Dict[str, float] = {}
        
        # Callbacks für Integration
        self._setup_callbacks()
    
    def start(self):
        """Starte BPMN Engine"""
        if self.running:
            return
        
        self.running = True
        
        # Lade Prozesse aus Ordner falls vorhanden
        self._load_processes_from_directory()
        
        # Falls keine Prozesse geladen wurden, deploye Standard-Bewerbungsprozess
        deployed_processes = self.execution_engine.process_definitions
        if not deployed_processes:
            self._deploy_sample_processes()
        
        logger.info("BPMN Engine gestartet")
    
    def stop(self):
        """Stoppe BPMN Engine"""
        if not self.running:
            return
        
        self.running = False
        logger.info("BPMN Engine gestoppt")
    
    def _load_processes_from_directory(self):
        """Lädt alle BPMN-Prozesse aus dem konfigurierten Ordner"""
        logger.info(f"Loading processes from directory: {self.processes_directory}")
        
        try:
            processes = self.parser.parse_directory(self.processes_directory)
            
            for process_id, process_def in processes.items():
                try:
                    self.execution_engine.deploy_process(process_def)
                    logger.info(f"Deployed process from directory: {process_def.name} (ID: {process_id})")
                except Exception as e:
                    logger.error(f"Failed to deploy process {process_id}: {e}")
            
            self._update_modification_times()
            logger.info(f"Successfully loaded {len(processes)} processes from directory")
            
        except Exception as e:
            logger.warning(f"Could not load processes from directory {self.processes_directory}: {e}")
    
    def reload_processes_from_directory(self):
        """Lädt alle Prozesse aus dem Ordner neu"""
        if not self.running:
            raise RuntimeError("BPMN Engine not running")
        
        logger.info("Reloading processes from directory")
        self._load_processes_from_directory()
    
    def get_available_process_files(self) -> List[Dict[str, str]]:
        """
        Hole Informationen über verfügbare BPMN-Dateien
        
        Returns:
            Liste mit Datei-Informationen (id, name, file, path)
        """
        return self.parser.get_available_processes(self.processes_directory)
    
    def check_for_process_updates(self) -> List[str]:
        """
        Prüft ob BPMN-Dateien im Ordner geändert wurden
        
        Returns:
            Liste der geänderten Dateien
        """
        changed_files = []
        directory = Path(self.processes_directory)
        
        if not directory.exists():
            return changed_files
        
        bpmn_files = list(directory.glob("*.bpmn")) + list(directory.glob("*.xml"))
        
        for bpmn_file in bpmn_files:
            try:
                current_mtime = bpmn_file.stat().st_mtime
                last_mtime = self._last_modified_times.get(str(bpmn_file), 0)
                
                if current_mtime > last_mtime:
                    changed_files.append(str(bpmn_file))
                    
            except Exception as e:
                logger.warning(f"Could not check modification time for {bpmn_file}: {e}")
        
        return changed_files
    
    def _update_modification_times(self):
        """Aktualisiert die gespeicherten Änderungszeiten der BPMN-Dateien"""
        directory = Path(self.processes_directory)
        
        if not directory.exists():
            return
        
        bpmn_files = list(directory.glob("*.bpmn")) + list(directory.glob("*.xml"))
        
        for bpmn_file in bpmn_files:
            try:
                self._last_modified_times[str(bpmn_file)] = bpmn_file.stat().st_mtime
            except Exception as e:
                logger.warning(f"Could not get modification time for {bpmn_file}: {e}")

    def _deploy_sample_processes(self):
        """Deploy Beispiel-Prozesse"""
        try:
            # Erstelle und deploye Beispiel-Bewerbungsprozess
            sample_bpmn = create_sample_bpmn()
            process_def = self.parser.parse_string(sample_bpmn)
            
            # Validiere Process (aber deploye trotzdem wenn nur Warnings)
            errors = process_def.validate()
            if errors:
                logger.warning(f"Process validation warnings: {errors}")
            
            self.execution_engine.deploy_process(process_def)
            
            # Registriere Service Handlers
            self._register_service_handlers()
            
            logger.info(f"Sample process '{process_def.id}' deployed successfully")
        except Exception as e:
            logger.error(f"Error deploying sample processes: {e}")
            # Deploye einen vereinfachten Prozess als Fallback
            self._deploy_fallback_process()
    
    def _register_service_handlers(self):
        """Registriere Service Task Handlers"""
        
        def accept_application_handler(context):
            """Handler für Bewerbungsannahme"""
            student_name = context.get_variable('student_name', 'Unknown')
            studiengang = context.get_variable('studiengang', 'Unknown')
            
            logger.info(f"Bewerbung akzeptiert: {student_name} für {studiengang}")
            
            return {
                'acceptance_date': '2025-10-10',
                'acceptance_status': 'ACCEPTED',
                'notification_sent': True
            }
        
        self.execution_engine.register_service_handler(
            'AcceptApplicationService', 
            accept_application_handler
        )
    
    def _deploy_fallback_process(self):
        """Deploy vereinfachten Fallback-Prozess"""
        from .elements import ProcessDefinition, StartEvent, UserTask, EndEvent, SequenceFlow
        
        # Erstelle einfachen Prozess programmatisch
        process_def = ProcessDefinition(id="bewerbung_process", name="Vereinfachter Bewerbungsprozess")
        
        # Elemente erstellen
        start_event = StartEvent("start_bewerbung", "Bewerbung eingegangen")
        user_task = UserTask("angaben_pruefen", "Angaben prüfen")
        user_task.assignee = "sachbearbeiter"
        user_task.add_form_field("student_email", "email", "E-Mail Adresse", True)
        
        end_event = EndEvent("end_bewerbung", "Bewerbung bearbeitet")
        
        # Elemente hinzufügen
        process_def.add_element(start_event)
        process_def.add_element(user_task)
        process_def.add_element(end_event)
        
        # SequenceFlows erstellen
        flow1 = SequenceFlow("flow1", start_event, user_task)
        flow2 = SequenceFlow("flow2", user_task, end_event)
        process_def.add_element(flow1)
        process_def.add_element(flow2)
        
        # Deploy
        self.execution_engine.deploy_process(process_def)
        logger.info("Fallback process deployed successfully")
    
    def _setup_callbacks(self):
        """Setup Event Callbacks"""
        
        def on_instance_started(instance: ProcessInstance):
            logger.info(f"Process instance started: {instance.id} ({instance.process_definition.name})")
        
        def on_instance_completed(instance: ProcessInstance):
            logger.info(f"Process instance completed: {instance.id}")
        
        def on_task_created(task: TaskInstance):
            logger.info(f"Task created: {task.id} ({task.task_definition.name})")
        
        def on_task_completed(task: TaskInstance):
            logger.info(f"Task completed: {task.id}")
        
        self.execution_engine.add_instance_started_callback(on_instance_started)
        self.execution_engine.add_instance_completed_callback(on_instance_completed)
        self.execution_engine.add_task_created_callback(on_task_created)
        self.execution_engine.add_task_completed_callback(on_task_completed)
    
    def deploy_bpmn_file(self, file_path: str) -> str:
        """Deploy BPMN Datei"""
        if not self.running:
            raise RuntimeError("BPMN Engine not running")
        
        try:
            process_def = self.parser.parse_file(file_path)
            self.execution_engine.deploy_process(process_def)
            logger.info(f"Deployed BPMN file: {file_path}")
            return process_def.id
        except Exception as e:
            logger.error(f"Error deploying BPMN file {file_path}: {e}")
            raise
    
    def deploy_bpmn_xml(self, bpmn_xml: str) -> str:
        """Deploy BPMN XML String"""
        if not self.running:
            raise RuntimeError("BPMN Engine not running")
        
        try:
            process_def = self.parser.parse_string(bpmn_xml)
            self.execution_engine.deploy_process(process_def)
            logger.info(f"Deployed BPMN XML for process: {process_def.id}")
            return process_def.id
        except Exception as e:
            logger.error(f"Error deploying BPMN XML: {e}")
            raise
    
    def start_process_instance(self, process_definition_id: str, variables: Dict[str, Any] = None, 
                              business_key: str = None) -> str:
        """Starte neue Process Instance"""
        if not self.running:
            raise RuntimeError("BPMN Engine not running")
        
        try:
            instance_id = self.execution_engine.start_process(
                process_definition_id, 
                variables or {}, 
                business_key
            )
            logger.info(f"Started process instance: {instance_id}")
            return instance_id
        except Exception as e:
            logger.error(f"Error starting process instance: {e}")
            raise
    
    def complete_task(self, task_id: str, variables: Dict[str, Any] = None) -> bool:
        """Schließe Task ab"""
        if not self.running:
            raise RuntimeError("BPMN Engine not running")
        
        try:
            success = self.execution_engine.complete_task(task_id, variables or {})
            if success:
                logger.info(f"Completed task: {task_id}")
            else:
                logger.warning(f"Task not found or already completed: {task_id}")
            return success
        except Exception as e:
            logger.error(f"Error completing task {task_id}: {e}")
            raise
    
    def get_process_instance(self, instance_id: str) -> Optional[ProcessInstance]:
        """Hole Process Instance"""
        if not self.running:
            return None
        
        return self.execution_engine.get_process_instance(instance_id)
    
    def get_active_instances(self) -> List[ProcessInstance]:
        """Hole alle aktiven Process Instances"""
        if not self.running:
            return []
        
        return self.execution_engine.get_active_instances()
    
    def get_active_tasks(self) -> List[TaskInstance]:
        """Hole alle aktiven Tasks"""
        if not self.running:
            return []
        
        return self.execution_engine.get_active_tasks()
    
    def get_tasks_for_assignee(self, assignee: str) -> List[TaskInstance]:
        """Hole Tasks für bestimmten Assignee"""
        if not self.running:
            return []
        
        return self.execution_engine.get_tasks_for_assignee(assignee)
    
    def get_tasks_for_instance(self, instance_id: str) -> List[TaskInstance]:
        """Hole alle Tasks für eine bestimmte Process Instance"""
        if not self.running:
            return []
        
        # Filter alle aktiven Tasks nach Instance ID
        all_tasks = self.execution_engine.get_active_tasks()
        return [task for task in all_tasks if task.process_instance_id == instance_id]
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Hole Engine Status"""
        base_status = {
            'running': self.running,
            'engine_type': 'BPMN Process Engine',
            'deployed_processes': 0,
            'active_instances': 0,
            'active_tasks': 0
        }
        
        if self.running:
            engine_status = self.execution_engine.get_engine_status()
            base_status.update(engine_status)
        
        return base_status
    
    def get_process_statistics(self) -> Dict[str, Any]:
        """
        Hole Statistiken über geladene Prozesse und Engine-Status
        
        Returns:
            Dictionary mit detaillierten Statistiken
        """
        if not self.running:
            return {
                'running': False,
                'total_processes': 0,
                'processes_directory': self.processes_directory,
                'available_files': []
            }
        
        # Basis-Statistiken von der Engine
        engine_status = self.execution_engine.get_engine_status()
        
        # Verfügbare Dateien im Ordner
        available_files = self.get_available_process_files()
        
        # Geänderte Dateien
        changed_files = self.check_for_process_updates()
        
        return {
            'running': True,
            'processes_directory': self.processes_directory,
            'deployed_processes': engine_status.get('deployed_processes', 0),
            'active_instances': engine_status.get('active_instances', 0),
            'active_tasks': engine_status.get('active_tasks', 0),
            'available_files': len(available_files),
            'file_details': available_files,
            'changed_files': changed_files,
            'engine_status': engine_status
        }

    # Convenience Methods für Bewerbungsprozess
    def start_bewerbung_process(self, student_name: str, studiengang: str, email: str = None,
                               additional_variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Starte Bewerbungsprozess (convenience method)"""
        variables = {
            'student_name': student_name,
            'studiengang': studiengang,
            'start_time': '2025-10-10T16:00:00'
        }
        
        if email:
            variables['email'] = email
        
        if additional_variables:
            variables.update(additional_variables)
        
        instance_id = self.start_process_instance('bewerbung_process', variables, f"{student_name}_{studiengang}")
        
        return {
            'success': True,
            'instance_id': instance_id,
            'student_name': student_name,
            'studiengang': studiengang,
            'email': email,
            'message': f'Bewerbungsprozess für {student_name} ({studiengang}) erfolgreich gestartet'
        }
    
    def complete_angaben_pruefen(self, task_id: str, student_email: str, bewerbung_gueltig: bool = True, 
                                 bemerkung: str = "") -> Dict[str, Any]:
        """Schließe Angaben-Prüfung Task ab (convenience method)"""
        variables = {
            'student_email': student_email,
            'bewerbung_gueltig': bewerbung_gueltig,
            'bemerkung': bemerkung,
            'checked_at': '2025-10-10T16:00:00',
            'checked_by': 'chatbot_agent'
        }
        
        success = self.complete_task(task_id, variables)
        
        return {
            'success': success,
            'task_id': task_id,
            'student_email': student_email,
            'bewerbung_gueltig': bewerbung_gueltig,
            'bemerkung': bemerkung,
            'message': f'Angaben-Prüfung {"erfolgreich" if success else "fehlgeschlagen"} abgeschlossen'
        }
    
    def get_bewerbung_tasks(self) -> List[TaskInstance]:
        """Hole alle Bewerbungs-Tasks"""
        all_tasks = self.get_active_tasks()
        return [task for task in all_tasks 
                if task.task_definition.id in ['angaben_pruefen', 'bewerbung_ablehnen']]


# Globale Engine Instance
_bpmn_engine_instance = None

def get_bpmn_engine() -> BPMNEngineManager:
    """Hole globale BPMN Engine Instance"""
    global _bpmn_engine_instance
    if _bpmn_engine_instance is None:
        _bpmn_engine_instance = BPMNEngineManager()
    return _bpmn_engine_instance

def start_bpmn_engine():
    """Starte globale BPMN Engine"""
    engine = get_bpmn_engine()
    if not engine.running:
        engine.start()
    return engine

def stop_bpmn_engine():
    """Stoppe globale BPMN Engine"""
    global _bpmn_engine_instance
    if _bpmn_engine_instance:
        _bpmn_engine_instance.stop()
        _bpmn_engine_instance = None