"""
BPMN Engine Tools für LangChain Agent
Echte Process Engine Integration mit LangChain
"""
from langchain_core.tools import BaseTool
from typing import Dict, Any, Optional, List
import json
from src.bpmn_engine.integration import get_bpmn_engine, start_bpmn_engine


class BPMNEngineStartTool(BaseTool):
    """Tool zum Starten neuer BPMN Prozesse"""
    
    name: str = "start_bpmn_process"
    description: str = """
    Startet einen neuen BPMN-Prozess in der echten Process Engine.
    Benötigt den Namen des Studierenden und die Bezeichnung des Studiengangs.
    
    Parameter:
    - student_name: Name des Studierenden (String)
    - studiengang: Bezeichnung des Studiengangs (String)
    
    Gibt die Process Instance ID und Task-Informationen zurück.
    """
    
    def _run(self, student_name: str, studiengang: str) -> str:
        try:
            engine = get_bpmn_engine()
            if not engine.running:
                start_bpmn_engine()
            
            instance_id = engine.start_bewerbung_process(student_name, studiengang)
            
            # Hole aktive Tasks für diese Instance
            all_tasks = engine.get_active_tasks()
            instance_tasks = [
                {
                    "task_id": task.id,
                    "task_name": task.task_definition.name,
                    "task_type": task.task_definition.__class__.__name__,
                    "assignee": task.assignee,
                    "form_fields": getattr(task.task_definition, 'form_fields', [])
                }
                for task in all_tasks 
                if task.process_instance_id == instance_id
            ]
            
            return json.dumps({
                "success": True,
                "instance_id": instance_id,
                "message": f"BPMN-Bewerbungsprozess für {student_name} ({studiengang}) gestartet",
                "process_type": "BPMN Process",
                "active_tasks": instance_tasks,
                "next_steps": "Warten auf Bearbeitung der User Tasks"
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Starten des BPMN-Prozesses: {e}",
                "process_type": "BPMN Process"
            }, ensure_ascii=False)


class BPMNEngineCompleteTaskTool(BaseTool):
    """Tool zum Abschließen von BPMN Tasks"""
    
    name: str = "complete_bpmn_task"
    description: str = """
    Schließt einen BPMN Task ab und setzt den Prozess fort.
    
    Parameter:
    - task_id: ID des Tasks (String)
    - student_email: E-Mail-Adresse des Studenten (String, für Angaben-Prüfung)
    - additional_data: Zusätzliche Daten als JSON String (Optional)
    
    Führt den Prozess automatisch bis zum nächsten User Task oder Ende fort.
    """
    
    def _run(self, task_id: str, student_email: str, additional_data: str = "{}") -> str:
        try:
            engine = get_bpmn_engine()
            if not engine.running:
                return json.dumps({
                    "success": False,
                    "error": "BPMN Engine nicht gestartet",
                    "message": "Die BPMN Engine muss zuerst gestartet werden"
                }, ensure_ascii=False)
            
            # Parse additional data
            try:
                extra_data = json.loads(additional_data) if additional_data != "{}" else {}
            except json.JSONDecodeError:
                extra_data = {}
            
            # Hole Task Info vor Completion
            all_tasks = engine.get_active_tasks()
            target_task = None
            for task in all_tasks:
                if task.id == task_id:
                    target_task = task
                    break
            
            if not target_task:
                return json.dumps({
                    "success": False,
                    "error": "Task nicht gefunden",
                    "message": f"Task {task_id} ist nicht aktiv oder existiert nicht"
                }, ensure_ascii=False)
            
            # Vervollständige Task-Daten
            completion_data = {
                'student_email': student_email,
                'bewerbung_gueltig': extra_data.get('bewerbung_gueltig', True),
                'bemerkung': extra_data.get('bemerkung', ''),
                'checked_at': '2025-10-10T16:00:00',
                'checked_by': 'chatbot_agent'
            }
            completion_data.update(extra_data)
            
            # Schließe Task ab
            success = engine.complete_task(task_id, completion_data)
            
            if not success:
                return json.dumps({
                    "success": False,
                    "error": "Task-Completion fehlgeschlagen",
                    "message": f"Task {task_id} konnte nicht abgeschlossen werden"
                }, ensure_ascii=False)
            
            # Prüfe Prozess-Status nach Completion
            instance = engine.get_process_instance(target_task.process_instance_id)
            new_tasks = [task for task in engine.get_active_tasks() 
                        if task.process_instance_id == target_task.process_instance_id]
            
            result = {
                "success": True,
                "task_id": task_id,
                "message": f"Task '{target_task.task_definition.name}' erfolgreich abgeschlossen",
                "process_status": instance.status.value if instance else "UNKNOWN",
                "completion_data": completion_data
            }
            
            if new_tasks:
                result["new_tasks"] = [
                    {
                        "task_id": task.id,
                        "task_name": task.task_definition.name,
                        "task_type": task.task_definition.__class__.__name__,
                        "assignee": task.assignee
                    }
                    for task in new_tasks
                ]
                result["next_steps"] = f"Neue Tasks verfügbar: {len(new_tasks)}"
            else:
                if instance and instance.status.value == "COMPLETED":
                    result["next_steps"] = "Prozess vollständig abgeschlossen"
                else:
                    result["next_steps"] = "Prozess läuft weiter - keine User Tasks erforderlich"
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Abschließen des Tasks: {e}"
            }, ensure_ascii=False)


class BPMNEngineStatusTool(BaseTool):
    """Tool für BPMN Engine Status und Prozess-Informationen"""
    
    name: str = "bpmn_engine_status"
    description: str = """
    Zeigt den Status der BPMN Engine und laufende Prozesse an.
    Keine Parameter erforderlich.
    
    Gibt Informationen über:
    - Engine-Status und Deploy-Status
    - Aktive Process Instances mit Details
    - Alle aktiven Tasks mit Zuweisungen
    - Engine-Statistiken
    """
    
    def _run(self) -> str:
        try:
            engine = get_bpmn_engine()
            
            # Engine Status
            engine_status = engine.get_engine_status()
            
            # Aktive Instances
            active_instances = engine.get_active_instances()
            instances_info = []
            for instance in active_instances:
                instances_info.append({
                    "instance_id": instance.id,
                    "process_name": instance.process_definition.name,
                    "status": instance.status.value,
                    "variables": instance.variables,
                    "business_key": instance.business_key,
                    "start_time": instance.start_time.isoformat(),
                    "active_tokens": len(instance.get_active_tokens())
                })
            
            # Aktive Tasks
            active_tasks = engine.get_active_tasks()
            tasks_info = []
            for task in active_tasks:
                tasks_info.append({
                    "task_id": task.id,
                    "task_name": task.task_definition.name,
                    "task_type": task.task_definition.__class__.__name__,
                    "process_instance_id": task.process_instance_id,
                    "assignee": task.assignee,
                    "status": task.status.value,
                    "created_at": task.created_at.isoformat(),
                    "form_fields": getattr(task.task_definition, 'form_fields', [])
                })
            
            result = {
                "engine_status": engine_status,
                "active_instances": instances_info,
                "active_tasks": tasks_info,
                "statistics": {
                    "total_instances": len(instances_info),
                    "total_tasks": len(tasks_info),
                    "deployed_processes": engine_status.get("deployed_processes", 0)
                }
            }
            
            return json.dumps(result, ensure_ascii=False, default=str)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Abrufen des BPMN Engine Status: {e}"
            }, ensure_ascii=False)


class BPMNEngineInstanceTool(BaseTool):
    """Tool für Details einer spezifischen BPMN Process Instance"""
    
    name: str = "get_bpmn_instance"
    description: str = """
    Holt detaillierte Informationen einer spezifischen BPMN Process Instance.
    
    Parameter:
    - instance_id: ID der Process Instance (String)
    
    Gibt alle verfügbaren Informationen zur Instance und ihren Tasks zurück.
    """
    
    def _run(self, instance_id: str) -> str:
        try:
            engine = get_bpmn_engine()
            if not engine.running:
                return json.dumps({
                    "success": False,
                    "error": "BPMN Engine nicht gestartet",
                    "message": "Die BPMN Engine muss zuerst gestartet werden"
                }, ensure_ascii=False)
            
            instance = engine.get_process_instance(instance_id)
            
            if not instance:
                return json.dumps({
                    "success": False,
                    "error": "Instance nicht gefunden",
                    "message": f"BPMN Process Instance {instance_id} existiert nicht oder ist nicht aktiv"
                }, ensure_ascii=False)
            
            # Hole Tasks für diese Instance
            all_tasks = engine.get_active_tasks()
            instance_tasks = [
                {
                    "task_id": task.id,
                    "task_name": task.task_definition.name,
                    "task_type": task.task_definition.__class__.__name__,
                    "status": task.status.value,
                    "assignee": task.assignee,
                    "created_at": task.created_at.isoformat(),
                    "variables": task.variables,
                    "form_fields": getattr(task.task_definition, 'form_fields', [])
                }
                for task in all_tasks 
                if task.process_instance_id == instance_id
            ]
            
            # Token-Informationen
            tokens_info = [
                {
                    "token_id": token.id,
                    "current_element": token.current_element.id,
                    "element_name": token.current_element.name,
                    "element_type": token.current_element.__class__.__name__,
                    "active": token.active,
                    "created_at": token.created_at.isoformat()
                }
                for token in instance.tokens
            ]
            
            result = {
                "success": True,
                "instance": {
                    "instance_id": instance.id,
                    "process_definition": {
                        "id": instance.process_definition.id,
                        "name": instance.process_definition.name
                    },
                    "status": instance.status.value,
                    "variables": instance.variables,
                    "business_key": instance.business_key,
                    "start_time": instance.start_time.isoformat(),
                    "end_time": instance.end_time.isoformat() if instance.end_time else None,
                    "is_active": instance.is_active()
                },
                "tokens": tokens_info,
                "active_tasks": instance_tasks,
                "statistics": {
                    "total_tokens": len(instance.tokens),
                    "active_tokens": len(instance.get_active_tokens()),
                    "active_tasks": len(instance_tasks)
                }
            }
            
            return json.dumps(result, ensure_ascii=False, default=str)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": f"Fehler beim Abrufen der Instance-Details: {e}"
            }, ensure_ascii=False)


def get_bpmn_engine_tools() -> List[BaseTool]:
    """Hole alle BPMN Engine Tools"""
    return [
        BPMNEngineStartTool(),
        BPMNEngineCompleteTaskTool(), 
        BPMNEngineStatusTool(),
        BPMNEngineInstanceTool()
    ]