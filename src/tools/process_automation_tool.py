
from __future__ import annotations
from typing import Any, Dict, Optional
from langchain_core.tools import tool

# Global holder wired from your app
_CAMUNDA_SERVICE = None

def set_camunda_service(service):
    global _CAMUNDA_SERVICE
    _CAMUNDA_SERVICE = service

def _svc():
    if _CAMUNDA_SERVICE is None:
        raise RuntimeError("CamundaService not configured. Call set_camunda_service(...)")
    return _CAMUNDA_SERVICE

@tool
def discover_processes() -> Dict[str, Any]:
    """Listet alle verfügbaren Prozesse inkl. erwarteter Pflichtfelder (falls aus BPMN ableitbar)."""
    return _svc().discover_processes()

@tool
def start_process(process_key: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Startet einen Prozess per Key und Variablen (als Objekt). Validiert Pflichtfelder vorab, wenn möglich."""
    res = _svc().start_process(process_key, variables)
    return res.model_dump()

@tool
def get_process_status(process_instance_id: str) -> Dict[str, Any]:
    """Gibt den Status und offene User Tasks einer Instanz zurück."""
    res = _svc().get_process_status(process_instance_id)
    return res.model_dump()

@tool
def complete_task(process_instance_id: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Vervollständigt den nächsten offenen User Task einer Instanz. Wenn Variablen fehlen, wird need_input=True geliefert."""
    res = _svc().complete_next_task(process_instance_id, variables)
    return res.model_dump()
