"""
Universal Process Automation Tool für Camunda BPM
Ermöglicht dynamische Prozessinteraktion ohne hardcodierte Logik
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool

from config.settings import settings
from src.camunda_integration.client.camunda_client import CamundaClient


@dataclass
class ProcessInfo:
    """Information über einen verfügbaren Prozess"""
    key: str
    name: str
    version: int
    definition_id: str
    form_fields: List[Dict[str, Any]]
    required_fields: List[str]


@dataclass
class ProcessResult:
    """Ergebnis einer Prozessoperation"""
    success: bool
    message: str
    process_instance_id: Optional[str] = None
    next_tasks: List[Dict[str, Any]] = None
    process_status: str = "unknown"  # active, completed, failed


class UniversalProcessTool:
    """
    Universelles Tool für Camunda Process Automation
    
    Ermöglicht dynamische Prozessinteraktion ohne hardcodierte Logik.
    """
    
    def __init__(self, camunda_base_url: str = None):
        base_url = camunda_base_url or settings.CAMUNDA_BASE_URL
        self.client = CamundaClient(base_url)
        self.logger = logging.getLogger(__name__)
    
    def discover_processes(self, filter_name: Optional[str] = None) -> List[ProcessInfo]:
        """
        Entdeckt verfügbare Prozesse zur Laufzeit
        
        Args:
            filter_name: Optionaler Filter für Prozessnamen
            
        Returns:
            Liste verfügbarer Prozesse mit Metadaten
        """
        try:
            process_definitions = self.client.get_process_definitions()
            processes = []
            
            for definition in process_definitions:
                # Filter anwenden
                if filter_name and filter_name.lower() not in definition.name.lower():
                    continue
                
                # Form Fields analysieren - VOLLSTÄNDIG DYNAMISCH
                form_fields = []
                required_fields = []
                
                try:
                    # Versuche Start Event Forms aus BPMN XML zu extrahieren
                    form_key = getattr(definition, 'form_key', None)
                    if form_key:
                        # Wenn Form Key existiert, versuche Metadaten zu laden
                        # TODO: Implementiere BPMN XML Parsing für echte Form-Extraktion
                        pass
                    
                    # Fallback: Keine hardcodierte Logik - leer lassen
                    # Der Chatbot muss dynamisch nachfragen welche Daten benötigt werden
                    form_fields = []
                    required_fields = []
                
                except Exception as e:
                    self.logger.warning(f"Could not analyze form for process {definition.key}: {e}")
                    # Bei Fehlern: leer lassen, keine Annahmen treffen
                    form_fields = []
                    required_fields = []
                
                processes.append(ProcessInfo(
                    key=definition.key,
                    name=definition.name,
                    version=definition.version,
                    definition_id=definition.id,
                    form_fields=form_fields,
                    required_fields=required_fields
                ))
            
            return processes
            
        except Exception as e:
            self.logger.error(f"Error discovering processes: {e}")
            return []
    
    def start_process(self, process_key: str, variables: Dict[str, Any]) -> ProcessResult:
        """
        Startet einen Prozess dynamisch
        
        Args:
            process_key: Schlüssel des Prozesses
            variables: Variables für den Prozessstart
            
        Returns:
            ProcessResult mit Status und Details
        """
        try:
            # Validierung (vereinfacht)
            if not process_key:
                return ProcessResult(
                    success=False,
                    message="ERROR: Process key is required"
                )
            
            if not variables:
                return ProcessResult(
                    success=False,
                    message="ERROR: Variables are required"
                )
            
            # Prozess starten
            instance = self.client.start_process(process_key, variables)
            
            if not instance:
                return ProcessResult(
                    success=False,
                    message=f"ERROR: Failed to start process '{process_key}'"
                )
            
            # Nächste Tasks ermitteln
            next_tasks = []
            try:
                tasks = self.client.get_tasks(process_instance_id=instance.id)
                next_tasks = [
                    {
                        "id": task.id,
                        "name": task.name,
                        "assignee": task.assignee
                    } for task in tasks
                ]
            except:
                pass
            
            return ProcessResult(
                success=True,
                message=f"SUCCESS: Process '{process_key}' started successfully",
                process_instance_id=instance.id,
                next_tasks=next_tasks,
                process_status="active"
            )
            
        except Exception as e:
            self.logger.error(f"Error starting process {process_key}: {e}")
            return ProcessResult(
                success=False,
                message=f"ERROR: Error starting process: {str(e)}"
            )
    
    def complete_next_task(self, process_instance_id: str, 
                          variables: Optional[Dict[str, Any]] = None) -> ProcessResult:
        """
        Führt den nächsten User Task einer Prozessinstanz aus
        
        Args:
            process_instance_id: ID der Prozessinstanz
            variables: Zusätzliche Variables für Task
            
        Returns:
            ProcessResult mit Ausführungsstatus
        """
        try:
            # Finde Tasks für diese Prozessinstanz
            tasks = self.client.get_tasks(process_instance_id=process_instance_id)
            
            if not tasks:
                return ProcessResult(
                    success=False,
                    message=f"ERROR: No tasks found for process instance {process_instance_id}",
                    process_instance_id=process_instance_id,
                    process_status="completed"
                )
            
            # Nimm ersten Task
            task = tasks[0]
            
            # Task claimen (optional)
            try:
                self.client.claim_task(task.id, "chatbot")
            except:
                pass  # Claiming ist nicht kritisch
            
            # Task abschließen
            task_variables = variables or {}
            self.client.complete_task(task.id, task_variables)
            
            # Kurz warten und Status prüfen
            time.sleep(0.5)
            
            # Neue Tasks prüfen
            remaining_tasks = self.client.get_tasks(process_instance_id=process_instance_id)
            next_tasks = [
                {
                    "id": t.id,
                    "name": t.name,
                    "assignee": t.assignee
                } for t in remaining_tasks
            ]
            
            # Process Status bestimmen
            process_status = "active" if remaining_tasks else "completed"
            
            variables_msg = f" with variables: {task_variables}" if task_variables else ""
            
            return ProcessResult(
                success=True,
                message=f"SUCCESS: Task '{task.name}' completed{variables_msg}",
                process_instance_id=process_instance_id,
                next_tasks=next_tasks,
                process_status=process_status
            )
            
        except Exception as e:
            self.logger.error(f"Error completing task for process {process_instance_id}: {e}")
            return ProcessResult(
                success=False,
                message=f"ERROR: Error completing task: {str(e)}",
                process_instance_id=process_instance_id
            )
    
    def get_process_status(self, process_instance_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Ermittelt Prozessstatus
        
        Args:
            process_instance_id: Spezifische Instance oder None für alle
            
        Returns:
            Dictionary mit Statusinformationen
        """
        try:
            status = {
                "active_instances": 0,
                "active_tasks": 0,
                "processes": []
            }
            
            # Aktive Instanzen
            instances = self.client.get_process_instances()
            status["active_instances"] = len(instances)
            
            # Aktive Tasks
            tasks = self.client.get_tasks()
            status["active_tasks"] = len(tasks)
            
            # Spezifische Instance
            if process_instance_id:
                instance_tasks = [t for t in tasks if t.process_instance_id == process_instance_id]
                instance_info = {
                    "process_instance_id": process_instance_id,
                    "active_tasks": len(instance_tasks),
                    "tasks": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "assignee": t.assignee
                        } for t in instance_tasks
                    ]
                }
                status["current_instance"] = instance_info
            
            # Alle Prozesse (begrenzt auf letzte 5)
            for instance in instances[:5]:
                instance_tasks = [t for t in tasks if t.process_instance_id == instance.id]
                status["processes"].append({
                    "instance_id": instance.id,
                    "definition_id": instance.definition_id,
                    "business_key": instance.business_key,
                    "active_tasks": len(instance_tasks)
                })
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting process status: {e}")
            return {"error": str(e)}


# Global tool instance
_process_tool = None

def get_process_tool():
    """Get or create global process tool instance"""
    global _process_tool
    if _process_tool is None:
        _process_tool = UniversalProcessTool()
    return _process_tool


# LangChain Tool Definitions using @tool decorator

@tool
def discover_processes(filter_name: str = "") -> str:
    """Entdecke verfügbare Geschäftsprozesse in der Process Engine.
    Verwende dieses Tool wenn ein Benutzer nach verfügbaren Prozessen fragt oder wissen möchte welche Prozesse gestartet werden können.
    WICHTIG: Rufe dieses Tool AUTOMATISCH auf wenn jemand sich bewerben, einschreiben oder einen Antrag stellen möchte!
    
    Args:
        filter_name: Optionaler Filter um nach spezifischen Prozessnamen zu suchen (z.B. "bewerbung")
    
    Returns:
        Liste aller verfügbaren Prozesse. Benötigte Felder werden später automatisch durch den Form-Validator ermittelt.
    """
    tool_instance = get_process_tool()
    filter_value = filter_name.strip() if filter_name else None
    processes = tool_instance.discover_processes(filter_value)
    
    if not processes:
        return "No processes found in the process engine."
    
    result = "Available Processes:\n\n"
    for process in processes:
        result += f"- **{process.name}** (Key: {process.key})\n"
        result += f"   Version: {process.version}\n"
        
        if process.required_fields:
            result += f"   Required fields: {', '.join(process.required_fields)}\n"
        
        if process.form_fields:
            result += "   Form fields:\n"
            for field in process.form_fields:
                required = " (required)" if field.get("required") else " (optional)"
                result += f"      - {field['label']}{required}\n"
        
        result += "\n"
    
    return result


@tool
def start_process(process_key: str, variables: str) -> str:
    """Starte einen Geschäftsprozess mit den angegebenen Variablen.
    Verwende dieses Tool wenn ein Benutzer einen spezifischen Prozess starten möchte (z.B. Bewerbung, Einschreibung, Antrag).
    WICHTIG: Sammle die grundlegenden Daten vom Benutzer. Der Form-Validator wird automatisch die BPMN-Definition prüfen und alle erforderlichen Felder validieren.
    
    Args:
        process_key: Der Schlüssel/Identifier des zu startenden Prozesses (z.B. 'bewerbung_process')
        variables: JSON-String mit den verfügbaren Variablen (z.B. '{"student_name": "Max Mustermann", "studiengang": "Informatik"}')
    
    Returns:
        Prozessstart-Ergebnis mit Instanz-ID und nächsten Schritten. Fehlende oder ungültige Felder werden automatisch erkannt.
    """
    tool_instance = get_process_tool()
    
    try:
        # Parse variables JSON
        vars_dict = json.loads(variables) if isinstance(variables, str) else variables
    except json.JSONDecodeError:
        return "ERROR: Invalid variables format. Please provide valid JSON."
    
    result = tool_instance.start_process(process_key, vars_dict)
    
    response = result.message
    
    if result.success:
        response += f"\n\nProcess Instance ID: {result.process_instance_id}"
        
        if result.next_tasks:
            response += "\n\nNext Tasks:"
            for task in result.next_tasks:
                assignee = f" (assigned to: {task['assignee']})" if task['assignee'] else ""
                response += f"\n   - {task['name']}{assignee}"
        else:
            response += "\n\nProcess completed automatically (no user tasks required)"
    
    return response


@tool
def complete_task(process_instance_id: str, variables: str = "{}") -> str:
    """Schließe die nächste Benutzer-Aufgabe einer laufenden Prozessinstanz ab.
    Verwende dieses Tool wenn ein Benutzer zusätzliche Informationen bereitstellen oder einen Schritt in einem laufenden Prozess abschließen möchte.
    WICHTIG: Verwende dieses Tool um Prozesse voranzutreiben wenn der Benutzer weitere Daten liefert!
    
    Args:
        process_instance_id: Die ID der Prozessinstanz (wird von start_process zurückgegeben)
        variables: Optionale zusätzliche Variablen/Daten für die Aufgabe (als JSON-String, z.B. '{"zusatz_info": "Weitere Details"}')
    
    Returns:
        Aufgaben-Abschluss-Ergebnis und Prozessstatus
    """
    tool_instance = get_process_tool()
    
    try:
        # Parse variables JSON
        vars_dict = json.loads(variables) if variables and variables != "{}" else None
    except json.JSONDecodeError:
        return "ERROR: Invalid variables format. Please provide valid JSON."
    
    result = tool_instance.complete_next_task(process_instance_id, vars_dict)
    
    response = result.message
    
    if result.success:
        if result.next_tasks:
            response += "\n\nRemaining Tasks:"
            for task in result.next_tasks:
                assignee = f" (assigned to: {task['assignee']})" if task['assignee'] else ""
                response += f"\n   - {task['name']}{assignee}"
        else:
            response += "\n\nProcess completed successfully!"
        
        response += f"\n\nProcess Status: {result.process_status}"
    
    return response


@tool
def get_process_status(process_instance_id: str = "") -> str:
    """Erhalte den aktuellen Status von Prozessen in der Engine.
    Verwende dieses Tool wenn ein Benutzer nach laufenden Prozessen fragt, den Status prüfen möchte oder eine Übersicht benötigt.
    WICHTIG: Verwende dieses Tool um Benutzern Feedback über ihre gestarteten Prozesse zu geben!
    
    Args:
        process_instance_id: Optionale spezifische Prozessinstanz-ID zum Prüfen (leer = alle Prozesse anzeigen)
    
    Returns:
        Aktueller Prozessstatus und aktive Aufgaben
    """
    tool_instance = get_process_tool()
    instance_id = process_instance_id.strip() if process_instance_id else None
    status = tool_instance.get_process_status(instance_id)
    
    if "error" in status:
        return f"ERROR: Error getting process status: {status['error']}"
    
    response = "Process Engine Status:\n\n"
    response += f"- Active Process Instances: {status['active_instances']}\n"
    response += f"- Active Tasks: {status['active_tasks']}\n\n"
    
    if process_instance_id and "current_instance" in status:
        inst = status["current_instance"]
        response += f"Instance {process_instance_id}:\n"
        response += f"   Active Tasks: {inst['active_tasks']}\n"
        
        if inst["tasks"]:
            response += "   Tasks:\n"
            for task in inst["tasks"]:
                assignee = f" (assigned to: {task['assignee']})" if task['assignee'] else ""
                response += f"      - {task['name']}{assignee}\n"
        
        response += "\n"
    
    if status["processes"]:
        response += "Recent Process Instances:\n"
        for proc in status["processes"]:
            business_key = f" ({proc['business_key']})" if proc['business_key'] else ""
            response += f"   - {proc['instance_id']}{business_key} - {proc['active_tasks']} tasks\n"
    
    return response


def get_process_automation_tools():
    """
    Factory-Funktion für alle Process Automation Tools
    
    Returns:
        Liste aller verfügbaren Process Automation Tools
    """
    return [
        discover_processes,
        start_process,
        complete_task,
        get_process_status
    ]