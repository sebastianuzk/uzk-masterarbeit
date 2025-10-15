
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
    Zeigt alle verfügbaren BPMN-Prozesse und deren Eigenschaften an.
    
    Returns:
        Dictionary mit verfügbaren Prozessen und deren Details
        
    Beispiel Antwort:
        {
            "processes": [
                {
                    "key": "bewerbung_process", 
                    "name": "Universitäts-Bewerbungsprozess",
                    "version": 1
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
    Startet einen Prozess in Camunda mit den gegebenen Variablen.
    
    Args:
        process_key: Der Key des BPMN-Prozesses (z.B. "bewerbung_process")
        variables: Dictionary mit Prozessvariablen (z.B. {"student_name": "Max", "studiengang": "Informatik"})
    
    Returns:
        Dictionary mit Prozess-Details und Status
        
    Beispiel:
        start_process("bewerbung_process", {"student_name": "Pascal", "studiengang": "Informatik"})
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
    Zeigt den Status einer laufenden Prozessinstanz und offene Tasks an.
    
    Args:
        process_instance_id: Die ID der Prozessinstanz
        
    Returns:
        Dictionary mit Prozess-Status und offenen Tasks
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
    
    Args:
        process_instance_id: Die ID der Prozessinstanz
        variables: Optionale zusätzliche Variablen für die Task-Completion
        
    Returns:
        Dictionary mit Completion-Status
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
