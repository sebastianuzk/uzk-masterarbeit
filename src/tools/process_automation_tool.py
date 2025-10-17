
from __future__ import annotations
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from pathlib import Path

from config.settings import settings
from src.camunda_integration.client.camunda_client import CamundaClient
from src.camunda_integration.services.camunda_service import CamundaService

# Global holder wired from your app
_CAMUNDA_SERVICE = None

def set_camunda_service(service):
    global _CAMUNDA_SERVICE
    _CAMUNDA_SERVICE = service

def _svc():
    if _CAMUNDA_SERVICE is None:
        # Auto-initialize if not set
        try:
            client = CamundaClient(settings.CAMUNDA_BASE_URL)
            bpmn_dir = Path("src/camunda_integration/bpmn_processes")
            service = CamundaService(client=client, bpmn_dir=bpmn_dir)
            set_camunda_service(service)
        except Exception as e:
            raise RuntimeError(f"CamundaService not configured and auto-init failed: {e}")
    return _CAMUNDA_SERVICE

@tool
def discover_processes() -> Dict[str, Any]:
    """
    Zeigt alle verfügbaren BPMN-Prozesse mit ihren Eigenschaften und Eingabefeldern an.
    
    Keine Parameter erforderlich - zeigt alle verfügbaren Prozesse an.

    Nutze dieses Tool, um den process_key eines Prozesses für "process_start" zu erhalten.
    
    Returns:
        Dictionary mit verfügbaren Prozessen, deren Details und erforderlichen Formular-Variablen
        
    Beispiel Aufruf:
        discover_processes()
        
    Beispiel Antwort:
        {
            "success": True,
            "processes": [
                {
                    "id": "bewerbung_process:1:abc123",
                    "key": "bewerbung_process", 
                    "name": "Universitäts-Bewerbungsprozess",
                    "version": 1,
                    "required_fields": [
                        {
                            "id": "student_name",
                            "label": "Name des Studenten",
                            "type": "string",
                            "required": true
                        },
                        {
                            "id": "studiengang",
                            "label": "Gewünschter Studiengang",
                            "type": "string",
                            "required": true
                        }
                    ]
                }
            ]
        }
    """
    try:
        return _svc().discover_processes()
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Fehler beim Laden der Prozesse: {e}"
        }

@tool
def start_process(process_key: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Startet einen BPMN-Geschäftsprozess in Camunda mit den gegebenen Variablen.
    
    Args:
        process_key: Der Key des BPMN-Prozesses (z.B. "bewerbung_process")
        variables: Dictionary mit Prozessvariablen entsprechend der required_fields aus discover_processes
    
    Returns:
        Dictionary mit Prozess-Details, Status und nächsten Tasks
        
    Beispiel Aufruf:
        start_process(
            process_key="bewerbung_process", 
            variables={
                "student_name": "Pascal Müller",
                "studiengang": "Informatik",
                "semester": 3,
                "email": "pascal.mueller@student.uni-koeln.de"
            }
        )
        
    Erfolgreiche Antwort:
        {
            "success": True,
            "message": "Started process bewerbung_process -> instance pi_12345",
            "process_instance_id": "pi_12345",
            "process_status": "running",
            "next_tasks": [{"id": "task_1", "name": "Bewerbung prüfen"}]
        }
    """
    try:
        res = _svc().start_process(process_key, variables)
        return res.model_dump()
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Fehler beim Starten des Prozesses {process_key}: {e}"
        }

@tool
def get_process_status(process_instance_id: str) -> Dict[str, Any]:
    """
    Zeigt den aktuellen Status einer laufenden Prozessinstanz und alle offenen User Tasks an. Nutze hierfür die Prozess-Instanz-ID aus start_process oder aus dem Chatverlauf.
    Benutze NICHT die ID aus dem Beispiel Aufruf!
    
    Args:
        process_instance_id: Die ID der Prozessinstanz (aus start_process oder dem Chatverlauf erhalten)
        
    Returns:
        Dictionary mit Prozess-Status und Liste der offenen Tasks
        
    Beispiel Aufruf:
        get_process_status(process_instance_id="pi_12345")
        
    Beispiel Antwort:
        {
            "success": True,
            "message": "Instance pi_12345 status: running",
            "process_instance_id": "pi_12345",
            "process_status": "running", # oder "completed"
            "next_tasks": [
                {
                    "id": "task_abc123",
                    "name": "Bewerbung prüfen",
                    "assignee": null
                }
            ]
        }
    """
    try:
        res = _svc().get_process_status(process_instance_id)
        return res.model_dump()
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Fehler beim Abrufen des Prozess-Status: {e}"
        }

@tool
def complete_task(process_instance_id: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Vervollständigt den nächsten offenen User Task einer Prozessinstanz.
    Automatische Auswahl des ersten verfügbaren Tasks.
    
    Args:
        process_instance_id: Die ID der Prozessinstanz
        variables: Optionale zusätzliche Variablen für die Task-Vervollständigung
        
    Returns:
        Dictionary mit Completion-Status und verbleibenden Tasks
        
    Beispiel Aufruf ohne zusätzliche Variablen:
        complete_task(process_instance_id="pi_12345")
        
    Beispiel Aufruf mit zusätzlichen Variablen:
        complete_task(
            process_instance_id="pi_12345",
            variables={
                "approval_status": "approved",
                "reviewer_comment": "Bewerbung ist vollständig und qualifiziert"
            }
        )
        
    Erfolgreiche Antwort:
        {
            "success": True,
            "message": "Completed task Bewerbung prüfen",
            "process_instance_id": "pi_12345",
            "process_status": "running", # oder "completed" wenn Prozess beendet
            "next_tasks": [...] # Verbleibende offene Tasks
        }
        
    Bei Fehlern:
        {
            "success": False,
            "message": "No open user tasks"
        }
    """
    try:
        res = _svc().complete_next_task(process_instance_id, variables)
        return res.model_dump()
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Fehler beim Vervollständigen der Task: {e}"
        }

def get_process_automation_tools() -> List:
    """Factory function to get all process automation tools for compatibility with react_agent.py"""
    return [
        discover_processes,
        start_process,
        get_process_status,
        complete_task
    ]
